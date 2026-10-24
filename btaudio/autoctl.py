"""D4 Auto Profile Changer + D5 Auto Dynamic Live — karar mantığı (domain: saf, saat parametre).

Parametre kaynakları (docs/research/findings.md R35–R38; araştırma ajanı tabloları): histerezis/kalma/marj değerleri
için akademik kaynak YOK → "tasarım önerisi" olarak işaretli; ADL ilkeleri Dolby IEQ (R37: yeterince bas varsa dokunma),
iZotope TBC (hedef = aralık → ölü bölge), Harman bas tercihi (R38: +4–6 dB), ISO 226 (düşük seviyede bas telafisi)."""
from __future__ import annotations

import math

# ── D4 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
APC_DEFAULTS = {"tau_s": 10.0, "margin": 0.15, "sustain_s": 8.0, "dwell_s": 30.0, "conf_min": 0.30,
                "manual_pause_s": 10.0}


class ProfileChanger:
    """Tür olasılıkları (EMA) → türle etiketli profil. Salınım koruması: marj + süreklilik + en az kalma + elle askı."""

    def __init__(self, mapping: dict, fallback: str | None = None, **cfg):
        self.mapping, self.fallback = dict(mapping), fallback
        self.cfg = {**APC_DEFAULTS, **cfg}
        self.ema, self.t = {}, None
        self.current, self.last_switch = None, -1e9
        self.cand, self.cand_since = None, None
        self.paused_until = -1e9
        self.log = []

    def manual(self, now):
        """Elle dokunuş: `manual_pause_s` (10 sn) boyunca otomatik geçiş yapılmaz."""
        self.paused_until = now + self.cfg["manual_pause_s"]

    def _smooth(self, macro, now):
        dt = 1.0 if self.t is None else max(0.0, now - self.t)
        self.t = now
        a = 1 - math.exp(-dt / self.cfg["tau_s"])
        for k, v in macro.items():
            self.ema[k] = v if k not in self.ema else self.ema[k] + a * (v - self.ema[k])

    def update(self, macro: dict | None, now: float):
        """Makro tür olasılıklarını EMA'ya katar; marj + süreklilik + en az kalma koşulları sağlanınca hedef profil kimliğini döndürür, aksi hâlde None."""
        if macro:
            self._smooth(macro, now)
        if not self.ema or now < self.paused_until:
            return None
        best = max(self.ema, key=self.ema.get)
        genre = best if self.ema[best] >= self.cfg["conf_min"] else None
        target = self.mapping.get(genre) if genre else self.fallback
        if target is None or target == self.current:
            self.cand = None
            return None
        cur_score = self.ema.get(next((g for g, p in self.mapping.items() if p == self.current), ""), 0.0)
        if genre and self.ema[best] - cur_score < self.cfg["margin"] and self.current is not None:
            return None
        if self.cand != target:
            self.cand, self.cand_since = target, now
            return None
        if now - self.cand_since < self.cfg["sustain_s"] or now - self.last_switch < self.cfg["dwell_s"]:
            return None
        self.current, self.last_switch, self.cand = target, now, None
        self.log.append({"t": now, "to": target, "genre": genre, "score": round(self.ema.get(best, 0), 2)})
        self.log = self.log[-100:]
        return target


# ── D5 ─────────────────────────────────────────────────────────────────────────────────────────────────────────
ADL_BANDS = {"bas": ("lowshelf", 80.0, 0.7, "sub", (-3.0, 4.0)),
             "alt_orta": ("bell", 300.0, 1.0, "alt_orta", (-3.0, 3.0)),
             "varlık": ("bell", 3000.0, 1.0, "varlık", (-3.0, 3.0)),
             "hava": ("highshelf", 10000.0, 0.7, "hava", (-3.0, 3.0))}
ADL_DEFAULTS = {"dead_db": 2.0, "strength": 0.5, "rate_db_s": 1.0, "loud_db": -14.0, "quiet_db": -30.0,
                "learn": 0.2, "bias_max": 6.0}


