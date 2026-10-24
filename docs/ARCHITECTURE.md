# ARCHITECTURE — bt-audio-hifi (bağlayıcı sözleşme)

> Sürüm: PRD-BTA04 tamamlanışı (2026-09-28). Katman katman ayrıntı: [layers/](layers/00-overview.md) ·
> modül modül (kaynaktan üretilir): [modules/](modules/README.md) · özellikler: [FEATURES](FEATURES.md).
> Factory faz 05/06 (`~/private-project-2/pipeline/05-architecture.md`, `06-security-design.md`).

Desen: **modüler monolit, portlar ve adaptörler** (tek süreç, tek kullanıcı, yerel). Bağımlılık yönü daima İÇE doğru.

## Yazılım katmanları (L5 içi)

| katman | modüller | kural |
|---|---|---|
| **domain** (saf, G/Ç yok) | `dsp` `console` `profiles` `history` `features` `autoctl` `presetfit` `state` `codecs` `bass` `loudness` `eqconf` `analysis` `tuner` | numpy/scipy dışında içe aktarım yok; saat/disk/ağ YOK → deterministik birim test |
| **application** | `consoleserver.Session` (tek durum sahibi, kilit) · `autoengine.AutoEngine` (1 Hz otomasyon) · `tunerserver` (eski) | domain'i çağırır; altyapıya yalnız arayüz üzerinden |
| **infrastructure** | `crossfade` `analyzer` `journal` `classifier` `paths` `procs` `tones` `collect` `sbclib` `resample` `link` `btmon` `bench` | yan etkiler burada; hepsi sahte ile değiştirilebilir (testler) |
| **ölçüm** | `eqverify` `consoleverify` `analyzerverify` `zipperverify` `abx` | ürün katmanında kanıt; kullanıcının kulaklığına dokunmaz (null sink) |
| **presentation** | HTTP (`consoleserver.make_handler`) · `tools/console.html` · `tools/admin.html` | yalnız JSON API; domain içe aktarmaz |
| **cli** | `cli` (`bin/bta`) | giriş noktası |

Her modülün katmanı `tools/gen-docs.py` `LAYERS` haritasında tanımlıdır; yeni modül haritaya eklenmeden U67 geçmez.

## Geçilmez çizgiler

1. HTTP istek iş parçacığı diske YAZMAZ (yalnız kuyruk → `journal.Writer`) — U52.
2. PipeWire'a canlı parametreyi yalnız `Crossfader` yazar (A/B: yalnız SESSİZ zincire yükleme) — U57, R33.
3. Hazır tarzlar (kod) hiçbir yoldan değiştirilemez; kilitli profil yalnız açık "üzerine yaz / ana profile uygula" ile değişir — U51.
4. Otomasyonun ADL düzeltmesi bir **üst katmandır**: sese eklenir, kullanıcının durumuna / çalışma kopyasına / geçmişine YAZILMAZ — U58.
5. Kullanıcı her zaman kazanır: elle dokunuş otomasyonu 10 sn askıya alır; APC yüklemesi geri alınabilir (nav geçmişi) — U59.
6. Hiçbir alt süreç ebeveyninden uzun yaşamaz (`procs.spawn`: tek doğurucu iş parçacığı + `setpriv --pdeathsig`) — U64, E23.
7. Kimse bakmıyorken bedel ödenmez: analizör abonesizken süreç yok; yalnız otomasyon dinliyorsa hafif mod — U46, U62.
8. Kullanıcı verisi repo dışında (XDG); repo'ya çalışma zamanında yazılmaz — U40, U49.

## Veri akışı

**Elle düzenleme:** UI → `POST /api/state` → `Session.set_state` (kilit, sanitize) → aktif tarz/kilitli profilse
**Özel N çatalı** → `Crossfader.submit(40 ms)` → `History.push` (1 sn birleştirme) → `journal.enqueue_lines` (O(1)) → yanıt.
Arka planda `journal.Writer`: 300 ms birleştir → `journal/<id>.jsonl` satırı (≈2 KB) + profil dosyasını atomik yaz.

**Otomasyon:** `AutoEngine.tick` (1 Hz) → `Analyzer.snapshot("pre")` (hafif mod: halka tampon + istek anında FFT) →
LTAS τ 8 sn → `features.region_excess` + `classifier.predict` (2 sn'de bir) → **APC:** `ProfileChanger.update` →
`Session.auto_load(target, fade 1,5 s)` · **ADL:** `DynamicEQ.step` → 0,5 dB kuanta → `Session.set_auto_offsets(fade 1,5 s)`.

**A/B zincir grafı (D2, R42 sonrası biçim):**
```
girdi X ─ copyX ─┬─ zincirA_X: preAX·denge → eqAX_1…10 (bq_raw) → hiAX/loAX → mixAX ─┐
                 └─ zincirB_X: (aynısı)                                            ─┴─ sumX (mixer: Gain 1 = A, Gain 2 = B) → çıktı X
```
Geçiş = yeni durumu sessiz zincire yükle (bq belleğinin sıfırlanması sessizde duyulmaz) → `sumX` kazançlarını
`STEP_S` = 12 ms adımlarla kaydır (doğrusal, ilişkili sinyalde sabit genlik). `ramp`/`mult` KULLANILMAZ (R42: denetim
portları aralıksız → 0'a kırpılır). Bir geçiş bitmeden sessizleşen zincir yeniden yüklenmez; bekleyen istekler birleşir.

## Hata kipleri

| hata | davranış |
|---|---|
| pw-cli başarısız / düğüm yeniden doğdu | kalıcı oturum yeniden çözülür ve başlatılır; hata `Crossfader.errors` → görünür |
| pw-cli stdin EOF | `quit` ile kapatılır (EOF'ta dönüyordu, E23); ebeveyn ölürse SIGTERM |
| disk dolu / yazılamıyor | durum bellekte kalır, `saved.errors` arayüzde "kayıt hatası!" |
| onnxruntime / model yok ya da sha uyuşmaz | sınıflayıcı `available=False`; otomasyon yalnız tonal dengeyle çalışır, arayüz nedeni yazar |
| geçiş sürerken yeni istek | en sonuncu kazanır (sıralayıcı) |
| analizör verisi yok (sessizlik) | otomasyon karar vermez, son durum korunur |
| otomasyon içinde istisna | motor düşmez; hata `status().errors`'a yazılır |
| sunucu kapanışı | ADL katmanı sesten kaldırılır, otomasyon ayarı diske yazılır, pw-cli `quit` |

## Güvenlik (faz 06)

Varlıklar: kullanıcı profilleri/geçmişi, ses yolu. Tehditler: tarayıcıdaki başka site (CSRF / DNS rebinding), dosya
sistemi geçişi, büyük istek, zehirli model dosyası, zehirli içe aktarılan profil/paket. Önlemler: yalnız 127.0.0.1 +
Host kontrolü + yalnız JSON POST + CSP (U36, U47, U63) · profil kimliği regex + realpath · istek ≤ 256 KB · profil/paket
sanitize + şema kontrolü · model **sha256 sabitli** (`models.lock.json`), yalnız kullanıcı komutuyla indirilir
(`bta model fetch`), uyuşmazsa silinir · ONNX tek iş parçacığı, sağlayıcı CPU. Ağ: sınıflama tamamen yerel; ses
verisi makineden çıkmaz.
