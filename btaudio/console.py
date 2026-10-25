"""F9 — Profesyonel ses konsolu modeli: 10 bant stereo PEQ + bs2b crossfeed + stereo genişlik + denge + otomatik
preamp. Her şey PipeWire filter-chain'de CANLI değişir (bq_raw katsayıları + mixer kazançları + linear çarpan).

Graf (kanal başına):
    preX(linear) → eqX_1 … eqX_N (bq_raw) ─┬→ hiX (bq_raw, bs2b yüksek raf) ─┐
                                           └→ loX (bq_raw, bs2b alçak geçiren)┤→ mixL / mixR (mixer)
    mixL = g·[a·hiL + b·hiR + a·loR + b·loL]   mixR = g·[a·hiR + b·hiL + a·loL + b·loR]
    a=(1+w)/2, b=(1−w)/2 (w=genişlik; L=R içerikte a+b=1 → mono uyumlu), g = bs2b kazancı.
bs2b: docs/research/upstream/bs2b.c:131-214 (birinci derece filtreler → bq_raw ile BİREBİR).
"""
from __future__ import annotations

import copy
import json
import os
import re
import math

import numpy as np

from . import dsp

N_BANDS = 10
FS = 48000
RATES = (44100, 48000)
F_MIN, F_MAX = 20.0, 20000.0
G_MIN, G_MAX = -18.0, 12.0
Q_MIN, Q_MAX = 0.1, 10.0
W_MIN, W_MAX = 0.0, 1.6
BS2B_FCUT = (300, 2000)            # bs2b.h BS2B_MINFCUT/MAXFCUT
BS2B_FEED = (1.0, 15.0)            # bs2b.h BS2B_MINFEED/MAXFEED (dB)
BS2B_PRESETS = {                   # bs2b.h:56-58
    "default": {"fcut": 700, "feed": 4.5, "label": "Varsayılan (bs2b)"},
    "cmoy": {"fcut": 700, "feed": 6.0, "label": "Chu Moy"},
    "jmeier": {"fcut": 650, "feed": 9.5, "label": "Jan Meier"},
}
DEFAULT_FREQS = [32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]
ZERO = {"b0": 0.0, "b1": 0.0, "b2": 0.0, "a0": 1.0, "a1": 0.0, "a2": 0.0}


def default_state() -> dict:
    """Şeffaf başlangıç durumu: 10 kapalı bant, crossfeed kapalı, genişlik 1, denge 0."""
    return {
        "bands": [{"type": "bell", "freq": float(f), "gain": 0.0, "q": 1.0, "enabled": False} for f in DEFAULT_FREQS],
        "crossfeed": {"enabled": False, "fcut": 700, "feed": 4.5},
        "width": 1.0,
        "balance": 0.0,
    }


RECOMMENDED_PRESET = "hifi_uzay"   # U80: konsolda Nötr'den sonra 2. hazır tarz
RECOMMENDED_LOUD_DB = 6.0          # U80: preamp'i (≈ −6 dB) dengeler → orta bölge kaynakla aynı seviye (U78 ölçümü)


def recommended_state() -> dict:
    """U80: ilk kurulum varsayılanı = `hifi_uzay` hazır tarzı (ölçülü Harman bas rafı + hafif uzay).
    'Nötr' (default_state) şeffaf referans olarak kalır; bu yalnız hiç durumu olmayan kuruluma verilir."""
    return apply_preset(default_state(), RECOMMENDED_PRESET)


def _clip(v, lo, hi):
    return float(min(max(float(v), lo), hi))


def sanitize(st: dict) -> dict:
    """Dış girdiyi sözleşmeye zorlar: tip listesi, sınır kırpma, eksik alan tamamlama (her yazımdan önce)."""
    s = copy.deepcopy(st)
    bands = s.get("bands", [])
    if len(bands) != N_BANDS:
        raise ValueError(f"{N_BANDS} bant bekleniyor, {len(bands)} geldi")
    for b in bands:
        if b.get("type") not in dsp.TYPES:
            raise ValueError(f"bilinmeyen filtre tipi: {b.get('type')}")
        b["freq"] = round(_clip(b["freq"], F_MIN, F_MAX), 1)
        b["gain"] = round(_clip(b.get("gain", 0.0), G_MIN, G_MAX), 1)
        b["q"] = round(_clip(b.get("q", 1.0), Q_MIN, Q_MAX), 2)
        b["enabled"] = bool(b.get("enabled", True))
    cf = s.setdefault("crossfeed", {"enabled": False, "fcut": 700, "feed": 4.5})
    cf["enabled"] = bool(cf.get("enabled", False))
    cf["fcut"] = int(round(_clip(cf.get("fcut", 700), *BS2B_FCUT)))
    cf["feed"] = round(_clip(cf.get("feed", 4.5), *BS2B_FEED), 1)
    s["width"] = round(_clip(s.get("width", 1.0), W_MIN, W_MAX), 2)
    s["balance"] = round(_clip(s.get("balance", 0.0), -1.0, 1.0), 2)
    return s


def bs2b_coeffs(fcut: float, feed_db: float, fs: int = FS) -> dict:
    """bs2b.c init(): level=feed dB, GB_lo=level·(−5/6)−3, GB_hi=level/6−3 …"""
    gb_lo = feed_db * -5.0 / 6.0 - 3.0
    gb_hi = feed_db / 6.0 - 3.0
    g_lo = 10 ** (gb_lo / 20.0)
    g_hi = 1.0 - 10 ** (gb_hi / 20.0)
    fc_hi = fcut * 2.0 ** ((gb_lo - 20.0 * math.log10(g_hi)) / 12.0)
    x = math.exp(-2.0 * math.pi * fcut / fs)
    lo = {"b0": g_lo * (1.0 - x), "b1": 0.0, "b2": 0.0, "a0": 1.0, "a1": -x, "a2": 0.0}
    xh = math.exp(-2.0 * math.pi * fc_hi / fs)
    hi = {"b0": 1.0 - g_hi * (1.0 - xh), "b1": -xh, "b2": 0.0, "a0": 1.0, "a1": -xh, "a2": 0.0}
    return {"lo": lo, "hi": hi, "gain": 1.0 / (1.0 - g_hi + g_lo)}


