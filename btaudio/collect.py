"""Canlı sistem durumu toplayıcı (salt-okuma). Her dış komut timeout'ludur; bir kaynak düşerse alan `error` taşır,
snapshot yine üretilir (kısmi durum sessizce "yok" sayılmaz)."""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import subprocess

from . import codecs, paths, state

HOME = os.path.expanduser("~")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _bt_audio_devices() -> list[dict]:
    """Bağlı BT ses kartları: [{mac, alias, form_factor}] (pactl)."""
    p = subprocess.run(["pactl", "-f", "json", "list", "cards"], capture_output=True, text=True, timeout=5)
    out = []
    for c in json.loads(p.stdout or "[]"):
        pr = c.get("properties", {})
        if pr.get("device.bus") == "bluetooth" and pr.get("api.bluez5.address"):
            out.append({"mac": pr["api.bluez5.address"].upper(),
                        "alias": pr.get("device.alias") or pr.get("device.description"),
                        "form_factor": pr.get("device.form_factor") or pr.get("device.form-factor")})
    return out


def _detect_mac() -> str:
    """C5.1 → U72 cihaz: $BTA_DEVICE → bağlı kartlardan kimlik önbelleğiyle seçilen kulaklık (bilinen MAC > aynı ad >
    kulaklık biçimli; hoparlör ASLA) → önbellekteki son MAC. Kodda sabit MAC YOK (açık kaynak: kişisel kimlik kodda durmaz)."""
    env = os.environ.get("BTA_DEVICE")
    if env:
        return env.upper()
    from . import identity
    ident = identity.load()
    try:
        dev = identity.choose(_bt_audio_devices(), ident)
        if dev:
            try:
                identity.remember(dev)
            except OSError:
                pass
            return dev["mac"]
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return ident.get("last_mac") or ""


def filter_target():
    """U72: konsol/EQ smart filter hedefi — MAC'siz kimlik (ad). Ad bilinmiyorsa (eski önbellek, kulaklık yok)
    bağlı sink adı; o da yoksa None (kurulum yapılmaz)."""
    from . import identity
    t = identity.target(identity.load().get("alias"))   # güvensiz/boş ad → None → sink adına düş
    if t:
        return t
    s = _safe(sink)
    return s.get("name") or None                    # sink() bağlı değilken name taşımaz


DEVICE_MAC = _detect_mac()
DEV_ID = DEVICE_MAC.replace(":", "_")
CARD = f"bluez_card.{DEV_ID}"
WP_STATE = os.path.join(HOME, ".local/state/wireplumber")
CONFIG_SRC = os.path.join(REPO, "config")
CONFIG_DST = os.environ.get("BTA_CONFIG_DST") or os.path.join(HOME, ".config")   # testte izole hedef
EE_APP = "com.github.wwmm.easyeffects"


def run(cmd, timeout=8):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return 127, "", str(e)


def run_json(cmd, timeout=8):
    rc, out, err = run(cmd, timeout)
    if rc != 0:
        raise RuntimeError(f"{' '.join(cmd)} rc={rc}: {err.strip()[:200]}")
    return json.loads(out)


def _safe(fn):
    try:
        return fn()
    except Exception as e:  # kaynak düşerse snapshot yine üretilsin
        return {"error": str(e)[:300]}


def versions():
    rc, out, _ = run(["rpm", "-q", "--qf", "%{NAME}=%{VERSION}-%{RELEASE}\\n",
                      "pipewire", "wireplumber", "bluez", "pipewire-libs", "fdk-aac-free"])
    v = dict(line.split("=", 1) for line in out.splitlines() if "=" in line)
    v["kernel"] = os.uname().release
    return v


def device():
    rc, out, _ = run(["bluetoothctl", "info", DEVICE_MAC])
    d = {"address": DEVICE_MAC}
    for key in ("Name", "Connected", "Paired", "Trusted"):
        m = re.search(rf"^\s*{key}: (.+)$", out, re.M)
        d[key.lower()] = m.group(1).strip() if m else None
    m = re.search(r"Battery Percentage: 0x[0-9a-f]+ \((\d+)\)", out)
    d["battery"] = int(m.group(1)) if m else None
    return d


