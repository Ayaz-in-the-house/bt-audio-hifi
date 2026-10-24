# `btaudio/abx.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [ölçüm](../layers/L5-bta-software.md#olcum) |
| rol | Kör ABX dinleme testi (kullanıcı kararı için) |
| boyut | 106 satır |
| içe aktarır (iç) | [`collect`](collect.md) |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__`, `datetime`, `json`, `math`, `os`, `random`, `subprocess`, `tempfile`, `time` |
| kullanan modüller | [`abxsession`](abxsession.md), [`cli`](cli.md) |

## Amaç (modül docstring'i)

F2.4 — Kör ABX dinleme testi (ITU-R BS.1116 ruhunda: kör, dengeli, istatistiksel karar).

Her denemede A, B ve bilinmeyen X çalınır; dinleyici X'in A mı B mi olduğunu söyler. 12 denemede ≥10 doğru
(p < 0.05) → fark duyuluyor; ardından tercih sorulur. Profil geçişinin kendisi ipucu olmasın diye her çalmadan önce
ÖNCE diğer codec'e SONRA hedefe geçilir (her çalmada aynı geçiş dizisi = sabit ipucu).

## Sabitler

| ad | değer |
|---|---|
| `PROFILES` | `{'aac': 'a2dp-sink', 'sbc': 'a2dp-sink-sbc', 'sbc_xq': 'a2dp-sink-s…` |

## Genel API

- `p_value(correct: int, n: int) -> float` — Tek yönlü binom: şansla (p=0.5) en az `correct` doğru olasılığı.
- `make_trials(n: int, seed=None) -> list`
- `verdict(correct: int, n: int, alpha: float=0.05) -> dict`
- `switch_plan(target: str, other: str) -> list`
- `excerpt(clip: str, start: float, dur: float) -> str`
- `play_as(codec: str, other: str, wav: str)`
- `run(codec_a='aac', codec_b='sbc', clip=None, n=12, start=0.0, dur=8.0, answers=None, apply=False, out_dir=None, log=print, ask=input) -> dict` — answers: yalnız otomatik (headful duman) test için önceden verilmiş cevaplar listesi.

## Testler

- [`tests/live/test_live.py`](../../tests/live/test_live.py) — T-L01, T-L10, T-L12, T-L13, T-L14, T-L20
- [`tests/live/test_live_d7.py`](../../tests/live/test_live_d7.py) — T-L43, T-L44
- [`tests/test_abx.py`](../../tests/test_abx.py) — U18
