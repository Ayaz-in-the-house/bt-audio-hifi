"""U72 cihaz kimliği: kulaklık = ad (alias) + bilinen MAC kümesi. MAC tek başına kimlik DEĞİLDİR.

Neden: yeniden eşleştirme / yeni ünite / TWS'de birincil tekin değişmesi yeni MAC verir. Filtre hedefi MAC'e
bağlıyken (2026-10-15) akışlar filtreyi sessizce atladı — EQ yok, analizör sessiz, otomatik mod ölü.

- Önbellek: $XDG_CONFIG_HOME/bt-audio-hifi/device.json {alias, macs[], last_mac, updated} — atomik yazım.
- Seçim (çakışma yok): bilinen MAC > aynı ad > kulaklık biçimli (headset/headphone/hands-free) cihaz.
  Hoparlör (JBL vb.) hiçbir koşulda kulaklık sayılmaz.
- Filtre hedefi: {media.class, device.api, node.description} — MAC içermez. WirePlumber smart filter hedefi
  tüm özellikleri birebir (VE) eşleştirir, regex yok (filter-utils.lua, WP 0.5.14).
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re

_SAFE_ALIAS = re.compile(r'[^"\\{}\[\]\x00-\x1f\x7f]{1,128}')
HEADPHONE_FORMS = {"headset", "headphone", "hands-free", "handsfree", "earbuds"}


def _config_dir() -> str:
    from . import paths                               # tek kaynak: BTA_HOME (test izolasyonu) > XDG_CONFIG_HOME > ~/.config
    return paths._root("config")


def default_path() -> str:
    return os.path.join(_config_dir(), "device.json")


def _empty() -> dict:
    return {"alias": None, "macs": [], "last_mac": None, "updated": None}


def load(path: str | None = None, legacy: str | None = None) -> dict:
    """legacy: C5.1 düz MAC dosyası (varsayılan: önbelleğin yanındaki `device`) — tek seferlik göç kaynağı."""
    path = path or default_path()
    try:
        d = json.load(open(path))
        if isinstance(d, dict):
            ident = _empty()
            ident.update({k: d.get(k) for k in ident if k in d})
            ident["macs"] = [str(m).upper() for m in (ident["macs"] or [])]
            return ident
    except (OSError, ValueError):
        pass
    ident = _empty()
    try:
        mac = open(legacy or os.path.join(os.path.dirname(path), "device")).read().strip().upper()
        if mac:
            ident["macs"], ident["last_mac"] = [mac], mac
    except OSError:
        pass
    return ident


def remember(dev: dict, path: str | None = None) -> dict:
    """Seçilen cihazı önbelleğe ekle (MAC kümesi büyür, ad güncellenir). Değişiklik yoksa yazmaz."""
    path = path or default_path()
    ident = load(path)
    mac = dev["mac"].upper()
    new = dict(ident)
    new["macs"] = ident["macs"] + ([mac] if mac not in ident["macs"] else [])
    new["alias"] = (dev.get("alias") if safe_alias(dev.get("alias")) else None) or ident["alias"]
    new["last_mac"] = mac
    if {k: new[k] for k in ("alias", "macs", "last_mac")} == {k: ident[k] for k in ("alias", "macs", "last_mac")}:
        return ident
    new["updated"] = _dt.datetime.now().astimezone().isoformat(timespec="seconds")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(new, f, indent=1, ensure_ascii=False)
    os.replace(tmp, path)
    return new


def is_headphone(dev: dict) -> bool:
    return str(dev.get("form_factor") or "").lower() in HEADPHONE_FORMS


def choose(devices: list[dict], ident: dict | None) -> dict | None:
    """Bağlı BT ses cihazlarından kulaklığı seç. devices: [{mac, alias, form_factor}]."""
    ident = ident or _empty()
    macs = {m.upper() for m in ident.get("macs") or []}
    for d in devices:
        if d["mac"].upper() in macs:
            return d
    if ident.get("alias"):
        for d in devices:
            if d.get("alias") == ident["alias"] and not str(d.get("form_factor") or "").lower() == "speaker":
                return d
    return next((d for d in devices if is_headphone(d)), None)


def safe_alias(alias) -> bool:
    """Cihaz adı uzaktaki cihazın yayınıdır (güvenilmez) → yalnız config'e kaçışsız yazılabilir karakterler."""
    return isinstance(alias, str) and bool(_SAFE_ALIAS.fullmatch(alias))


def target(alias: str) -> dict | None:
    """MAC'siz smart filter hedefi; güvensiz adda None (çağıran node.name'e düşer)."""
    if not safe_alias(alias):
        return None
    return {"media.class": "Audio/Sink", "device.api": "bluez5", "node.description": alias}
