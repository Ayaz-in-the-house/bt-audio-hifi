# `btaudio/resample.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [infrastructure](../layers/L5-bta-software.md#infrastructure) |
| rol | Resampler ölçümü + geçici null sink yardımcıları |
| boyut | 111 satır |
| içe aktarır (iç) | [`collect`](collect.md), [`procs`](procs.md) |
| içe aktarır (dış) | `numpy`, `scipy` |
| standart kitaplık | `__future__`, `os`, `subprocess`, `tempfile`, `time` |
| kullanan modüller | [`analyzerverify`](analyzerverify.md), [`consoleverify`](consoleverify.md), [`eqverify`](eqverify.md), [`zipperverify`](zipperverify.md) |

## Amaç (modül docstring'i)

F4 — PipeWire resampler kalitesinin CANLI ölçümü.

44.1 kHz çok tonlu sinyal `pw-play -P '{ resample.quality = N }'` ile BT sink'e çalınır; sink MONITOR'ü (encoder
öncesi, 48 kHz) float olarak kaydedilir; spektrumda tonlar dışındaki en büyük bileşen (SFDR), 21 kHz tonunun
48 kHz'deki görüntüsü (44100−21000 = 23100 Hz) ve gürültü tabanı ölçülür. CPU: pw-play sürecinin rusage'ı.

## Sabitler

| ad | değer |
|---|---|
| `TONES_441` | `[997.0, 5000.0, 12000.0, 17000.0, 19500.0, 21000.0]` |
| `IMAGE_HZ` | `44100 - 21000` |
| `GUARD_HZ` | `40.0` |
| `NFFT` | `65536` |

## Genel API

- `analyze(x, fs: int) -> dict`
- `make_tones(seconds=6, rate=44100, level_db=-20.0) -> str`
- `null_sink(name='bta_resample_probe')` — Geçici sanal 48 kHz sink (kullanıcının kulaklığını meşgul etmeden resampler ölçümü). Modül id döner.
- `unload(module_id: int)`
- `measure(quality: int, seconds: int=6, sink: str | None=None) -> dict` — Çalar + sink monitörünü kaydeder. sink=None → gerçek BT sink (HEADFUL; başka akış varsa reddedilir).

## Testler

- [`tests/live/test_live_d7.py`](../../tests/live/test_live_d7.py) — T-L43, T-L44
- [`tests/test_resample.py`](../../tests/test_resample.py) — U19
