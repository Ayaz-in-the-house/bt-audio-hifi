"""Encoder/resampler kalite metrikleri (numpy/scipy). Metriklerin kendisi tests/test_analysis.py ile doğrulanır."""
from __future__ import annotations

import numpy as np
from scipy import signal

SNR_CAP_DB = 200.0


def _mono(x):
    x = np.asarray(x, dtype=np.float64)
    return x.mean(axis=1) if x.ndim == 2 else x


def cutoff_frequency(y, fs: int, drop_db: float = 30.0) -> float:
    """Geniş bantlı test sinyalinde üst kesim: PSD'nin 1–8 kHz medyanından `drop_db` altına kalıcı düştüğü frekans."""
    y = _mono(y)
    f, p = signal.welch(y, fs=fs, nperseg=8192)
    pdb = 10 * np.log10(p + 1e-30)
    ref = np.median(pdb[(f >= 1000) & (f <= 8000)])
    above = np.where(pdb > ref - drop_db)[0]
    return float(f[above[-1]]) if len(above) else 0.0


def snr_db(ref, test) -> float:
    ref, test = _mono(ref), _mono(test)
    n = min(len(ref), len(test))
    ref, test = ref[:n], test[:n]
    err = np.sum((test - ref) ** 2)
    if err == 0:
        return SNR_CAP_DB
    return float(min(SNR_CAP_DB, 10 * np.log10(np.sum(ref ** 2) / err)))


def align(ref, test, max_lag: int = 48000):
    """Çapraz korelasyonla tamsayı gecikmeyi bul, test'i kaydır, iki diziyi aynı uzunluğa kırp."""
    ref, test = _mono(ref), _mono(test)
    n = min(len(ref), len(test))
    corr = signal.correlate(test[:n], ref[:n], mode="full", method="fft")
    lags = signal.correlation_lags(n, n, mode="full")
    sel = np.abs(lags) <= max_lag
    lag = int(lags[sel][np.argmax(corr[sel])])
    if lag > 0:
        test = test[lag:]
    elif lag < 0:
        ref = ref[-lag:]
    m = min(len(ref), len(test))
    return ref[:m], test[:m]


def _band(x, fs, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / fs)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, n=len(x))


def band_snr_db(ref, test, fs: int, lo: float = 20.0, hi: float = 16000.0) -> float:
    ref, test = _mono(ref), _mono(test)
    n = min(len(ref), len(test))
    return snr_db(_band(ref[:n], fs, lo, hi), _band(test[:n], fs, lo, hi))


def gain_matched(ref, test):
    """En küçük kareler kazanç eşlemesi (codec küçük seviye kayması yaparsa SNR'yi haksız düşürmesin)."""
    ref, test = _mono(ref), _mono(test)
    n = min(len(ref), len(test))
    ref, test = ref[:n], test[:n]
    g = np.dot(ref, test) / max(np.dot(test, test), 1e-30)
    return ref, test * g
