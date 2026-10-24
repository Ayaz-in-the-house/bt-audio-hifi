"""F4 — PipeWire resampler kalitesinin CANLI ölçümü.

44.1 kHz çok tonlu sinyal `pw-play -P '{ resample.quality = N }'` ile BT sink'e çalınır; sink MONITOR'ü (encoder
öncesi, 48 kHz) float olarak kaydedilir; spektrumda tonlar dışındaki en büyük bileşen (SFDR), 21 kHz tonunun
48 kHz'deki görüntüsü (44100−21000 = 23100 Hz) ve gürültü tabanı ölçülür. CPU: pw-play sürecinin rusage'ı.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import time

import numpy as np
from scipy import signal
from scipy.io import wavfile

from . import collect, procs

TONES_441 = [997.0, 5000.0, 12000.0, 17000.0, 19500.0, 21000.0]
IMAGE_HZ = 44100 - 21000
GUARD_HZ = 40.0
NFFT = 65536


def _spectrum_db(x, fs):
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 2:
        x = x[:, 0]
    w = signal.windows.kaiser(NFFT, beta=20)
    segs = [x[i:i + NFFT] for i in range(0, len(x) - NFFT + 1, NFFT // 2)]
    mag = np.mean([np.abs(np.fft.rfft(s * w)) for s in segs], axis=0)
    f = np.fft.rfftfreq(NFFT, 1 / fs)
    return f, 20 * np.log10(2 * mag / w.sum() + 1e-15)


def analyze(x, fs: int) -> dict:
    f, db = _spectrum_db(x, fs)
    near = np.zeros_like(f, dtype=bool)
    tone_peaks = []
    for t in TONES_441:
        sel = np.abs(f - t) <= GUARD_HZ
        near |= sel
        tone_peaks.append(db[sel].max())
    band = (f >= 20) & (f <= min(23900, fs / 2 - 100)) & ~near
    img = np.abs(f - IMAGE_HZ) <= GUARD_HZ
    tone = float(np.median(tone_peaks))
    worst = float(db[band].max())
    return {
        "tone_level_db": round(tone, 2),
        "tone_levels_db": [round(float(p), 2) for p in tone_peaks],
        "worst_spur_db": round(worst, 2),
        "worst_spur_hz": round(float(f[band][np.argmax(db[band])]), 1),
        "image_23100_db": round(float(db[img].max()), 2),
        "noise_floor_db": round(float(np.median(db[band])), 2),
        "sfdr_db": round(tone - worst, 2),
    }


def make_tones(seconds=6, rate=44100, level_db=-20.0) -> str:
    path = os.path.join(tempfile.gettempdir(), f"bta-tones-{rate}-{seconds}s.wav")
    t = np.arange(rate * seconds) / rate
    x = sum(np.sin(2 * np.pi * fr * t) for fr in TONES_441) * 10 ** (level_db / 20)
    ramp = np.minimum(1, np.minimum(np.arange(len(t)), np.arange(len(t))[::-1]) / (0.05 * rate))
    wavfile.write(path, rate, np.stack([x * ramp] * 2, 1).astype(np.float32))
    return path


def null_sink(name="bta_resample_probe"):
    """Geçici sanal 48 kHz sink (kullanıcının kulaklığını meşgul etmeden resampler ölçümü). Modül id döner."""
    out = subprocess.run(["pactl", "load-module", "module-null-sink", f"sink_name={name}", "rate=48000",
                          "channels=2", f"sink_properties=node.description={name}"],
                         capture_output=True, text=True, timeout=10)
    if out.returncode != 0:
        raise RuntimeError(out.stderr)
    time.sleep(0.8)
    return int(out.stdout.strip())


def unload(module_id: int):
    subprocess.run(["pactl", "unload-module", str(module_id)], timeout=10)


def measure(quality: int, seconds: int = 6, sink: str | None = None) -> dict:
    """Çalar + sink monitörünü kaydeder. sink=None → gerçek BT sink (HEADFUL; başka akış varsa reddedilir)."""
    if sink is None:
        sink = collect.sink()["name"]
        busy = [s for s in collect.streams_to_sink() if s.get("state") == "running"]
        if busy:
            raise RuntimeError(f"BT sink'te başka akış çalıyor, ölçüm kirlenir: {busy}")
    src = make_tones(seconds)
    rec = os.path.join(tempfile.gettempdir(), f"bta-rec-q{quality}.wav")
    r = procs.spawn(["pw-record", "--target", sink, "-P", "{ stream.capture.sink = true }",
                          "--format", "f32", "--rate", "48000", "--channels", "2", rec])
    time.sleep(0.8)
    p = procs.spawn(["pw-play", "--target", sink, "-P", f"{{ resample.quality = {quality} }}", src])
    _, status, ru = os.wait4(p.pid, 0)
    p.returncode = os.waitstatus_to_exitcode(status)
    time.sleep(0.5)
    r.terminate()
    r.wait(timeout=5)
    fs, y = wavfile.read(rec)
    y = y.astype(np.float64)
    env = np.abs(y[:, 0])
    on = np.where(env > 10 ** (-40 / 20))[0]
    y = y[on[0] + fs // 2: on[-1] - fs // 2] if len(on) > fs * 2 else y   # yalnız kararlı orta bölüm
    res = analyze(y, fs)
    res.update({"quality": quality, "cpu_s": round(ru.ru_utime + ru.ru_stime, 3), "audio_s": seconds,
                "cpu_pct_of_one_core": round(100 * (ru.ru_utime + ru.ru_stime) / seconds, 2),
                "analyzed_s": round(len(y) / fs, 2), "play_rc": p.returncode})
    return res
