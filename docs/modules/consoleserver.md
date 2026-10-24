# `btaudio/consoleserver.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [application](../layers/L5-bta-software.md#application) |
| rol | Session (tek durum sahibi) + yerel HTTP API + güvenlik kapıları |
| boyut | 762 satır |
| içe aktarır (iç) | [`abxsession`](abxsession.md), [`autoctl`](autoctl.md), [`console`](console.md), [`history`](history.md), [`journal`](journal.md), [`paths`](paths.md), [`profiles`](profiles.md), [`tunerserver`](tunerserver.md) |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__`, `http`, `json`, `os`, `re`, `threading`, `time`, `urllib` |
| kullanan modüller | [`cli`](cli.md) |

## Amaç (modül docstring'i)

F9 — Profesyonel konsolun yerel sunucusu (yalnız 127.0.0.1). Tam durum PUT edilir → sanitize → canlı uygula.
Kullanıcı profilleri repo DIŞINDA (`paths.profiles_dir()`, C0); dışa/içe aktarma ile paylaşılır.

## Sabitler

| ad | değer |
|---|---|
| `ROOT` | `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` |
| `PAGE` | `os.path.join(ROOT, 'tools', 'console.html')` |
| `ADMIN_PAGE` | `os.path.join(ROOT, 'tools', 'admin.html')` |
| `BUNDLE_SCHEMA` | `'bta-bundle/1'` |
| `NODE` | `'effect_input.bta_console'` |
| `MAX_BODY` | `256 * 1024` |
| `CSP` | `"default-src 'self'; script-src 'self' 'unsafe-inline'; style-src '…` |

## Genel API

### `class Session`

Canlı konsol oturumu (application katmanı): tek durum sahibi.

- `__init__(self, applier, on_commit, initial=None, idle_timeout_s=3600, profiles_dir=None, analyzer=None, device=None, writer=None, clock=time.time, tone_player=None)`
- `set_loud(self, db)` — U78 ses yükseltme: ayarı yazar + sınırlayıcıya canlı uygular (A/B geçişi gerekmez, tek kazanç).
- `set_auto_offsets(self, offsets, fade_s=1.5)` — ADL üst katmanını ayarlar/kaldırır (None) ve 1,5 sn geçişle uygular; kullanıcının durumuna/geçmişine YAZMAZ.
- `auto_load(self, target, fade_s=1.5)` — APC hedefi: "preset:<id>" | "profile:<id>". Geri alınabilir (nav geçmişi); çalışma kopyası kayıtlı kalır.
- `dirty(self)` — Kilitli profil/tarz aktifken kaydedilmemiş değişiklik var mı (çalışma kopyası her an kayıtlı → False).
- `view(self)` — Arayüzün tam görünümü: durum, eğriler, tarzlar, profiller, geçmiş, kayıt durumu, otomasyon, uyarılar, ton.
- `auto_view(self)` — Hafif otomasyon görünümü (1 sn yoklama için): motor durumu, ADL katmanı + eğrisi, aktif profil.
- `set_state(self, st, seal=False)` — Elle düzenleme: kilitli/tarz aktifse Özel N çatalı açar, uygular, geçmişe ve arka plan günlüğe ekler (istek yolu diske yazmaz).
- `history_seal(self)` — Açık geçmiş adımını kapatır (kaydırıcı bırakıldı = bir geri-al adımı).
- `undo(self)` — Geri al: çalışma kopyası geçmişi, yoksa tarz/profil yükleme (nav) geçmişi.
- `redo(self)` — İleri al: undo'nun simetriği.
- `set_bypass(self, on)` — EQ'suz dinleme (A/B): EQ ve uzay kapalı, geçişle.
- `preset(self, pid)` — Hazır tarz uygular (nav geçmişine işlenir); Uzay tarzları mevcut ayarda düzenleme sayılır.
- `save_profile(self, name, overwrite=False, notes=None)` — Profil olarak kaydet: çalışma kopyası aktifse onu ADLANDIRIP ana (kilitli) profile TERFİ ettirir; değilse mevcut durumu yeni kilitli profil olarak kaydeder.
- `promote(self, pid, name, overwrite=False, notes=None)` — Çalışma kopyasını adlandırıp kilitli ana profile terfi ettirir.
- `apply_to_parent(self)` — Çalışma kopyasını türediği ANA profile yaz (yalnız açık eylemle — ana profil kendiliğinden değişmez).
- `load_profile(self, pid)` — Kullanıcı profili yükler (elle dokunuş sayılır → otomasyon askıya alınır).
- `rename_profile(self, pid, name, overwrite=False)` — Profil adını değiştirir; çalışma kopyasında terfi ile aynı.
- `set_genres(self, pid, genres)` — Profile tür etiketleri yazar (APC eşlemesi bunları okur).
- `duplicate_profile(self, pid)` — Profili kopyalar ('(kopya)' ekiyle).
- `delete_profile(self, pid)` — Profili çöp kutusuna taşır; geri yükleme belirteci döner.
- `restore_profile(self, token)` — Çöp kutusundaki profili belirteçle geri yükler (ad çakışırsa ek alır).
- `import_profile(self, doc, overwrite=False)` — Tek profil JSON'unu içe aktarır (sanitize, kilitli).
- `play_tone(self, kind, seconds=4.0)` — EQ'suz (kulaklığın kendi yanıtı) kısa ton: kulak tıkacı oturması bası belirler (R40). Uygulama kulaktaki sesi ÖLÇEMEZ (mikrofon yok) — kullanıcı uçları değiştirip bas tonunun en dolgun duyulduğunu seçer.
- `stop_tone(self, restore=True)` — Oturma testi tonunu durdurur ve (restore=True) önceki EQ/bypass hâlini geri getirir.
- `abx_view(self)`
- `abx_clip_from(self, source)` — source: "music" (EQ öncesi dokunuştan 12 sn, kullanıcının çalan müziği) | "default" (hazır klip).
- `abx_start(self, a='aac', b='sbc')`
- `abx_do(self, fn, *args)`
- `admin_profiles(self)` — Yönetim tablosu: profil satırları + dosya/günlük boyutu + sürüm sayısı.
- `admin_timeline(self, pid)` — Profilin sürüm zaman çizelgesi: her sürümün zamanı, özeti ve bir öncekine göre fark satırları.
- `admin_restore(self, pid, v)` — Bir sürümü GERİ YÜKLE: geçmiş silinmez, o sürüm yeni bir sürüm olarak eklenir (ve geri alınabilir).
- `admin_export_all(self)` — Tüm profilleri tek pakette (bta-bundle/1) döndürür.
- `admin_import_bundle(self, bundle)` — bta-bundle/1 paketini içe aktarır (en çok 500 profil); şema yanlışsa ValueError.
- `commit(self)` — 'Açılışta kullan': mevcut durumu kalıcı config olarak kurar (on_commit).

