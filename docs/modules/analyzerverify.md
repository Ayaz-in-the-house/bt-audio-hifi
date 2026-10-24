# `btaudio/analyzerverify.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [ölçüm](../layers/L5-bta-software.md#olcum) |
| rol | T-L34: analizörün ürün katmanında doğrulaması |
| boyut | 80 satır |
| içe aktarır (iç) | [`analyzer`](analyzer.md), [`console`](console.md), [`eqverify`](eqverify.md), [`procs`](procs.md), [`resample`](resample.md) |
| içe aktarır (dış) | `numpy`, `scipy` |
| standart kitaplık | `__future__`, `os`, `subprocess`, `tempfile`, `time` |
| kullanan modüller | — |

## Amaç (modül docstring'i)

T-L34 — analizörün ürün katmanında doğrulaması (kulaklığa dokunmaz): null sink'e bağlı bir KOPYA konsol grafı,
analizör aynı `pw-record` + elle `pw-link` yolundan dinler. Beklenen: EQ sonrası − öncesi = model (preamp dahil),
EQ öncesi mutlak seviye = çalınan seviye.

## Sabitler

| ad | değer |
|---|---|
| `FS` | `48000` |
| `TONES` | `[100.0, 1000.0, 5000.0]` |
| `LEVEL_DB` | `-30.0` |

## Genel API

- `test_state()`
- `verify(seconds=6.0) -> dict`

## Testler

- [`tests/live/test_live.py`](../../tests/live/test_live.py) — T-L01, T-L10, T-L12, T-L13, T-L14, T-L20
