# `btaudio/state.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [domain](../layers/L5-bta-software.md#domain) |
| rol | Snapshot diff, WirePlumber durum ayrıştırma, config manifesti |
| boyut | 88 satır |
| içe aktarır (iç) | — |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__`, `hashlib`, `os`, `re` |
| kullanan modüller | [`cli`](cli.md), [`collect`](collect.md) |

## Amaç (modül docstring'i)

Saf durum mantığı: snapshot diff, WirePlumber state dosyası ayrıştırma, config drop-in manifesti.

## Sabitler

| ad | değer |
|---|---|
| `VOLATILE` | `{'taken_at', 'label', 'battery', 'uptime', 'load', 'delay_us'}` |

## Genel API

- `diff(a: dict, b: dict) -> dict`
- `parse_wp_state(text: str) -> dict` — ~/.local/state/wireplumber/<dosya> — `[grup]` başlıkları + `anahtar=değer` satırları (değer JSON olabilir).
- `sha256_file(path: str) -> str`
- `config_manifest(src_roots, dst_root: str) -> dict` — Her kaynak kökteki (repo şablonları + üretilmiş kullanıcı config'i) her dosya için kurulu kopyanın durumu: ok | drift | missing. `src` alanı hangi kökten kurulacağını söyler (C0: iki kök).
- `spa_json_name(value: str)` — SPA JSON'daki `name` alanı. SPA JSON iki nokta üst üsteyi zorunlu tutmaz; PipeWire'ın kendi modülleri `{ "name""x" }` yazabilir (module-switch-on-connect.c:142) → katı json.loads bunu reddeder.

## Testler

- [`tests/test_paths.py`](../../tests/test_paths.py) — U40
- [`tests/test_state.py`](../../tests/test_state.py) — U07, U10
