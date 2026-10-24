# `btaudio/dsp.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [domain](../layers/L5-bta-software.md#domain) |
| rol | RBJ biquad katsayıları + frekans yanıtı (numpy) |
| boyut | 72 satır |
| içe aktarır (iç) | — |
| içe aktarır (dış) | `numpy` |
| standart kitaplık | `__future__`, `math` |
| kullanan modüller | [`console`](console.md), [`presetfit`](presetfit.md) |

## Amaç (modül docstring'i)

RBJ Audio EQ Cookbook biquad katsayıları — PipeWire filter-chain `bq_raw` düğümüne CANLI yazılır.

`bq_raw` için impl->type = BQ_NONE → bq_run her blokta b0..a2 portlarını okur ve değiştiyse günceller
(docs/research/upstream/plugin_builtin.c:275, 545-556). Böylece tip dahil her şey servis yeniden başlatılmadan
değişir. Katsayılar a0=1'e normalize edilir (bq_raw ayrıca 1/a0 ile çarpar; ikisi tutarlı).

## Sabitler

| ad | değer |
|---|---|
| `FS` | `48000` |
| `TYPES` | `('bell', 'lowshelf', 'highshelf', 'lowpass', 'highpass', 'notch')` |
| `IDENTITY` | `{'b0': 1.0, 'b1': 0.0, 'b2': 0.0, 'a0': 1.0, 'a1': 0.0, 'a2': 0.0}` |

## Genel API

- `coeffs(band: dict, fs: int=FS) -> dict` — Bir bandın normalize biquad katsayıları [b0,b1,b2,a1,a2] (RBJ; kapalıysa geçirgen).
- `freq_response(k: dict, freqs, fs: int=FS)` — H(e^jw) = (b0 + b1 z⁻¹ + b2 z⁻²)/(a0 + a1 z⁻¹ + a2 z⁻²) — saf numpy (scipy.freqz ile aynı matematik, ~100× daha hızlı; istek yolunda her değişiklikte hesaplanıyor → D1 gecikme bütçesi, U52).
- `response_db(bands, freqs, fs: int=FS) -> list` — Bant listesinin toplam genlik yanıtı (dB), verilen frekanslarda.

## Testler

- [`tests/test_console.py`](../../tests/test_console.py) — U31, U35
- [`tests/test_dsp.py`](../../tests/test_dsp.py) — T-L30, U30
- [`tests/test_presets.py`](../../tests/test_presets.py) — U43
- [`tests/ui/test_console_page.py`](../../tests/ui/test_console_page.py) — T-U04
