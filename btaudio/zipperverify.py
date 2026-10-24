"""D0 fizibilite (PRD-BTA04) — canlı katsayı güncellemesi tıklama/zipper üretiyor mu?

Otomatik modlar (Auto Profile Changer, Auto Dynamic Live) EQ'yu müzik çalarken `pw-cli set-param` ile değiştirir.
Biquad katsayısını blok ortasında ani değiştirmek dalga biçiminde süreksizlik (tık) yaratabilir. Ölçüm: null sink'te
KOPYA konsol grafı, 1 kHz saf sinüs çalarken 1 kHz bell kazancı değiştirilir; çıkışın 4 kHz üstü (saf sinüste olmaması
gereken) enerjisi 5 ms'lik pencerelerde izlenir. Senaryolar: büyük sıçrama (0↔+6 dB) ve küçük adım rampası."""
from __future__ import annotations

import os
import subprocess
import tempfile
import time

import numpy as np
from scipy import signal
from scipy.io import wavfile

from . import console, eqverify, procs, resample
from .tunerserver import PwApplier

FS = 48000


def _state(gain):
    st = console.default_state()
    st["bands"][0].update(type="bell", freq=1000.0, gain=float(gain), q=1.0, enabled=True)
    return console.sanitize(st)


def _residual_db(y, t_events):
    sos = signal.butter(8, 4000, "highpass", fs=FS, output="sos")
    r = signal.sosfilt(sos, y[:, 0])
    win = int(0.005 * FS)
    n = len(r) // win
    lv = 10 * np.log10(np.maximum(np.mean(r[:n * win].reshape(n, win) ** 2, axis=1), 1e-30))
    return lv