class DynamicEQ:
    """Ölçülen tonal denge (bölge fazlası, dB) ↔ kişisel referans → sınırlı, yavaş, ölü bölgeli düzeltme."""

    def __init__(self, reference: dict | None = None, **cfg):
        self.cfg = {**ADL_DEFAULTS, **cfg}
        self.ref = dict(reference or {})
        self.bias = {k: 0.0 for k in ADL_BANDS}
        self.off = {k: 0.0 for k in ADL_BANDS}
        self.t = None

    def learn_reference(self, excess: dict, weight: float = 0.02):
        """Kişisel tonal referansı (bölge fazlası) `weight` ağırlıklı üstel ortalama ile günceller."""
        for k, v in excess.items():
            self.ref[k] = v if k not in self.ref else self.ref[k] + weight * (v - self.ref[k])

    def manual(self, band: str, delta_db: float):
        """Kullanıcı bant tercihini öğrenir: bias += learn·delta, ±bias_max ile sınırlı."""
        b = self.bias[band] + self.cfg["learn"] * delta_db
        self.bias[band] = max(-self.cfg["bias_max"], min(self.cfg["bias_max"], b))

    def target(self, excess: dict, genre: str | None, level_db: float | None) -> dict:
        """Hedef düzeltme (dB, bant başına): ölü bölge, güç, tür kuralı (R37), seviye kuralları (ISO 226 / sürücü koruma), bant sınırları. Konuşmada tümü 0."""
        if genre == "konuşma":
            return {k: 0.0 for k in ADL_BANDS}                            # konuşmada tonal düzeltme YOK (bas şişirmez)
        out = {}
        for name, (_t, _f, _q, region, (lo, hi)) in ADL_BANDS.items():
            diff = self.ref.get(region, 0.0) - excess.get(region, 0.0)       # + = şarkıda eksik
            if abs(diff) <= self.cfg["dead_db"]:
                diff = 0.0                                                    # hedef aralığında → dokunma (TBC)
            else:
                diff = math.copysign(abs(diff) - self.cfg["dead_db"], diff)
            g = self.cfg["strength"] * diff + self.bias[name]
            if name == "bas":
                if genre in ("elektronik", "hiphop") and excess.get("sub", 0) >= self.ref.get("sub", 0):
                    g = min(g, 0.0)                                           # zaten yeterince bas (R37)
                if level_db is not None and level_db > self.cfg["loud_db"]:
                    g -= 0.5 * (level_db - self.cfg["loud_db"])               # yüksek seviye → sürücüyü koru (R38/R40)
                elif level_db is not None and level_db < self.cfg["quiet_db"]:
                    g += min(3.0, 0.15 * (self.cfg["quiet_db"] - level_db))    # kısık → ISO 226 telafisi
            out[name] = max(lo, min(hi, g))
        return out

    def step(self, excess: dict | None, genre: str | None, level_db: float | None, now: float) -> dict:
        """Hedefe `rate_db_s` hızıyla yaklaşır; sessizlikte son değeri korur. Uygulanacak katmanı döndürür."""
        dt = 1.0 if self.t is None else max(0.0, now - self.t)
        self.t = now
        if not excess:
            return dict(self.off)                                             # sessizlik → son durum korunur
        tg = self.target(excess, genre, level_db)
        lim = self.cfg["rate_db_s"] * dt
        for k, v in tg.items():
            d = max(-lim, min(lim, v - self.off[k]))
            self.off[k] = round(self.off[k] + d, 3)
        return dict(self.off)


def apply_offsets(state: dict, offsets: dict) -> dict:
    """Kullanıcının durumuna ADL bantlarını BOŞ (kapalı) yuvalara ekler — kullanıcının bantlarına dokunmaz."""
    import copy
    st = copy.deepcopy(state)
    free = [i for i, b in enumerate(st["bands"]) if not b.get("enabled")]
    for (name, (typ, f, q, _r, _l)), i in zip(ADL_BANDS.items(), free):
        g = offsets.get(name, 0.0)
        st["bands"][i] = {"type": typ, "freq": f, "gain": round(g, 1), "q": q, "enabled": abs(g) >= 0.05}
    return st
