"""C2 — Grafik EQ presetlerini (ör. VLC 10 bant) kompakt parametrik EQ'ya dönüştürme.

Neden: yayımlanmış grafik presetler 10 sabit bant kullanır; konsolda 10 bandın hepsini doldurmak kullanıcıya ince ayar
için yer bırakmaz. AutoEQ'nun yaptığı gibi hedef eğriye az sayıda parametrik bantla uydururuz.

Hedef eğri: bant değerleri log-frekansta doğrusal ara değerlenir (grafik EQ'nun alışılmış gösterimi), 1 kHz'e göre
sıfırlanır (tonal denge biçimi; genel seviye otomatik preamp'ın işi) ve `scale` ile ölçeklenir.
Uydurma YALNIZ tasarım anında koşar; sonuç `console.PRESETS`'e sabit sayı olarak yazılır ve U43 aynı hedefe karşı
hata ≤ 1 dB'yi yeniden ÖLÇER (kaynak → ses zinciri çalıştırılabilir kanıt)."""
from __future__ import annotations

import numpy as np
from scipy import optimize

from . import dsp

VLC_CENTERS = (60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000)   # equalizer_presets.h
FIT_GRID = np.geomspace(30, 16000, 160)


def target_curve(centers, values, scale=1.0, freqs=FIT_GRID):
    """Grafik EQ merkez/değerlerinden sürekli hedef eğri (log-frekans ara değer)."""
    c, v = np.log10(np.asarray(centers, float)), np.asarray(values, float)
    ref = np.interp(np.log10(1000.0), c, v)
    return scale * (np.interp(np.log10(freqs), c, v) - ref)


def _bands(x, kinds):
    out = []
    for i, k in enumerate(kinds):
        f, g, q = 10 ** x[3 * i], x[3 * i + 1], 10 ** x[3 * i + 2]
        out.append({"type": k, "freq": float(f), "gain": float(g), "q": float(q), "enabled": True})
    return out


def fit(centers, values, scale=0.5, max_err_db=1.0, max_bands=7):
    """En az bantla max|hata| ≤ max_err_db. Dönüş: (bantlar, max_hata). Deterministik (sabit başlangıçlar)."""
    t = target_curve(centers, values, scale)
    best = None
    for n in range(3, max_bands + 1):
        kinds = ["lowshelf"] + ["bell"] * (n - 2) + ["highshelf"]
        inner = np.geomspace(120, 8000, n - 2) if n > 2 else []
        x0 = [np.log10(100), 0, np.log10(0.7)]
        for f in inner:
            x0 += [np.log10(f), float(np.interp(np.log10(f), np.log10(FIT_GRID), t)), np.log10(1.0)]
        x0 += [np.log10(8000), 0, np.log10(0.7)]
        lo, hi = [], []
        for k in kinds:                          # tip başına anlamlı aralık: kullanıcı düzenlerken "18 kHz'te bas rafı" görmesin
            f_lo, f_hi = {"lowshelf": (40, 400), "highshelf": (1500, 14000), "bell": (30, 16000)}[k]
            lo += [np.log10(f_lo), -12, np.log10(0.3 if k == "bell" else 0.5)]
            hi += [np.log10(f_hi), 12, np.log10(4.0 if k == "bell" else 1.0)]

        def resid(x):                            # küçük kazanç cezası: eşdeğer çözümler arasında en ölçülüsü
            b = _bands(x, kinds)
            return np.concatenate([np.asarray(dsp.response_db(b, FIT_GRID)) - t, 0.05 * x[1::3]])
        res = optimize.least_squares(resid, np.clip(x0, lo, hi), bounds=(lo, hi), max_nfev=4000)
        bands = [{**b, "freq": round(b["freq"]), "gain": round(b["gain"], 1), "q": round(b["q"], 2)}
                 for b in _bands(res.x, kinds) if abs(b["gain"]) >= 0.3]
        err = float(np.max(np.abs(np.asarray(dsp.response_db(bands, FIT_GRID)) - t)))
        if best is None or err < best[1]:
            best = (bands, err)
        if err <= max_err_db:
            return bands, err
    return best


def fit_error(bands, centers, values, scale=0.5) -> float:
    """Uydurulan parametrik EQ ile hedef arasındaki en büyük mutlak hata (dB)."""
    t = target_curve(centers, values, scale)
    return float(np.max(np.abs(np.asarray(dsp.response_db(bands, FIT_GRID)) - t)))