def _spatial(st, fs=FS, bypass=False):
    w = 1.0 if bypass else st["width"]
    a, b = (1 + w) / 2, (1 - w) / 2
    cf = st["crossfeed"]
    if cf["enabled"] and not bypass:
        k = bs2b_coeffs(cf["fcut"], cf["feed"], fs)
        return a, b, k["hi"], k["lo"], k["gain"]
    return a, b, dict(dsp.IDENTITY), dict(ZERO), 1.0


def _balance(st, bypass=False):
    if bypass:
        return 1.0, 1.0
    bal = st["balance"]
    return min(1.0, 1.0 - bal), min(1.0, 1.0 + bal)


def _h(k, freqs, fs=FS):
    return dsp.freq_response(k, freqs, fs)


def _eq_h(st, freqs, fs=FS):
    h = np.ones(len(freqs), dtype=complex)
    for bd in st["bands"]:
        h *= _h(dsp.coeffs(bd, fs), freqs, fs)
    return h


def _db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-10))


def stereo_model(st: dict, freqs, include_preamp=False, fs=FS) -> dict:
    """Karmaşık transfer fonksiyonları: LL (L giriş→L çıkış), LR (L→R), RL, RR, mono (L=R→L)."""
    freqs = [float(f) for f in freqs]
    eq = _eq_h(st, freqs, fs)
    a, b, hi, lo, g = _spatial(st, fs)
    hh, hl = _h(hi, freqs, fs), _h(lo, freqs, fs)
    bl, br = _balance(st)
    pre = 10 ** (st.get("preamp_override", preamp_db(st)) / 20) if include_preamp else 1.0
    ll = pre * g * eq * bl * (a * hh + b * hl)
    lr = pre * g * eq * bl * (b * hh + a * hl)
    rl = pre * g * eq * br * (b * hh + a * hl)
    rr = pre * g * eq * br * (a * hh + b * hl)
    mono_l = ll + rl
    return {k: dict(zip(freqs, _db(v).tolist())) for k, v in
            {"LL": ll, "LR": lr, "RL": rl, "RR": rr, "mono": mono_l}.items()}


GRID = np.geomspace(20, 20000, 240).tolist()


def preamp_db(st: dict) -> float:
    """En kötü durum sınırı: |L çıkışı| ≤ |LL|+|RL| (tam ölçek, aynı fazlı L ve R). Tepe >0 dB ise o kadar kıs."""
    eq = _eq_h(st, GRID)
    a, b, hi, lo, g = _spatial(st)
    hh, hl = _h(hi, GRID), _h(lo, GRID)
    bl, br = _balance(st)
    bound_l = np.abs(g * eq * bl * (a * hh + b * hl)) + np.abs(g * eq * br * (b * hh + a * hl))
    bound_r = np.abs(g * eq * bl * (b * hh + a * hl)) + np.abs(g * eq * br * (a * hh + b * hl))
    peak = float(np.max(_db(np.maximum(bound_l, bound_r))))
    return round(-peak, 2) if peak > 0 else 0.0


def _kv(node, k):
    return " ".join(f'"{node}:{n}" {k[n]:.10f}' for n in ("b0", "b1", "b2", "a0", "a1", "a2"))


def pw_params(st: dict, bypass: bool = False) -> str:
    """Tek zincirli graf için PipeWire Props yükü (bq_raw katsayıları, preamp, uzay kazançları)."""
    parts = []
    pre = 1.0 if bypass else 10 ** (preamp_db(st) / 20)
    bl, br = _balance(st, bypass)
    parts.append(f'"preL:Mult" {pre * bl:.6f}')
    parts.append(f'"preR:Mult" {pre * br:.6f}')
    for i, bd in enumerate(st["bands"], 1):
        k = dict(dsp.IDENTITY) if bypass else dsp.coeffs(bd)
        parts.append(_kv(f"eqL_{i}", k))
        parts.append(_kv(f"eqR_{i}", k))
    a, b, hi, lo, g = _spatial(st, bypass=bypass)
    for ch in ("L", "R"):
        parts.append(_kv(f"hi{ch}", hi))
        parts.append(_kv(f"lo{ch}", lo))
    for mix, gains in (("mixL", (g * a, g * b, g * a, g * b)), ("mixR", (g * a, g * b, g * a, g * b))):
        parts += [f'"{mix}:Gain {i}" {v:.6f}' for i, v in enumerate(gains, 1)]
    return "{ params = [ " + " ".join(parts) + " ] }"


def _coef_block(bands_or_k):
    rows = []
    for r in RATES:
        k = bands_or_k(r)
        rows.append("{ rate = %d b0 = %.10f b1 = %.10f b2 = %.10f a0 = %.10f a1 = %.10f a2 = %.10f }"
                    % (r, k["b0"], k["b1"], k["b2"], k["a0"], k["a1"], k["a2"]))
    return "config = { coefficients = [ " + " ".join(rows) + " ] }"


