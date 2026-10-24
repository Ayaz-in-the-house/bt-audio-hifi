"""F6.2 — btmon kaydı (`btmon -r` metni) ve `btmgmt conn-info` örneklerinin ayrıştırılması.

Kayıt ROOT ister → kullanıcı `tools/btmon-capture.sh` ile alır; okuma root istemez (`btmon -r`).
Başlık satırı biçimi (BlueZ monitor/packet.c): `< ACL Data TX: Handle H flags F dlen N   #seq [hciX] <zaman>`.
A2DP medya akışı sabit aralıklı ACL TX paketleridir → büyük boşluk = takılma adayı; Mode/Role Change,
Disconnect ve Number of Completed Packets gecikmesi radyo sorunlarının izidir.
"""
from __future__ import annotations

import re
import subprocess

_HDR = re.compile(r"^([<>@=]) (.+?)(?: \(0x[0-9a-f]+\))?(?: plen \d+)?\s+#\d+ \[hci\d+\] ([\d.]+)$")
_ACL = re.compile(r"ACL Data TX: Handle (\d+) flags 0x[0-9a-f]+ dlen (\d+)")
_RSSI = re.compile(r"RSSI (-?\d+)\s+TX power (-?\d+)")
WATCH = ("Mode Change", "Role Change", "Disconnect Complete", "Link Supervision Timeout Changed",
         "Hardware Error", "Data Buffer Overflow", "Encryption Change")


def parse_trace(lines, audio_handle=None) -> dict:
    tx = []
    other = {}
    events = {k: 0 for k in WATCH}
    for line in lines:
        line = line.rstrip()
        m = _HDR.match(line)
        if not m:
            continue
        body, t = m.group(2), float(m.group(3))
        a = _ACL.search(body)
        if a:
            h, n = int(a.group(1)), int(a.group(2))
            if audio_handle is None or h == audio_handle:
                tx.append((t, n))
            else:
                other[h] = other.get(h, 0) + 1
            continue
        for k in WATCH:
            if body.startswith(f"HCI Event: {k}"):
                events[k] += 1
    gaps = [(b[0] - a[0]) * 1000 for a, b in zip(tx, tx[1:])]
    dur = (tx[-1][0] - tx[0][0]) if len(tx) > 1 else 0
    return {"acl_tx_packets": len(tx), "acl_tx_bytes": sum(n for _, n in tx),
            "kbps": round(sum(n for _, n in tx) * 8 / dur / 1000, 1) if dur else None,
            "max_gap_ms": round(max(gaps), 2) if gaps else None,
            "gaps_over_100ms": sum(1 for g in gaps if g > 100), "events": events, "other_handles": other}


def parse_rssi(lines) -> dict:
    vals, fails = [], 0
    for line in lines:
        m = _RSSI.search(line)
        if m:
            vals.append(int(m.group(1)))
        elif "failed" in line.lower():
            fails += 1
    return {"samples": len(vals), "rssi_min": min(vals) if vals else None,
            "rssi_mean": round(sum(vals) / len(vals), 1) if vals else None,
            "rssi_max": max(vals) if vals else None, "failures": fails}


def read_btsnoop(path):
    return subprocess.run(["btmon", "-r", path], capture_output=True, text=True, timeout=120).stdout.splitlines()


def dominant_handle(lines):
    """A2DP medya akışı en çok bayt taşıyan ACL tanıtıcısıdır (klavye/fare küçük paketler)."""
    tot = {}
    for line in lines:
        a = _ACL.search(line)
        if a:
            tot[int(a.group(1))] = tot.get(int(a.group(1)), 0) + int(a.group(2))
    return max(tot, key=tot.get) if tot else None
