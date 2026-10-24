# `btaudio/btmon.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [infrastructure](../layers/L5-bta-software.md#infrastructure) |
| rol | btmon/RSSI kaydı ayrıştırma (root kaydı kullanıcıdan) |
| boyut | 73 satır |
| içe aktarır (iç) | — |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__`, `re`, `subprocess` |
| kullanan modüller | [`cli`](cli.md) |

## Amaç (modül docstring'i)

F6.2 — btmon kaydı (`btmon -r` metni) ve `btmgmt conn-info` örneklerinin ayrıştırılması.

Kayıt ROOT ister → kullanıcı `tools/btmon-capture.sh` ile alır; okuma root istemez (`btmon -r`).
Başlık satırı biçimi (BlueZ monitor/packet.c): `< ACL Data TX: Handle H flags F dlen N   #seq [hciX] <zaman>`.
A2DP medya akışı sabit aralıklı ACL TX paketleridir → büyük boşluk = takılma adayı; Mode/Role Change,
Disconnect ve Number of Completed Packets gecikmesi radyo sorunlarının izidir.

## Sabitler

| ad | değer |
|---|---|
| `WATCH` | `('Mode Change', 'Role Change', 'Disconnect Complete', 'Link Supervi…` |

## Genel API

- `parse_trace(lines, audio_handle=None) -> dict`
- `parse_rssi(lines) -> dict`
- `read_btsnoop(path)`
- `dominant_handle(lines)` — A2DP medya akışı en çok bayt taşıyan ACL tanıtıcısıdır (klavye/fare küçük paketler).

## Testler

- [`tests/test_btmon.py`](../../tests/test_btmon.py) — U27