def run(scenario: str, seconds=6.0) -> dict:
    tmp = tempfile.mkdtemp(prefix="bta-zip-")
    probe = "bta_zipper_probe"
    conf = os.path.join(tmp, "c.conf")
    body = console.render_graph(probe, _state(0), "zipperverify").split("context.modules = [", 1)[1]
    body = body.replace("effect_input.bta_console", "effect_input.bta_zprobe").replace(
        "effect_output.bta_console", "effect_output.bta_zprobe").replace('"bta-console"', '"bta-zprobe"')
    open(conf, "w").write(eqverify.BASE_CONF.rstrip()[:-1] + body)
    t = np.arange(int(FS * seconds)) / FS
    x = 10 ** (-12 / 20) * np.sin(2 * np.pi * 1000 * t)
    ramp = np.minimum(1, np.minimum(np.arange(len(t)), np.arange(len(t))[::-1]) / (0.05 * FS))
    src = os.path.join(tmp, "s.wav")
    wavfile.write(src, FS, np.stack([x * ramp] * 2, 1).astype(np.float32))
    mid = resample.null_sink(probe)
    proc = procs.spawn(["pipewire", "-c", conf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ap = PwApplier(node_name="effect_input.bta_zprobe")
    events = []
    try:
        time.sleep(2.5)
        rec = os.path.join(tmp, "rec.wav")
        r = eqverify._record_monitor_start(probe, rec, name="bta_zip_rec")
        time.sleep(0.3)
        play = procs.spawn(["pw-play", "--target", probe, src])
        t0 = time.time()
        time.sleep(1.5)
        if scenario == "jump":
            g = 0.0
            while time.time() - t0 < seconds - 1.0:
                g = 6.0 - g
                ap.apply_payload(console.pw_params(_state(g)))
                events.append(time.time() - t0)
                time.sleep(0.7)
        elif scenario.startswith("ramp"):
            g, step = 0.0, float(scenario[4:] or 0.25)
            while time.time() - t0 < seconds - 1.0:
                g = min(6.0, g + step)
                ap.apply_payload(console.pw_params(_state(g)))
                events.append(time.time() - t0)
                time.sleep(0.05)
        elif scenario == "none":
            pass
        play.wait(timeout=30)
        time.sleep(0.3)
        r.terminate()
        r.wait(timeout=5)
    finally:
        proc.terminate()
        proc.wait(timeout=5)
        resample.unload(mid)
    _, y = wavfile.read(rec)
    y = y.astype(np.float64)
    on = np.where(np.abs(y[:, 0]) > 1e-3)[0]
    y = y[on[0] + int(0.2 * FS): on[-1] - int(0.2 * FS)] if len(on) else y
    lv = _residual_db(y, events)
    return {"scenario": scenario, "updates": len(events), "residual_max_dbfs": round(float(np.max(lv)), 1),
            "residual_p50_dbfs": round(float(np.median(lv)), 1),
            "windows_over_-80": int(np.sum(lv > -80)), "windows_over_-60": int(np.sum(lv > -60)), "windows": len(lv),
            "top10": [round(float(v), 1) for v in np.sort(lv)[-10:]],
            "top_times_s": [round(float(i * 0.005), 2) for i in np.argsort(lv)[-6:]]}


def run_ab(fade_s: float = 0.05, seconds: float = 6.0, updates: str = "jump") -> dict:
    """T-L39: aynı ölçüm, A/B grafı + Crossfader ile. Beklenen: güncelleme başına tık YOK.
    updates: "jump" (0↔+6 dB, 0,7 sn) · "ramp" (0,25 dB/50 ms) · "adl" (T-L41: otomasyonun gerçek deseni — 0,5 dB
    kuantalı adım, geçiş süresi + 0,1 sn arayla, ADL_QUANT/CLASSIFY ile aynı)."""
    from . import crossfade
    tmp = tempfile.mkdtemp(prefix="bta-zipab-")
    probe = "bta_zipab_probe"
    conf = os.path.join(tmp, "c.conf")
    body = console.render_graph_ab(probe, _state(0), "zipperverify-ab", node_suffix="bta_zabprobe").split(
        "context.modules = [", 1)[1]
    open(conf, "w").write(eqverify.BASE_CONF.rstrip()[:-1] + body)
    t = np.arange(int(FS * seconds)) / FS
    x = 10 ** (-12 / 20) * np.sin(2 * np.pi * 1000 * t)
    ramp = np.minimum(1, np.minimum(np.arange(len(t)), np.arange(len(t))[::-1]) / (0.05 * FS))
    src = os.path.join(tmp, "s.wav")
    wavfile.write(src, FS, np.stack([x * ramp] * 2, 1).astype(np.float32))
    mid = resample.null_sink(probe)
    proc = procs.spawn(["pipewire", "-c", conf], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sess_cli = crossfade.PwCliSession("effect_input.bta_zabprobe")
    xf = crossfade.Crossfader(sess_cli, fade_s=fade_s)
    n, sub_t = 0, []
    try:
        time.sleep(2.5)
        rec = os.path.join(tmp, "rec.wav")
        r = eqverify._record_monitor_start(probe, rec, name="bta_zipab_rec")
        time.sleep(0.3)
        play = procs.spawn(["pw-play", "--target", probe, src])
        t0 = time.time()
        time.sleep(1.5)
        g = 0.0
        while time.time() - t0 < seconds - 1.2:
            g = (6.0 - g) if updates == "jump" else min(6.0, g + (0.5 if updates == "adl" else 0.25))
            xf.submit(_state(g), fade_s=fade_s)
            sub_t.append(round(time.time() - t0, 2))
            n += 1
            time.sleep({"jump": 0.7, "adl": fade_s + 0.1}.get(updates, 0.05))
        xf.wait_idle(5)
        final_g = g
        play.wait(timeout=30)
        time.sleep(0.3)
        r.terminate()
        r.wait(timeout=5)
    finally:
        xf.close()
        sess_cli.close()
        proc.terminate()
        proc.wait(timeout=5)
        resample.unload(mid)
    _, y = wavfile.read(rec)
    y = y.astype(np.float64)
    on = np.where(np.abs(y[:, 0]) > 1e-3)[0]
    y = y[on[0] + int(0.2 * FS): on[-1] - int(0.2 * FS)] if len(on) else y
    lv = _residual_db(y, [])
    tail = y[-int(0.5 * FS):, 0]
    level = 20 * np.log10(np.sqrt(2) * np.sqrt(np.mean(tail ** 2)))
    model = -12 + console.stereo_model(_state(final_g), [1000.0], include_preamp=True)["LL"][1000.0]
    return {"fade_s": fade_s, "updates": n, "applied": xf.applied, "errors": xf.errors,
            "residual_max_dbfs": round(float(np.max(lv)), 1), "windows_over_-90": int(np.sum(lv > -90)),
            "windows_over_-80": int(np.sum(lv > -80)), "top6": [round(float(v), 1) for v in np.sort(lv)[-6:]],
            "final_level_db": round(float(level), 2), "model_db": round(float(model), 2),
            "event_times_s": [round(float(i * 0.005) + 0.2 + on[0] / FS, 2) for i in np.where(lv > -90)[0]] if len(on) else [],
            "submit_times_s": sub_t, "play_start_s": round(float(on[0] / FS), 2) if len(on) else None,
            # ilk pencere = süzgecin başlangıç tepkisi (kırpılmış kaydın ilk örneği) → ölçüm ARTEFAKTI, tık değil
            "max_time_s": round(float(np.argmax(lv) * 0.005) + 0.2 + on[0] / FS, 2) if len(on) else None,
            "residual_after_start_dbfs": round(float(np.max(lv[int(0.3 / 0.005):])), 1) if len(lv) > 60 else None}