def render_graph(target_sink: str, st: dict | None = None, source: str = "-") -> str:
    """Kalıcı config: mevcut durumun katsayıları GÖMÜLÜ (yeniden başlatmada aynı ses)."""
    st = sanitize(st or default_state())
    pre = 10 ** (preamp_db(st) / 20)
    bl, br = _balance(st)
    nodes, links = [], []

    def node(name, label, extra):
        nodes.append(f"                    {{ type = builtin name = {name} label = {label} {extra} }}")

    for ch, bal in (("L", bl), ("R", br)):
        node(f"pre{ch}", "linear", f'control = {{ "Mult" = {pre * bal:.6f} "Add" = 0.0 }}')
        prev = f"pre{ch}"
        for i, bd in enumerate(st["bands"], 1):
            node(f"eq{ch}_{i}", "bq_raw", _coef_block(lambda r, bd=bd: dsp.coeffs(bd, r)))
            links.append(f'{{ output = "{prev}:Out" input = "eq{ch}_{i}:In" }}')
            prev = f"eq{ch}_{i}"
        node(f"hi{ch}", "bq_raw", _coef_block(lambda r: _spatial(st, r)[2]))
        node(f"lo{ch}", "bq_raw", _coef_block(lambda r: _spatial(st, r)[3]))
        links.append(f'{{ output = "{prev}:Out" input = "hi{ch}:In" }}')
        links.append(f'{{ output = "{prev}:Out" input = "lo{ch}:In" }}')
    a, b, _, _, g = _spatial(st)
    for mix, ins in (("mixL", ("hiL", "hiR", "loR", "loL")), ("mixR", ("hiR", "hiL", "loL", "loR"))):
        node(mix, "mixer", 'control = { "Gain 1" = %.6f "Gain 2" = %.6f "Gain 3" = %.6f "Gain 4" = %.6f }'
             % (g * a, g * b, g * a, g * b))
        for i, src in enumerate(ins, 1):
            links.append(f'{{ output = "{src}:Out" input = "{mix}:In {i}" }}')
    link_txt = "\n".join("                    " + l for l in links)
    return f"""# bt-audio-hifi (PRD-BTA02) — ÜRETİLMİŞ DOSYA. Profesyonel konsol durumu gömülü. Kaynak: {source}
context.modules = [
    {{ name = libpipewire-module-filter-chain
        args = {{
            node.description = "BT kulaklık konsolu (bta)"
            media.name       = "BT kulaklık konsolu (bta)"
            filter.graph = {{
                nodes = [
{chr(10).join(nodes)}
                ]
                links = [
{link_txt}
                ]
                inputs  = [ "preL:In" "preR:In" ]
                outputs = [ "mixL:Out" "mixR:Out" ]
            }}
            audio.channels = 2
            audio.position = [ FL FR ]
            capture.props = {{
                node.name   = "effect_input.bta_console"
                media.class = Audio/Sink
                filter.smart = true
                filter.smart.name = "bta-console"
                filter.smart.target = {target_spa(target_sink)}
            }}
            playback.props = {{
                node.name    = "effect_output.bta_console"
                node.passive = true
            }}
        }}
    }}
]
"""


def _bands(*specs):
    bands = [{"type": "bell", "freq": float(f), "gain": 0.0, "q": 1.0, "enabled": False} for f in DEFAULT_FREQS]
    for i, (t, f, g, q) in enumerate(specs):
        bands[i] = {"type": t, "freq": float(f), "gain": float(g), "q": float(q), "enabled": True}
    return bands


def _fitted(specs):
    return _bands(*[(t, f, g, q) for t, f, g, q in specs])


CATEGORIES = ["Referans", "Bas", "Tür", "Karakter", "Kullanım", "Uzay"]
KINDS = {"hedef": "Araştırma hedef eğrisinden (ölçülmüş veri)",
         "kaynak": "Yayımlanmış bir presetten (değerleri dosyadan okundu)",
         "standart": "Standart / yayımlanmış algoritma",
         "tasarım": "Tasarım kararı — yetkili tek kaynak yok; gerekçesi açıklamada"}
DESIGN = "Tasarım (yetkili tek-değer kaynağı yok). Bölge sınırları: TeachMeAudio sub 20–60 / bas 60–250 Hz; iZotope EQ cheat sheet warmth 120–400, presence 1–4k, air 8–12 kHz"
VLC_SRC = "VLC equalizer_presets.h (LGPL-2.1+) '{n}' 10 bant → 1 kHz'e göre, ×0,5 ölçek (kulakiçi + otomatik preamp), parametrik uydurma ≤1 dB (btaudio.presetfit)"
EE_SRC = "JackHack96/EasyEffects-Presets '{n}.json' (MIT) — 10 bell bant birebir"


def _vlc(name, values):
    return {"kind": "vlc", "name": name, "values": values, "scale": 0.5}