def other_bt_devices():
    rc, out, _ = run(["bluetoothctl", "devices", "Connected"])
    return sorted(line.split(" ", 2)[2] for line in out.splitlines()
                  if line.startswith("Device") and DEVICE_MAC not in line)


def card():
    cards = run_json(["pactl", "-f", "json", "list", "cards"])
    c = next((x for x in cards if x["name"] == CARD), None)
    if c is None:
        return {"present": False}
    return {
        "present": True,
        "active_profile": c["active_profile"],
        "profiles": sorted(k for k, v in c["profiles"].items() if v.get("available", True)),
    }


def sink():
    sinks = run_json(["pactl", "-f", "json", "list", "sinks"])
    s = next((x for x in sinks if x["name"].startswith(f"bluez_output.{DEV_ID}")), None)
    if s is None:
        return {"present": False}
    ss = s["sample_specification"].split()
    return {
        "present": True,
        "name": s["name"],
        "state": s["state"],
        "format": ss[0], "channels": int(ss[1].rstrip("ch")), "rate": int(ss[2].rstrip("Hz")),
        "codec": s["properties"].get("api.bluez5.codec"),
        "profile": s["properties"].get("api.bluez5.profile"),
        "volume_pct": next(iter(s["volume"].values()))["value_percent"] if s.get("volume") else None,
    }


def _busctl_prop(path, iface, prop):
    return run_json(["busctl", "--json=short", "get-property", "org.bluez", path, iface, prop])["data"]


def bluez_endpoints():
    rc, out, _ = run(["busctl", "tree", "org.bluez", "--list"])
    paths = [p for p in out.split() if f"dev_{DEV_ID}/" in p]
    eps, transports = {}, {}
    for p in paths:
        if re.search(r"/sep\d+$", p):
            try:
                cid = _busctl_prop(p, "org.bluez.MediaEndpoint1", "Codec")
                caps = bytes(_busctl_prop(p, "org.bluez.MediaEndpoint1", "Capabilities"))
                eps[p.rsplit("/", 1)[1]] = codecs.decode(cid, caps)
            except Exception as e:
                eps[p.rsplit("/", 1)[1]] = {"error": str(e)[:200]}
        elif re.search(r"/fd\d+$", p):
            try:
                cid = _busctl_prop(p, "org.bluez.MediaTransport1", "Codec")
                conf = bytes(_busctl_prop(p, "org.bluez.MediaTransport1", "Configuration"))
                t = codecs.decode(cid, conf)
                t["state"] = _busctl_prop(p, "org.bluez.MediaTransport1", "State")
                t["delay_us"] = _busctl_prop(p, "org.bluez.MediaTransport1", "Delay") * 100
                if t.get("codec") == "AAC":
                    eff = codecs.pipewire_effective_aac_bitrate(t["bitrate"])
                    t["pipewire_target_bitrate"] = eff
                    t["pipewire_forced_bandwidth_hz"] = codecs.pipewire_aac_forced_bandwidth(t["vbr"], eff)
                transports[p.split(f"dev_{DEV_ID}/", 1)[1]] = t
            except Exception as e:
                transports[p] = {"error": str(e)[:200]}
    return {"endpoints": eps, "transports": transports}


def wp_settings():
    out = {}
    for key in ("bluetooth.autoswitch-to-headset-profile", "bluetooth.use-persistent-storage"):
        rc, o, _ = run(["wpctl", "settings", key])
        m = re.search(r"Value: (\S+)(?: \(Saved: (\S+)\))?", o)
        out[key] = {"value": m.group(1) if m else None, "saved": m.group(2) if m else None}
    return out


def wp_state():
    out = {}
    for name in ("default-profile", "bluetooth-autoswitch"):
        p = os.path.join(WP_STATE, name)
        if os.path.exists(p):
            with open(p) as f:
                kv = state.parse_wp_state(f.read())
            out[name] = {k: v for k, v in kv.items() if DEV_ID in k}
    return out


def default_nodes():
    """default.configured.* (istemcinin seçtiği) ve default.* (WirePlumber'ın etkin seçimi)."""
    rc, out, _ = run(["pw-metadata", "-n", "default", "0"])
    res = {}
    for m in re.finditer(r"key:'(default\.(?:configured\.)?audio\.(?:sink|source))' value:'([^']*)'", out):
        res[m.group(1)] = state.spa_json_name(m.group(2)) or m.group(2)
    return res


