"""C0 — Ürün / kullanıcı verisi ayrımı (XDG Base Directory).

Repo = ürün (kod, şablon config, belge). Kullanıcının ayarları ve üretilmiş config'ler repo DIŞINDA yaşar:
  profiller          $XDG_CONFIG_HOME/bt-audio-hifi/profiles/        (paylaşılabilir: dışa/içe aktar)
  kalıcı durum geçm. $XDG_STATE_HOME/bt-audio-hifi/console/*.json
  üretilmiş config   $XDG_STATE_HOME/bt-audio-hifi/generated/<~/.config ile aynı düzen>
`$BTA_HOME` verilirse her şey onun altında (testler gerçek kullanıcı verisine dokunmaz).
Neden: "Kalıcı yap" izlenen repo dosyasını yazıyordu → git kirleniyor, açık kaynakta kişisel ayar sızıyordu (PRD-BTA03)."""
from __future__ import annotations

import glob
import os
import shutil

APP = "bt-audio-hifi"


def _root(kind: str) -> str:
    override = os.environ.get("BTA_HOME")
    if override:
        return os.path.join(override, kind)
    if kind == "config":
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    else:
        base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return os.path.join(base, APP)


def _dir(*parts) -> str:
    p = os.path.join(*parts)
    os.makedirs(p, exist_ok=True)
    return p


def profiles_dir() -> str:
    """Kullanıcı profilleri: $XDG_CONFIG_HOME/bt-audio-hifi/profiles."""
    return _dir(_root("config"), "profiles")


def trash_dir() -> str:
    """Profil çöp kutusu (.trash)."""
    return _dir(_root("config"), "profiles", ".trash")


def console_states_dir() -> str:
    """'Açılışta kullan' durum geçmişi: $XDG_STATE_HOME/bt-audio-hifi/console."""
    return _dir(_root("state"), "console")


def backups_root() -> str:
    """Yedek kök yolu (oluşturmaz — yedek alınırken makedirs yapılır)."""
    return os.path.join(_root("state"), "backups")


def journal_dir() -> str:
    """Çalışma kopyası günlükleri: $XDG_STATE_HOME/bt-audio-hifi/journal."""
    return _dir(_root("state"), "journal")


def auto_state_path() -> str:
    """Otomasyon (D3–D5) kalıcı durumu: mod + öğrenilen kişisel tonal referans + bas tercihi yoklaması."""
    return os.path.join(_dir(_root("state")), "auto.json")


def generated_dir() -> str:
    """Durumdan üretilen PipeWire config'leri (kurulumdan önce)."""
    return _dir(_root("state"), "generated")


GENERATED_RELS = ("pipewire/filter-chain.conf.d/60-bta-console.conf",
                  "pipewire/filter-chain.conf.d/60-bta-bass-eq.conf")


def migrate(repo: str) -> dict:
    """Eski yerleşimden (repo içi) yeni yerleşime KOPYALA. Kaynak silinmez; hedef varsa ezilmez; tekrar koşu no-op."""
    copied, skipped = [], []
    pairs = [(p, os.path.join(console_states_dir(), os.path.basename(p)))
             for p in sorted(glob.glob(os.path.join(repo, "analysis", "console", "*-committed.json")))]
    pairs += [(p, os.path.join(profiles_dir(), os.path.basename(p)))
              for p in sorted(glob.glob(os.path.join(repo, "profiles", "*.json")))]
    for rel in GENERATED_RELS:
        src = os.path.join(repo, "config", rel)
        if os.path.exists(src):
            pairs.append((src, os.path.join(generated_dir(), rel)))
    for src, dst in pairs:
        if os.path.exists(dst):
            skipped.append(dst)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(dst)
    return {"copied": copied, "skipped": skipped}