PRESETS = {
    # ── Referans ──
    "notr": {"label": "Nötr", "group": "Referans", "kind": "standart", "tags": ["referans"],
             "desc": "Hiçbir işlem yok — karşılaştırma noktası.", "source": "—", "bands": _bands()},
    "hifi_uzay": {"label": "Hi-fi dengeli + uzay", "group": "Referans", "kind": "hedef", "tags": ["dengeli", "bas", "uzay", "varsayılan"],
                  "desc": "İlk kurulum varsayılanı: ölçülü dolgun bas (105 Hz altına +6 dB raf) + hafif uzay (bs2b crossfeed, genişlik 1,1). Tüm frekanslar dengeli, 'kafa içi' hissi azalır.",
                  "source": "AutoEq targets: 'Harman over-ear 2018' − 'without bass' = lowshelf 105 Hz Q0,7 +6,0 dB + bs2b.h BS2B_DEFAULT_CLEVEL 700 Hz / 4,5 dB + genişlik 1,1 (tasarım)",
                  "bands": _bands(("lowshelf", 105, 6.0, 0.7)),
                  "spatial": {"crossfeed": {"enabled": True, "fcut": 700, "feed": 4.5}, "width": 1.1}},
    "harman_bas": {"label": "Harman bas (kulakiçi 2019)", "group": "Referans", "kind": "hedef", "tags": ["bas", "dengeli"],
                   "desc": "Harman kulakiçi hedefinin bas bileşeni: 105 Hz altına +9 dB raf. Kulakiçi için araştırmayla en çok beğenilen bas miktarı.",
                   "source": "AutoEq targets: 'Harman in-ear 2019' − 'without bass' = lowshelf 105 Hz Q0,7 +9,0 dB (max hata 0,06 dB, çalıştırılarak)",
                   "bands": _bands(("lowshelf", 105, 9.0, 0.7))},
    "harman_oe": {"label": "Harman bas (kulaküstü 2018)", "group": "Referans", "kind": "hedef", "tags": ["bas", "dengeli"],
                  "desc": "Kulaküstü hedefinin daha ölçülü bas rafı (+6 dB). Uzun dinleme için güvenli başlangıç.",
                  "source": "AutoEq targets: 'Harman over-ear 2018' − 'without bass' = lowshelf 105 Hz Q0,7 +6,0 dB (max hata 0,04 dB)",
                  "bands": _bands(("lowshelf", 105, 6.0, 0.7))},
    # ── Bas ──
    "hafif_bas": {"label": "Hafif bas", "group": "Bas", "kind": "tasarım", "tags": ["bas"],
                  "desc": "Ölçülü bas takviyesi (+4 dB raf) — vokali hiç etkilemez.", "source": DESIGN,
                  "bands": _bands(("lowshelf", 105, 4.0, 0.7))},
    "zengin_bas": {"label": "Zengin bas", "group": "Bas", "kind": "tasarım", "tags": ["bas", "sıcak", "dolgun"],
                   "desc": "Dolgun, sıcak ve geniş bas: derin raf + 200 Hz civarı gövde; vokal bölgesi korunur, tizde hafif hava.",
                   "source": DESIGN + ". Raf köşesi Harman ile aynı (105→120 Hz); gövde iZotope 'warmth' bölgesinde",
                   "bands": _bands(("lowshelf", 120, 7.0, 0.7), ("bell", 200, 1.5, 0.9), ("highshelf", 9000, 1.5, 0.7))},
    "derin_sub": {"label": "Derin sub-bas", "group": "Bas", "kind": "tasarım", "tags": ["bas", "sub", "elektronik"],
                  "desc": "60 Hz altına odaklı: hissedilen gümbürtü (sub), orta bas şişmeden.",
                  "source": DESIGN + ". Sub = 20–60 Hz (TeachMeAudio); 250 Hz çamur azaltma (iZotope)",
                  "bands": _bands(("bell", 42, 7.0, 0.8), ("lowshelf", 60, 2.0, 0.7), ("bell", 250, -1.0, 1.0))},
    "vurucu_bas": {"label": "Vurucu bas (punch)", "group": "Bas", "kind": "tasarım", "tags": ["bas", "davul", "rock"],
                   "desc": "Kick/davul vuruşu öne: 70 Hz tepe + 300 Hz çamur temizliği + 3 kHz atak.",
                   "source": DESIGN + ". Tom 'fundamental' 60–120 / 'mud' 250–600 Hz (iZotope)",
                   "bands": _bands(("bell", 70, 5.5, 1.2), ("bell", 300, -2.0, 1.0), ("bell", 3000, 1.0, 1.2))},
    "guclu_bas": {"label": "Güçlü bas", "group": "Bas", "kind": "tasarım", "tags": ["bas", "elektronik", "hip-hop"],
                  "desc": "Belirgin, vurucu bas (EDM/hip-hop) — en yüksek bas.", "source": DESIGN,
                  "bands": _bands(("lowshelf", 105, 8.5, 0.7), ("bell", 55, 3.0, 1.0))},
    "ee_bass_boosted": {"label": "Bas takviyeli (EasyEffects)", "group": "Bas", "kind": "kaynak", "tags": ["bas", "topluluk"],
                        "desc": "Linux EasyEffects topluluğunun popüler 'Bass Boosted' eğrisi: alt uç + tizde hafif parlaklık.",
                        "source": EE_SRC.format(n="Bass Boosted"),
                        "bands": _bands(*[("bell", f, g, 1.5) for f, g in zip(DEFAULT_FREQS, (4, 2, 1, 0, -1, -2, 0, 2, 3, 3))])},
    # ── Tür (VLC → parametrik; değerler tests U43 ile kaynağa karşı ölçülür) ──
    "elektronik": {"label": "Elektronik / Techno", "group": "Tür", "kind": "kaynak", "tags": ["elektronik", "bas", "parlak"],
                   "desc": "Güçlü alt uç + parlak üst; orta geride.", "source": VLC_SRC.format(n="Techno"),
                   "ref": _vlc("techno", [8.0, 5.6, 0.0, -5.6, -4.8, 0.0, 8.0, 9.6, 9.6, 8.8]),
                   "bands": _fitted([("lowshelf", 243, 6.2, 0.72), ("bell", 319, 0.8, 2.6), ("highshelf", 3589, 7.3, 0.6)])},
    "dans": {"label": "Dans / Club", "group": "Tür", "kind": "kaynak", "tags": ["elektronik", "bas"],
             "desc": "Kulüp sistemi hissi: dolgun bas, yumuşatılmış üst orta.", "source": VLC_SRC.format(n="Dance"),
             "ref": _vlc("dance", [9.6, 7.2, 2.4, 0.0, 0.0, -5.6, -7.2, -7.2, 0.0, 0.0]),
             "bands": _fitted([("lowshelf", 104, 4.7, 0.69), ("bell", 164, 2.9, 0.83), ("bell", 9615, -9.9, 0.43), ("highshelf", 5187, 6.5, 0.73)])},
    "rock": {"label": "Rock", "group": "Tür", "kind": "kaynak", "tags": ["rock", "gitar"],
             "desc": "Gitar ve zillere parlaklık, davula vuruş; boğuk orta alt azaltılmış.", "source": VLC_SRC.format(n="Rock"),
             "ref": _vlc("rock", [8.0, 4.8, -5.6, -8.0, -3.2, 4.0, 8.8, 11.2, 11.2, 11.2]),
             "bands": _fitted([("lowshelf", 235, 5.6, 0.71), ("bell", 433, -2.8, 0.69), ("highshelf", 2831, 7.3, 0.5)])},
    "pop": {"label": "Pop", "group": "Tür", "kind": "kaynak", "tags": ["pop", "vokal"],
            "desc": "Vokal ve orta-alt öne, uçlar hafif geride — radyo sesi.", "source": VLC_SRC.format(n="Pop"),
            "ref": _vlc("pop", [-1.6, 4.8, 7.2, 8.0, 5.6, 0.0, -2.4, -2.4, -1.6, -1.6]),
            "bands": _fitted([("lowshelf", 398, -4.1, 0.77), ("bell", 240, 4.2, 0.53), ("bell", 7335, -1.1, 0.41), ("highshelf", 1849, -3.1, 0.5)])},
    "hiphop": {"label": "Hip-hop / Rap", "group": "Tür", "kind": "tasarım", "tags": ["hip-hop", "bas", "vokal"],
               "desc": "808 sub-bas + net rap vokali: alt uç güçlü, 400 Hz çamur temiz, 3 kHz söz anlaşılırlığı.",
               "source": DESIGN + " (bu tür için yayımlanmış açık preset bulunamadı)",
               "bands": _bands(("lowshelf", 90, 7.0, 0.7), ("bell", 50, 2.0, 1.0), ("bell", 400, -2.0, 1.0), ("bell", 3000, 2.0, 1.0), ("highshelf", 10000, 1.0, 0.7))},
    "klasik": {"label": "Klasik", "group": "Tür", "kind": "kaynak", "tags": ["klasik", "akustik", "yumuşak"],
               "desc": "Doğal tını, yorucu olmayan yumuşak tiz.", "source": VLC_SRC.format(n="Classical"),
               "ref": _vlc("classical", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, -7.2, -7.2, -7.2, -9.6]),
               "bands": _fitted([("bell", 3102, 1.6, 0.96), ("bell", 6247, -3.5, 0.62), ("highshelf", 14000, -6.1, 0.54)])},
    "akustik_caz": {"label": "Akustik / Caz", "group": "Tür", "kind": "tasarım", "tags": ["caz", "akustik", "sıcak"],
                    "desc": "Kontrbas ve ahşap gövdesine sıcaklık, enstrüman varlığı, zillere hava.",
                    "source": DESIGN + " (bu tür için yayımlanmış açık preset bulunamadı)",
                    "bands": _bands(("bell", 150, 2.0, 0.8), ("bell", 3000, 1.5, 1.0), ("highshelf", 7000, 2.0, 0.7))},
    "konser": {"label": "Canlı konser", "group": "Tür", "kind": "kaynak", "tags": ["canlı", "orta", "uzay"],
               "desc": "Sahne önü hissi: orta bölge dolgun, alt uç sıkı; hafif crossfeed ile ferah.",
               "source": VLC_SRC.format(n="Live") + " + bs2b varsayılan crossfeed",
               "ref": _vlc("live", [-4.8, 0.0, 4.0, 5.6, 5.6, 5.6, 4.0, 2.4, 2.4, 2.4]),
               "bands": _fitted([("lowshelf", 249, -2.0, 0.77), ("bell", 42, -3.3, 0.39), ("highshelf", 6118, -1.6, 0.66)]),
               "spatial": {"crossfeed": {"enabled": True, "fcut": 700, "feed": 4.5}, "width": 1.1}},
    "parti": {"label": "Parti", "group": "Tür", "kind": "kaynak", "tags": ["eğlence", "bas", "parlak"],
              "desc": "Uçlar yukarıda — yüksek enerjili, eğlenceli.", "source": VLC_SRC.format(n="Party"),
              "ref": _vlc("party", [7.2, 7.2, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 7.2, 7.2]),
              "bands": _fitted([("lowshelf", 205, 3.5, 0.86), ("bell", 184, 0.9, 2.25), ("highshelf", 13287, 4.0, 0.98)])},
    # ── Karakter ──
    "v_sekli": {"label": "V-şekli", "group": "Karakter", "kind": "tasarım", "tags": ["bas", "parlak", "eğlence"],
                "desc": "Bas + tiz öne, orta hafif geride (eğlenceli, canlı).", "source": DESIGN,
                "bands": _bands(("lowshelf", 105, 6.0, 0.7), ("bell", 1000, -1.5, 0.7), ("highshelf", 8000, 4.0, 0.7))},
    "bas_tiz": {"label": "Bas + tiz (VLC)", "group": "Karakter", "kind": "kaynak", "tags": ["bas", "parlak"],
                "desc": "Klasik 'loudness' benzeri: iki uç belirgin, orta alt çekik.", "source": VLC_SRC.format(n="Full bass & treble"),
                "ref": _vlc("fullbasstreble", [7.2, 5.6, 0.0, -7.2, -4.8, 1.6, 8.0, 11.2, 12.0, 12.0]),
                "bands": _fitted([("lowshelf", 391, 6.0, 1.0), ("bell", 298, -3.1, 0.87), ("bell", 434, 0.7, 2.76), ("bell", 14794, 2.6, 0.3), ("highshelf", 2845, 5.8, 0.5)])},
    "sicak": {"label": "Sıcak", "group": "Karakter", "kind": "tasarım", "tags": ["sıcak", "yumuşak"],
              "desc": "Dolgun alt-orta, yumuşak tiz (uzun dinleme).", "source": DESIGN,
              "bands": _bands(("bell", 180, 2.5, 0.8), ("highshelf", 7000, -2.5, 0.7))},
    "parlak": {"label": "Parlak", "group": "Karakter", "kind": "tasarım", "tags": ["parlak", "detay"],
               "desc": "Daha fazla detay/hava; tiz rafı.", "source": DESIGN,
               "bands": _bands(("bell", 250, -1.0, 1.0), ("highshelf", 7000, 3.5, 0.7))},
    "vokal": {"label": "Vokal netliği", "group": "Karakter", "kind": "tasarım", "tags": ["vokal", "netlik"],
              "desc": "Sesler öne: gövde temizliği + varlık bölgesi.", "source": DESIGN,
              "bands": _bands(("highpass", 70, 0, 0.7), ("bell", 250, -2.0, 1.0), ("bell", 2500, 3.0, 1.0))},
    "ee_boosted": {"label": "Canlı (EasyEffects Boosted)", "group": "Karakter", "kind": "kaynak", "tags": ["bas", "parlak", "topluluk"],
                   "desc": "EasyEffects topluluğunun 'Boosted' eğrisi: alt uç ve 4 kHz varlık öne.",
                   "source": EE_SRC.format(n="Boosted"),
                   "bands": _bands(*[("bell", f, g, 1.5) for f, g in zip(DEFAULT_FREQS, (5, 5, 0, 0, 1, 1, 2, 4, 3, 2))])},
    # ── Kullanım ──
    "konusma": {"label": "Konuşma / podcast", "group": "Kullanım", "kind": "tasarım", "tags": ["konuşma", "vokal"],
                "desc": "Konuşma anlaşılırlığı; gürleme ve sibilans kısık.", "source": DESIGN,
                "bands": _bands(("highpass", 100, 0, 0.7), ("bell", 300, -2.0, 1.0), ("bell", 3000, 3.5, 1.2), ("highshelf", 9000, -2.0, 0.7))},
    "gece": {"label": "Gece / düşük ses", "group": "Kullanım", "kind": "standart", "tags": ["düşük ses", "loudness"],
             "desc": "Kısık seste bas ve tiz kaybını telafi (loudness).",
             "source": "ISO 226:2003 eşit-yükseklik eğrileri: düşük seviyede bas/tiz için daha fazla SPL gerekir (btaudio.loudness)",
             "bands": _bands(("lowshelf", 90, 6.0, 0.7), ("highshelf", 7000, 3.0, 0.7))},
    "film": {"label": "Film / dizi", "group": "Kullanım", "kind": "tasarım", "tags": ["film", "diyalog", "bas", "uzay"],
             "desc": "Patlamalara alt uç, diyaloğa netlik, geniş sahne.", "source": DESIGN + " + bs2b varsayılan crossfeed",
             "bands": _bands(("lowshelf", 80, 6.0, 0.7), ("bell", 2500, 2.0, 1.0), ("bell", 350, -1.0, 1.0)),
             "spatial": {"crossfeed": {"enabled": True, "fcut": 700, "feed": 4.5}, "width": 1.2}},
    "oyun": {"label": "Oyun (ayak sesi)", "group": "Kullanım", "kind": "tasarım", "tags": ["oyun", "detay"],
             "desc": "Ayak sesi/konum ipuçları öne (2–5 kHz), patlama gürlemesi geride.",
             "source": DESIGN + " (ölçüme dayalı oyun EQ kaynağı bulunamadı — araştırma notu R30)",
             "bands": _bands(("bell", 250, -2.0, 1.0), ("bell", 3500, 3.0, 1.0), ("highshelf", 8000, 2.0, 0.7))},
    # ── Uzay ──
    "sahne": {"label": "Geniş sahne", "group": "Uzay", "kind": "standart", "tags": ["uzay", "crossfeed"],
              "desc": "Crossfeed (bs2b) + hafif genişlik: 'kafa içi' hissi azalır.",
              "source": "bs2b.h BS2B_DEFAULT_CLEVEL 700 Hz / 4,5 dB + genişlik 1,15 (tasarım)",
              "bands": _bands(), "spatial": {"crossfeed": {"enabled": True, "fcut": 700, "feed": 4.5}, "width": 1.15}},
    "studyo": {"label": "Stüdyo monitör", "group": "Uzay", "kind": "standart", "tags": ["uzay", "crossfeed", "nötr"],
               "desc": "Hoparlör karşısında oturur gibi: güçlü crossfeed (Jan Meier), EQ yok.",
               "source": "bs2b.h BS2B_JMEIER_CLEVEL 650 Hz / 9,5 dB",
               "bands": _bands(), "spatial": {"crossfeed": {"enabled": True, "fcut": 650, "feed": 9.5}, "width": 1.0}},
    "dogal_crossfeed": {"label": "Doğal crossfeed", "group": "Uzay", "kind": "standart", "tags": ["uzay", "crossfeed"],
                        "desc": "Orta düzey crossfeed (Chu Moy) — uzun dinlemede yorgunluğu azaltır.",
                        "source": "bs2b.h BS2B_CMOY_CLEVEL 700 Hz / 6,0 dB",
                        "bands": _bands(), "spatial": {"crossfeed": {"enabled": True, "fcut": 700, "feed": 6.0}, "width": 1.0}},
}

