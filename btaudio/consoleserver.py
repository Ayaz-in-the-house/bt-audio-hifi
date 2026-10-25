"""F9 — Profesyonel konsolun yerel sunucusu (yalnız 127.0.0.1). Tam durum PUT edilir → sanitize → canlı uygula.
Kullanıcı profilleri repo DIŞINDA (`paths.profiles_dir()`, C0); dışa/içe aktarma ile paylaşılır."""
from __future__ import annotations

import json
import os
import re
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import abxsession, autoctl, console, history, journal, paths, profiles
from .tunerserver import PwApplier

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = os.path.join(ROOT, "tools", "console.html")
ADMIN_PAGE = os.path.join(ROOT, "tools", "admin.html")
BUNDLE_SCHEMA = "bta-bundle/1"
NODE = "effect_input.bta_console"
# U86: arayüz dili dosyaları — TAM YOL izin listesi (dosya sistemi yolu açılmaz, U36)
I18N_FILES = {"/i18n/en.json": ("en.json", "application/json; charset=utf-8"),
              "/i18n/tr.json": ("tr.json", "application/json; charset=utf-8"),
              "/i18n/i18n.js": ("i18n.js", "text/javascript; charset=utf-8")}
I18N_DIR = os.path.join(ROOT, "tools", "i18n")

# U85: sunucu iletilerinin İngilizcesi. Makine alanı `error` (TR) DEĞİŞMEZ; yanıta `error_en` eklenir, metni istemci
# dile göre seçer (karar: docs/ARCHITECTURE.md → Arayüz dili). Desen = tam ileti; {0}… = yakalanan parçalar
# (`*` önekli parça yeniden çevrilir: iç içe ileti). Yeni bir Türkçe raise iletisi eklenirse test_i18n U85 kırmızı olur.
ERRORS_EN = [
    (r"yasak host", "Forbidden host"),
    (r"application/json gerekli", "Content-Type must be application/json"),
    (r"istek çok büyük \(> (\d+) KB\)", "Request too large (over {0} KB)"),
    (r"geçersiz JSON: (.*)", "Invalid JSON: {*0}"),
    (r"JSON nesnesi bekleniyor", "Expected a JSON object"),
    (r"profil yok", "Profile not found"),
    (r"yok", "Not found"),
    (r"bulunamadı / eksik alan: (.*)", "Not found or missing field: {*0}"),
    (r"'sürüm (\d+)'", "'version {0}'"),
    (r"sürüm (\d+)", "version {0}"),
    (r"loud_db sayı olmalı", "loud_db must be a number"),
    (r"çalışma kopyasının yazılabilecek bir ana profili yok", "This working copy has no parent profile to save into"),
    (r"bu oturumda ton çalınamıyor \(kulaklık yok\)", "Test tones aren't available in this session (no headphones)"),
    (r"kör test bu oturumda yok", "The blind test isn't available in this session"),
    (r"kayıt yapılamıyor \(konsol kulaklığa bağlı değil\)", "Can't record: the console isn't connected to headphones"),
    (r"hazır klip yok", "No built-in clip available"),
    (r"kilitli \(ana\) profilin sürüm geçmişi yok — yalnız çalışma kopyaları \(Özel N\) sürüm tutar",
     "Saved profiles are locked and have no version history — only working copies (Custom N) keep versions"),
    (r"paket şeması tanınmadı \(beklenen (.+)\)", "Unrecognised bundle schema (expected {0})"),
    (r"otomasyon motoru bu oturumda yok", "Auto mode isn't available in this session"),
    (r"profil adı boş", "Profile name can't be empty"),
    (r"profil JSON nesnesi değil", "The profile isn't a JSON object"),
    (r"desteklenmeyen şema: (.*)", "Unsupported schema: {0}"),
    (r"profilde 'state' yok", "The profile has no 'state' field"),
    (r"profil durumu bozuk: (.*)", "The profile's settings are corrupt: {*0}"),
    (r"klip seviyesi (\S+) dBFS — müzik çalmıyor ya da çok kısık",
     "Clip level is {0} dBFS — nothing is playing, or it's too quiet"),
    (r"test zaten sürüyor", "A test is already running"),
    (r"önce test klibi seç", "Pick a test clip first"),
    (r"test başlamadı", "The test hasn't started"),
    (r"bir çalma sürüyor", "Playback is still running"),
    (r"codec (\S+) etkinleşmedi", "Codec {0} didn't switch on"),
    (r"çalma bitmeden cevap verilemez", "Wait for playback to finish before answering"),
    (r"önce X'i dinle", "Listen to X first"),
    (r"fark kanıtlanmadan tercih sorulmaz", "A preference is only asked for once a difference is proven"),
    (r"test bitmedi", "The test isn't finished"),
    (r"geçersiz mod: (\S+) \(geçerli: (.*)\)", "Invalid mode: {0} (valid: {1})"),
    (r"bilinmeyen bant: (.*)", "Unknown band: {0}"),
    (r"(\S+) bant bekleniyor, (\S+) geldi", "Expected {0} bands, got {1}"),
    (r"bilinmeyen filtre tipi: (.*)", "Unknown filter type: {0}"),
    (r"güvensiz smart filter hedefi: (.*)", "Unsafe smart filter target: {0}"),
    (r"sınıflayıcı yok", "No classifier loaded"),
    (r"model yok/doğrulanamadı: (.*) — `bta model fetch`", "Model missing or unverified: {0} — run `bta model fetch`"),
    (r"(.+): sha256 uyuşmuyor — reddedildi", "{0}: sha256 mismatch — rejected"),
    (r"ISO 226 tablo frekansı değil: (.*)", "Not an ISO 226 table frequency: {0}"),
]
_ERRORS_EN = [(re.compile(rx + r"\Z", re.S), en) for rx, en in ERRORS_EN]


