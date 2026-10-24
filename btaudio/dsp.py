"""RBJ Audio EQ Cookbook biquad katsayıları — PipeWire filter-chain `bq_raw` düğümüne CANLI yazılır.

`bq_raw` için impl->type = BQ_NONE → bq_run her blokta b0..a2 portlarını okur ve değiştiyse günceller
(docs/research/upstream/plugin_builtin.c:275, 545-556). Böylece tip dahil her şey servis yeniden başlatılmadan
değişir. Katsayılar a0=1'e normalize edilir (bq_raw ayrıca 1/a0 ile çarpar; ikisi tutarlı).
"""
from __future__ import annotations

import math

import numpy as np

FS = 48000
TYPES = ("bell", "lowshelf", "highshelf", "lowpass", "highpass", "notch")
IDENTITY = {"b0": 1.0, "b1": 0.0, "b2": 0.0, "a0": 1.0, "a1": 0.0, "a2": 0.0}


def coeffs(band: dict, fs: int = FS) -> dict:
    """Bir bandın normalize biquad katsayıları [b0,b1,b2,a1,a2] (RBJ; kapalıysa geçirgen)."""
    t = band["type"]
    if t not in TYPES:
        raise ValueError(f"bilinmeyen filtre tipi: {t}")
    if not band.get("enabled", True):
        return dict(IDENTITY)
    f0 = min(max(float(band["freq"]), 10.0), fs / 2 * 0.95)
    q = max(float(band.get("q", 0.7071)), 0.05)
    a_ = 10 ** (float(band.get("gain", 0.0)) / 40)
    w0 = 2 * math.pi * f0 / fs
    c, s = math.cos(w0), math.sin(w0)
    alpha = s / (2 * q)
    if t == "bell":
        b = (1 + alpha * a_, -2 * c, 1 - alpha * a_)
        a = (1 + alpha / a_, -2 * c, 1 - alpha / a_)
    elif t in ("lowshelf", "highshelf"):
        sq = 2 * math.sqrt(a_) * alpha
        if t == "lowshelf":
            b = (a_ * ((a_ + 1) - (a_ - 1) * c + sq), 2 * a_ * ((a_ - 1) - (a_ + 1) * c), a_ * ((a_ + 1) - (a_ - 1) * c - sq))
            a = ((a_ + 1) + (a_ - 1) * c + sq, -2 * ((a_ - 1) + (a_ + 1) * c), (a_ + 1) + (a_ - 1) * c - sq)
        else:
            b = (a_ * ((a_ + 1) + (a_ - 1) * c + sq), -2 * a_ * ((a_ - 1) + (a_ + 1) * c), a_ * ((a_ + 1) + (a_ - 1) * c - sq))
            a = ((a_ + 1) - (a_ - 1) * c + sq, 2 * ((a_ - 1) - (a_ + 1) * c), (a_ + 1) - (a_ - 1) * c - sq)
    elif t == "lowpass":
        b = ((1 - c) / 2, 1 - c, (1 - c) / 2)
        a = (1 + alpha, -2 * c, 1 - alpha)
    elif t == "highpass":
        b = ((1 + c) / 2, -(1 + c), (1 + c) / 2)
        a = (1 + alpha, -2 * c, 1 - alpha)
    else:  # notch
        b = (1.0, -2 * c, 1.0)
        a = (1 + alpha, -2 * c, 1 - alpha)
    n = a[0]
    return {"b0": b[0] / n, "b1": b[1] / n, "b2": b[2] / n, "a0": 1.0, "a1": a[1] / n, "a2": a[2] / n}


def freq_response(k: dict, freqs, fs: int = FS):
    """H(e^jw) = (b0 + b1 z⁻¹ + b2 z⁻²)/(a0 + a1 z⁻¹ + a2 z⁻²) — saf numpy (scipy.freqz ile aynı matematik, ~100×
    daha hızlı; istek yolunda her değişiklikte hesaplanıyor → D1 gecikme bütçesi, U52)."""
    w = 2 * np.pi * np.asarray(freqs, dtype=float) / fs
    z1 = np.exp(-1j * w)
    z2 = z1 * z1
    return (k["b0"] + k["b1"] * z1 + k["b2"] * z2) / (k.get("a0", 1.0) + k["a1"] * z1 + k["a2"] * z2)


def response_db(bands, freqs, fs: int = FS) -> list:
    """Bant listesinin toplam genlik yanıtı (dB), verilen frekanslarda."""
    freqs = np.asarray(freqs, dtype=float)
    tot = np.zeros(len(freqs))
    for bd in bands:
        k = coeffs(bd, fs)
        h = freq_response(k, freqs, fs)
        tot += 20 * np.log10(np.maximum(np.abs(h), 1e-12))
    return tot.tolist()