PREVIEW_F = [round(f, 1) for f in np.geomspace(20, 20000, 48)]


_CATALOG = None


def preset_catalog() -> dict:
    """Arayüz için: meta + küçük önizleme eğrisi (EQ, preamp hariç). Hazır tarzlar koddadır → bir kez hesaplanır."""
    global _CATALOG
    if _CATALOG is not None:
        return _CATALOG
    out = {}
    for pid, p in PRESETS.items():
        prev = dsp.response_db([b for b in p["bands"] if b["enabled"]], PREVIEW_F) if any(b["enabled"] for b in p["bands"]) \
            else [0.0] * len(PREVIEW_F)
        out[pid] = {k: p[k] for k in ("label", "group", "desc", "source", "kind", "tags")}
        out[pid]["spatial"] = "spatial" in p
        out[pid]["preview"] = [round(v, 2) for v in prev]
    _CATALOG = out
    return out


def apply_preset(st: dict, pid: str) -> dict:
    """EQ profilleri yalnız bantları, 'Uzay' profilleri yalnız uzay ayarını değiştirir (biri diğerini silmesin);
    'film'/'konser' gibi ikisini birden tanımlayanlar ikisini; 'Nötr' her şeyi sıfırlar (açıklamasındaki vaat)."""
    p = PRESETS[pid]
    s = copy.deepcopy(st)
    if pid == "notr":
        return sanitize(default_state())
    if p["group"] != "Uzay":
        s["bands"] = copy.deepcopy(p["bands"])
    if "spatial" in p:
        s["crossfeed"] = dict(p["spatial"]["crossfeed"])
        s["width"] = p["spatial"]["width"]
    return sanitize(s)


