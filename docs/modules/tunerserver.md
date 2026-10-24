# `btaudio/tunerserver.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [application](../layers/L5-bta-software.md#application) |
| rol | Eski bas ayarlayıcı sunucusu + PwApplier (pw-cli ile canlı yazım) |
| boyut | 162 satır |
| içe aktarır (iç) | [`loudness`](loudness.md), [`tuner`](tuner.md) |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__`, `http`, `json`, `os`, `subprocess`, `threading`, `time` |
| kullanan modüller | [`cli`](cli.md), [`consoleserver`](consoleserver.md), [`crossfade`](crossfade.md), [`zipperverify`](zipperverify.md) |

## Amaç (modül docstring'i)

F8 v2 — Canlı bas ayarlayıcının yerel HTTP sunucusu (yalnız 127.0.0.1). Uygulayıcı enjekte edilir:
gerçek kullanımda `PwApplier` (pw-cli set-param), testte sahte uygulayıcı.

## Sabitler

| ad | değer |
|---|---|
| `PAGE` | `os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file…` |
| `NODE` | `'effect_input.bta_bass_eq'` |

## Genel API

### `class PwApplier`

Çalışan filter-chain düğümüne kontrol değerlerini yazar (servis yeniden başlatılmaz).

- `__init__(self, node_name=NODE)`
- `apply(self, st, bypass=False)`
- `apply_payload(self, payload)`

### `class Session`

—

- `__init__(self, applier, on_save, initial=None, idle_timeout_s=3600)`
- `snapshot(self)`
- `set_gains(self, gains)`
- `set_bypass(self, on)`
- `save(self)`

- `make_handler(sess: Session, stop_event: threading.Event)`
- `serve(sess: Session, port: int=0)` — Sunucuyu başlatır; (httpd, url, stop_event, thread) döner. Boşta kalma süresi dolunca kendini kapatır.

## Testler

- [`tests/ui/test_bass_tune_page.py`](../../tests/ui/test_bass_tune_page.py) — T-U02