### `class ApiError(Exception)`

HTTP hata kodu taşıyan API istisnası.

- `__init__(self, code, msg, **extra)`

- `make_handler(sess: Session, stop: threading.Event, allow_hosts=())` — Session'a bağlı HTTP işleyici sınıfı üretir (Host/JSON/boyut kapıları, CSP, rotalar). allow_hosts: loopback dışında açıkça adlandırılmış Host adları (ör. `tailscale serve` tailnet adı).
- `serve(sess: Session, port: int=0, allow_hosts=())` — 127.0.0.1'de iş parçacıklı sunucu + boşta kalma bekçisi başlatır → (httpd, url, stop olayı).

## Testler

- [`tests/live/test_live_auto.py`](../../tests/live/test_live_auto.py) — T-L39, T-L40, T-L41, T-L42, U62
- [`tests/test_admin.py`](../../tests/test_admin.py) — U63
- [`tests/test_analyzer.py`](../../tests/test_analyzer.py) — T-L40, U44, U46
- [`tests/test_autoengine.py`](../../tests/test_autoengine.py) — U58, U59, U60, U73
- [`tests/test_loud_limiter.py`](../../tests/test_loud_limiter.py) — U77, U78
- [`tests/test_profiles.py`](../../tests/test_profiles.py) — U41, U42
- [`tests/test_protection.py`](../../tests/test_protection.py) — U65
- [`tests/test_server_security.py`](../../tests/test_server_security.py) — U36, U47
- [`tests/test_service.py`](../../tests/test_service.py) — U74, U76
- [`tests/test_workcopy.py`](../../tests/test_workcopy.py) — U51, U53
- [`tests/ui/test_abx_page.py`](../../tests/ui/test_abx_page.py) — T-U08
- [`tests/ui/test_admin_page.py`](../../tests/ui/test_admin_page.py) — T-U06
- [`tests/ui/test_auto_page.py`](../../tests/ui/test_auto_page.py) — T-U05
- [`tests/ui/test_console_page.py`](../../tests/ui/test_console_page.py) — T-U04
- [`tests/ui/test_protection_page.py`](../../tests/ui/test_protection_page.py) — T-U07, U65
