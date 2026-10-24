"""D1.4 — Profil başına kalıcı geri/ileri al (domain: G/Ç yok, zaman parametre).

Sürüm = tam durum (≈2 KB JSON). Hızlı ardışık değişiklikler (sürükleme) `merge_s` içinde TEK adımda birleşir; açık
`seal()` (bırakma anı) ya da duraklama yeni adım başlatır. Geri alınmış konumdan yeni değişiklik ileri dalı keser.

Günlük biçimi (ekle-yalnız, satır başına bir JSON):
  {"v": i, "t": ts, "state": {...}}   → versions = versions[:i] + [state]   (değiştirme = aynı i ile yeniden yazım)
  {"ptr": n, "t": ts}                  → geçerli konum
Yeniden oynatma idempotenttir; çökmede yarım kalan son satır yok sayılır."""
from __future__ import annotations

import json

MAX_VERSIONS = 2000


class History:
    """Profil başına sürüm yığını: tam durum sürümleri, birleştirme penceresi (merge_s), geri/ileri al, ileri dal kesme."""
    def __init__(self, versions=None, ptr=None, merge_s=1.0):
        self.versions = list(versions or [])
        self.ptr = len(self.versions) - 1 if ptr is None else ptr
        self.merge_s = merge_s
        self._open_at = None                      # açık (birleşebilir) sürümün son değişiklik zamanı

    # ── sorgu ──
    def current(self):
        """Geçerli konumdaki durum (kopya); boşsa None."""
        return json.loads(self.versions[self.ptr]) if self.versions else None

    def info(self):
        """{can_undo, can_redo, ptr, versions}."""
        return {"can_undo": self.ptr > 0, "can_redo": self.ptr < len(self.versions) - 1,
                "ptr": self.ptr, "versions": len(self.versions)}

    # ── değişiklik → günlük olayları döndürür ──
    def push(self, state: dict, now: float) -> list:
        """Yeni durum: merge_s içinde açık adımı günceller, değilse yeni sürüm ekler; günlük olaylarını döndürür."""
        s = json.dumps(state, sort_keys=True, ensure_ascii=False)
        if self.versions and s == self.versions[self.ptr]:
            return []
        ev = []
        if self.ptr < len(self.versions) - 1:           # geri alınmış konumdan yeni değişiklik → ileri dal kesilir
            self.versions = self.versions[:self.ptr + 1]
            self._open_at = None
        merge = (self._open_at is not None and now - self._open_at <= self.merge_s and self.ptr == len(self.versions) - 1
                 and self.ptr > 0)
        if merge:
            self.versions[self.ptr] = s
        else:
            self.versions.append(s)
            self.ptr = len(self.versions) - 1
            if len(self.versions) > MAX_VERSIONS:       # bellek sınırı: en eski adımlar düşer (günlükte kalır)
                drop = len(self.versions) - MAX_VERSIONS
                self.versions, self.ptr = self.versions[drop:], self.ptr - drop
        self._open_at = now
        ev.append({"v": self.ptr, "t": round(now, 3), "state": json.loads(s)})
        return ev

    def seal(self):
        """Açık adımı kapatır (sonraki değişiklik yeni sürüm olur)."""
        self._open_at = None

    def undo(self, now: float):
        """Bir geri: (durum, günlük olayları); başta ise (None, [])."""
        if self.ptr <= 0:
            return None, []
        self.ptr -= 1
        self._open_at = None
        return self.current(), [{"ptr": self.ptr, "t": round(now, 3)}]

    def redo(self, now: float):
        """Bir ileri: (durum, günlük olayları); sonda ise (None, [])."""
        if self.ptr >= len(self.versions) - 1:
            return None, []
        self.ptr += 1
        self._open_at = None
        return self.current(), [{"ptr": self.ptr, "t": round(now, 3)}]


def replay(lines) -> History:
    """Günlük satırlarından History kurar (yarım/bozuk satır yok sayılır, 'reset' dizini sıfırlar)."""
    h = History()
    for raw in lines:
        try:
            d = json.loads(raw)
        except (ValueError, TypeError):
            continue                               # yarım/bozuk satır (çökme) → atla
        if d.get("reset"):
            h.versions, h.ptr = [], -1
        if "v" in d and isinstance(d.get("state"), dict):
            i = int(d["v"])
            h.versions = h.versions[:i] + [json.dumps(d["state"], sort_keys=True, ensure_ascii=False)]
            h.ptr = len(h.versions) - 1
        elif "ptr" in d:
            h.ptr = max(0, min(int(d["ptr"]), len(h.versions) - 1))
    return h


def timeline(lines) -> dict:
    """Yönetim sayfası (D6): yeniden oynatmayla AYNI anlam + her sürümün zamanı. {versions: [{v, t, state}], ptr}."""
    vs, ptr = [], -1
    for raw in lines:
        try:
            d = json.loads(raw)
        except (ValueError, TypeError):
            continue
        if d.get("reset"):
            vs, ptr = [], -1
        if "v" in d and isinstance(d.get("state"), dict):
            i = int(d["v"])
            vs = vs[:i] + [{"v": i, "t": d.get("t"), "state": d["state"]}]
            ptr = len(vs) - 1
        elif "ptr" in d:
            ptr = max(0, min(int(d["ptr"]), len(vs) - 1))
    for i, x in enumerate(vs):
        x["v"] = i
    return {"versions": vs, "ptr": ptr}


def load(path: str) -> History:
    """Günlük dosyasını yeniden oynatır; dosya yoksa boş History."""
    try:
        with open(path, "rb") as f:
            return replay(f.read().splitlines())
    except FileNotFoundError:
        return History()
