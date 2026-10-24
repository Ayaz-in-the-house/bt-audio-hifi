# `btaudio/codecs.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [domain](../layers/L5-bta-software.md#domain) |
| rol | A2DP codec bayt çözücüleri (AAC/SBC) |
| boyut | 124 satır |
| içe aktarır (iç) | — |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__`, `math` |
| kullanan modüller | [`bench`](bench.md), [`collect`](collect.md) |

## Amaç (modül docstring'i)

A2DP codec capability/configuration byte çözücüleri.

Kaynak otoritesi: PipeWire 1.6.8 `spa/plugins/bluez5/a2dp-codec-caps.h` (little-endian bitfield düzeni) ve
`a2dp-codec-aac.c` — kopyaları `docs/research/upstream/` altında, SHA256SUMS ile.

## Sabitler

| ad | değer |
|---|---|
| `A2DP_CODEC_SBC` | `0` |
| `A2DP_CODEC_MPEG24` | `2` |
| `A2DP_CODEC_VENDOR` | `255` |
| `DEFAULT_AAC_BITRATE` | `320000` |
| `MIN_AAC_BITRATE` | `64000` |
| `AAC_FORCED_BANDWIDTH` | `19293` |
| `RTP_HEADER_SIZE` | `12` |

## Genel API

- `decode_aac(raw: bytes) -> dict`
- `encode_aac_bitrate(bitrate: int, vbr: bool) -> bytes` — AAC_SET_BITRATE makrosunun eşdeğeri (vbr biti bitrate1'in üst bitinde).
- `pipewire_effective_aac_bitrate(conf_bitrate: int) -> int` — get_valid_aac_bitrate(): bilinmeyen/sahte (<64k) → 320k; aksi hâlde min(conf, 320k).
- `pipewire_aac_max_bitrate(mtu: int, rate: int) -> int` — Fragmentation yok → her AAC çerçevesi (mtu - RTP başlığı) içine sığmalı (a2dp-codec-aac.c:382).
- `pipewire_aac_forced_bandwidth(vbr: bool, cur_bitrate: int)` — a2dp-codec-aac.c:400 — yalnız vbr=0 ve >110 kbps CBR'de 19293 Hz zorlanır; aksi hâlde FDK otomatik.
- `decode_sbc(raw: bytes) -> dict`
- `sbc_frame_length(mode: str, subbands: int, blocks: int, bitpool: int) -> int` — A2DP spec SBC çerçeve uzunluğu (bayt).
- `sbc_bitrate(mode: str, rate: int, subbands: int, blocks: int, bitpool: int) -> int`
- `decode(codec_id: int, raw: bytes) -> dict`

## Testler

- [`tests/test_codecs.py`](../../tests/test_codecs.py) — U01, U06
- [`tests/test_sbclib.py`](../../tests/test_sbclib.py) — U17
