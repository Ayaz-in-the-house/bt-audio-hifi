# `btaudio/tuner.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [domain](../layers/L5-bta-software.md#domain) |
| rol | Eski canlı bas ayarlayıcı mantığı (PRD-BTA01 F8 v2) |
| boyut | 65 satır |
| içe aktarır (iç) | [`loudness`](loudness.md) |
| içe aktarır (dış) | `numpy`, `scipy` |
| standart kitaplık | `__future__` |
| kullanan modüller | [`cli`](cli.md), [`tunerserver`](tunerserver.md) |

## Amaç (modül docstring'i)

F8 v2 — Canlı bas ayarlayıcı (kullanıcı kendi müziğini dinlerken). Saf mantık; PipeWire'a uygulama `apply_live`.

Neden v2: eşit-yükseklik eşleştirmesi (v1) sahada anlaşılmadı (2026-09-27 gerçek oturum: 9/10 'tavan'). Kullanıcının
kendi gözlemi "düşük frekansları +dB yapınca güzel bas veriyor" → doğrudan tercih ayarı, anında duyulur.
Filter-chain kontrolleri çalışırken değiştirilebilir (ölçüldü: pw-cli set-param 90 Hz +9 → ölçülen +9,00 dB).

## Sabitler

| ad | değer |
|---|---|
| `BANDS` | `[('deep', 40, 0.9, 'Derin bas', 'gümbürtü, yere vuran bas (40 Hz ci…` |
| `STEP_DB` | `0.5` |
| `GRID` | `np.geomspace(20, 2000, 120).tolist()` |
| `PRESETS` | `{'notr': {'deep': 0.0, 'punch': 0.0, 'warmth': 0.0}, 'hafif': {'dee…` |

## Genel API

- `state(gains: dict) -> dict`
- `pw_params(st: dict, bypass: bool=False) -> str` — `pw-cli set-param <effect_input id> Props '<bu>'` yükü. Bant adları eqconf ile aynı: eq_band_1..N, preamp.

## Testler

- [`tests/test_tuner.py`](../../tests/test_tuner.py) — T-U02, U29
- [`tests/ui/test_bass_tune_page.py`](../../tests/ui/test_bass_tune_page.py) — T-U02
