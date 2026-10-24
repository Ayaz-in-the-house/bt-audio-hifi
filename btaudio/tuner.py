"""F8 v2 — Canlı bas ayarlayıcı (kullanıcı kendi müziğini dinlerken). Saf mantık; PipeWire'a uygulama `apply_live`.

Neden v2: eşit-yükseklik eşleştirmesi (v1) sahada anlaşılmadı (2026-09-27 gerçek oturum: 9/10 'tavan'). Kullanıcının
kendi gözlemi "düşük frekansları +dB yapınca güzel bas veriyor" → doğrudan tercih ayarı, anında duyulur.
Filter-chain kontrolleri çalışırken değiştirilebilir (ölçüldü: pw-cli set-param 90 Hz +9 → ölçülen +9,00 dB).
"""
from __future__ import annotations

import numpy as np
from scipy import optimize

from . import loudness

BANDS = [  # id, merkez Hz, Q, etiket, açıklama
    ("deep", 40, 0.9, "Derin bas", "gümbürtü, yere vuran bas (40 Hz civarı)"),
    ("punch", 90, 1.0, "Vuruş", "davulun/kick'in tokluğu, bas gitarın gövdesi (90 Hz civarı)"),
    ("warmth", 200, 1.0, "Sıcaklık", "dolgunluk; fazlası sesi boğuk/çamurlu yapar (200 Hz civarı)"),
]
MIN_GAIN, MAX_GAIN = -6.0, 12.0
STEP_DB = 0.5          # sayfadaki kaydırıcı adımıyla AYNI: aksi hâlde başka kaydırıcıya dokunmak değeri sessizce kaydırır
GRID = np.geomspace(20, 2000, 120).tolist()


def _bands(gains: dict, rounded: bool = True) -> list:
    """rounded=False: optimizasyon içinde KULLAN — 0,1 dB yuvarlama amaç fonksiyonunu basamaklı yapar, sonlu fark
    gradyanı sıfır görünür ve optimizer başlangıçta durur (ölçüldü: Harman hazır ayarı 0/0/0 çıktı)."""
    out = []
    for bid, f, q, label, _ in BANDS:
        g = float(np.clip(float(gains.get(bid, 0.0)), MIN_GAIN, MAX_GAIN))
        out.append({"id": bid, "label": label, "type": "Bell", "frequency": f, "q": q,
                    "gain": round(round(g / STEP_DB) * STEP_DB, 1) if rounded else g})
    return out


def state(gains: dict) -> dict:
    bands = _bands(gains)
    peak = max(loudness.eq_response_db(bands, GRID)) if any(b["gain"] for b in bands) else 0.0
    return {"bands": bands, "preamp_db": round(-peak, 2) if peak > 0 else 0.0, "target": "user-preference"}


def _fit_harman() -> dict:
    fr = [31.5, 40, 50, 63, 80, 100, 125, 160, 250, 500, 1000, 2000]
    want = np.array(loudness.target_db("harman-ie-bass", fr))

    def resid(g):
        return np.array(loudness.eq_response_db(_bands(dict(zip([b[0] for b in BANDS], g)), rounded=False), fr)) - want

    sol = optimize.least_squares(resid, np.zeros(len(BANDS)), bounds=([MIN_GAIN] * 3, [MAX_GAIN] * 3))
    return {b[0]: round(round(float(g) / STEP_DB) * STEP_DB, 1) for b, g in zip(BANDS, sol.x)}


PRESETS = {
    "notr": {"deep": 0.0, "punch": 0.0, "warmth": 0.0},
    "hafif": {"deep": 4.0, "punch": 3.0, "warmth": 0.0},
    "harman": _fit_harman(),
    "guclu": {"deep": 10.0, "punch": 7.0, "warmth": 1.0},
}


def pw_params(st: dict, bypass: bool = False) -> str:
    """`pw-cli set-param <effect_input id> Props '<bu>'` yükü. Bant adları eqconf ile aynı: eq_band_1..N, preamp."""
    parts = [f'"preamp:Mult" {1.0 if bypass else 10 ** (st["preamp_db"] / 20):.6f}']
    for i, b in enumerate(st["bands"], 1):
        parts.append(f'"eq_band_{i}:Gain" {0.0 if bypass else b["gain"]:.1f}')
    return "{ params = [ " + " ".join(parts) + " ] }"
