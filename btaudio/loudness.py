"""F8 — Kulağında (in-situ) bas yanıtı: eşit-yükseklik eşleşmesi + ISO 226:2003 → kulaklık yanıtı → PEQ.

Yöntem: dinleyici her test tonunun dijital seviyesini (1 kHz referansa göre g_f dB) eşit yükseklikte duyana dek
ayarlar. Eşit yükseklikte SPL_f − SPL_1k = L_iso(f) − L_iso(1k) (ISO 226, aynı phon). SPL = S(dijital)+yanıt ⇒
    H(f) − H(1k) = [L_iso(f) − L_iso(1k)] − g_f
Geçerlilik: < 1 kHz (bas/alt-orta). Üstünde kulak kanalı/rezonans etkileri ISO 226 serbest-alan varsayımını bozar.
ISO 226 katsayıları: IoSR Surrey MatlabToolbox iso226.m ile birebir doğrulandı (docs/research/findings.md).
"""
from __future__ import annotations

import numpy as np
from scipy import optimize, signal

_F = [20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600, 2000,
      2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500]
_AF = [0.532, 0.506, 0.480, 0.455, 0.432, 0.409, 0.387, 0.367, 0.349, 0.330, 0.315, 0.301, 0.288, 0.276, 0.267,
       0.259, 0.253, 0.250, 0.246, 0.244, 0.243, 0.243, 0.243, 0.242, 0.242, 0.245, 0.254, 0.271, 0.301]
_LU = [-31.6, -27.2, -23.0, -19.1, -15.9, -13.0, -10.3, -8.1, -6.2, -4.5, -3.1, -2.0, -1.1, -0.4, 0.0, 0.3, 0.5,
       0.0, -2.7, -4.1, -1.0, 1.7, 2.5, 1.2, -2.1, -7.1, -11.2, -10.7, -3.1]
_TF = [78.5, 68.7, 59.5, 51.1, 44.0, 37.5, 31.5, 26.5, 22.1, 17.9, 14.4, 11.4, 8.6, 6.2, 4.4, 3.0, 2.2, 2.4, 3.5,
       1.7, -1.3, -4.2, -6.0, -5.4, -1.5, 6.0, 12.6, 13.9, 12.3]

FS = 48000
TEST_FREQS = [31.5, 40, 50, 63, 80, 100, 125, 160, 250, 500]
PEQ_CENTERS = [(35, 1.0), (55, 1.0), (90, 1.0), (150, 1.0), (250, 1.0), (450, 1.0)]
ANCHORS = {1000: 0.0, 2000: 0.0, 4000: 0.0}          # bas düzeltmesi yukarıyı etkilemesin


def iso226_spl(phon: float, freqs) -> list:
    out = []
    for f in freqs:
        if f not in _F:
            raise ValueError(f"ISO 226 tablo frekansı değil: {f}")
        i = _F.index(f)
        if phon == 0:
            out.append(_TF[i])
            continue
        af = 0.00447 * (10 ** (0.025 * phon) - 1.15) + (0.4 * 10 ** ((_TF[i] + _LU[i]) / 10 - 9)) ** _AF[i]
        out.append((10 / _AF[i]) * np.log10(af) - _LU[i] + 94)
    return out


def response_from_matches(matches: dict, phon: float) -> dict:
    fs = sorted(matches)
    iso = dict(zip(fs + [1000], iso226_spl(phon, fs + [1000])))
    return {f: (iso[f] - iso[1000]) - matches[f] for f in fs}


def _biquad(kind: str, f0: float, gain: float, q: float, fs=FS):
    """RBJ Audio EQ Cookbook."""
    a_ = 10 ** (gain / 40)
    w0 = 2 * np.pi * f0 / fs
    alpha = np.sin(w0) / (2 * q)
    c = np.cos(w0)
    if kind == "Bell":
        b = [1 + alpha * a_, -2 * c, 1 - alpha * a_]
        a = [1 + alpha / a_, -2 * c, 1 - alpha / a_]
    elif kind == "Lo-shelf":
        sq = 2 * np.sqrt(a_) * alpha
        b = [a_ * ((a_ + 1) - (a_ - 1) * c + sq), 2 * a_ * ((a_ - 1) - (a_ + 1) * c), a_ * ((a_ + 1) - (a_ - 1) * c - sq)]
        a = [(a_ + 1) + (a_ - 1) * c + sq, -2 * ((a_ - 1) + (a_ + 1) * c), (a_ + 1) + (a_ - 1) * c - sq]
    else:
        raise ValueError(kind)
    return np.array(b) / a[0], np.array(a) / a[0]


def eq_response_db(bands, freqs, fs=FS) -> list:
    freqs = np.asarray(freqs, dtype=float)
    tot = np.zeros(len(freqs))
    for bd in bands:
        b, a = _biquad(bd["type"], bd["frequency"], bd["gain"], bd["q"], fs)
        _, h = signal.freqz(b, a, worN=2 * np.pi * freqs / fs)
        tot += 20 * np.log10(np.abs(h))
    return tot.tolist()


def target_db(name: str, freqs) -> list:
    """Hedef eğri, 1 kHz'e göre. harman-ie-bass: AutoEQ'nun Harman IE hedefi için kullandığı 105 Hz Q0.7 low-shelf
    biçiminde +8 dB bas rafı (tam Harman eğrisinin yalnız bas bölgesi yaklaşığı)."""
    if name == "flat":
        return [0.0] * len(freqs)
    if name == "harman-ie-bass":
        ref = eq_response_db([{"type": "Lo-shelf", "frequency": 105, "gain": 8.0, "q": 0.7}], [1000])[0]
        return [v - ref for v in eq_response_db([{"type": "Lo-shelf", "frequency": 105, "gain": 8.0, "q": 0.7}], freqs)]
    raise ValueError(name)


def design_eq(h: dict, target="harman-ie-bass", max_boost_db=12.0, max_cut_db=-12.0) -> dict:
    fs = sorted(h) + sorted(ANCHORS)
    want = [t - h.get(f, 0.0) for f, t in zip(fs, target_db(target, fs))]

    grid_c = np.geomspace(20, 2000, 60)

    def bands_of(g):
        return [{"type": "Bell", "frequency": f0, "gain": gi, "q": q} for (f0, q), gi in zip(PEQ_CENTERS, g)]

    def resid(g, penalize=True):
        r = np.array(eq_response_db(bands_of(g), fs)) - np.array(want)
        if not penalize:
            return r
        # Toplam yanıt tavanı: bantlar üst üste binince tek-bant sınırı yetmez (U24 ikinci test)
        over = np.maximum(0, np.array(eq_response_db(bands_of(g), grid_c)) - max_boost_db)
        return np.concatenate([r, 10 * over])

    sol = optimize.least_squares(resid, x0=np.zeros(len(PEQ_CENTERS)),
                                 bounds=([max_cut_db] * len(PEQ_CENTERS), [max_boost_db] * len(PEQ_CENTERS)))
    bands = [{"type": "Bell", "frequency": f0, "gain": round(float(g), 2), "q": q}
             for (f0, q), g in zip(PEQ_CENTERS, sol.x)]
    grid = np.geomspace(20, 20000, 400)
    peak = max(eq_response_db(bands, grid))
    err = dict(zip(fs, np.round(resid(sol.x, penalize=False), 2).tolist()))
    return {"target": target, "bands": bands, "preamp_db": round(-max(0.0, peak), 2), "fit_error_db": err,
            "max_boost_db": max_boost_db}
