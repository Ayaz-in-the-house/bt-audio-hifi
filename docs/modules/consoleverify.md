# `btaudio/consoleverify.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [ölçüm](../layers/L5-bta-software.md#olcum) |
| rol | T-L32: tam stereo konsol grafı null sink'te model ±0,05 dB |
| boyut | 69 satır |
| içe aktarır (iç) | [`console`](console.md), [`eqverify`](eqverify.md), [`procs`](procs.md), [`resample`](resample.md) |
| içe aktarır (dış) | `numpy`, `scipy` |
| standart kitaplık | `__future__`, `json`, `os`, `subprocess`, `tempfile`, `time` |
| kullanan modüller | — |

## Amaç (modül docstring'i)

T-L32 — tam stereo konsol grafının null sink'te ürün doğrulaması: L-only ve R-only girişte her iki çıkış kanalının
ton seviyeleri ↔ console.stereo_model (preamp dahil). Kulaklığa dokunmaz.

## Sabitler

| ad | değer |
|---|---|
| `FS` | `48000` |
| `TONES` | `[40.0, 100.0, 300.0, 1000.0, 3000.0, 8000.0, 15000.0]` |

## Genel API

- `verify(state: dict) -> dict`

## Testler

- [`tests/live/test_live.py`](../../tests/live/test_live.py) — T-L01, T-L10, T-L12, T-L13, T-L14, T-L20
