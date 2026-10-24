# `btaudio/analysis.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [domain](../layers/L5-bta-software.md#domain) |
| rol | Encoder/resampler kalite metrikleri |
| boyut | 70 satır |
| içe aktarır (iç) | — |
| içe aktarır (dış) | `numpy`, `scipy` |
| standart kitaplık | `__future__` |
| kullanan modüller | [`bench`](bench.md) |

## Amaç (modül docstring'i)

Encoder/resampler kalite metrikleri (numpy/scipy). Metriklerin kendisi tests/test_analysis.py ile doğrulanır.

## Sabitler

| ad | değer |
|---|---|
| `SNR_CAP_DB` | `200.0` |

## Genel API

- `cutoff_frequency(y, fs: int, drop_db: float=30.0) -> float` — Geniş bantlı test sinyalinde üst kesim: PSD'nin 1–8 kHz medyanından `drop_db` altına kalıcı düştüğü frekans.
- `snr_db(ref, test) -> float`
- `align(ref, test, max_lag: int=48000)` — Çapraz korelasyonla tamsayı gecikmeyi bul, test'i kaydır, iki diziyi aynı uzunluğa kırp.
- `band_snr_db(ref, test, fs: int, lo: float=20.0, hi: float=16000.0) -> float`
- `gain_matched(ref, test)` — En küçük kareler kazanç eşlemesi (codec küçük seviye kayması yaparsa SNR'yi haksız düşürmesin).

## Testler

- [`tests/test_analysis.py`](../../tests/test_analysis.py) — U11, U12
