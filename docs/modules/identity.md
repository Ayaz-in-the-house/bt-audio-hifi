# `btaudio/identity.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [infrastructure](../layers/L5-bta-software.md#infrastructure) |
| rol | Cihaz kimliği: ad + bilinen MAC kümesi önbelleği, kulaklık seçici, MAC'siz filtre hedefi (U72) |
| boyut | 105 satır |
| içe aktarır (iç) | [`paths`](paths.md) |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__`, `datetime`, `json`, `os`, `re` |
| kullanan modüller | [`collect`](collect.md) |

## Amaç (modül docstring'i)

U72 cihaz kimliği: kulaklık = ad (alias) + bilinen MAC kümesi. MAC tek başına kimlik DEĞİLDİR.

Neden: yeniden eşleştirme / yeni ünite / TWS'de birincil tekin değişmesi yeni MAC verir. Filtre hedefi MAC'e
bağlıyken (2026-10-15) akışlar filtreyi sessizce atladı — EQ yok, analizör sessiz, otomatik mod ölü.

- Önbellek: $XDG_CONFIG_HOME/bt-audio-hifi/device.json {alias, macs[], last_mac, updated} — atomik yazım.
- Seçim (çakışma yok): bilinen MAC > aynı ad > kulaklık biçimli (headset/headphone/hands-free) cihaz.
  Hoparlör (JBL vb.) hiçbir koşulda kulaklık sayılmaz.
- Filtre hedefi: {media.class, device.api, node.description} — MAC içermez. WirePlumber smart filter hedefi
  tüm özellikleri birebir (VE) eşleştirir, regex yok (filter-utils.lua, WP 0.5.14).

## Sabitler

| ad | değer |
|---|---|
| `HEADPHONE_FORMS` | `{'headset', 'headphone', 'hands-free', 'handsfree', 'earbuds'}` |

## Genel API

- `default_path() -> str`
- `load(path: str | None=None, legacy: str | None=None) -> dict` — legacy: C5.1 düz MAC dosyası (varsayılan: önbelleğin yanındaki `device`) — tek seferlik göç kaynağı.
- `remember(dev: dict, path: str | None=None) -> dict` — Seçilen cihazı önbelleğe ekle (MAC kümesi büyür, ad güncellenir). Değişiklik yoksa yazmaz.
- `is_headphone(dev: dict) -> bool`
- `choose(devices: list[dict], ident: dict | None) -> dict | None` — Bağlı BT ses cihazlarından kulaklığı seç. devices: [{mac, alias, form_factor}].
- `safe_alias(alias) -> bool` — Cihaz adı uzaktaki cihazın yayınıdır (güvenilmez) → yalnız config'e kaçışsız yazılabilir karakterler.
- `target(alias: str) -> dict | None` — MAC'siz smart filter hedefi; güvensiz adda None (çağıran node.name'e düşer).

## Testler

- [`tests/test_identity.py`](../../tests/test_identity.py) — U72
- [`tests/test_retarget.py`](../../tests/test_retarget.py) — U71, U72
