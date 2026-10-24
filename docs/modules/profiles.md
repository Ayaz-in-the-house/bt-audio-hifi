# `btaudio/profiles.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [domain](../layers/L5-bta-software.md#domain) |
| rol | Profil deposu mantığı: kaydet/kilit/çalışma kopyası/çöp/içe-dışa aktar |
| boyut | 288 satır |
| içe aktarır (iç) | [`console`](console.md) |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__`, `hashlib`, `json`, `os`, `re`, `shutil`, `time` |
| kullanan modüller | [`consoleserver`](consoleserver.md) |

## Amaç (modül docstring'i)

C1 — Kullanıcı profil deposu. Bir profil = adlandırılmış konsol durumu; dosya başına bir JSON (şema `bta.profile/1`).

Tasarım kararları:
- kimlik = addan türetilen slug (büyük/küçük harf ve noktalama farkı aynı profil) → "aynı ad" çakışması tek kuralla;
- yazım atomik (geçici dosya + os.replace) → yarım yazılmış profil olmaz;
- silme = çöpe taşıma (geri alınabilir, core-principles §1);
- içe aktarma her durumu `console.sanitize`'dan geçirir (sınır dışı değerler kırpılır, bozuk yapı reddedilir);
- kimlik doğrulaması regex + realpath: dışarıdan gelen hiçbir kimlik depo dizininden çıkamaz (E16 sınıfı).

## Sabitler

| ad | değer |
|---|---|
| `SCHEMA` | `'bta.profile/1'` |
| `MAX_NAME` | `80` |
| `META_KEYS` | `('locked', 'auto', 'derived_from', 'genres')` |

## Genel API

### `class Conflict(Exception)`

Aynı adlı profil var ve üzerine yazma istenmedi (HTTP 409).

- `__init__(self, pid)`

### `class ProfileStore`

Dosya başına bir profil. `writer` verilirse yazımlar ARKA PLANDA yapılır (istek yolu diske dokunmaz, D1.3); henüz diske inmemiş belgeler bellek katmanında (`_pending`) tutulur → okuma her zaman en güncel hâli görür.

- `__init__(self, directory: str, writer=None)`
- `exists(self, pid: str) -> bool` — Kimlikli profil var mı (bekleyen yazım dahil).
- `next_auto_number(self) -> int` — Özel N numarası ASLA yeniden kullanılmaz (silinen Özel 1'den sonra Özel 3 gelir) — sayaç kalıcı.
- `bump_seq(self, n: int)` — Özel N sayacını kalıcı olarak ilerletir (numara asla yeniden kullanılmaz).
- `get(self, pid: str) -> dict` — Profil belgesi (bekleyen yazım katmanı önce); yoksa KeyError.
- `list(self) -> list` — Profil özet satırları (önbellekli; yazımda geçersizleşir).
- `save(self, name: str, state: dict, overwrite: bool=False, notes: str | None=None, meta: dict | None=None) -> str` — meta: locked (varsayılan True — adıyla kaydedilen profil 'ana' profildir), auto, derived_from, genres.
- `update_state(self, pid: str, state: dict)` — Çalışma kopyasının otomatik kaydı: yalnız durum + zaman (meta korunur).
- `set_meta(self, pid: str, **meta)` — Meta alanlarını (locked/auto/derived_from/genres) günceller.
- `rename(self, pid: str, new_name: str, overwrite: bool=False) -> str` — Profili yeni ada taşır; ad doluysa ve overwrite yoksa Conflict.
- `duplicate(self, pid: str) -> str` — '(kopya)' ekli yeni profil üretir.
- `delete(self, pid: str) -> str` — Profili .trash/ altına taşır, geri yükleme belirteci döner (kalıcı silme YOK).
- `restore(self, token: str) -> str` — Çöpten geri yükler; ad çakışırsa '(geri yüklendi)' eki.
- `trash_list(self) -> list` — Çöp kutusu (D6): en yeni önce. Silme tarihi belirtecin içinden okunur.
- `export(self, pid: str) -> dict` — Paylaşım biçimi (şema bta.profile/1).
- `import_doc(self, doc, overwrite: bool=False) -> str` — Paylaşım belgesini doğrular, sanitize eder, kilitli profil olarak kaydeder.

- `slug(name: str) -> str` — Profil adından güvenli kimlik (Türkçe harfler korunur, yol karakterleri atılır).

## Testler

- [`tests/test_profiles.py`](../../tests/test_profiles.py) — U41, U42
