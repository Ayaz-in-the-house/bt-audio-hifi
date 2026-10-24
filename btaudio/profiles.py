"""C1 — Kullanıcı profil deposu. Bir profil = adlandırılmış konsol durumu; dosya başına bir JSON (şema `bta.profile/1`).

Tasarım kararları:
- kimlik = addan türetilen slug (büyük/küçük harf ve noktalama farkı aynı profil) → "aynı ad" çakışması tek kuralla;
- yazım atomik (geçici dosya + os.replace) → yarım yazılmış profil olmaz;
- silme = çöpe taşıma (geri alınabilir, core-principles §1);
- içe aktarma her durumu `console.sanitize`'dan geçirir (sınır dışı değerler kırpılır, bozuk yapı reddedilir);
- kimlik doğrulaması regex + realpath: dışarıdan gelen hiçbir kimlik depo dizininden çıkamaz (E16 sınıfı)."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time

from . import console

SCHEMA = "bta.profile/1"
_ID_RE = re.compile(r"^[a-z0-9ğüşıöç_-]{1,64}$")
MAX_NAME = 80


class Conflict(Exception):
    """Aynı adlı profil var ve üzerine yazma istenmedi (HTTP 409)."""
    def __init__(self, pid):
        super().__init__(f"'{pid}' adlı profil zaten var")
        self.pid = pid


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def slug(name: str) -> str:
    """Profil adından güvenli kimlik (Türkçe harfler korunur, yol karakterleri atılır)."""
    name = (name or "").strip()
    if not name:
        raise ValueError("profil adı boş")
    s = re.sub(r"[^a-z0-9ğüşıöç_-]+", "-", name.lower()).strip("-")[:48].strip("-")
    return s or "profil-" + hashlib.sha1(name.encode()).hexdigest()[:8]


def _clean_name(name: str) -> str:
    name = re.sub(r"\s+", " ", (name or "").strip())
    if not name:
        raise ValueError("profil adı boş")
    return name[:MAX_NAME]


META_KEYS = ("locked", "auto", "derived_from", "genres")


class ProfileStore:
    """Dosya başına bir profil. `writer` verilirse yazımlar ARKA PLANDA yapılır (istek yolu diske dokunmaz, D1.3);
    henüz diske inmemiş belgeler bellek katmanında (`_pending`) tutulur → okuma her zaman en güncel hâli görür."""

    def __init__(self, directory: str, writer=None):
        self.dir = directory
        self.trash = os.path.join(directory, ".trash")
        os.makedirs(self.trash, exist_ok=True)
        self.writer = writer
        self._pending = {}
        self._list_cache = None                        # list() her istekte diski okumasın (D1 gecikme bütçesi)
        self._seq_path = os.path.join(directory, ".seq")

    # ── yol güvenliği ──
    def _path(self, pid: str, base: str | None = None) -> str:
        if not isinstance(pid, str) or not _ID_RE.match(pid):
            raise KeyError(pid)
        base = base or self.dir
        p = os.path.realpath(os.path.join(base, pid + ".json"))
        if not p.startswith(os.path.realpath(base) + os.sep):
            raise KeyError(pid)
        return p

    def _write(self, pid: str, doc: dict):
        self._list_cache = None
        p = self._path(pid)
        if self.writer is not None:
            self._pending[pid] = doc
            self.writer.enqueue_doc(p, doc)
            return
        tmp = p + ".tmp"
        with open(tmp, "w") as f:
            json.dump(doc, f, indent=2, ensure_ascii=False)
        os.replace(tmp, p)

    def exists(self, pid: str) -> bool:
        """Kimlikli profil var mı (bekleyen yazım dahil)."""
        try:
            return pid in self._pending or os.path.exists(self._path(pid))
        except KeyError:
            return False

    def next_auto_number(self) -> int:
        """Özel N numarası ASLA yeniden kullanılmaz (silinen Özel 1'den sonra Özel 3 gelir) — sayaç kalıcı."""
        try:
            n = int(open(self._seq_path).read().strip())
        except (OSError, ValueError):
            n = 0
        for p in self.list():
            m = re.match(r"^Özel (\d+)$", p["name"])
            if m:
                n = max(n, int(m.group(1)))
        return n + 1

    def bump_seq(self, n: int):
        """Özel N sayacını kalıcı olarak ilerletir (numara asla yeniden kullanılmaz)."""
        if self.writer is not None:
            self.writer.enqueue_raw(self._seq_path, f"{n}\n")
        else:
            open(self._seq_path, "w").write(f"{n}\n")

    def _unique_name(self, base_name: str, suffix: str) -> str:
        n = 1
        while True:
            cand = f"{base_name} ({suffix})" if n == 1 else f"{base_name} ({suffix} {n})"
            if not self.exists(slug(cand)):
                return cand
            n += 1

    # ── okuma ──
    def get(self, pid: str) -> dict:
        """Profil belgesi (bekleyen yazım katmanı önce); yoksa KeyError."""
        p = self._path(pid)
        if pid in self._pending:
            return json.loads(json.dumps(self._pending[pid]))
        if not os.path.exists(p):
            raise KeyError(pid)
        with open(p) as f:
            return json.load(f)

    def list(self) -> list:
        """Profil özet satırları (önbellekli; yazımda geçersizleşir)."""
        if self._list_cache is not None:
            return [dict(x) for x in self._list_cache]
        out = []
        ids = {fn[:-5] for fn in os.listdir(self.dir) if fn.endswith(".json")} | set(self._pending)
        for pid in sorted(ids):
            try:
                d = self.get(pid)
            except (KeyError, ValueError, OSError):
                continue                                      # bozuk dosya listeyi düşürmez
            on = [b for b in d.get("state", {}).get("bands", []) if b.get("enabled")]
            out.append({"id": pid, "name": d.get("name", pid), "created": d.get("created"),
                        "updated": d.get("updated") or d.get("saved_at"), "notes": d.get("notes", ""),
                        "bands_on": len(on), "locked": d.get("locked", True), "auto": d.get("auto", False),
                        "derived_from": d.get("derived_from"), "genres": d.get("genres", [])})
        self._list_cache = sorted(out, key=lambda x: x["name"].lower())
        return [dict(x) for x in self._list_cache]

    # ── yazma ──
    def save(self, name: str, state: dict, overwrite: bool = False, notes: str | None = None, meta: dict | None = None) -> str:
        """meta: locked (varsayılan True — adıyla kaydedilen profil 'ana' profildir), auto, derived_from, genres."""
        name = _clean_name(name)
        pid = slug(name)
        st = console.sanitize(state)
        old = self.get(pid) if self.exists(pid) else None
        if old and not overwrite:
            raise Conflict(pid)
        doc = {"schema": SCHEMA, "name": name, "created": (old or {}).get("created") or _now(), "updated": _now(),
               "notes": notes if notes is not None else (old or {}).get("notes", ""), "state": st}
        base = {"locked": True, "auto": False, "derived_from": None, "genres": []}
        base.update({k: (old or {})[k] for k in META_KEYS if k in (old or {})})
        base.update(meta or {})
        doc.update(base)
        self._write(pid, doc)
        return pid

    def update_state(self, pid: str, state: dict):
        """Çalışma kopyasının otomatik kaydı: yalnız durum + zaman (meta korunur)."""
        doc = self.get(pid)
        doc.update(state=state, updated=_now())
        self._write(pid, doc)

    def set_meta(self, pid: str, **meta):
        """Meta alanlarını (locked/auto/derived_from/genres) günceller."""
        doc = self.get(pid)
        doc.update({k: v for k, v in meta.items() if k in META_KEYS})
        doc["updated"] = _now()
        self._write(pid, doc)

    def rename(self, pid: str, new_name: str, overwrite: bool = False) -> str:
        """Profili yeni ada taşır; ad doluysa ve overwrite yoksa Conflict."""
        doc = self.get(pid)
        new_name = _clean_name(new_name)
        nid = slug(new_name)
        if nid != pid and self.exists(nid) and not overwrite:
            raise Conflict(nid)
        doc.update(name=new_name, updated=_now(), schema=SCHEMA)
        self._write(nid, doc)
        if nid != pid:
            self._remove(pid)
        return nid

    def _remove(self, pid: str):
        self._list_cache = None
        self._pending.pop(pid, None)
        if self.writer is not None:
            self.writer.flush()                        # bekleyen yazım silinen dosyayı geri yaratmasın
            self._pending.pop(pid, None)
        p = self._path(pid)
        if os.path.exists(p):
            os.remove(p)

    def duplicate(self, pid: str) -> str:
        """'(kopya)' ekli yeni profil üretir."""
        doc = self.get(pid)
        name = self._unique_name(doc["name"], "kopya")
        return self.save(name, doc["state"], notes=doc.get("notes", ""),
                         meta={"locked": doc.get("locked", True), "auto": False, "derived_from": doc.get("derived_from"),
                               "genres": doc.get("genres", [])})

    def delete(self, pid: str) -> str:
        """Profili .trash/ altına taşır, geri yükleme belirteci döner (kalıcı silme YOK)."""
        p = self._path(pid)
        if self.writer is not None and pid in self._pending:
            self.writer.flush()                        # önce diske insin, sonra çöpe taşınsın
            self._pending.pop(pid, None)
        if not os.path.exists(p):
            raise KeyError(pid)
        self._list_cache = None
        token = f"{pid}--{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}-{int(time.time() * 1000) % 1000:03d}"
        shutil.move(p, os.path.join(self.trash, token + ".json"))
        return token

    def restore(self, token: str) -> str:
        """Çöpten geri yükler; ad çakışırsa '(geri yüklendi)' eki."""
        if not isinstance(token, str) or not re.match(r"^[a-z0-9ğüşıöç_-]{1,64}--[0-9-]{1,40}$", token):
            raise KeyError(token)
        src = os.path.join(self.trash, token + ".json")
        if not os.path.exists(src):
            raise KeyError(token)
        with open(src) as f:
            doc = json.load(f)
        name = doc.get("name") or token.split("--")[0]
        if self.exists(slug(name)):
            name = self._unique_name(name, "geri yüklendi")
        pid = self.save(name, doc["state"], notes=doc.get("notes", ""),
                        meta={k: doc[k] for k in META_KEYS if k in doc})
        os.remove(src)
        return pid

    def trash_list(self) -> list:
        """Çöp kutusu (D6): en yeni önce. Silme tarihi belirtecin içinden okunur."""
        out = []
        for fn in os.listdir(self.trash):
            if not fn.endswith(".json"):
                continue
            token = fn[:-5]
            try:
                with open(os.path.join(self.trash, fn)) as f:
                    name = json.load(f).get("name", token)
            except (OSError, ValueError):
                continue
            m = re.search(r"--(\d{8})-(\d{6})", token)
            deleted = f"{m.group(1)[:4]}-{m.group(1)[4:6]}-{m.group(1)[6:]}T{m.group(2)[:2]}:{m.group(2)[2:4]}:{m.group(2)[4:]}" if m else None
            out.append({"token": token, "name": name, "deleted": deleted})
        return sorted(out, key=lambda x: x["token"].split("--", 1)[-1], reverse=True)

    # ── paylaşım ──
    def export(self, pid: str) -> dict:
        """Paylaşım biçimi (şema bta.profile/1)."""
        d = self.get(pid)
        return {"schema": SCHEMA, "name": d["name"], "created": d.get("created"), "updated": d.get("updated"),
                "notes": d.get("notes", ""), "genres": d.get("genres", []), "app": "bt-audio-hifi", "state": d["state"]}

    def import_doc(self, doc, overwrite: bool = False) -> str:
        """Paylaşım belgesini doğrular, sanitize eder, kilitli profil olarak kaydeder."""
        if not isinstance(doc, dict):
            raise ValueError("profil JSON nesnesi değil")
        schema = doc.get("schema")
        if schema not in (None, SCHEMA):
            raise ValueError(f"desteklenmeyen şema: {schema}")
        if not isinstance(doc.get("state"), dict):
            raise ValueError("profilde 'state' yok")
        try:
            st = console.sanitize(doc["state"])               # sınır dışı değer kırpılır
        except (KeyError, TypeError, AttributeError) as e:    # yapı bozuk → tek hata tipi
            raise ValueError(f"profil durumu bozuk: {e}") from e
        name = _clean_name(doc.get("name") or "içe aktarılan")
        if self.exists(slug(name)) and not overwrite:
            name = self._unique_name(name, "içe aktarıldı")
        genres = [g for g in doc.get("genres", []) if isinstance(g, str)][:16] if isinstance(doc.get("genres"), list) else []
        return self.save(name, st, overwrite=overwrite, notes=str(doc.get("notes", ""))[:500],
                         meta={"locked": True, "auto": False, "derived_from": None, "genres": genres})
