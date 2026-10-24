"""D3–D5 canlı bağlantı (application): analizör → öznitelik + sınıflayıcı → APC/ADL kararı → oturuma uygula.

Katman sınırları (docs/ARCHITECTURE.md):
- Karar mantığı SAF: `autoctl` (APC/ADL) + `features` (tonal denge). Bu dosya yalnız zamanlar ve bağlar.
- Ses yolu: ADL düzeltmesi `Session.set_auto_offsets` ile ÜST KATMAN olarak uygulanır → kullanıcının durumu, çalışma
  kopyası ve geçmişi DEĞİŞMEZ (U58). APC `Session.auto_load` ile tarz/profil yükler (geri alınabilir, nav geçmişi).
- Elle dokunuş → `manual()` → APC 10 sn askı (kullanıcı her zaman kazanır).
- Kaynak disiplini: mod kapalıyken analizör aboneliği YOK → yakalama süreci yok (kimse bakmıyorken bedel ödenmez).
  Sınıflayıcı 2 sn'de bir, tek iş parçacığı (ölçüm: 5–10 ms / 2 sn ses, T-L40).
- Tıksızlık: ADL çıkışı 0,5 dB adımlara kuantalanır → yalnız anlamlı değişimde, 1,5 sn A/B geçişle uygulanır (D2/R43)."""
from __future__ import annotations

import json
import math
import os
import threading
import time

import numpy as np

from . import autoctl, console, features

MODES = ("off", "apc", "adl", "both")
MODE_LABELS = {"off": "Kapalı", "apc": "Otomatik profil", "adl": "Canlı uyarlama", "both": "İkisi birden"}

# Makro tür → varsayılan hazır tarz (kullanıcı profiline tür etiketi verirse o öncelikli)
DEFAULT_MAPPING = {"elektronik": "preset:elektronik", "hiphop": "preset:hiphop", "rock": "preset:rock",
                   "pop": "preset:pop", "klasik": "preset:klasik", "caz_akustik": "preset:akustik_caz",
                   "konuşma": "preset:konusma"}
GENRE_LABELS = {"elektronik": "Elektronik", "hiphop": "Hip-hop / R&B", "rock": "Rock / Metal", "pop": "Pop",
                "klasik": "Klasik", "caz_akustik": "Caz / Akustik", "konuşma": "Konuşma"}
# Profil etiketleri serbest metindir → makro türe normalleştir
ALIASES = {"hip-hop": "hiphop", "hip hop": "hiphop", "rap": "hiphop", "r&b": "hiphop", "metal": "rock",
           "caz": "caz_akustik", "jazz": "caz_akustik", "akustik": "caz_akustik", "konusma": "konuşma",
           "podcast": "konuşma", "speech": "konuşma", "electronic": "elektronik", "edm": "elektronik",
           "techno": "elektronik", "classical": "klasik"}

LTAS_TAU_S = 8.0          # parça tonal dengesi: ~8 sn güç-alanı ortalaması (anlık vuruş kararı bozmasın)
REF_MIN_W = 1 / 300       # kişisel referans ~5 dk zaman sabitiyle öğrenilir (senin dinlediğin müziğin ortalaması)
ADL_QUANT = 0.5           # dB — bu kadar değişmeden ses yolu güncellenmez
ADL_HYST = 0.75           # dB — E31: ham değer uygulanandan en az bu kadar uzaklaşmadan yeni geçiş yok (sınır salınımı)
ADL_MIN_S = 5.0           # sn — iki ADL geçişi arası en az süre (1,5 sn geçiş = 125 set-param; ADL yavaş bir uyarlamadır)
CLASSIFY_S = 2.0


def normalize_genre(tag: str) -> str | None:
    """Serbest metin profil etiketini makro türe çevirir ('hip-hop' → 'hiphop'); tanınmazsa None."""
    t = str(tag).strip().lower()
    t = ALIASES.get(t, t)
    return t if t in GENRE_LABELS else None


