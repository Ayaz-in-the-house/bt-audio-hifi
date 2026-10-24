"""T-L34 — analizörün ürün katmanında doğrulaması (kulaklığa dokunmaz): null sink'e bağlı bir KOPYA konsol grafı,
analizör aynı `pw-record` + elle `pw-link` yolundan dinler. Beklenen: EQ sonrası − öncesi = model (preamp dahil),
EQ öncesi mutlak seviye = çalınan seviye."""
from __future__ import annotations

import os
import subprocess
import tempfile
import time

import numpy as np
from scipy.io import wavfile

from . import analyzer, console, eqverify, procs, resample

FS = 48000
TONES = [100.0, 1000.0, 5000.0]
LEVEL_DB = -30.0


def test_state():
    st = console.default_state()
    st["bands"][0].update(type="bell", freq=1000.0, gain=6.0, q=1.0, enabled=True)
    st["bands"][1].update(type="lowshelf", freq=200.0, gain=-3.0, q=0.7, enabled=True)
    return console.sanitize(st)


def verify(seconds=6.0) -> dict:
    st = test_state()
    tmp = tempfile.mkdtemp(prefix="bta-av-")
    probe = "bta_analyzer_probe"
    conf = os.path.join(tmp, "c.conf")
    body = console.render_graph(probe, st, "analyzerverify").split("context.modules = [", 1)[1]
    body = body.replace("effect_input.bta_console", "effect_input.bta_aprobe").replace(
        "effect_output.bta_console", "effect_output.bta_aprobe").replace('"bta-console"', '"bta-aprobe"')
    open(conf, "w").write(eqverify.BASE_CONF.rstrip()[:-1] + body)
    t = np.arange(int(FS * seconds)) / FS
    x = sum(np.sin(2 * np.pi * f * t) for f in TONES) * 10 ** (LEVEL_DB / 20)
    src = os.path.join(tmp, "tones.wav")
    wavfile.write(src, FS, np.stack([x, x], 1).astype(np.float32))
    mid = resample.null_sink(probe)
    proc = procs.spawn(["pipewire", "-c", conf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    an = analyzer.Analyzer({"pre": {"ports": ["effect_input.bta_aprobe:monitor_FL", "effect_input.bta_aprobe:monitor_FR"]},
                            "post": {"ports": ["effect_output.bta_aprobe:output_FL", "effect_output.bta_aprobe:output_FR"]}},
                           linger_s=0.1, response="fast")
    frames, pids = [], []
    try:
        time.sleep(2.5)
        sid = an.subscribe()
        time.sleep(1.0)
        pids = an.pids()
        play = procs.spawn(["pw-play", "--target", probe, src])
        t0 = time.time()
        while time.time() - t0 < seconds - 0.5:
            fr = an.wait_frame(sid, timeout=1.0)
            if fr and time.time() - t0 > 2.0 and fr["pre"]:
                frames.append(fr)
        play.wait(timeout=30)
        links = eqverify._links_through_filter()
        an.unsubscribe(sid)
        time.sleep(0.8)
        stopped = not an.running()
    finally:
        an.close()
        proc.terminate()
        proc.wait(timeout=5)
        resample.unload(mid)
    cen = np.asarray(frames[0]["f"]) if frames else np.array([])
    m = console.stereo_model(st, TONES, include_preamp=True)
    rows, worst = {}, 0.0
    for f in TONES:
        i = int(np.argmin(np.abs(np.log(cen / f))))
        pre = float(np.median([fr["pre"][i] for fr in frames]))
        post = float(np.median([fr["post"][i] for fr in frames]))
        err = (post - pre) - m["LL"][f]
        worst = max(worst, abs(err), abs(pre - (LEVEL_DB)))
        rows[int(f)] = {"pre": round(pre, 2), "post": round(post, 2), "post_minus_pre": round(post - pre, 2),
                        "model": round(m["LL"][f], 2)}
    return {"rows": rows, "frames": len(frames), "max_abs_error_db": round(worst, 3), "stopped_after_unsubscribe": stopped,
            "capture_pids": pids, "links": [l for l in links if l[1] and l[1].startswith("bta_analyzer_") and l[1] != probe]}
