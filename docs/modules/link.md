# `btaudio/link.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [infrastructure](../layers/L5-bta-software.md#infrastructure) |
| rol | Bağlantı sağlığı (bitrate düşürme olayları) |
| boyut | 95 satır |
| içe aktarır (iç) | [`collect`](collect.md) |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__`, `os`, `re`, `subprocess`, `tempfile`, `time` |
| kullanan modüller | [`cli`](cli.md) |

## Amaç (modül docstring'i)

F6 — Bağlantı sağlığı: A2DP soket tamponu dolduğunda PipeWire encoder bitrate'i düşürür ve paketi atlar.

Kaynak: media-sink.c (PipeWire 1.6.8)
  :1080 flush_buffer() == -EAGAIN → :1088 codec->reduce_bitpool() → debug "reduce bitpool: <yeni>"  → paket ATLANIR
  :1160 1 sn hatasız + gönderilmemiş veri yok → increase_bitpool() → debug "increase bitpool: <yeni|0=tavanda>"
AAC için reduce = ×2/3, increase = ×4/3 (a2dp-codec-aac.c:631/637, alt sınır 64 kbps).

## Sabitler

| ad | değer |
|---|---|
| `TOPIC` | `'spa.bluez5.sink.media'` |

## Genel API

- `parse(lines, seconds: float) -> dict`
- `quiet_signal(seconds: int) -> str` — -50 dBFS civarı pembe gürültü: CBR AAC tam boy paket üretir ama kulağı rahatsız etmez.
- `run_test(seconds: int=30, passive: bool=False) -> dict` — Debug günlüğünü YALNIZ bu konu için aç, çal (veya pasif izle), günlüğü ayrıştır, düzeyi her durumda geri al.

## Testler

- [`tests/test_link.py`](../../tests/test_link.py) — U15
