# `btaudio/tones.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [infrastructure](../layers/L5-bta-software.md#infrastructure) |
| rol | Oturma testi tonları (pw-play) |
| boyut | 58 satır |
| içe aktarır (iç) | [`procs`](procs.md) |
| içe aktarır (dış) | `numpy`, `scipy` |
| standart kitaplık | `__future__`, `os`, `subprocess`, `tempfile` |
| kullanan modüller | [`cli`](cli.md) |

## Amaç (modül docstring'i)

D7.3 — oturma (seal) testi tonları (infrastructure).

Kısa sinüs, 30 ms yükseltilmiş-kosinüs giriş/çıkış (açma/kapama tıkı olmasın), sabit seviye (dBFS tepe).
Çalma: pw-play → hedef sink (kulaklık). Alt süreç `procs.spawn` ile (ebeveynle ölür, E23).

## Sabitler

| ad | değer |
|---|---|
| `FS` | `48000` |
| `FADE_S` | `0.03` |

## Genel API

- `tone(freq: float, seconds: float, level_db: float) -> np.ndarray` — Stereo float32 sinüs: seviye dBFS tepe, 30 ms yükseltilmiş-kosinüs giriş/çıkış.
- `player(target: str | None)` — Session.tone_player için çağrılabilir: (freq, seconds, level_db) → durdurulabilir tanıtıcı.

## Testler

- [`tests/live/test_live_d7.py`](../../tests/live/test_live_d7.py) — T-L43, T-L44
- [`tests/test_protection.py`](../../tests/test_protection.py) — U65
