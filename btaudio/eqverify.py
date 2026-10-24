"""T-L30 — Smart filter-chain EQ'sunun ÜRÜN katmanında doğrulanması: tasarım modeli ↔ gerçekten uygulanan yanıt.

Kulaklığı meşgul etmemek için geçici null sink hedeflenir: ayrı bir `pipewire -c <conf>` süreci aynı
filter-chain modülünü yükler; WirePlumber smart-filter politikası onu hedefin önüne sokar; çok tonlu sinyal hedefe
çalınır, hedefin monitörü kaydedilir; her tonun seviyesi ölçülür ve `loudness.eq_response_db + preamp` ile
karşılaştırılır.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time

import numpy as np
from scipy import signal
from scipy.io import wavfile

from . import eqconf, loudness, procs, resample

FS = 48000
TONES = [40.0, 63.0, 90.0, 150.0, 250.0, 500.0, 1000.0, 4000.0]
BASE_CONF = """context.properties = { log.level = 0 }
context.spa-libs = { audio.convert.* = audioconvert/libspa-audioconvert  support.* = support/libspa-support }
context.modules = [
    { name = libpipewire-module-rt args = { } flags = [ ifexists nofail ] }
    { name = libpipewire-module-protocol-native }
    { name = libpipewire-module-client-node }
    { name = libpipewire-module-adapter }
]
"""


def tone_levels(x, fs=FS, freqs=TONES):
    x = np.asarray(x, dtype=np.float64)
    x = x[:, 0] if x.ndim == 2 else x
    n = 1 << int(np.floor(np.log2(len(x))))
    w = signal.windows.kaiser(n, 20)
    spec = np.abs(np.fft.rfft(x[:n] * w)) * 2 / w.sum()
    f = np.fft.rfftfreq(n, 1 / fs)
    return {fr: float(20 * np.log10(spec[np.abs(f - fr) <= 3].max() + 1e-15)) for fr in freqs}


def _multitone(path, seconds=5, level_db=-30.0):
    t = np.arange(FS * seconds) / FS
    x = sum(np.sin(2 * np.pi * fr * t) for fr in TONES) * 10 ** (level_db / 20)
    ramp = np.minimum(1, np.minimum(np.arange(len(t)), np.arange(len(t))[::-1]) / (0.05 * FS))
    wavfile.write(path, FS, np.stack([x * ramp] * 2, 1).astype(np.float32))


def _record_monitor_start(sink: str, out: str, name="bta_eqv_rec"):
    """Hedef sink'in MONITOR portlarına ELLE bağlanan kayıt. Otomatik bağlantı kullanılmaz: WirePlumber smart filter,
    hedefi monitörleyen yakalama akışlarını da filtrenin GİRİŞİNE yönlendirir (ölçüldü: EQ öncesi sinyal kaydedildi)."""
    r = procs.spawn(["pw-record", "-P", f'{{ node.name = "{name}" node.autoconnect = false }}',
                          "--format", "f32", "--rate", "48000", "--channels", "2", out],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.8)
    for ch in ("FL", "FR"):
        subprocess.run(["pw-link", f"{sink}:monitor_{ch}", f"{name}:input_{ch}"], timeout=10, check=True)
    return r


def _trim(y):
    on = np.where(np.abs(y[:, 0]) > 1e-4)[0]
    return y[on[0] + FS // 2: on[-1] - FS // 2] if len(on) > FS * 2 else y


def _capture(sink, src, rec):
    r = _record_monitor_start(sink, rec)
    time.sleep(0.3)
    subprocess.run(["pw-play", "--target", sink, src], timeout=60)
    time.sleep(0.4)
    r.terminate()
    r.wait(timeout=5)
    _, y = wavfile.read(rec)
    return _trim(y.astype(np.float64))


def _links_through_filter():
    objs = json.loads(subprocess.run(["pw-dump"], capture_output=True, text=True, timeout=15).stdout)
    nodes = {o["id"]: o["info"]["props"].get("node.name") for o in objs if o.get("type") == "PipeWire:Interface:Node"}
    return sorted({(nodes.get(o["info"]["output-node-id"]), nodes.get(o["info"]["input-node-id"]))
                   for o in objs if o.get("type") == "PipeWire:Interface:Link"})


def verify(design: dict, probe_sink="bta_eq_probe") -> dict:
    tmp = tempfile.mkdtemp(prefix="bta-eqv-")
    src, rec_dry, rec_wet = (os.path.join(tmp, n) for n in ("tones.wav", "dry.wav", "wet.wav"))
    _multitone(src)
    mid = resample.null_sink(probe_sink)
    proc = None
    try:
        dry = tone_levels(_capture(probe_sink, src, rec_dry))            # filtresiz referans
        conf = os.path.join(tmp, "eq-probe.conf")
        body = eqconf.render_filter_chain(design, probe_sink, source="eqverify").split("context.modules = [", 1)[1]
        with open(conf, "w") as f:
            f.write(BASE_CONF.rstrip()[:-1] + body.replace("effect_input.bta_bass_eq", "effect_input.bta_eq_probe")
                    .replace("effect_output.bta_bass_eq", "effect_output.bta_eq_probe")
                    .replace('"bta-bass-eq"', '"bta-eq-probe"'))
        proc = procs.spawn(["pipewire", "-c", conf], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        time.sleep(2.0)
        links_during = []
        wet_lvls = None
        r = _record_monitor_start(probe_sink, rec_wet)
        time.sleep(0.3)
        p = procs.spawn(["pw-play", "--target", probe_sink, src])
        time.sleep(2.0)
        links_during = _links_through_filter()
        p.wait(timeout=60)
        time.sleep(0.4)
        r.terminate()
        r.wait(timeout=5)
        _, y = wavfile.read(rec_wet)
        wet_lvls = tone_levels(_trim(y.astype(np.float64)))
    finally:
        if proc:
            proc.terminate()
            proc.wait(timeout=5)
        resample.unload(mid)
    model = dict(zip(TONES, loudness.eq_response_db(design["bands"], TONES)))
    rows = {f: {"measured_db": round(wet_lvls[f] - dry[f], 2),
                "model_db": round(model[f] + design["preamp_db"], 2)} for f in TONES}
    for v in rows.values():
        v["error_db"] = round(v["measured_db"] - v["model_db"], 2)
    through = [l for l in links_during if l[0] and "bta_eq_probe" in str(l)]
    return {"rows": rows, "max_abs_error_db": max(abs(v["error_db"]) for v in rows.values()),
            "filter_links": through, "stream_went_through_filter":
                any(a == "pw-play" and b == "effect_input.bta_eq_probe" for a, b in through) or
                any("effect_input.bta_eq_probe" == b for a, b in through)}
