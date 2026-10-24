# `btaudio/bass.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [domain](../layers/L5-bta-software.md#domain) |
| rol | Bas analizi: eşleştirme → kulakta yanıt → EQ tasarımı (F8) |
| boyut | 93 satır |
| içe aktarır (iç) | [`loudness`](loudness.md) |
| içe aktarır (dış) | `numpy` |
| standart kitaplık | `__future__`, `json` |
| kullanan modüller | [`cli`](cli.md) |

## Amaç (modül docstring'i)

F8 — Bas analizi: eşleştirme dosyaları → kulakta yanıt, sızdırmazlık kazancı, phon duyarlılığı, EQ tasarımı.

## Sabitler

| ad | değer |
|---|---|
| `LOW` | `[31.5, 40, 50, 63]` |
| `SEAL_THRESHOLD_DB` | `3.0` |
| `DEFICIT_THRESHOLD_DB` | `-6.0` |
| `MAX_FLAGS` | `2` |
| `PLAUSIBLE_DEV_DB` | `{'low': 30.0, 'high': 20.0}` |

## Genel API

### `class LowQualityRun(ValueError)`

Eşleştirme verisi fiziksel olarak inandırıcı değil → EQ üretilmez (yanlış EQ, EQ'suzdan kötüdür).

- `quality_problems(d) -> list` — Ölçüm oturumunun inandırıcılık kontrolü (2026-09-27 gerçek oturum: 9/10 'tavan', 500 Hz +40 dB).
- `load(path)`
- `analyze(paths, target='harman-ie-bass', max_boost_db=12.0, basis=None, force=False) -> dict`

## Testler

- [`tests/test_bass.py`](../../tests/test_bass.py) — U26
