"""T-L32 — tam stereo konsol grafının null sink'te ürün doğrulaması: L-only ve R-only girişte her iki çıkış kanalının
ton seviyeleri ↔ console.stereo_model (preamp dahil). Kulaklığa dokunmaz."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time

import numpy as np
from scipy.io import wavfile

from . import console, eqverify, procs, resample

FS = 48000
TONES = [40.0, 100.0, 300.0, 1000.0, 3000.0, 8000.0, 15000.0]


def _levels(y, ch):
    return eqverify.tone_levels(y[:, ch:ch + 1], freqs=TONES)


def _src(path, side):
    t = np.arange(FS * 4) / FS
    x = sum(np.sin(2 * np.pi * f * t) for f in TONES) * 10 ** (-30 / 20)
    ramp = np.minimum(1, np.minimum(np.arange(len(t)), np.arange(len(t))[::-1]) / (0.05 * FS))
    z = np.zeros_like(x)
    st = np.stack([x * ramp, z] if side == "L" else [z, x * ramp], 1)
    wavfile.write(path, FS, st.astype(np.float32))


def verify(state: dict) -> dict:
    tmp = tempfile.mkdtemp(prefix="bta-cv-")
    probe = "bta_console_probe"
    conf = os.path.join(tmp, "c.conf")
    body = console.render_graph(probe, state, "consoleverify").split("context.modules = [", 1)[1]
    body = body.replace("effect_input.bta_console", "effect_input.bta_cprobe").replace(
        "effect_output.bta_console", "effect_output.bta_cprobe").replace('"bta-console"', '"bta-cprobe"')
    open(conf, "w").write(eqverify.BASE_CONF.rstrip()[:-1] + body)
    mid = resample.null_sink(probe)
    proc = procs.spawn(["pipewire", "-c", conf], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    out = {}
    try:
        time.sleep(2.5)
        for side in ("L", "R"):
            src = os.path.join(tmp, f"{side}.wav")
            _src(src, side)
            # referans: aynı tonların giriş seviyesi (filtre yokken tek kanal = girişin kendisi)
            t = np.arange(FS * 4) / FS
            ref = eqverify.tone_levels(sum(np.sin(2 * np.pi * f * t) for f in TONES) * 10 ** (-30 / 20), freqs=TONES)
            y = eqverify._capture(probe, src, os.path.join(tmp, f"rec{side}.wav"))
            out[side] = {"L": _levels(y, 0), "R": _levels(y, 1), "ref": ref}
        err = proc.stderr.read() if proc.poll() is not None else ""
    finally:
        proc.terminate(); proc.wait(timeout=5); resample.unload(mid)
    m = console.stereo_model(state, TONES, include_preamp=True)
    rows, worst = {}, 0.0
    for side, (same, cross) in (("L", ("LL", "LR")), ("R", ("RR", "RL"))):
        for f in TONES:
            meas_same = out[side][side][f] - out[side]["ref"][f]
            other = "R" if side == "L" else "L"
            meas_cross = out[side][other][f] - out[side]["ref"][f]
            e1 = meas_same - m[same][f]
            e2 = (meas_cross - m[cross][f]) if m[cross][f] > -60 else 0.0
            worst = max(worst, abs(e1), abs(e2))
            rows[f"{side}{int(f)}"] = {"same": round(meas_same, 2), "model_same": round(m[same][f], 2),
                                       "cross": round(meas_cross, 2), "model_cross": round(m[cross][f], 2)}
    return {"rows": rows, "max_abs_error_db": round(worst, 3), "pipewire_error": err}