def error_en(msg):
    """Sunucu iletisinin İngilizcesi (U85). Tanınmayan ileti olduğu gibi döner (istemci TR metnini gösterir)."""
    if not isinstance(msg, str):
        return msg
    for rx, en in _ERRORS_EN:
        m = rx.match(msg)
        if m:
            return re.sub(r"\{(\*?)(\d)\}", lambda g: error_en(m.group(int(g.group(2)) + 1)) if g.group(1)
                          else m.group(int(g.group(2)) + 1), en)
    return msg


class Session:
    """Canlı konsol oturumu (application katmanı): tek durum sahibi.

    D1 kuralları: hazır tarzlar ve KİLİTLİ profiller hiç değişmez → üzerlerinde ilk elle dokunuş otomatik "Özel N"
    çalışma kopyası açar; çalışma kopyası her değişiklikte ARKA PLANDA kaydedilir (istek yolu diske dokunmaz) ve
    profil başına kalıcı geri/ileri al geçmişi tutulur (sunucu yeniden başlasa da)."""

    def __init__(self, applier, on_commit, initial=None, idle_timeout_s=3600, profiles_dir=None, analyzer=None,
                 device=None, writer=None, clock=time.time, tone_player=None):
        self.applier, self.on_commit = applier, on_commit
        self.state = console.sanitize(initial or console.default_state())
        self.bypass, self.committed, self.last = False, None, clock()
        self.idle_timeout_s = idle_timeout_s
        # günlük yeri: profil dizini açıkça verildiyse onun yanında (testler gerçek XDG'ye yazmaz), yoksa XDG
        self.writer = writer if writer is not None else journal.Writer(
            os.path.join(profiles_dir, ".journal") if profiles_dir else paths.journal_dir())
        self.store = profiles.ProfileStore(profiles_dir or paths.profiles_dir(), writer=self.writer)
        self.loud_file = os.path.join(profiles_dir, ".loudness.json") if profiles_dir else console.loud_path()   # U78
        self.active, self.baseline = None, None           # {"kind": "profile"|"preset", "id", "name", ...}
        self.default_json = json.dumps(self.state, sort_keys=True)   # açılışta kurulu olan (son "açılışta kullan")
        self.hist = None                                  # aktif çalışma kopyasının geçmişi
        self.nav, self.nav_redo = [], []                  # tarz/profil yükleme geçmişi (yanlış tıklama geri alınır)
        self.analyzer, self.device = analyzer, device
        self.clock = clock
        self.lock = threading.Lock()
        self.engine = None                                # D3–D5 otomasyon motoru (autoengine.AutoEngine kendini bağlar)
        self.tone_player = tone_player                    # D7.3 oturma testi tonu (None → çalamaz)
        self.tone, self._tone_h, self._tone_prev, self._tone_timer = None, None, None, None
        self.abx = None                                   # PRD-BTA05 E1 kör test (cli bağlar)
        self.abx_clip, self.abx_recorder, self.abx_default_clip, self.abx_env = None, None, None, None
        self.auto_offsets = None                          # ADL üst katmanı: sese eklenir, kullanıcı durumuna YAZILMAZ

    # ── yardımcılar ──
    def _effective(self):
        """Sese giden durum = kullanıcının durumu + (varsa) ADL üst katmanı (boş bant yuvalarına)."""
        return autoctl.apply_offsets(self.state, self.auto_offsets) if self.auto_offsets else self.state

    def _apply(self, fade_s=None):
        """Crossfader varsa tıksız A/B geçiş (D2, istek yolunu bloklamaz); yoksa doğrudan yük (testlerdeki sahte)."""
        st = self._effective()
        if hasattr(self.applier, "apply_state"):
            self.applier.apply_state(st, bypass=self.bypass, fade_s=fade_s)
        else:
            self.applier.apply_payload(console.pw_params(st, bypass=self.bypass))
        self.last = self.clock()

    def set_loud(self, db):
        """U78 ses yükseltme: ayarı yazar + sınırlayıcıya canlı uygular (A/B geçişi gerekmez, tek kazanç)."""
        if isinstance(db, bool) or not isinstance(db, (int, float)):
            raise TypeError("loud_db sayı olmalı")
        with self.lock:
            v = console.save_loud_db(db, self.loud_file)
            self.applier.apply_payload(console.loud_payload(v))
        return self.view()

    def _user_touch(self):
        if self.engine is not None:
            self.engine.manual()

    # ── otomasyon yolu (D4/D5): uzun geçiş, kullanıcı dokunuşu SAYILMAZ ──
    def set_auto_offsets(self, offsets, fade_s=1.5):
        """ADL üst katmanını ayarlar/kaldırır (None) ve 1,5 sn geçişle uygular; kullanıcının durumuna/geçmişine YAZMAZ."""
        with self.lock:
            self.auto_offsets = dict(offsets) if offsets else None
            self._apply(fade_s=fade_s)
        return self.view()

    def auto_load(self, target, fade_s=1.5):
        """APC hedefi: "preset:<id>" | "profile:<id>". Geri alınabilir (nav geçmişi); çalışma kopyası kayıtlı kalır."""
        kind, _, tid = str(target).partition(":")
        if kind == "preset" and tid in console.PRESETS and console.PRESETS[tid]["group"] != "Uzay":
            with self.lock:
                self._nav_push()
                self.state = console.apply_preset(self.state, tid)
                self._apply(fade_s=fade_s)
                self.hist = None
                self._mark("preset", tid, console.PRESETS[tid]["label"], {"by": "auto"})
            return True
        if kind == "profile" and self.store.exists(tid):
            self._load_profile(tid, fade_s=fade_s, extra={"by": "auto"})
            return True
        return False

    def _mark(self, kind, pid, name, extra=None):
        self.active = {"kind": kind, "id": pid, "name": name, **(extra or {})}
        self.baseline = json.dumps(self.state, sort_keys=True)

    def _writable(self):
        """Aktif profil otomatik kaydedilebilir mi (kilitsiz çalışma kopyası)?"""
        return bool(self.active and self.active["kind"] == "profile" and not self.active.get("locked", True))

    def _load_history(self, pid):
        h = history.load(self.writer.journal_path(pid))
        cur = self.store.get(pid)["state"]
        if not h.versions or h.current() != cur:          # günlük yoksa/eskiyse dosyadaki hâli son sürüm yap
            ev = h.push(cur, self.clock())
            self.writer.enqueue_lines(pid, ev)
            h.seal()
        return h

    def _fork(self, base_state):
        """Hazır tarz / kilitli profil / kaydedilmemiş ayar üzerinde ilk dokunuş → Özel N (ana kaynak DEĞİŞMEZ)."""
        n = self.store.next_auto_number()
        name = f"Özel {n}"
        src = ({"kind": self.active["kind"], "id": self.active["id"], "name": self.active["name"]}
               if self.active else None)
        pid = self.store.save(name, base_state, meta={"locked": False, "auto": True, "derived_from": src})
        self.store.bump_seq(n)
        self.hist = history.History(merge_s=1.0)
        # yeni çalışma kopyasının günlüğü SIFIRDAN başlar: aynı adda eski bir günlük (silinmiş profil, test artığı)
        # yeniden oynatmaya karışmasın (E21) — v0 satırı tam dizini sıfırlar
        ev = self.hist.push(base_state, self.clock())
        ev[0]["reset"] = True
        self.writer.enqueue_lines(pid, ev)                # v0 = dokunuş öncesi
        self.hist.seal()
        self._mark("profile", pid, name, {"locked": False, "auto": True, "derived_from": src})
        return pid

    def _history_info(self):
        h = self.hist.info() if (self.hist and self._writable()) else {"can_undo": False, "can_redo": False, "ptr": 0, "versions": 0}
        return {**h, "can_undo": h["can_undo"] or bool(self.nav), "can_redo": h["can_redo"] or bool(self.nav_redo)}

    def dirty(self):
        """Kilitli profil/tarz aktifken kaydedilmemiş değişiklik var mı (çalışma kopyası her an kayıtlı → False)."""
        if self._writable():
            return False                                   # çalışma kopyası her an kayıtlı
        return self.baseline is not None and json.dumps(self.state, sort_keys=True) != self.baseline

    def view(self):
        """Arayüzün tam görünümü: durum, eğriler, tarzlar, profiller, geçmiş, kayıt durumu, otomasyon, uyarılar, ton."""
        m = console.stereo_model(self.state, console.GRID, include_preamp=False)
        return {"state": self.state, "bypass": self.bypass, "preamp_db": console.preamp_db(self.state),
                "curve": {"f": [round(f, 1) for f in console.GRID], "L": [round(v, 2) for v in m["LL"].values()],
                          "cross": [round(v, 2) for v in m["LR"].values()], "mono": [round(v, 2) for v in m["mono"].values()]},
                "presets": console.preset_catalog(), "categories": console.CATEGORIES,
                "bs2b": console.BS2B_PRESETS, "types": list(console.dsp.TYPES), "profiles": self.store.list(),
                "active": self.active, "dirty": self.dirty(),
                "is_default": json.dumps(self.state, sort_keys=True) == self.default_json,
                "history": self._history_info(),
                "saved": {"pending": self.writer.pending(), "last_write": self.writer.last_write,
                          "errors": list(self.writer.errors)},
                "limits": {"f": [console.F_MIN, console.F_MAX], "g": [console.G_MIN, console.G_MAX],
                           "q": [console.Q_MIN, console.Q_MAX], "w": [console.W_MIN, console.W_MAX],
                           "fcut": console.BS2B_FCUT, "feed": console.BS2B_FEED},
                "committed": self.committed, "device": self.device,
                "auto_offsets": self.auto_offsets, **self._auto_curve(),
                "warnings": console.protection_warnings(self._effective(), codec=(self.device or {}).get("codec")),
                "tone": self.tone, "can_tone": self.tone_player is not None,
                "loud": {"db": console.load_loud_db(self.loud_file), "max": console.LOUD_MAX_DB},
                "auto": self._auto_status(),
                "analyzer": self.analyzer.info() if self.analyzer else None}

    def auto_view(self):
        """Hafif otomasyon görünümü (1 sn yoklama için): motor durumu, ADL katmanı + eğrisi, aktif profil."""
        return {"auto": self._auto_status(), "auto_offsets": self.auto_offsets,
                **self._auto_curve(), "active": self.active}

    def _auto_status(self):
        """Motor durumu + sınıflayıcı nedeninin İngilizcesi (`classifier.reason_en`, U85)."""
        if not self.engine:
            return None
        st = self.engine.status()
        c = st.get("classifier")
        if isinstance(c, dict) and "reason" in c:
            st["classifier"] = {**c, "reason_en": error_en(c["reason"])}
        return st

    def _auto_curve(self):
        if not self.auto_offsets:
            return {}
        m = console.stereo_model(self._effective(), console.GRID, include_preamp=False)
        return {"curve_auto": [round(v, 2) for v in m["mono"].values()]}

    # ── durum değişikliği ──
    def set_state(self, st, seal=False):
        """Elle düzenleme: kilitli/tarz aktifse Özel N çatalı açar, uygular, geçmişe ve arka plan günlüğe ekler (istek yolu diske yazmaz)."""
        self._user_touch()
        with self.lock:
            new = console.sanitize(st)
            if json.dumps(new, sort_keys=True) == json.dumps(self.state, sort_keys=True):
                return self.view()
            if not self._writable():
                self._fork(self.state)
            self.state = new
            self._apply()
            pid = self.active["id"]
            self.writer.enqueue_lines(pid, self.hist.push(new, self.clock()))
            if seal:
                self.hist.seal()
            self.store.update_state(pid, new)
        return self.view()

    def history_seal(self):
        """Açık geçmiş adımını kapatır (kaydırıcı bırakıldı = bir geri-al adımı)."""
        if self.hist:
            self.hist.seal()
        return self.view()

    def _nav_push(self):
        self.nav.append((json.loads(json.dumps(self.active)) if self.active else None, json.dumps(self.state)))
        self.nav = self.nav[-50:]
        self.nav_redo = []

    def _nav_restore(self, entry):
        active, st = entry
        self.state = console.sanitize(json.loads(st))
        self._apply()
        if active and active["kind"] == "profile" and self.store.exists(active["id"]):
            d = self.store.get(active["id"])
            self._mark("profile", active["id"], d["name"], {"locked": d.get("locked", True), "auto": d.get("auto", False),
                                                          "derived_from": d.get("derived_from")})
            self.hist = None if d.get("locked", True) else self._load_history(active["id"])
        elif active and active["kind"] == "preset":
            self.hist = None
            self._mark("preset", active["id"], active["name"])
        else:
            self.active, self.baseline, self.hist = None, None, None

    def _step(self, fn):
        with self.lock:
            if not (self.hist and self._writable()):
                return self.view()
            st, ev = fn(self.clock())
            if st is None:
                return self.view()
            self.state = console.sanitize(st)
            self._apply()
            pid = self.active["id"]
            self.writer.enqueue_lines(pid, ev)
            self.store.update_state(pid, self.state)
        return self.view()

    def undo(self):
        """Geri al: çalışma kopyası geçmişi, yoksa tarz/profil yükleme (nav) geçmişi."""
        self._user_touch()
        with self.lock:
            use_nav = not (self.hist and self._writable() and self.hist.info()["can_undo"]) and self.nav
            if use_nav:
                self.nav_redo.append((json.loads(json.dumps(self.active)) if self.active else None, json.dumps(self.state)))
                self._nav_restore(self.nav.pop())
                return self.view()
        return self._step(lambda now: self.hist.undo(now))

    def redo(self):
        """İleri al: undo'nun simetriği."""
        self._user_touch()
        with self.lock:
            use_nav = not (self.hist and self._writable() and self.hist.info()["can_redo"]) and self.nav_redo
            if use_nav:
                self.nav.append((json.loads(json.dumps(self.active)) if self.active else None, json.dumps(self.state)))
                self._nav_restore(self.nav_redo.pop())
                return self.view()
        return self._step(lambda now: self.hist.redo(now))

    def set_bypass(self, on):
        """EQ'suz dinleme (A/B): EQ ve uzay kapalı, geçişle."""
        with self.lock:
            self.bypass = bool(on)
            self._apply()
        return self.view()

    def preset(self, pid):
        """Hazır tarz uygular (nav geçmişine işlenir); Uzay tarzları mevcut ayarda düzenleme sayılır."""
        if pid not in console.PRESETS:
            raise KeyError(pid)
        self._user_touch()
        if console.PRESETS[pid]["group"] == "Uzay":      # uzay tarzı = mevcut ayarda DÜZENLEME (EQ korunur, çalışma kopyasına işlenir)
            return self.set_state(console.apply_preset(self.state, pid), seal=True)
        with self.lock:
            self._nav_push()
            self.state = console.apply_preset(self.state, pid)
            self._apply()
            self.hist = None
            self._mark("preset", pid, console.PRESETS[pid]["label"])
        return self.view()

    # ── profiller (C1 + D1) ──
    def save_profile(self, name, overwrite=False, notes=None):
        """Profil olarak kaydet: çalışma kopyası aktifse onu ADLANDIRIP ana (kilitli) profile TERFİ ettirir; değilse
        mevcut durumu yeni kilitli profil olarak kaydeder."""
        if self._writable():
            return self.promote(self.active["id"], name, overwrite=overwrite, notes=notes)
        with self.lock:
            pid = self.store.save(name, self.state, overwrite=overwrite, notes=notes, meta={"locked": True, "auto": False})
            d = self.store.get(pid)
            self.hist = None
            self._mark("profile", pid, d["name"], {"locked": True, "auto": False, "derived_from": d.get("derived_from")})
        return self.view()

    def promote(self, pid, name, overwrite=False, notes=None):
        """Çalışma kopyasını adlandırıp kilitli ana profile terfi ettirir."""
        with self.lock:
            nid = self.store.rename(pid, name, overwrite=overwrite) if profiles.slug(name) != pid else pid
            self.store.set_meta(nid, locked=True, auto=False)
            if notes is not None:
                d = self.store.get(nid)
                self.store.save(d["name"], d["state"], overwrite=True, notes=notes)
            d = self.store.get(nid)
            if self.active and self.active.get("id") == pid:
                self.hist = None
                self._mark("profile", nid, d["name"], {"locked": True, "auto": False, "derived_from": d.get("derived_from")})
        return self.view()

    def apply_to_parent(self):
        """Çalışma kopyasını türediği ANA profile yaz (yalnız açık eylemle — ana profil kendiliğinden değişmez)."""
        with self.lock:
            src = (self.active or {}).get("derived_from")
            if not (self._writable() and src and src.get("kind") == "profile" and self.store.exists(src["id"])):
                raise ValueError("çalışma kopyasının yazılabilecek bir ana profili yok")
            d = self.store.get(src["id"])
            self.store.save(d["name"], self.state, overwrite=True)
            self.hist = None
            self._mark("profile", src["id"], d["name"], {"locked": True, "auto": False, "derived_from": d.get("derived_from")})
        return self.view()

    def load_profile(self, pid):
        """Kullanıcı profili yükler (elle dokunuş sayılır → otomasyon askıya alınır)."""
        self.store.get(pid)
        self._user_touch()
        return self._load_profile(pid)

    def _load_profile(self, pid, fade_s=None, extra=None):
        doc = self.store.get(pid)
        with self.lock:
            self._nav_push()
            self.state = console.sanitize(doc["state"])
            self._apply(fade_s=fade_s)
            locked = doc.get("locked", True)
            self._mark("profile", pid, doc["name"], {"locked": locked, "auto": doc.get("auto", False),
                                                     "derived_from": doc.get("derived_from"), **(extra or {})})
            self.hist = None if locked else self._load_history(pid)
        return self.view()

    def rename_profile(self, pid, name, overwrite=False):
        """Profil adını değiştirir; çalışma kopyasında terfi ile aynı."""
        doc = self.store.get(pid)
        if doc.get("auto"):
            return self.promote(pid, name, overwrite=overwrite)      # çalışma kopyasını adlandırmak = terfi
        nid = self.store.rename(pid, name, overwrite=overwrite)
        if self.active and self.active["kind"] == "profile" and self.active["id"] == pid:
            self.active = {**self.active, "id": nid, "name": self.store.get(nid)["name"]}
        return self.view()

    def set_genres(self, pid, genres):
        """Profile tür etiketleri yazar (APC eşlemesi bunları okur)."""
        self.store.set_meta(pid, genres=[str(g)[:32] for g in genres][:16])
        return self.view()

    def duplicate_profile(self, pid):
        """Profili kopyalar ('(kopya)' ekiyle)."""
        self.store.duplicate(pid)
        return self.view()

    def delete_profile(self, pid):
        """Profili çöp kutusuna taşır; geri yükleme belirteci döner."""
        token = self.store.delete(pid)
        if self.active and self.active["kind"] == "profile" and self.active["id"] == pid:
            self.active, self.baseline, self.hist = None, None, None
        return {**self.view(), "trash": token}

    def restore_profile(self, token):
        """Çöp kutusundaki profili belirteçle geri yükler (ad çakışırsa ek alır)."""
        self.store.restore(token)
        return self.view()

    def import_profile(self, doc, overwrite=False):
        """Tek profil JSON'unu içe aktarır (sanitize, kilitli)."""
        pid = self.store.import_doc(doc, overwrite=overwrite)
        return {**self.view(), "imported": pid}

    # ── D7.3 oturma (seal) testi ──
    TONES = {"bass": 50.0, "ref": 1000.0}
    TONE_DB = -24.0

    def play_tone(self, kind, seconds=4.0):
        """EQ'suz (kulaklığın kendi yanıtı) kısa ton: kulak tıkacı oturması bası belirler (R40). Uygulama kulaktaki sesi
        ÖLÇEMEZ (mikrofon yok) — kullanıcı uçları değiştirip bas tonunun en dolgun duyulduğunu seçer."""
        if kind not in self.TONES:
            raise KeyError(kind)
        if self.tone_player is None:
            raise ValueError("bu oturumda ton çalınamıyor (kulaklık yok)")
        self.stop_tone(restore=False)
        seconds = max(0.2, min(8.0, float(seconds)))
        with self.lock:
            if self._tone_prev is None:
                self._tone_prev = self.bypass
            self.bypass = True
            self._apply(fade_s=0.04)
        self._tone_h = self.tone_player(self.TONES[kind], seconds, self.TONE_DB)
        self.tone = {"kind": kind, "freq": self.TONES[kind], "seconds": seconds, "level_db": self.TONE_DB}
        self._tone_timer = threading.Timer(seconds + 0.15, self.stop_tone)
        self._tone_timer.daemon = True
        self._tone_timer.start()
        return self.view()

    def stop_tone(self, restore=True):
        """Oturma testi tonunu durdurur ve (restore=True) önceki EQ/bypass hâlini geri getirir."""
        t, self._tone_timer = self._tone_timer, None
        if t:
            t.cancel()
        h, self._tone_h = self._tone_h, None
        if h is not None:
            try:
                h.stop()
            except Exception:
                pass
        self.tone = None
        if restore and self._tone_prev is not None:
            with self.lock:
                self.bypass, self._tone_prev = self._tone_prev, None
                self._apply(fade_s=0.04)
        return self.view()

    # ── PRD-BTA05 E1: kör ABX testi ──
    def abx_view(self):
        if self.abx is None:
            return {"available": False}
        env = self.abx_env() if self.abx_env else {}
        st = self.abx.status()
        return {"available": True, **st, "error_en": error_en(st.get("error")), "clip_ready": self.abx_clip,
                "default_clip": bool(self.abx_default_clip), "can_record": self.abx_recorder is not None, **env}

    def abx_clip_from(self, source):
        """source: "music" (EQ öncesi dokunuştan 12 sn, kullanıcının çalan müziği) | "default" (hazır klip)."""
        if self.abx is None:
            raise ValueError("kör test bu oturumda yok")
        if source == "music":
            if self.abx_recorder is None:
                raise ValueError("kayıt yapılamıyor (konsol kulaklığa bağlı değil)")
            self.abx_clip = abxsession.capture_clip(self.abx_recorder, os.path.join(self.abx.results_dir, "..", "clips"))
        elif source == "default":
            if not self.abx_default_clip:
                raise ValueError("hazır klip yok")
            self.abx_clip = self.abx_default_clip() if callable(self.abx_default_clip) else self.abx_default_clip
        else:
            raise KeyError(source)
        return self.abx_view()

    def abx_start(self, a="aac", b="sbc"):
        self.abx.start(a, b, self.abx_clip)
        return self.abx_view()

    def abx_do(self, fn, *args):
        getattr(self.abx, fn)(*args)
        return self.abx_view()

    # ── yönetim (D6) ──
    @staticmethod
    def _summary(st):
        on = [b for b in st.get("bands", []) if b.get("enabled")]
        cf = st.get("crossfeed", {})
        return {"bands_on": len(on), "preamp_db": console.preamp_db(console.sanitize(st)),
                "crossfeed": bool(cf.get("enabled")), "width": st.get("width"), "balance": st.get("balance")}

    @staticmethod
    def _tr(v, fmt, en=False):
        return format(v, fmt) if en else format(v, fmt).replace(".", ",")   # Türkçe ondalık ayırıcı (EN: nokta)

    @classmethod
    def _diff(cls, a, b, en=False):
        """İki sürüm arasında ne değişti — okunur kısa satırlar (hızlı fark analizi). en=True → İngilizce (U85)."""
        w = (lambda tr, e: e) if en else (lambda tr, e: tr)
        out = []
        for i, (x, y) in enumerate(zip(a.get("bands", []), b.get("bands", []))):
            if x == y:
                continue
            if x.get("enabled") != y.get("enabled"):
                out.append(w(f"bant {i + 1} {'açıldı' if y.get('enabled') else 'kapandı'}",
                             f"band {i + 1} {'on' if y.get('enabled') else 'off'}"))
                continue
            parts = []
            if x.get("type") != y.get("type"):
                parts.append(f"{x.get('type')}→{y.get('type')}")
            if x.get("freq") != y.get("freq"):
                parts.append(f"{cls._tr(x.get('freq'), 'g', en)}→{cls._tr(y.get('freq'), 'g', en)} Hz")
            if x.get("gain") != y.get("gain"):
                parts.append(f"{cls._tr(x.get('gain'), '+.1f', en)}→{cls._tr(y.get('gain'), '+.1f', en)} dB")
            if x.get("q") != y.get("q"):
                parts.append(f"Q {cls._tr(x.get('q'), 'g', en)}→{cls._tr(y.get('q'), 'g', en)}")
            out.append(w(f"bant {i + 1}: ", f"band {i + 1}: ") + ", ".join(parts))
        if a.get("crossfeed") != b.get("crossfeed"):
            on = b.get("crossfeed", {}).get("enabled")
            out.append("crossfeed " + (w("açık", "on") if on else w("kapalı", "off"))
                       + f" ({b.get('crossfeed', {}).get('fcut')} Hz, {b.get('crossfeed', {}).get('feed')} dB)")
        for k, lbl in (("width", w("genişlik", "width")), ("balance", w("denge", "balance")), ("preamp", "preamp")):
            if a.get(k) != b.get(k):
                out.append(f"{lbl} {a.get(k)}→{b.get(k)}")
        return out

    def _journal_lines(self, pid):
        self.writer.flush(2.0)                            # yönetim isteği: bekleyen yazım diske insin (sıcak yol değil)
        try:
            with open(self.writer.journal_path(pid), "rb") as f:
                return f.read().splitlines()
        except (FileNotFoundError, IsADirectoryError, PermissionError):
            return []

    def admin_profiles(self):
        """Yönetim tablosu: profil satırları + dosya/günlük boyutu + sürüm sayısı."""
        self.writer.flush(2.0)                            # boyut/sürüm sayısı diskteki gerçek hâlden
        rows = []
        for p in self.store.list():
            try:
                size = os.path.getsize(self.store._path(p["id"]))
            except OSError:
                size = len(json.dumps(self.store.get(p["id"]), ensure_ascii=False).encode())
            jp = self.writer.journal_path(p["id"])
            jb = os.path.getsize(jp) if jp != os.devnull and os.path.exists(jp) else 0
            n = len(history.timeline(self._journal_lines(p["id"]))["versions"]) if (jb and not p.get("locked", True)) else 1
            rows.append({**p, "bytes": size, "journal_bytes": jb, "versions": max(1, n)})
        return rows

    def admin_timeline(self, pid):
        """Profilin sürüm zaman çizelgesi: her sürümün zamanı, özeti ve bir öncekine göre fark satırları."""
        doc = self.store.get(pid)
        tl = history.timeline(self._journal_lines(pid)) if not doc.get("locked", True) else {"versions": [], "ptr": -1}
        if not tl["versions"]:
            tl = {"versions": [{"v": 0, "t": None, "state": doc["state"]}], "ptr": 0}
        prev = None
        for x in tl["versions"]:
            x["summary"] = self._summary(x["state"])
            x["diff"] = self._diff(prev, x["state"]) if prev is not None else ["ilk sürüm"]
            x["diff_en"] = self._diff(prev, x["state"], en=True) if prev is not None else ["first version"]
            prev = x["state"]
        return {"id": pid, "name": doc["name"], "locked": doc.get("locked", True), "ptr": tl["ptr"],
                "versions": tl["versions"], "active": bool(self.active and self.active.get("id") == pid)}

    def admin_restore(self, pid, v):
        """Bir sürümü GERİ YÜKLE: geçmiş silinmez, o sürüm yeni bir sürüm olarak eklenir (ve geri alınabilir)."""
        doc = self.store.get(pid)
        if doc.get("locked", True):
            raise ValueError("kilitli (ana) profilin sürüm geçmişi yok — yalnız çalışma kopyaları (Özel N) sürüm tutar")
        tl = history.timeline(self._journal_lines(pid))
        if not (isinstance(v, int) and 0 <= v < len(tl["versions"])):
            raise KeyError(f"sürüm {v}")
        if not (self.active and self.active.get("id") == pid):
            self.load_profile(pid)
        if self.hist:
            self.hist.seal()
        return self.set_state(tl["versions"][v]["state"], seal=True)

    def admin_export_all(self):
        """Tüm profilleri tek pakette (bta-bundle/1) döndürür."""
        return {"schema": BUNDLE_SCHEMA, "app": "bt-audio-hifi",
                "exported": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "profiles": [self.store.export(p["id"]) for p in self.store.list()]}

    def admin_import_bundle(self, bundle):
        """bta-bundle/1 paketini içe aktarır (en çok 500 profil); şema yanlışsa ValueError."""
        if not isinstance(bundle, dict) or bundle.get("schema") != BUNDLE_SCHEMA or not isinstance(bundle.get("profiles"), list):
            raise ValueError(f"paket şeması tanınmadı (beklenen {BUNDLE_SCHEMA})")
        ids = [self.store.import_doc(d) for d in bundle["profiles"][:500]]
        return {**self.view(), "imported": ids}

    def commit(self):
        """'Açılışta kullan': mevcut durumu kalıcı config olarak kurar (on_commit)."""
        with self.lock:
            self.committed = self.on_commit(self.state)
            self.default_json = json.dumps(self.state, sort_keys=True)
            self.last = self.clock()
        return self.view()


