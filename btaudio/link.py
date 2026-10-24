"""F6 — Bağlantı sağlığı: A2DP soket tamponu dolduğunda PipeWire encoder bitrate'i düşürür ve paketi atlar.

Kaynak: media-sink.c (PipeWire 1.6.8)
  :1080 flush_buffer() == -EAGAIN → :1088 codec->reduce_bitpool() → debug "reduce bitpool: <yeni>"  → paket ATLANIR
  :1160 1 sn hatasız + gönderilmemiş veri yok → increase_bitpool() → debug "increase bitpool: <yeni|0=tavanda>"
AAC için reduce = ×2/3, increase = ×4/3 (a2dp-codec-aac.c:631/637, alt sınır 64 kbps).
"""
from __future__ import annotations

import os
import re
import subprocess
import tempfile
import time

from . import collect

TOPIC = "spa.bluez5.sink.media"
_RE = re.compile(r"(reduce|increase) bitpool: (-?\d+)")


def parse(lines, seconds: float) -> dict:
    reduce, increase, recoveries = [], [], []
    for line in lines:
        m = _RE.search(line)
        if not m:
            continue
        val = int(m.group(2))
        if m.group(1) == "reduce":
            reduce.append(val)
        else:
            increase.append(val)
            if val > 0:
                recoveries.append(val)
    if not reduce and not increase:
        verdict = "NO_DATA"
    elif reduce:
        verdict = "DEGRADED"
    else:
        verdict = "CLEAN"
    return {
        "seconds": seconds,
        "reduce_events": len(reduce),
        "increase_events": len(increase),
        "min_bitrate_seen": min(reduce) if reduce else None,
        "recoveries": recoveries,
        "verdict": verdict,
    }


def _cursor():
    out = subprocess.run(["journalctl", "--user", "-u", "wireplumber", "-n", "0", "--show-cursor"],
                         capture_output=True, text=True, timeout=10).stdout
    m = re.search(r"-- cursor: (\S+)", out)
    return m.group(1) if m else None


def _lines_after(cursor):
    cmd = ["journalctl", "--user", "-u", "wireplumber", "--no-pager", "-o", "short-precise"]
    cmd += ["--after-cursor", cursor] if cursor else ["--since", "-5min"]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout.splitlines()


def quiet_signal(seconds: int) -> str:
    """-50 dBFS civarı pembe gürültü: CBR AAC tam boy paket üretir ama kulağı rahatsız etmez."""
    path = os.path.join(tempfile.gettempdir(), f"bta-pink-quiet-{seconds}s.wav")
    if not os.path.exists(path):
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                        f"anoisesrc=color=pink:sample_rate=48000:amplitude=0.003:duration={seconds}",
                        "-af", "aformat=channel_layouts=stereo", path], check=True, timeout=60)
    return path


def run_test(seconds: int = 30, passive: bool = False) -> dict:
    """Debug günlüğünü YALNIZ bu konu için aç, çal (veya pasif izle), günlüğü ayrıştır, düzeyi her durumda geri al."""
    sink = collect.sink()
    if not sink.get("present"):
        return {"verdict": "NO_DEVICE"}
    cursor = _cursor()
    subprocess.run(["wpctl", "set-log-level", f"2,{TOPIC}:4"], timeout=10)
    try:
        t0 = time.time()
        if passive:
            time.sleep(seconds)
        else:
            subprocess.run(["pw-play", "--target", sink["name"], quiet_signal(seconds)], timeout=seconds + 30)
        dur = time.time() - t0
        time.sleep(1.5)
        res = parse(_lines_after(cursor), round(dur, 1))
    finally:
        subprocess.run(["wpctl", "set-log-level", "2"], timeout=10)
    res.update({"mode": "passive" if passive else "active-quiet-pink", "codec": sink.get("codec"),
                "transport": collect._safe(collect.bluez_endpoints).get("transports"),
                "wifi": collect._safe(collect.wifi), "other_bt_devices": collect._safe(collect.other_bt_devices)})
    return res