# ── D2: A/B tıksız geçiş grafı (R33: PipeWire biquad'ları güncellemede belleği sıfırlar → tık) ─────────────────
#   girdi X → copyX ─┬→ zincir A: preAX → eqAX_1…10 → hiAX/loAX → mixAX ─┐ (Gain 1)
#                    └→ zincir B: …aynı…                           mixBX ─┴→ sumX (Gain 2) → çıktı X
#   Geçiş: yeni durum SESSİZ zincire yüklenir (belleğin sıfırlanması sessizde duyulmaz) → sumX kazançları küçük
#   adımlarla ters yönde (R42: `ramp` düğümü 1.6.8'de kullanılamaz). İlişkili sinyalde doğrusal geçiş sabit genlik.

def pw_params_ab(st: dict, chain: str, bypass: bool = False) -> str:
    """Tek zincirin (A|B) tüm denetim değerleri — `pw_params` ile aynı katsayılar, düğüm adları zincir önekli."""
    parts = []
    pre = 1.0 if bypass else 10 ** (preamp_db(st) / 20)
    bl, br = _balance(st, bypass)
    parts.append(f'"pre{chain}L:Mult" {pre * bl:.6f}')
    parts.append(f'"pre{chain}R:Mult" {pre * br:.6f}')
    for i, bd in enumerate(st["bands"], 1):
        k = dict(dsp.IDENTITY) if bypass else dsp.coeffs(bd)
        parts.append(_kv(f"eq{chain}L_{i}", k))
        parts.append(_kv(f"eq{chain}R_{i}", k))
    a, b, hi, lo, g = _spatial(st, bypass=bypass)
    for ch in ("L", "R"):
        parts.append(_kv(f"hi{chain}{ch}", hi))
        parts.append(_kv(f"lo{chain}{ch}", lo))
    for mix in (f"mix{chain}L", f"mix{chain}R"):
        parts += [f'"{mix}:Gain {i}" {v:.6f}' for i, v in enumerate((g * a, g * b, g * a, g * b), 1)]
    return "{ params = [ " + " ".join(parts) + " ] }"


