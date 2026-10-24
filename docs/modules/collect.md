# `btaudio/collect.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [infrastructure](../layers/L5-bta-software.md#infrastructure) |
| rol | Canlı sistem durumu toplayıcı (salt-okuma: pactl, bluez, systemd) |
| boyut | 284 satır |
| içe aktarır (iç) | [`codecs`](codecs.md), [`identity`](identity.md), [`paths`](paths.md), [`state`](state.md) |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__`, `datetime`, `json`, `os`, `re`, `subprocess` |
| kullanan modüller | [`abx`](abx.md), [`cli`](cli.md), [`link`](link.md), [`resample`](resample.md) |

## Amaç (modül docstring'i)

Canlı sistem durumu toplayıcı (salt-okuma). Her dış komut timeout'ludur; bir kaynak düşerse alan `error` taşır,
snapshot yine üretilir (kısmi durum sessizce "yok" sayılmaz).

## Sabitler

| ad | değer |
|---|---|
| `HOME` | `os.path.expanduser('~')` |
| `REPO` | `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` |
| `DEVICE_MAC` | `_detect_mac()` |
| `DEV_ID` | `DEVICE_MAC.replace(':', '_')` |
| `CARD` | `f'bluez_card.{DEV_ID}'` |
| `WP_STATE` | `os.path.join(HOME, '.local/state/wireplumber')` |
| `CONFIG_SRC` | `os.path.join(REPO, 'config')` |
| `CONFIG_DST` | `os.environ.get('BTA_CONFIG_DST') or os.path.join(HOME, '.config')` |
| `EE_APP` | `'com.github.wwmm.easyeffects'` |

## Genel API

- `filter_target()` — U72: konsol/EQ smart filter hedefi — MAC'siz kimlik (ad). Ad bilinmiyorsa (eski önbellek, kulaklık yok) bağlı sink adı; o da yoksa None (kurulum yapılmaz).
- `run(cmd, timeout=8)`
- `run_json(cmd, timeout=8)`
- `versions()`
- `device()`
- `other_bt_devices()`
- `card()`
- `sink()`
- `bluez_endpoints()`
- `wp_settings()`
- `wp_state()`
- `default_nodes()` — default.configured.* (istemcinin seçtiği) ve default.* (WirePlumber'ın etkin seçimi).
- `set_configured_default_sink(name: str) -> bool`
- `graph_clock()`
- `streams_to_sink()` — BT sink'e — DOĞRUDAN veya bizim smart filtrelerimiz (effect_input.bta_*) ÜZERİNDEN — giden UYGULAMA akışları. Filtre kurulunca uygulamalar filtreye bağlanır; yalnız sink'e bakmak gerçek çalanı gizler (ölçüldü 2026-09-27).
- `wifi()`
- `easyeffects()`
- `configs()` — Repo şablonları + kullanıcıya özel üretilmiş config'ler (C0) → kurulu kopyaların durumu.
- `snapshot(label: str='') -> dict`

## Testler

- [`tests/live/test_live.py`](../../tests/live/test_live.py) — T-L01, T-L10, T-L12, T-L13, T-L14, T-L20
- [`tests/live/test_live_d7.py`](../../tests/live/test_live_d7.py) — T-L43, T-L44
- [`tests/test_commit_isolation.py`](../../tests/test_commit_isolation.py) — T-L37, U49, U72
