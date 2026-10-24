# `btaudio/history.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [domain](../layers/L5-bta-software.md#domain) |
| rol | Sürüm yığını (geri/ileri al) + günlük yeniden oynatma + zaman çizelgesi |
| boyut | 126 satır |
| içe aktarır (iç) | — |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__`, `json` |
| kullanan modüller | [`consoleserver`](consoleserver.md) |

## Amaç (modül docstring'i)

D1.4 — Profil başına kalıcı geri/ileri al (domain: G/Ç yok, zaman parametre).

Sürüm = tam durum (≈2 KB JSON). Hızlı ardışık değişiklikler (sürükleme) `merge_s` içinde TEK adımda birleşir; açık
`seal()` (bırakma anı) ya da duraklama yeni adım başlatır. Geri alınmış konumdan yeni değişiklik ileri dalı keser.

Günlük biçimi (ekle-yalnız, satır başına bir JSON):
  {"v": i, "t": ts, "state": {...}}   → versions = versions[:i] + [state]   (değiştirme = aynı i ile yeniden yazım)
  {"ptr": n, "t": ts}                  → geçerli konum
Yeniden oynatma idempotenttir; çökmede yarım kalan son satır yok sayılır.

## Sabitler

| ad | değer |
|---|---|
| `MAX_VERSIONS` | `2000` |

## Genel API

### `class History`

Profil başına sürüm yığını: tam durum sürümleri, birleştirme penceresi (merge_s), geri/ileri al, ileri dal kesme.

- `__init__(self, versions=None, ptr=None, merge_s=1.0)`
- `current(self)` — Geçerli konumdaki durum (kopya); boşsa None.
- `info(self)` — {can_undo, can_redo, ptr, versions}.
- `push(self, state: dict, now: float) -> list` — Yeni durum: merge_s içinde açık adımı günceller, değilse yeni sürüm ekler; günlük olaylarını döndürür.
- `seal(self)` — Açık adımı kapatır (sonraki değişiklik yeni sürüm olur).
- `undo(self, now: float)` — Bir geri: (durum, günlük olayları); başta ise (None, []).
- `redo(self, now: float)` — Bir ileri: (durum, günlük olayları); sonda ise (None, []).

- `replay(lines) -> History` — Günlük satırlarından History kurar (yarım/bozuk satır yok sayılır, 'reset' dizini sıfırlar).
- `timeline(lines) -> dict` — Yönetim sayfası (D6): yeniden oynatmayla AYNI anlam + her sürümün zamanı. {versions: [{v, t, state}], ptr}.
- `load(path: str) -> History` — Günlük dosyasını yeniden oynatır; dosya yoksa boş History.

## Testler

- [`tests/test_admin.py`](../../tests/test_admin.py) — U63
- [`tests/test_workcopy.py`](../../tests/test_workcopy.py) — U51, U53
