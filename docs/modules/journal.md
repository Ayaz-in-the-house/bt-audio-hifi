# `btaudio/journal.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [infrastructure](../layers/L5-bta-software.md#infrastructure) |
| rol | Arka plan disk yazıcı (ekle-yalnız günlük + atomik profil yazımı) |
| boyut | 159 satır |
| içe aktarır (iç) | — |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__`, `collections`, `json`, `os`, `threading`, `time` |
| kullanan modüller | [`consoleserver`](consoleserver.md) |

## Amaç (modül docstring'i)

D1.3 — Arka plan disk yazıcısı (infrastructure).

Sözleşme: istek iş parçacığı yalnız `enqueue_*` çağırır (O(1), kilit + deque, disk YOK). Yazıcı iş parçacığı `delay_s`
boyunca birleştirir: aynı profil dosyası için yalnız EN SON belge yazılır (atomik: geçici dosya + os.replace), aynı
(profil, sürüm) günlük satırı için yalnız en sonuncusu eklenir. Çökmede kayıp üst sınırı ≈ `delay_s`.
`flush()` yazım bitene dek bekler (testler / kapanış); `close()` = flush + dur.

## Genel API

### `class Writer`

Arka plan yazıcı iş parçacığı: istek yolu yalnız kuyruğa ekler; `delay_s` birleştirme ile profil belgeleri atomik yazılır, günlük satırları eklenir.

- `__init__(self, journal_dir: str, delay_s: float=0.3)`
- `enqueue_doc(self, path: str, doc: dict)` — Profil belgesini yazım kuyruğuna koyar (aynı yol için en sonuncusu kazanır).
- `enqueue_raw(self, path: str, text: str)` — Ham metni (ör. .seq sayacı) yazım kuyruğuna koyar.
- `enqueue_lines(self, pid: str, events: list)` — Günlük olaylarını kuyruğa ekler; güncellenen (aynı sürüm) satır sona taşınır.
- `pending(self) -> int` — Diske inmemiş öğe sayısı (arayüzdeki 'kaydediliyor…').
- `journal_path(self, pid: str) -> str` — Profilin günlük dosyası yolu (<dizin>/<id>.jsonl).
- `flush(self, timeout: float=10.0) -> bool` — Bekleyen tüm yazımlar diske inene dek bekler (en çok timeout sn).
- `close(self)` — flush + iş parçacığını durdur.

### `class NullWriter`

Kalıcılık kapalı karşılaştırma (U52: yazıcının istek yoluna eklediği süre ölçülür).

- `enqueue_doc(self, path, doc)` — No-op (testler / yazıcısız mod).
- `enqueue_lines(self, pid, events)` — No-op.
- `enqueue_raw(self, path, text)` — No-op.
- `pending(self)` — Her zaman 0.
- `journal_path(self, pid)` — os.devnull.
- `flush(self, timeout=0)` — Hemen True.
- `close(self)` — No-op.

## Testler

- [`tests/test_workcopy.py`](../../tests/test_workcopy.py) — U51, U53