MAX_BODY = 256 * 1024          # profil içe aktarma dahil hiçbir istek bundan büyük olamaz (U47)


class ApiError(Exception):
    """HTTP hata kodu taşıyan API istisnası."""
    def __init__(self, code, msg, **extra):
        super().__init__(msg)
        self.code, self.extra = code, extra


def make_handler(sess: Session, stop: threading.Event, allow_hosts=()):
    """Session'a bağlı HTTP işleyici sınıfı üretir (Host/JSON/boyut kapıları, CSP, rotalar).
    allow_hosts: loopback dışında açıkça adlandırılmış Host adları (ör. `tailscale serve` tailnet adı)."""
    hosts = frozenset(("127.0.0.1", "localhost", *(h.strip().lower() for h in allow_hosts if h.strip())))
    def _auto(body):
        if sess.engine is None:
            raise ValueError("otomasyon motoru bu oturumda yok")
        sess.engine.configure(body)
        return sess.view()

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json", extra_headers=None):
            if isinstance(body, dict) and "error" in body and "error_en" not in body:
                body = {**body, "error_en": error_en(body["error"])}      # U85: metni istemci dile göre seçer
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            if ctype.startswith("text/html"):
                self.send_header("Content-Security-Policy", CSP)
            for k, v in (extra_headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def _guard(self, post=False):
            """DNS rebinding: yalnız 127.0.0.1/localhost Host · CSRF: POST yalnız application/json (basit istek değil →
            tarayıcı CORS ön-uçuşu yapar, izin başlığı vermediğimiz için başka site gönderemez)."""
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            if host.lower() not in hosts:
                self.close_connection = True             # okunmamış gövde keep-alive'da istek sanılmasın
                self._send(403, {"error": "yasak host"})
                return False
            if post and not (self.headers.get("Content-Type") or "").startswith("application/json"):
                self.close_connection = True
                self._send(415, {"error": "application/json gerekli"})
                return False
            return True

        def do_GET(self):
            if not self._guard():
                return
            path, _, query = self.path.partition("?")
            q = dict(kv.split("=", 1) for kv in query.split("&") if "=" in kv)
            if path == "/admin":
                with open(ADMIN_PAGE, "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            if path == "/api/admin/profiles":
                return self._send(200, {"profiles": sess.admin_profiles(), "trash": sess.store.trash_list(),
                                        "dirs": {"profiles": sess.store.dir}})
            if path == "/api/admin/timeline":
                from urllib.parse import unquote
                try:
                    return self._send(200, sess.admin_timeline(unquote(q.get("id", ""))))
                except KeyError:
                    return self._send(404, {"error": "profil yok"})
            if path == "/api/admin/export-all":
                return self._send(200, json.dumps(sess.admin_export_all(), indent=1, ensure_ascii=False).encode(),
                                  "application/json",
                                  {"Content-Disposition": 'attachment; filename="bta-profiller.json"'})
            if path in I18N_FILES:
                fn, ctype = I18N_FILES[path]
                with open(os.path.join(I18N_DIR, fn), "rb") as f:
                    return self._send(200, f.read(), ctype)
            if path in ("/", "/index.html"):
                with open(PAGE, "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            if path == "/api/state":
                return self._send(200, sess.view())
            if path == "/api/abx":
                return self._send(200, sess.abx_view())
            if path == "/api/auto":                  # hafif yoklama (arayüz 1 sn'de bir): tam görünüm DEĞİL
                return self._send(200, sess.auto_view())
            if path == "/api/saved":
                return self._send(200, {"pending": sess.writer.pending(), "last_write": sess.writer.last_write,
                                        "errors": list(sess.writer.errors)})
            if path == "/api/profile/export":
                from urllib.parse import unquote
                try:
                    doc = sess.store.export(unquote(q.get("id", "")))
                except KeyError:
                    return self._send(404, {"error": "profil yok"})
                from urllib.parse import quote
                fn = "bta-" + profiles.slug(doc["name"]) + ".json"   # başlık latin-1 → RFC 5987 ile UTF-8 ad
                return self._send(200, json.dumps(doc, indent=2, ensure_ascii=False).encode(), "application/json",
                                  {"Content-Disposition": f"attachment; filename=\"bta-profile.json\"; "
                                                          f"filename*=UTF-8''{quote(fn)}"})
            if path == "/api/analyzer/stream" and sess.analyzer:
                return sess.analyzer.serve_sse(self)
            self._send(404, {"error": "yok"})

        def do_POST(self):
            if not self._guard(post=True):
                return
            n = int(self.headers.get("Content-Length", 0) or 0)
            if n > MAX_BODY:
                if n <= 4 * MAX_BODY:                    # makul boyutta ise gövdeyi boşalt → istemci yanıtı okuyabilsin
                    self.rfile.read(n)
                self.close_connection = True
                return self._send(413, {"error": f"istek çok büyük (> {MAX_BODY // 1024} KB)"})
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
                if not isinstance(body, dict):
                    raise ValueError("JSON nesnesi bekleniyor")
            except ValueError as e:
                return self._send(400, {"error": f"geçersiz JSON: {e}"})
            if self.path == "/api/quit":
                self._send(200, {"ok": True})
                stop.set()
                return
            routes = {"/api/state": lambda: sess.set_state(body["state"], seal=bool(body.get("seal"))),
                      "/api/bypass": lambda: sess.set_bypass(body.get("on")),
                      "/api/loud": lambda: sess.set_loud(body["db"]),
                      "/api/preset": lambda: sess.preset(body["id"]),
                      "/api/profile/save": lambda: sess.save_profile(body["name"], bool(body.get("overwrite")),
                                                                     body.get("notes")),
                      "/api/profile/load": lambda: sess.load_profile(body["id"]),
                      "/api/profile/rename": lambda: sess.rename_profile(body["id"], body["name"], bool(body.get("overwrite"))),
                      "/api/profile/duplicate": lambda: sess.duplicate_profile(body["id"]),
                      "/api/profile/delete": lambda: sess.delete_profile(body["id"]),
                      "/api/profile/restore": lambda: sess.restore_profile(body["token"]),
                      "/api/profile/import": lambda: sess.import_profile(body["doc"], bool(body.get("overwrite"))),
                      "/api/profile/promote": lambda: sess.promote(body["id"], body["name"], bool(body.get("overwrite"))),
                      "/api/profile/apply-parent": lambda: sess.apply_to_parent(),
                      "/api/profile/genres": lambda: sess.set_genres(body["id"], body.get("genres", [])),
                      "/api/history/undo": lambda: sess.undo(),
                      "/api/history/redo": lambda: sess.redo(),
                      "/api/history/seal": lambda: sess.history_seal(),
                      "/api/analyzer/config": lambda: sess.analyzer.configure(body) if sess.analyzer else {},
                      "/api/auto": lambda: _auto(body),
                      "/api/tone": lambda: sess.play_tone(body["kind"], body.get("seconds", 4.0)),
                      "/api/tone/stop": lambda: sess.stop_tone(),
                      "/api/abx/clip": lambda: sess.abx_clip_from(body.get("source", "music")),
                      "/api/abx/start": lambda: sess.abx_start(body.get("a", "aac"), body.get("b", "sbc")),
                      "/api/abx/play": lambda: sess.abx_do("play", body["which"]),
                      "/api/abx/answer": lambda: sess.abx_do("answer", body["which"]),
                      "/api/abx/prefer": lambda: sess.abx_do("prefer", body["codec"]),
                      "/api/abx/finish": lambda: {**sess.abx_view(), "finished": sess.abx.finish(bool(body.get("apply")))},
                      "/api/abx/abort": lambda: sess.abx_do("abort"),
                      "/api/admin/restore": lambda: sess.admin_restore(body["id"], body["v"]),
                      "/api/admin/import-bundle": lambda: sess.admin_import_bundle(body["bundle"]),
                      "/api/commit": lambda: sess.commit()}
            if self.path not in routes:
                return self._send(404, {"error": "yok"})
            try:
                return self._send(200, routes[self.path]())
            except profiles.Conflict as e:
                return self._send(409, {"error": str(e), "conflict": e.pid})
            except (abxsession.NotReady, abxsession.Busy) as e:
                return self._send(409, {"error": str(e)})
            except abxsession.NoMusic as e:
                return self._send(422, {"error": str(e)})
            except KeyError as e:
                return self._send(404 if self.path.startswith("/api/profile/") else 400,
                                  {"error": f"bulunamadı / eksik alan: {e}"})
            except Exception as e:                       # hata sayfada görünsün
                return self._send(400, {"error": str(e)[:300]})
    return H


# Sayfa yalnız kendi kaynaklarını yükler; satır içi script/stil tek dosyalık sayfa için gerekli. Dış bağlantı YOK.
CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
       "img-src 'self' data: blob:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; "
       "frame-ancestors 'none'; form-action 'none'")


def serve(sess: Session, port: int = 0, allow_hosts=()):
    """127.0.0.1'de iş parçacıklı sunucu + boşta kalma bekçisi başlatır → (httpd, url, stop olayı)."""
    stop = threading.Event()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(sess, stop, allow_hosts))
    httpd.daemon_threads = True                      # açık SSE bağlantısı kapanışı bekletmesin
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    def watchdog():
        while not stop.is_set():
            if sess.idle_timeout_s and time.time() - sess.last > sess.idle_timeout_s:   # 0 = arka plan servisi (U74)
                stop.set()
            time.sleep(1)
        httpd.shutdown()
    threading.Thread(target=watchdog, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/", stop
