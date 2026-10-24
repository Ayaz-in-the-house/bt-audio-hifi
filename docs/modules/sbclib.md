# `btaudio/sbclib.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [infrastructure](../layers/L5-bta-software.md#infrastructure) |
| rol | libsbc ctypes sarmalayıcı (SBC-XQ ölçümü) |
| boyut | 95 satır |
| içe aktarır (iç) | — |
| içe aktarır (dış) | `numpy` |
| standart kitaplık | `__future__`, `ctypes` |
| kullanan modüller | [`bench`](bench.md) |

## Amaç (modül docstring'i)

libsbc (PipeWire'ın SBC eklentisinin bağlandığı /lib64/libsbc.so.1) için ctypes sarmalayıcı.

ffmpeg'in SBC encoder'ı kanal modu/alt-bant seçtirmediği için (ölçüldü: "XQ" isteğinde 4 alt-bant + joint + bp42
seçti) PipeWire'ın gerçek parametreleri ancak bu yolla birebir üretilebilir. Yapı: docs/research/upstream/sbc.h.

## Sabitler

| ad | değer |
|---|---|
| `FREQ` | `{16000: 0, 32000: 1, 44100: 2, 48000: 3}` |
| `BLK` | `{4: 0, 8: 1, 12: 2, 16: 3}` |
| `MODE` | `{'mono': 0, 'dual': 1, 'stereo': 2, 'joint': 3}` |
| `ALLOC` | `{'loudness': 0, 'snr': 1}` |
| `SB` | `{4: 0, 8: 1}` |
| `SBC_LE` | `0` |

## Genel API

### `class Codec`

—

- `__init__(self, rate=48000, mode='joint', bitpool=53, blocks=16, subbands=8, allocation='loudness', msbc=False)`
- `close(self)`
- `frame_length(self)`
- `codesize(self)`
- `encode(self, pcm: np.ndarray) -> bytes` — pcm: int16, (n,) veya (n, ch) interleaved.
- `decode(self, data: bytes) -> np.ndarray`

## Testler

- [`tests/test_sbclib.py`](../../tests/test_sbclib.py) — U17