def mix_gains(gain_a: float, gain_b: float) -> str:
    """Toplama düğümü kazançları (A = Gain 1, B = Gain 2). R42: PipeWire 1.6.8 `ramp` denetim portları aralıksız
    (min=max=0) → kullanılamaz; geçiş bu kazançların KÜÇÜK adımlarla değiştirilmesiyle yapılır (mixer blok başına sabit)."""
    return "{ params = [ " + " ".join(f'"sum{ch}:Gain 1" {gain_a:.5f} "sum{ch}:Gain 2" {gain_b:.5f}' for ch in ("L", "R")) + " ] }"


def crossfade_steps(to_chain: str, n: int) -> list:
    """Doğrusal (ilişkili sinyalde sabit genlik) n adımlı geçiş kazanç yükleri."""
    out = []
    for i in range(1, n + 1):
        x = i / n
        a, b = (1 - x, x) if to_chain == "B" else (x, 1 - x)
        out.append(mix_gains(a, b))
    return out


# U77 ses yükseltici + sınırlayıcı (zincirin son aşaması). Ayar repo dışında: ~/.config/bt-audio-hifi/loudness.json
LOUD_MAX_DB = 15.0         # U78 ölçüm: 14 dB'de sakin parçada sınırlama yok; üstü yüksek masterlarda pompalama
LIMIT_CEIL_DB = -1.0       # AAC kodlayıcı aşımı için pay
LSP_LADSPA = "/usr/lib64/ladspa/lsp-plugins-ladspa.so"


def loud_path() -> str:
    from . import paths
    return os.path.join(paths._root("config"), "loudness.json")


def load_loud_db(path: str | None = None) -> float:
    try:
        with open(path or loud_path()) as f:
            return _clip(json.load(f).get("loud_db", 0.0), 0.0, LOUD_MAX_DB)
    except (OSError, ValueError, AttributeError, TypeError):
        return 0.0


def save_loud_db(db: float, path: str | None = None) -> float:
    """Ayarı sınırlayıp atomik yazar (yarım dosya = bozuk ayar = 0 dB); yazılan değeri döndürür."""
    db = round(_clip(float(db), 0.0, LOUD_MAX_DB), 1)
    path = path or loud_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".tmp", "w") as f:
        json.dump({"loud_db": db}, f)
    os.replace(path + ".tmp", path)
    return db


def loud_payload(db: float) -> str:
    """Canlı sınırlayıcı giriş kazancı (Props yükü): müzik kesilmeden ses yükseltme."""
    return '{ params = [ "lim:Input gain (G)" %.6f ] }' % 10 ** (_clip(db, 0.0, LOUD_MAX_DB) / 20)


def _limiter_node(loud_db: float) -> str:
    """İleri bakışlı stereo bağlı sınırlayıcı. ALR (yavaş seviye düzenleme, 300 ms bırakma) tepeleri ses
    dalgasının içinde değil zarfında tutar → bas bozulmaz; ani başlangıçlar 5 ms ileri bakışla korunur."""
    g = 10 ** (_clip(loud_db, 0.0, LOUD_MAX_DB) / 20)
    ctl = {"Input gain (G)": g, "Output gain (G)": 1.0, "Threshold (G)": 10 ** (LIMIT_CEIL_DB / 20),
           "Lookahead (ms)": 5.0, "Attack time (ms)": 5.0, "Release time (ms)": 20.0,
           "Automatic level regulation": 1, "Automatic level regulation attack time (ms)": 10.0,
           "Automatic level regulation release time (ms)": 300.0, "Gain boost": 0, "Oversampling": 0,
           "Stereo linking (%)": 100.0}
    body = " ".join(f'"{k}" = {v:.6f}' if isinstance(v, float) else f'"{k}" = {v}' for k, v in ctl.items())
    return (f'                    {{ type = ladspa name = lim plugin = "{LSP_LADSPA}" '
            f'label = "http://lsp-plug.in/plugins/ladspa/limiter_stereo" control = {{ {body} }} }}')


def render_graph_ab(target_sink: str, st: dict | None = None, source: str = "-", node_suffix: str = "bta_console",
                    loud_db: float | None = None) -> str:
    """A/B zincirli smart filter-chain config metni (kopya → iki tam zincir → toplama → sınırlayıcı; hedef = BT sink)."""
    st = sanitize(st or default_state())
    loud_db = load_loud_db() if loud_db is None else loud_db
    pre = 10 ** (preamp_db(st) / 20)
    bl, br = _balance(st)
    a, b, _, _, g = _spatial(st)
    nodes, links = [], []

    def node(name, label, extra=""):
        nodes.append(f"                    {{ type = builtin name = {name} label = {label} {extra}}}")

    for ch, bal in (("L", bl), ("R", br)):
        node(f"copy{ch}", "copy")
        for c in ("A", "B"):
            node(f"pre{c}{ch}", "linear", f'control = {{ "Mult" = {pre * bal:.6f} "Add" = 0.0 }} ')
            links.append(f'{{ output = "copy{ch}:Out" input = "pre{c}{ch}:In" }}')
            prev = f"pre{c}{ch}"
            for i, bd in enumerate(st["bands"], 1):
                node(f"eq{c}{ch}_{i}", "bq_raw", _coef_block(lambda r, bd=bd: dsp.coeffs(bd, r)) + " ")
                links.append(f'{{ output = "{prev}:Out" input = "eq{c}{ch}_{i}:In" }}')
                prev = f"eq{c}{ch}_{i}"
            node(f"hi{c}{ch}", "bq_raw", _coef_block(lambda r: _spatial(st, r)[2]) + " ")
            node(f"lo{c}{ch}", "bq_raw", _coef_block(lambda r: _spatial(st, r)[3]) + " ")
            links.append(f'{{ output = "{prev}:Out" input = "hi{c}{ch}:In" }}')
            links.append(f'{{ output = "{prev}:Out" input = "lo{c}{ch}:In" }}')
    for c in ("A", "B"):
        for ch, ins in (("L", ("hi{c}L", "hi{c}R", "lo{c}R", "lo{c}L")), ("R", ("hi{c}R", "hi{c}L", "lo{c}L", "lo{c}R"))):
            node(f"mix{c}{ch}", "mixer", 'control = { "Gain 1" = %.6f "Gain 2" = %.6f "Gain 3" = %.6f "Gain 4" = %.6f } '
                 % (g * a, g * b, g * a, g * b))
            for i, src in enumerate(ins, 1):
                links.append(f'{{ output = "{src.format(c=c)}:Out" input = "mix{c}{ch}:In {i}" }}')
    for ch in ("L", "R"):
        node(f"sum{ch}", "mixer", 'control = { "Gain 1" = 1.0 "Gain 2" = 0.0 } ')     # A çalar, B sessiz
        links.append(f'{{ output = "mixA{ch}:Out" input = "sum{ch}:In 1" }}')
        links.append(f'{{ output = "mixB{ch}:Out" input = "sum{ch}:In 2" }}')
        links.append(f'{{ output = "sum{ch}:Out" input = "lim:Input {ch}" }}')
    nodes.append(_limiter_node(loud_db))
    link_txt = "\n".join("                    " + l for l in links)
    return f"""# bt-audio-hifi (PRD-BTA04 D2) — ÜRETİLMİŞ DOSYA. A/B tıksız geçiş grafı, durum A zincirinde gömülü. Kaynak: {source}
context.modules = [
    {{ name = libpipewire-module-filter-chain
        args = {{
            node.description = "BT kulaklık konsolu (bta)"
            media.name       = "BT kulaklık konsolu (bta)"
            filter.graph = {{
                nodes = [
{chr(10).join(nodes)}
                ]
                links = [
{link_txt}
                ]
                inputs  = [ "copyL:In" "copyR:In" ]
                outputs = [ "lim:Output L" "lim:Output R" ]
            }}
            audio.channels = 2
            audio.position = [ FL FR ]
            capture.props = {{
                node.name   = "effect_input.{node_suffix}"
                media.class = Audio/Sink
                filter.smart = true
                filter.smart.name = "{node_suffix.replace('_', '-')}"
                filter.smart.target = {target_spa(target_sink)}
            }}
            playback.props = {{
                node.name    = "effect_output.{node_suffix}"
                node.passive = true
            }}
        }}
    }}
]
"""


