# `btaudio/bench.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [infrastructure](../layers/L5-bta-software.md#infrastructure) |
| rol | Encoder benchmark (fdk-aac / libsbc) |
| boyut | 175 satır |
| içe aktarır (iç) | [`analysis`](analysis.md), [`codecs`](codecs.md), [`sbclib`](sbclib.md) |
| içe aktarır (dış) | `numpy`, `scipy` |
| standart kitaplık | `__future__`, `json`, `os`, `subprocess` |
| kullanan modüller | [`cli`](cli.md) |

## Amaç (modül docstring'i)

F2.2 — Encoder benchmark. Kulaklığa giden encoder ile AYNI kütüphane (/lib64/libfdk-aac.so.2) ffmpeg üzerinden
sürülür; her aday kodlanır → çözülür → 48 kHz'e döner → referansla hizalanır + kazanç eşlenir → metrikler.

Dürüstlük notları (rapora da yazılır):
  * Metrikler algısal DEĞİL (PEAQ/ViSQOL kurulu değil); bant-SNR ve kesim frekansıdır. Nihai hakem kör A/B dinleme.
  * Kulaklığın DECODER'ı bilinmiyor; burada ffmpeg decoder'ı kullanılır.
  * SBC adayları ffmpeg ile DEĞİL, PipeWire'ın bağlandığı aynı libsbc (ctypes) ile, canlı transport'tan okunan
    parametrelerle kodlanır (ffmpeg SBC kanal modu/alt-bant seçtirmiyor — ölçüldü, E9).

## Sabitler

| ad | değer |
|---|---|
| `FS` | `48000` |
| `BANDS` | `[(20, 4000), (4000, 10000), (10000, 16000), (16000, 20000)]` |
| `SBC_PARAMS` | `{'SBC-XQ(48k,dual,bp39)': dict(rate=48000, mode='dual', bitpool=39)…` |
| `CANDIDATES` | `{'PCM-kontrol': ([], FS, 2, 'wav', 'kayıpsız — hattın kendi hatası …` |

## Genel API

- `make_signals(out_dir: str, brahms: str | None=None, seconds: int=10) -> dict`
- `run_candidate(name: str, ref_path: str, tmp: str) -> str`
- `metrics(ref_path: str, dec_path: str) -> dict`
- `run(signals: dict, tmp: str, candidates=None) -> dict`
- `to_markdown(res: dict) -> str`
- `save(res: dict, out_dir: str, stamp: str)`

## Testler

- [`tests/test_bench.py`](../../tests/test_bench.py) — U16
