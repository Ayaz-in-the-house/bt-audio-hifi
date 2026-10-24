# `btaudio/eqverify.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [ölçüm](../layers/L5-bta-software.md#olcum) |
| rol | T-L30: smart filter EQ'sunun ürün katmanında doğrulanması |
| boyut | 130 satır |
| içe aktarır (iç) | [`eqconf`](eqconf.md), [`loudness`](loudness.md), [`procs`](procs.md), [`resample`](resample.md) |
| içe aktarır (dış) | `numpy`, `scipy` |
| standart kitaplık | `__future__`, `json`, `os`, `subprocess`, `tempfile`, `time` |
| kullanan modüller | [`analyzerverify`](analyzerverify.md), [`consoleverify`](consoleverify.md), [`zipperverify`](zipperverify.md) |

## Amaç (modül docstring'i)

T-L30 — Smart filter-chain EQ'sunun ÜRÜN katmanında doğrulanması: tasarım modeli ↔ gerçekten uygulanan yanıt.

Kulaklığı meşgul etmemek için geçici null sink hedeflenir: ayrı bir `pipewire -c <conf>` süreci aynı
filter-chain modülünü yükler; WirePlumber smart-filter politikası onu hedefin önüne sokar; çok tonlu sinyal hedefe
çalınır, hedefin monitörü kaydedilir; her tonun seviyesi ölçülür ve `loudness.eq_response_db + preamp` ile
karşılaştırılır.

## Sabitler

| ad | değer |
|---|---|
| `FS` | `48000` |
| `TONES` | `[40.0, 63.0, 90.0, 150.0, 250.0, 500.0, 1000.0, 4000.0]` |
| `BASE_CONF` | `'context.properties = { log.level = 0 }\ncontext.spa-libs = { audio…` |

## Genel API

- `tone_levels(x, fs=FS, freqs=TONES)`
- `verify(design: dict, probe_sink='bta_eq_probe') -> dict`

## Testler

- [`tests/live/test_live.py`](../../tests/live/test_live.py) — T-L01, T-L10, T-L12, T-L13, T-L14, T-L20
- [`tests/live/test_live_d7.py`](../../tests/live/test_live_d7.py) — T-L43, T-L44
