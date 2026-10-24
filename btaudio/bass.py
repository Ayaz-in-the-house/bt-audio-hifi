"""F8 — Bas analizi: eşleştirme dosyaları → kulakta yanıt, sızdırmazlık kazancı, phon duyarlılığı, EQ tasarımı."""
from __future__ import annotations

import json

import numpy as np

from . import loudness

LOW = [31.5, 40, 50, 63]
SEAL_THRESHOLD_DB = 3.0
DEFICIT_THRESHOLD_DB = -6.0


MAX_FLAGS = 2
PLAUSIBLE_DEV_DB = {"low": 30.0, "high": 20.0}     # |ayar − düz beklenti|: <80 Hz sızdırmazlık payı daha geniş


class LowQualityRun(ValueError):
    """Eşleştirme verisi fiziksel olarak inandırıcı değil → EQ üretilmez (yanlış EQ, EQ'suzdan kötüdür)."""


def quality_problems(d) -> list:
    """Ölçüm oturumunun inandırıcılık kontrolü (2026-09-27 gerçek oturum: 9/10 'tavan', 500 Hz +40 dB)."""
    probs = []
    flags = d.get("flags", {})
    if len(flags) > MAX_FLAGS:
        probs.append(f"{len(flags)} frekansta 'tavan' düğmesi kullanılmış (en fazla {MAX_FLAGS})")
    iso = dict(zip(loudness.TEST_FREQS + [1000], loudness.iso226_spl(d.get("assumed_phon", 65),
                                                                        loudness.TEST_FREQS + [1000])))
    for k, v in d["matches"].items():
        f = float(k)
        exp = iso[f] - iso[1000]
        lim = PLAUSIBLE_DEV_DB["low" if f < 80 else "high"]
        if abs(v - exp) > lim:
            probs.append(f"{_k(f)} Hz: ayar {v:+.1f} dB, düz bir kulaklık için beklenen {exp:+.1f} dB "
                         f"(fark {v - exp:+.1f} > ±{lim:.0f}) — gerçek kulaklık sapması bu kadar olmaz")
    return probs


def _k(f):
    return f"{float(f):g}"


def load(path):
    d = json.load(open(path))
    if d.get("tool") != "bta-loudness-match":
        raise ValueError(f"{path}: bta-loudness-match dosyası değil")
    d["_path"] = path
    d["_fit"] = d["fit"].split(":", 1)[0]
    return d


def analyze(paths, target="harman-ie-bass", max_boost_db=12.0, basis=None, force=False) -> dict:
    runs = {}
    for d in sorted((load(p) for p in paths), key=lambda x: x["created"]):
        probs = quality_problems(d)
        if probs and not force:
            raise LowQualityRun(f"{d['_path']}: " + " · ".join(probs))
        runs[d["_fit"]] = d                                   # her oturma tipinin EN YENİ koşusu
    out = {"runs": {}, "target": target}
    resp = {}
    for fit, d in runs.items():
        m = {float(k): float(v) for k, v in d["matches"].items() if v is not None}
        h = loudness.response_from_matches(m, d.get("assumed_phon", 65))
        resp[fit] = h
        out["runs"][fit] = {"file": d["_path"], "created": d["created"], "fit_label": d["fit"],
                            "flags": d.get("flags", {}), "response_db": {_k(f): round(v, 2) for f, v in h.items()}}
    basis = basis or ("normal" if "normal" in resp else next(iter(resp)))
    out["design_basis"] = basis
    d0 = runs[basis]
    m0 = {float(k): float(v) for k, v in d0["matches"].items()}
    h60, h70 = loudness.response_from_matches(m0, 60), loudness.response_from_matches(m0, 70)
    out["phon_sensitivity_db"] = {_k(f): round(abs(h60[f] - h70[f]), 2) for f in m0}
    if "normal" in resp and "bastirilmis" in resp:
        out["seal_gain_db"] = {_k(f): round(resp["bastirilmis"][f] - resp["normal"][f], 2) for f in resp["normal"]}
    else:
        out["seal_gain_db"] = None
    hb = resp[basis]
    low_def = float(np.mean([hb[f] for f in LOW if f in hb]))
    seal_low = (float(np.mean([out["seal_gain_db"][_k(f)] for f in LOW])) if out["seal_gain_db"] else None)
    if seal_low is not None and seal_low >= SEAL_THRESHOLD_DB:
        out["verdict"] = (f"seal — bastırınca 31–63 Hz ortalama +{seal_low:.1f} dB: bas kaybının ana nedeni tıkaç "
                          "sızdırmazlığı. Önce daha büyük/köpük tıkaç; EQ ikinci adım.")
    elif low_def <= DEFICIT_THRESHOLD_DB:
        out["verdict"] = (f"tuning — 31–63 Hz ortalama {low_def:.1f} dB (1 kHz'e göre): kulaklık akordu bas-zayıf; "
                          "EQ ile telafi edilir.")
    else:
        out["verdict"] = f"near-target — 31–63 Hz ortalama {low_def:.1f} dB."
    out["low_band_mean_db"] = round(low_def, 2)
    out["seal_low_mean_db"] = None if seal_low is None else round(seal_low, 2)
    out["design"] = loudness.design_eq(hb, target=target, max_boost_db=max_boost_db)
    return out
