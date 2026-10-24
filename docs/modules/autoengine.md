# `btaudio/autoengine.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [application](../layers/L5-bta-software.md#application) |
| rol | Otomasyon motoru: analizör → öznitelik/sınıflayıcı → APC/ADL → Session |
| boyut | 281 satır |
| içe aktarır (iç) | [`autoctl`](autoctl.md), [`console`](console.md), [`features`](features.md) |
| içe aktarır (dış) | `numpy` |
| standart kitaplık | `__future__`, `json`, `math`, `os`, `threading`, `time` |
| kullanan modüller | [`cli`](cli.md) |

## Amaç (modül docstring'i)

D3–D5 canlı bağlantı (application): analizör → öznitelik + sınıflayıcı → APC/ADL kararı → oturuma uygula.

Katman sınırları (docs/ARCHITECTURE.md):
- Karar mantığı SAF: `autoctl` (APC/ADL) + `features` (tonal denge). Bu dosya yalnız zamanlar ve bağlar.
- Ses yolu: ADL düzeltmesi `Session.set_auto_offsets` ile ÜST KATMAN olarak uygulanır → kullanıcının durumu, çalışma
  kopyası ve geçmişi DEĞİŞMEZ (U58). APC `Session.auto_load` ile tarz/profil yükler (geri alınabilir, nav geçmişi).
- Elle dokunuş → `manual()` → APC 10 sn askı (kullanıcı her zaman kazanır).
- Kaynak disiplini: mod kapalıyken analizör aboneliği YOK → yakalama süreci yok (kimse bakmıyorken bedel ödenmez).
  Sınıflayıcı 2 sn'de bir, tek iş parçacığı (ölçüm: 5–10 ms / 2 sn ses, T-L40).
- Tıksızlık: ADL çıkışı 0,5 dB adımlara kuantalanır → yalnız anlamlı değişimde, 1,5 sn A/B geçişle uygulanır (D2/R43).

## Sabitler

| ad | değer |
|---|---|
| `MODES` | `('off', 'apc', 'adl', 'both')` |
| `MODE_LABELS` | `{'off': 'Kapalı', 'apc': 'Otomatik profil', 'adl': 'Canlı uyarlama'…` |
| `DEFAULT_MAPPING` | `{'elektronik': 'preset:elektronik', 'hiphop': 'preset:hiphop', 'roc…` |
| `GENRE_LABELS` | `{'elektronik': 'Elektronik', 'hiphop': 'Hip-hop / R&B', 'rock': 'Ro…` |
| `ALIASES` | `{'hip-hop': 'hiphop', 'hip hop': 'hiphop', 'rap': 'hiphop', 'r&b': …` |
| `LTAS_TAU_S` | `8.0` |
| `REF_MIN_W` | `1 / 300` |
| `ADL_QUANT` | `0.5` |
| `ADL_HYST` | `0.75` |
| `ADL_MIN_S` | `5.0` |
| `CLASSIFY_S` | `2.0` |

## Genel API

### `class AutoEngine`

Otomasyon motoru: 1 Hz tick ile analizör anlık görüntüsünü okur, türü/tonal dengeyi çıkarır, APC/ADL kararını Session'a uygular. Durum (mod, öğrenilen referans/bias) `state_path`'e yazılır.

- `__init__(self, sess, analyzer, classifier=None, clock=time.monotonic, state_path=None, period_s=1.0, autostart=True)`
- `flush(self)` — Bekleyen ayar değişikliğini (mod, bias, referans) atomik olarak diske yazar; değişiklik yoksa no-op.
- `set_mode(self, mode)` — Modu değiştirir (off|apc|adl|both): analizör aboneliğini açar/kapatır, ADL dışı modda katmanı kaldırır. Geçersiz modda ValueError.
- `configure(self, body: dict)` — /api/auto gövdesi: {mode?, nudge?: {band, delta}, reset_learning?} → status().
- `hold(self, reason: str)` — Otomasyonu açıkça askıya al (kör test gibi): release() çağrılana dek karar verilmez, katman korunur.
- `release(self)` — hold()'u kaldır.
- `manual(self)` — Kullanıcı elle dokundu (oturum çağırır) → APC askıya alınır; kullanıcının seçimi otomasyonu ezer.
- `mapping(self) -> dict` — Tür → hedef eşlemesi: varsayılan hazır tarzlar, üzerine tür etiketli kullanıcı profilleri ('profile:<id>').
- `tick(self)` — Tek adım (test edilebilir): sessizlikte karar yok; LTAS (τ 8 sn) + sınıflama (2 sn'de bir) → APC yükleme / ADL katmanı (0,5 dB kuantalı).
- `genre(self)` — EMA'sı güven eşiğini (0,3) aşan en olası makro tür; yoksa None.
- `status(self) -> dict` — Arayüz/API durumu: mod, sınıflayıcı, tür skorları, karakter, enstrümanlar, ADL katmanı, bias, eşleme, geçiş günlüğü.
- `close(self, clear=False)` — clear=True (sunucu kapanışı): ADL katmanını sesten kaldır — motor yokken donmuş bir düzeltme kalmasın. Mod diske yazılıdır → sunucu yeniden açılınca otomasyon kaldığı yerden sürer.

- `normalize_genre(tag: str) -> str | None` — Serbest metin profil etiketini makro türe çevirir ('hip-hop' → 'hiphop'); tanınmazsa None.

## Testler

- [`tests/live/test_live_auto.py`](../../tests/live/test_live_auto.py) — T-L39, T-L40, T-L41, T-L42, U62
- [`tests/test_autoengine.py`](../../tests/test_autoengine.py) — U58, U59, U60, U73
- [`tests/ui/test_abx_page.py`](../../tests/ui/test_abx_page.py) — T-U08
- [`tests/ui/test_admin_page.py`](../../tests/ui/test_admin_page.py) — T-U06
- [`tests/ui/test_auto_page.py`](../../tests/ui/test_auto_page.py) — T-U05