class AutoEngine:
    """Otomasyon motoru: 1 Hz tick ile analizör anlık görüntüsünü okur, türü/tonal dengeyi çıkarır, APC/ADL kararını Session'a uygular. Durum (mod, öğrenilen referans/bias) `state_path`'e yazılır."""
    def __init__(self, sess, analyzer, classifier=None, clock=time.monotonic, state_path=None, period_s=1.0,
                 autostart=True):
        self.sess, self.an, self.clf, self.clock = sess, analyzer, classifier, clock
        self.state_path, self.period = state_path, period_s
        self.mode, self.sid = "off", None
        self.apc = autoctl.ProfileChanger({})
        self.dyn = autoctl.DynamicEQ({})
        self.ref_n = 0
        self.ltas, self.t_ltas, self.ex, self.level = None, None, None, None
        self.pred, self.t_cls = None, -1e9
        self.applied, self.applied_at = None, float("-inf")
        self.state = "kapalı"
        self.held = None                                   # askı nedeni (ör. "kör test") — None = serbest
        self.errors, self.cls_ms = [], []
        self._dirty, self._t_save = False, 0.0
        self._stop = threading.Event()
        self._load()
        sess.engine = self
        want = self.mode
        self.mode = "off"
        self.set_mode(want)
        self._thread = None
        if autostart:
            self._thread = threading.Thread(target=self._run, name="bta-auto", daemon=True)
            self._thread.start()

    # ── kalıcılık (küçük JSON; istek yolunda değil, iş parçacığında / flush'ta) ──
    def _load(self):
        if not (self.state_path and os.path.exists(self.state_path)):
            return
        try:
            with open(self.state_path) as f:
                d = json.load(f)
        except (OSError, ValueError):
            return
        self.mode = d.get("mode") if d.get("mode") in MODES else "off"
        self.dyn.bias.update({k: float(v) for k, v in d.get("bias", {}).items() if k in self.dyn.bias})
        self.dyn.ref.update({k: float(v) for k, v in d.get("ref", {}).items() if k in features.REGIONS})
        self.ref_n = int(d.get("ref_n", 0))

    def flush(self):
        """Bekleyen ayar değişikliğini (mod, bias, referans) atomik olarak diske yazar; değişiklik yoksa no-op."""
        if not (self.state_path and self._dirty):
            return
        d = {"mode": self.mode, "bias": self.dyn.bias, "ref": self.dyn.ref, "ref_n": self.ref_n,
             "saved_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        os.makedirs(os.path.dirname(self.state_path) or ".", exist_ok=True)
        tmp = self.state_path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.state_path)
        self._dirty, self._t_save = False, self.clock()

    # ── kontrol ──
    def set_mode(self, mode):
        """Modu değiştirir (off|apc|adl|both): analizör aboneliğini açar/kapatır, ADL dışı modda katmanı kaldırır. Geçersiz modda ValueError."""
        if mode not in MODES:
            raise ValueError(f"geçersiz mod: {mode} (geçerli: {', '.join(MODES)})")
        prev, self.mode = self.mode, mode
        if mode != "off" and self.sid is None and self.an is not None:
            self.sid = self.an.subscribe(kind="auto")
        if mode == "off" and self.sid is not None:
            self.an.unsubscribe(self.sid)
            self.sid = None
        if mode in ("off", "apc") and self.sess.auto_offsets is not None:
            self.sess.set_auto_offsets(None)
            self.applied, self.applied_at = None, float("-inf")
        if mode not in ("apc", "both"):
            self.apc.current = None
        self.state = "kapalı" if mode == "off" else "dinliyor"
        if prev != mode:
            self._dirty = True
        return self.status()

    def configure(self, body: dict):
        """/api/auto gövdesi: {mode?, nudge?: {band, delta}, reset_learning?} → status()."""
        if "mode" in body:
            self.set_mode(body["mode"])
        nd = body.get("nudge")
        if nd:
            band = nd.get("band")
            if band not in self.dyn.bias:
                raise ValueError(f"bilinmeyen bant: {band}")
            self.dyn.manual(band, max(-6.0, min(6.0, float(nd.get("delta", 0)))))
            self._dirty = True
        if body.get("reset_learning"):
            self.dyn.bias = {k: 0.0 for k in self.dyn.bias}
            self.dyn.ref, self.ref_n = {}, 0
            self._dirty = True
        return self.status()

    def hold(self, reason: str):
        """Otomasyonu açıkça askıya al (kör test gibi): release() çağrılana dek karar verilmez, katman korunur."""
        self.held = reason

    def release(self):
        """hold()'u kaldır."""
        self.held = None

    def manual(self):
        """Kullanıcı elle dokundu (oturum çağırır) → APC askıya alınır; kullanıcının seçimi otomasyonu ezer."""
        self.apc.manual(self.clock())

    def mapping(self) -> dict:
        """Tür → hedef eşlemesi: varsayılan hazır tarzlar, üzerine tür etiketli kullanıcı profilleri ('profile:<id>')."""
        m = dict(DEFAULT_MAPPING)
        for p in self.sess.store.list():
            for g in p.get("genres") or []:
                k = normalize_genre(g)
                if k and not m.get(k, "").startswith("profile:"):
                    m[k] = "profile:" + p["id"]
        return m

    # ── bir adım (test edilebilir; iş parçacığı bunu periyodik çağırır) ──
    def tick(self):
        """Tek adım (test edilebilir): sessizlikte karar yok; LTAS (τ 8 sn) + sınıflama (2 sn'de bir) → APC yükleme / ADL katmanı (0,5 dB kuantalı)."""
        now = self.clock()
        if self.mode == "off" or self.an is None:
            return
        self.sess.last = self.sess.clock()                # otomasyon = etkinlik (askıdayken de)
        if self.held:
            self.state = "askıda"
            return                # otomasyon = etkinlik (sayfa kapalıyken sunucu boşta kapanmaz)
        s = self.an.snapshot("pre", CLASSIFY_S)
        if not s or not s.get("signal"):
            self.state = "sessizlik"
            self.t_ltas = None
            return
        self.state = "dinliyor"
        p = 10 ** (np.asarray(s["bands"], float) / 10)
        dt = self.period if self.t_ltas is None else max(0.0, now - self.t_ltas)
        a = 1 - math.exp(-dt / LTAS_TAU_S)
        self.ltas = p if (self.ltas is None or self.t_ltas is None) else self.ltas + a * (p - self.ltas)
        self.t_ltas = now
        self.ex = features.region_excess((10 * np.log10(np.maximum(self.ltas, 1e-30))).tolist(), s["centers"])
        self.level = s.get("level_db")
        macro = None
        if self.clf is not None and getattr(self.clf, "available", False) and now - self.t_cls >= CLASSIFY_S \
                and s.get("audio") is not None:
            t0 = time.perf_counter()
            pred = self.clf.predict(s["audio"])
            self.cls_ms = (self.cls_ms + [round((time.perf_counter() - t0) * 1000, 1)])[-30:]
            self.t_cls = now
            if pred:
                self.pred, macro = pred, pred["macro"]
        self.apc.mapping = self.mapping()
        genre = self.genre()
        if self.mode in ("apc", "both"):
            target = self.apc.update(macro, now)
            if target:
                self.sess.auto_load(target)
        elif macro:
            self.apc._smooth(macro, now)                  # yalnız ADL'de de tür tahmini canlı kalsın
        if self.mode in ("adl", "both"):
            if self.ex and genre != "konuşma":
                w = max(1.0 / (self.ref_n + 1), REF_MIN_W)
                self.dyn.learn_reference(self.ex, weight=w)
                self.ref_n += 1
                if self.ref_n % 60 == 0:
                    self._dirty = True
            off = self.dyn.step(self.ex, genre, self.level, now)
            q = {k: round(v / ADL_QUANT) * ADL_QUANT for k, v in off.items()}
            if q != self.applied and self._adl_due(off, q, now):
                self.applied, self.applied_at = q, now
                self.sess.set_auto_offsets(q)

    def _adl_due(self, raw, q, now) -> bool:
        """U73: ilk uygulama ve sıfıra dönüş (konuşma/sessizlik) hemen; diğerleri histerezis + en az bekleme."""
        if self.applied is None or all(v == 0 for v in q.values()):
            return True
        moved = max(abs(raw[k] - self.applied.get(k, 0.0)) for k in raw)
        return moved >= ADL_HYST and now - self.applied_at >= ADL_MIN_S

    def genre(self):
        """EMA'sı güven eşiğini (0,3) aşan en olası makro tür; yoksa None."""
        if not self.apc.ema:
            return None
        best = max(self.apc.ema, key=self.apc.ema.get)
        return best if self.apc.ema[best] >= self.apc.cfg["conf_min"] else None

    def status(self) -> dict:
        """Arayüz/API durumu: mod, sınıflayıcı, tür skorları, karakter, enstrümanlar, ADL katmanı, bias, eşleme, geçiş günlüğü."""
        now = self.clock()
        top = sorted(self.apc.ema.items(), key=lambda kv: -kv[1])[:4]
        free = sum(1 for b in self.sess.state["bands"] if not b.get("enabled"))
        return {"mode": self.mode, "modes": [{"id": m, "label": MODE_LABELS[m]} for m in MODES],
                "classifier": {"available": bool(self.clf is not None and getattr(self.clf, "available", False)),
                               "reason": getattr(self.clf, "reason", "sınıflayıcı yok") if self.clf is not None else "sınıflayıcı yok",
                               "ms": (sorted(self.cls_ms)[len(self.cls_ms) // 2] if self.cls_ms else None)},
                "state": self.state, "held": self.held, "genre": self.genre(),
                "genre_label": GENRE_LABELS.get(self.genre() or "", None),
                "scores": [{"id": k, "label": GENRE_LABELS.get(k, k), "p": round(v, 3)} for k, v in top],
                "music": (self.pred or {}).get("music"),
                "instruments": (self.pred or {}).get("instruments", []) if self.state == "dinliyor" else [],
                "character": features.character(self.ex) if self.state == "dinliyor" else [],
                "excess": self.ex, "level_db": self.level, "offsets": self.sess.auto_offsets,
                "bias": {k: round(v, 3) for k, v in self.dyn.bias.items()}, "learned_s": self.ref_n,
                "mapping": self.mapping(), "log": self.apc.log[-8:],
                "paused_s": round(max(0.0, self.apc.paused_until - now), 1),
                "free_slots": free, "slots_needed": len(autoctl.ADL_BANDS),
                "errors": self.errors[-3:]}

    # ── iş parçacığı ──
    def _run(self):
        while not self._stop.wait(self.period):
            try:
                self.tick()
                if self._dirty and self.clock() - self._t_save >= 5.0:
                    self.flush()
            except Exception as e:                       # otomasyon asla sunucuyu düşürmez; hata görünür
                self.errors = (self.errors + [f"{type(e).__name__}: {e}"[:200]])[-10:]

    def close(self, clear=False):
        """clear=True (sunucu kapanışı): ADL katmanını sesten kaldır — motor yokken donmuş bir düzeltme kalmasın.
        Mod diske yazılıdır → sunucu yeniden açılınca otomasyon kaldığı yerden sürer."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
        if self.sid is not None and self.an is not None:
            self.an.unsubscribe(self.sid)
            self.sid = None
        if clear and self.sess.auto_offsets is not None:
            self.sess.set_auto_offsets(None)
        try:
            self.flush()
        except OSError:
            pass
