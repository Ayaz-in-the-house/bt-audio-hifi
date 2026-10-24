"""Saf durum mantığı: snapshot diff, WirePlumber state dosyası ayrıştırma, config drop-in manifesti."""
from __future__ import annotations

import hashlib
import os
import re

# Durum geçişi analizinde gürültü üreten, anlam taşımayan alanlar (tam yol veya son bileşen)
VOLATILE = {"taken_at", "label", "battery", "uptime", "load", "delay_us"}


def _flatten(d, prefix=""):
    out = {}
    if isinstance(d, dict):
        for k, v in d.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict):
                out.update(_flatten(v, key))
            else:
                out[key] = v
    return out


def _volatile(key: str) -> bool:
    return key in VOLATILE or key.rsplit(".", 1)[-1] in VOLATILE


def diff(a: dict, b: dict) -> dict:
    fa = {k: v for k, v in _flatten(a).items() if not _volatile(k)}
    fb = {k: v for k, v in _flatten(b).items() if not _volatile(k)}
    return {
        "changed": {k: [fa[k], fb[k]] for k in sorted(fa.keys() & fb.keys()) if fa[k] != fb[k]},
        "added": {k: fb[k] for k in sorted(fb.keys() - fa.keys())},
        "removed": {k: fa[k] for k in sorted(fa.keys() - fb.keys())},
    }


def parse_wp_state(text: str) -> dict:
    """~/.local/state/wireplumber/<dosya> — `[grup]` başlıkları + `anahtar=değer` satırları (değer JSON olabilir)."""
    out = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("[") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k] = v
    return out


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def config_manifest(src_roots, dst_root: str) -> dict:
    """Her kaynak kökteki (repo şablonları + üretilmiş kullanıcı config'i) her dosya için kurulu kopyanın durumu:
    ok | drift | missing. `src` alanı hangi kökten kurulacağını söyler (C0: iki kök)."""
    if isinstance(src_roots, str):
        src_roots = [src_roots]
    out = {}
    for src_root in src_roots:
        for base, _dirs, files in os.walk(src_root):
            for name in sorted(files):
                if name.startswith(".") or name.endswith(".md"):
                    continue
                src = os.path.join(base, name)
                rel = os.path.relpath(src, src_root)
                dst = os.path.join(dst_root, rel)
                s = sha256_file(src)
                if not os.path.exists(dst):
                    out[rel] = {"status": "missing", "sha": s, "src": src}
                else:
                    d = sha256_file(dst)
                    out[rel] = {"status": "ok" if d == s else "drift", "sha": s, "installed_sha": d, "src": src}
    return out


_NAME_RE = re.compile(r'"name"\s*:?\s*"([^"]*)"')


def spa_json_name(value: str):
    """SPA JSON'daki `name` alanı. SPA JSON iki nokta üst üsteyi zorunlu tutmaz; PipeWire'ın kendi modülleri
    `{ "name""x" }` yazabilir (module-switch-on-connect.c:142) → katı json.loads bunu reddeder."""
    m = _NAME_RE.search(value or "")
    return m.group(1) if m else None
