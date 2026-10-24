# `btaudio/zipperverify.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [ölçüm](../layers/L5-bta-software.md#olcum) |
| rol | D0/T-L39/T-L41: canlı güncelleme tık ölçümü (null sink) |
| boyut | 164 satır |
| içe aktarır (iç) | [`console`](console.md), [`crossfade`](crossfade.md), [`eqverify`](eqverify.md), [`procs`](procs.md), [`resample`](resample.md), [`tunerserver`](tunerserver.md) |
| içe aktarır (dış) | `numpy`, `scipy` |
| standart kitaplık | `__future__`, `os`, `subprocess`, `tempfile`, `time` |
| kullanan modüller | — |

## Amaç (modül docstring'i)

D0 fizibilite (PRD-BTA04) — canlı katsayı güncellemesi tıklama/zipper üretiyor mu?

Otomatik modlar (Auto Profile Changer, Auto Dynamic Live) EQ'yu müzik çalarken `pw-cli set-param` ile değiştirir.
Biquad katsayısını blok ortasında ani değiştirmek dalga biçiminde süreksizlik (tık) yaratabilir. Ölçüm: null sink'te
KOPYA konsol grafı, 1 kHz saf sinüs çalarken 1 kHz bell kazancı değiştirilir; çıkışın 4 kHz üstü (saf sinüste olmaması
gereken) enerjisi 5 ms'lik pencerelerde izlenir. Senaryolar: büyük sıçrama (0↔+6 dB) ve küçük adım rampası.

## Sabitler

| ad | değer |
|---|---|
| `FS` | `48000` |

## Genel API

- `run(scenario: str, seconds=6.0) -> dict`
- `run_ab(fade_s: float=0.05, seconds: float=6.0, updates: str='jump') -> dict` — T-L39: aynı ölçüm, A/B grafı + Crossfader ile. Beklenen: güncelleme başına tık YOK. updates: "jump" (0↔+6 dB, 0,7 sn) · "ramp" (0,25 dB/50 ms) · "adl" (T-L41: otomasyonun gerçek deseni — 0,5 dB kuantalı adım, geçiş süresi + 0,1 sn arayla, ADL_QUANT/CLASSIFY ile aynı).

## Testler

- [`tests/live/test_live.py`](../../tests/live/test_live.py) — T-L01, T-L10, T-L12, T-L13, T-L14, T-L20
- [`tests/live/test_live_auto.py`](../../tests/live/test_live_auto.py) — T-L39, T-L40, T-L41, T-L42, U62