def set_configured_default_sink(name: str) -> bool:
    rc, _, _ = run(["pw-metadata", "-n", "default", "0", "default.configured.audio.sink",
                    json.dumps({"name": name}), "Spa:String:JSON"])
    return rc == 0


def graph_clock():
    rc, out, _ = run(["pw-metadata", "-n", "settings", "0"])
    return {m.group(1): m.group(2) for m in re.finditer(r"key:'(clock\.[^']+)' value:'([^']*)'", out)}


def _param(node, name):
    ps = node.get("info", {}).get("params", {}).get(name) or []
    return ps[0] if ps else {}


def streams_to_sink():
    """BT sink'e — DOĞRUDAN veya bizim smart filtrelerimiz (effect_input.bta_*) ÜZERİNDEN — giden UYGULAMA akışları.
    Filtre kurulunca uygulamalar filtreye bağlanır; yalnız sink'e bakmak gerçek çalanı gizler (ölçüldü 2026-09-27)."""
    objs = run_json(["pw-dump"], timeout=15)
    nodes = {o["id"]: o for o in objs if o.get("type") == "PipeWire:Interface:Node"}
    name = lambda i: nodes.get(i, {}).get("info", {}).get("props", {}).get("node.name", "")
    targets = {i for i in nodes if name(i).startswith(f"bluez_output.{DEV_ID}") or name(i).startswith("effect_input.bta_")}
    if not any(name(i).startswith(f"bluez_output.{DEV_ID}") for i in targets):
        return []
    links = [o["info"] for o in objs if o.get("type") == "PipeWire:Interface:Link"]
    feeders = {l["output-node-id"] for l in links if l.get("input-node-id") in targets}
    out = []
    for nid in sorted(feeders):
        n = nodes.get(nid, {})
        pr = n.get("info", {}).get("props", {})
        if pr.get("node.name", "").startswith("effect_output.bta_"):
            continue                                   # kendi filtre çıkışımız uygulama değil
        fmt = _param(n, "Format")
        out.append({
            "node": pr.get("node.name"), "app": pr.get("application.name") or pr.get("node.description"),
            "media_class": pr.get("media.class"), "state": n.get("info", {}).get("state"),
            "format": fmt.get("format"), "rate": fmt.get("rate"), "channels": fmt.get("channels"),
            "resample_quality": pr.get("resample.quality"),
            "via": next((name(l["input-node-id"]) for l in links if l.get("output-node-id") == nid
                         and l.get("input-node-id") in targets), None),
        })
    return out


def wifi():
    rc, out, _ = run(["iw", "dev"])
    m = re.search(r"channel (\d+) \((\d+) MHz\), width: (\d+) MHz", out)
    return {"channel": int(m.group(1)), "freq_mhz": int(m.group(2)), "width_mhz": int(m.group(3)),
            "band": "5GHz" if int(m.group(2)) > 4000 else "2.4GHz"} if m else {"connected": False}


def easyeffects():
    rc, out, _ = run(["flatpak", "info", "--user", EE_APP])
    if rc != 0:
        return {"installed": False}
    info = {"installed": True}
    for key in ("Version", "Commit", "Ref"):
        m = re.search(rf"^\s*{key}: (.+)$", out, re.M)
        info[key.lower()] = m.group(1).strip() if m else None
    rc, o, _ = run(["pgrep", "-f", "easyeffects --gapplication-service|/app/bin/easyeffects"])
    info["running"] = rc == 0
    return info


def configs():
    """Repo şablonları + kullanıcıya özel üretilmiş config'ler (C0) → kurulu kopyaların durumu."""
    return state.config_manifest([CONFIG_SRC, paths.generated_dir()], CONFIG_DST)


def snapshot(label: str = "") -> dict:
    snap = {"taken_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"), "label": label}
    for name, fn in [("versions", versions), ("device", device), ("other_bt_devices", other_bt_devices),
                     ("card", card), ("sink", sink), ("bluez", bluez_endpoints), ("wp_settings", wp_settings),
                     ("wp_state", wp_state), ("defaults", default_nodes), ("graph_clock", graph_clock), ("streams", streams_to_sink),
                     ("wifi", wifi), ("easyeffects", easyeffects), ("configs", configs)]:
        snap[name] = _safe(fn)
    return snap