# ── D7.2 sürücü koruma + codec farkındalığı (uyarı; kullanıcının seçimi KIRPILMAZ) ──
BASS_WARN_DB = 12.0        # hazır tarzların en büyüğü +10,9 dB (ölçüldü) → yanlış alarm yok
INFRA_WARN_DB = 10.0       # 10–20 Hz: duyulmaz, yalnız diyafram gezinmesi (sürücüyü yorar)
HF_AAC_DB = 3.0            # AAC bu bağlantıda ~17 kHz'de keser (R4/R41)


def _db1(v):
    return f"{v:+.1f}".replace(".", ",")                 # Türkçe ondalık (metnin geri kalanına dokunmadan)


def protection_warnings(state: dict, codec: str | None = None) -> list:
    """Uyarılar: [{code, level: warn|info, text}]. Girdi = SESE GİDEN durum (ADL katmanı dahil)."""
    import numpy as np
    on = [b for b in state.get("bands", []) if b.get("enabled")]
    if not on:
        return []
    out = []
    lo = dsp.response_db(on, list(np.geomspace(20, 100, 40)))
    if max(lo) > BASS_WARN_DB:
        out.append({"code": "bass_high", "level": "warn",
                    "text": f"Bas takviyesi {_db1(max(lo))} dB (20–100 Hz). Yüksek seste 12 mm sürücü zorlanabilir, "
                            "bozulma (distorsiyon) duyulursa sesi ya da bası kıs. Harman araştırması: bas sevenler "
                            "hedefe +4–6 dB ekler (R38)."})
    infra = dsp.response_db(on, list(np.geomspace(10, 20, 8)))
    if max(infra) > INFRA_WARN_DB:
        out.append({"code": "sub_infra", "level": "warn",
                    "text": f"20 Hz altı {_db1(max(infra))} dB yükseltiliyor: kulak duymaz, yalnız sürücü yorulur. "
                            "Bas rafının frekansını 30 Hz üstüne al."})
    if (codec or "").lower() == "aac":
        hf = dsp.response_db(on, list(np.geomspace(17000, 20000, 10)))
        if max(hf) > HF_AAC_DB:
            pa = preamp_db(state)
            out.append({"code": "hf_aac", "level": "info",
                        "text": f"17 kHz üstü {_db1(max(hf))} dB: AAC bağlantısı bu bölgeyi zaten kesiyor (duyulmaz), "
                                f"ama kırpılmayı önleyen preamp tüm sesi {_db1(abs(pa))[1:]} dB kısıyor. Tizi 12–16 kHz'e çekersen "
                                "ses daha yüksek ve aynı parlaklıkta olur."})
    return out



def target_spa(target) -> str:
    """Smart filter hedefi SPA-JSON nesnesi. str → {node.name} (doğrulama sondaları), dict → kimlik eşleşmesi (U72)."""
    props = {"node.name": target} if isinstance(target, str) else dict(target)
    for k, v in props.items():                       # güvenlik: cihaz adı uzaktaki cihazın kontrolünde → enjeksiyon yok
        if not (isinstance(k, str) and _SAFE_KEY.fullmatch(k) and isinstance(v, str) and _SAFE_VAL.fullmatch(v)):
            raise ValueError(f"güvensiz smart filter hedefi: {k!r}={v!r}")
    return "{ " + " ".join(f'{k} = "{v}"' for k, v in props.items()) + " }"


_SAFE_KEY = re.compile(r"[A-Za-z0-9_.\-]+")
_SAFE_VAL = re.compile(r'[^"\\{}\[\]\x00-\x1f\x7f]{1,128}')


_SMART_TARGET = re.compile(r"filter\.smart\.target\s*=\s*\{([^}]*)\}")
_KV = re.compile(r'([A-Za-z0-9_.\-]+)\s*=\s*"([^"]*)"')


def smart_target(conf_text: str) -> dict | None:
    """Kurulu graf config'inin smart filter hedefi (özellik sözlüğü) — yoksa None."""
    m = _SMART_TARGET.search(conf_text or "")
    return dict(_KV.findall(m.group(1))) if m else None


def target_stale(conf_text: str, current) -> bool:
    """U71/U72: kurulu hedef, bağlı kulaklığın kimlik hedefiyle aynı değilse bayattır (eski MAC biçimi, ad değişimi).
    Kulaklık bağlı değilse (current boş) bayat SAYILMAZ: son bilinen hedef korunur, boşuna yeniden kurulum yok."""
    if not current:
        return False
    cur = {"node.name": current} if isinstance(current, str) else dict(current)
    return smart_target(conf_text) != cur
