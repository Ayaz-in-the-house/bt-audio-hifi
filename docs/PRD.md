# PRD-BTA01 — Bluetooth Kulaklık Hi-Fi Ses Hattı (Fedora / PipeWire)

| alan | değer |
|---|---|
| sürüm | 1.0.0 |
| tarih | 2026-09-27 |
| sahip | user (karar) · Claude (uygulama) |
| makine | workstation — Fedora 44, kernel 7.1.10, PipeWire 1.6.8, WirePlumber 0.5.14, BlueZ 5.87 |
| adaptör | Intel AX210 (USB 8087:0032), BT 5.x, hci0 |
| cihaz | Solix Nexus ANC (Audeeo Innovations, TWS, BT 5.4, 12 mm sürücü) — `02:00:00:00:00:02` |

## 1. Problem

Kullanıcı: *"bluetooth kulaklığa bağlıyım ancak kalitesi güzel değil … cihazın materyal kalite potansiyelini
kullanabileceğimiz … data transferinde paket sorunları mı var … çok yüksek kalitede ses istiyorum"*.

### 1.1 Ölçülmüş başlangıç durumu (S0, 2026-09-27 ~18:50)

| katman | gözlem | kanıt |
|---|---|---|
| profil | `headset-head-unit` (HFP) aktif | `pactl list cards` → `Active Profile: headset-head-unit` |
| codec | mSBC, **mono 16 kHz** | Zen akışı `output_MONO > playback_MONO` |
| kalıcılık | WirePlumber bu kartı HFP olarak kaydetmiş | `~/.local/state/wireplumber/default-profile` → `=headset-head-unit` (yedek: `state/backups/wireplumber-state-20260927-pre-session/`) |
| otomatik geçiş | `bluetooth.autoswitch-to-headset-profile = true` | `wpctl settings` |
| RF | Wi-Fi 5 GHz ch108/160 MHz → 2.4 GHz çakışması yok | `iw dev` |

### 1.2 Oturum içi ilk müdahale (S1) — PRD'den önce yapıldı, bu PRD onu kodlar ve test eder

- `pactl set-card-profile … a2dp-sink` → AAC, stereo, 48 kHz.
- `wpctl settings --save bluetooth.autoswitch-to-headset-profile false`.

## 2. Hedef ve kapsam

**Hedef:** Bu kulaklığın donanımının izin verdiği en yüksek ses kalitesini, **ölçülebilir** ve **geri alınabilir**
şekilde, kalıcı olarak sağlamak; her karar sayısal kanıta ve kaynak koda dayanmalı.

**Kapsam İÇİ:** profil/codec kalıcılığı · codec seçimi (nesnel encoder ölçümü) · AAC bitrate modu · resampler kalitesi ·
saat hızı politikası · kaynak (uygulama akışı) denetimi · EasyEffects EQ altyapısı · bağlantı sağlığı izleme ·
durum snapshot/diff aracı · test paketi · belgeler/dersler.

**Kapsam DIŞI:** PipeWire/BlueZ kaynak yaması veya derleme (laptopta derleme YASAK — remote-build rule) · kulaklık
firmware'i · sistem geneli `/etc` değişikliği (sudo gerektirir, kullanıcı-sahipli) · diğer ses cihazlarının ayarı
(yan etki analizi hariç) · ücretli streaming hizmeti seçimi.

## 3. Donanım/codec tavanı (araştırma sonucu — `docs/research/findings.md`)

- Kulaklık uzak endpoint'leri: **SBC** (sep1, bitpool 2–53) ve **AAC** (sep2, MPEG-2 LC, VBR destekli, bitrate alanı 0).
- aptX / aptX-HD / LDAC / LC3 (LE Audio) **yok** → codec tavanı **AAC** veya **SBC-XQ**.
- Canlı AAC konfigürasyonu: `80 00 84 84 00 00` → MPEG-2 AAC-LC · 48 kHz · 2 kanal · **vbr=1** · **262 144 bps**.
- PipeWire 1.6.8 kaynak (`a2dp-codec-aac.c`): `vbr=1` iken CBR'de 19,3 kHz bant genişliği genişletmesi **atlanır**
  (satır 400) → FDK'nın otomatik kesimi geçerli. Bu, F2'nin ölçmesi gereken asıl sorudur.
- PipeWire'ın AAC eklentisi ve `ffmpeg` aynı `/lib64/libfdk-aac.so.2`'ye bağlı → ffmpeg ile encoder ölçümü birebir.

## 4. Özellikler → alt katmanlar

### F0 — Altyapı (araç + test + belge)
- F0.1 `btaudio` Python paketi (stdlib): codec byte çözücüler (AAC/SBC), durum toplayıcı, snapshot diff.
- F0.2 `bin/bta` CLI: `snapshot [label]` · `diff A B` · `status` · `check` · `install` · `uninstall` · `codec` · `watch-link`.
- F0.3 Test: `tests/` (birim, saf mantık) + `tests/live/` (canlı sistem = headful kabul testleri).
- F0.4 Belge: PRD · TEST-PLAN · research/findings · lessons (errors / golden-paths / edge-cases) · STATE-LOG · CHANGELOG.

### F1 — Profil & codec kalıcılığı
- F1.1 A2DP profili kalıcı kayıt (WirePlumber `default-profile`).
- F1.2 Otomatik HFP geçişi kapalı (kalıcı `wpctl settings --save`).
- F1.3 Yeniden bağlanma dayanıklılığı: disconnect → connect sonrası A2DP+AAC'e dönmeli.

### F2 — Codec seçimi (nesnel)
- F2.1 Transport/endpoint çözümleme (canlı byte'lar → insan-okur).
- F2.2 Encoder benchmark: AAC@262k CBR (oto-bant) · AAC VBR 1–5 · SBC-XQ (44.1k dual, bitpool 43) · SBC (53) —
  test sinyalleri + müzik benzeri sinyal; metrikler: kesim frekansı, bant-içi SNR, spektral hata.
- F2.3 AAC `bitratemode` kararı (WirePlumber `monitor.bluez.properties` → `bluez5.a2dp.aac.bitratemode`).
- F2.4 Kör A/B dinleme protokolü (kullanıcının kulağı nihai hakem) + uygulanan karar.

### F3 — Kaynak kalitesi
- F3.1 Akış denetçisi: BT sink'e giden her akışın format/hız/kanalı (`pw-dump`).
- F3.2 Referans test seti (yerel üretilmiş: sweep, pembe gürültü, çok tonlu, 44.1/48 kHz FLAC).
- F3.3 Kılavuz: hangi kaynak ne verir (YouTube Opus 48k, vb.).

### F4 — Resampler + saat hızı
- F4.1 `resample.quality` drop-in'leri (client + pipewire-pulse).
- F4.2 `default.clock.allowed-rates` değerlendirmesi (resmî uyarı: "Bluetooth sorunları" → headful test ile karar).
- F4.3 Nesnel resampler ölçümü: 44.1k sweep → BT sink monitor kaydı → aliasing/gürültü tabanı.
- F4.4 CPU maliyeti ölçümü.

### F5 — EQ (EasyEffects)
- F5.1 Kurulum: Flathub `--user` (sudo'suz), sürüm/commit sabitlenmiş.
- F5.2 Preset: nötr başlangıç (AutoEQ ölçümü YOK → uydurma düzeltme eğrisi YASAK) + ayarlanabilir PEQ iskeleti.
- F5.3 Cihaza özel otomatik yükleme (yalnız bu kulaklık).
- F5.4 CPU/gecikme maliyeti ölçümü · F5.5 geri alma.

### F6 — Bağlantı sağlığı
- F6.1 Pasif izleme: WirePlumber bluez5 debug log'unda bitrate düşürme / kuyruk olayları (sudo'suz).
- F6.2 `btmon` reçetesi (sudo → kullanıcı çalıştırır) + çözümleyici.
- F6.3 RF ortamı: Wi-Fi bandı, aynı radyodaki diğer BT cihazlar.

### F8 — Bas + ses sahnesi (kullanıcı talebi, oturum içi eklendi 2026-09-27 ~19:40)
Kullanıcı: *"kulaklık daha çok vokal kalitesi odaklı güzel ancak hiç bas almıyorum … jbl, sennheiser, airpods ses
uzay kalitelerine ulaşabiliriz"*.
- F8.1 Kulakta (in-situ) bas yanıtı ölçümü: eşit-yükseklik eşleştirme (warble, 1 kHz ref) + ISO 226:2003 →
  H(f) 31,5–500 Hz; iki oturma (normal / bastırılmış) → **sızdırmazlık kazancı** (bas kaybının 1 numaralı nedeni).
- F8.2 EQ tasarımı: Harman IE bas rafı yaklaşığı (+8 dB, 105 Hz Q0.7 low-shelf biçimi) − H(f); 6 bant bq_peaking;
  bant başı ve TOPLAM güçlendirme ≤ 12 dB (12 mm sürücü + kırpılma); preamp = −tepe.
- F8.3 Uygulama mimarisi (KARAR): **WirePlumber 0.5 smart filter + PipeWire filter-chain** — EQ yalnız bu kulaklığa
  giden akışlara girer (hoparlör/Dock etkilenmez), GUI süreci yok, config tabanlı, `bq_peaking`=RBJ → tasarım modeli
  ürünle ±0,01 dB (T-L30). EasyEffects kuruldu ve sabitlendi ama **otomatik başlatılmaz**: 7/24 Qt süreci + cihaz
  autoload rota adlandırması gerekir; aynı bantlarla preset `config-optional/easyeffects/bta-bass.json` üretilir
  (GUI ile deneme/ince ayar için).
- F8.4 Ses sahnesi: AirPods "spatial audio" = HRTF + kafa takibi; burada yalnız crossfeed/HRTF evrişimi mümkün
  (kafa takibi yok) — isteğe bağlı, A/B ile karar.

### F7 — Kalıcı bilgi
- F7.1 lessons + golden-paths + edge-cases · F7.2 hafıza indeksi (`INDEX-private-project-1.md` + tetikleyici + sözleşme testi).

## 5. Bağımlılık zinciri

```
F0 ──► F1 ──► F6.1(baz çizgi) ──► F2.1 ──► F2.2 ──► F2.3 ──► F2.4
                                   │
                                   └──► F4.1 ──► F4.2 ──► F4.3/F4.4 ──► F5 ──► F7
F3 (bağımsız; F2.4 A/B için F3.2 test seti gerekir)
```

Gerekçe: F6.1 baz çizgisi değişiklikten ÖNCE alınmalı (sonra "iyileşti mi" sorusu ölçülebilsin). F4, F5'ten önce:
EasyEffects grafa girer; resampler/saat politikası onun giriş/çıkışını etkiler. F2.4 dinleme testi F3.2 setine bağlı.

## 6. Kabul kriterleri (V = karşılanmamış kriter sayısı; hedef V=0)

| # | kriter | ölçüm |
|---|---|---|
| AC1 | Profil A2DP, codec PRD kararındaki codec | `bta check` T-L01..03 |
| AC2 | Yeniden bağlanmadan sonra AC1 korunur | headful T-L10 |
| AC3 | HFP'ye otomatik düşüş yok (mikrofon açan uygulama varken) | headful T-L11 |
| AC4 | Codec kararı sayısal benchmark tablosuna dayanır | `analysis/encoder-benchmark.*` |
| AC5 | Resampler kalitesi drop-in aktif ve bir akışta ölçülmüş | T-L20..22 |
| AC6 | Cihaza özel EQ yolu kurulu ve ürün katmanında doğrulanmış; EasyEffects kurulu+sabit, isteğe bağlı | T-L30, T-L31 |
| AC7 | Bağlantı sağlığı baz + son ölçüm karşılaştırılmış | `analysis/link-health.md` |
| AC8 | `bta snapshot/diff` her durum geçişini kayıt altına almış | `state/snapshots/*` + STATE-LOG |
| AC9 | Tüm birim + canlı testler yeşil, fail/skip gerekçesiz yok | `tests/run.sh` |
| AC10 | `uninstall` tam geri dönüş (config sha'ları baz ile eşleşir) | T-L40 |
| AC11 | Bas: kulakta ölçüm (≥1 koşu) → EQ tasarımı → kurulum → EQ'nun kulaklık yolunda olduğu grafta kanıtlı | `analysis/bass/`, T-L31 |

## 7. Riskler

| risk | etki | azaltma |
|---|---|---|
| PipeWire restart ses kesintisi | birkaç saniye sessizlik | kullanıcıya duyur; yalnız config yüklemede |
| `allowed-rates` BT sorunları (resmî uyarı) | glitch/sessizlik | ayrı adım, headful test, başarısızsa uygulanmaz |
| EasyEffects sürekli CPU | pil/ısı | ölç; yalnız bu cihazda autoload; bypass seçeneği |
| Uydurma EQ | ses kötüleşir | ölçüm yoksa düzeltme eğrisi YOK (nötr) |
| Kulak testi öznel | yanlış karar | kör A/B + nesnel metrik birlikte |


---

# PRD-BTA02 — Profesyonel ses konsolu (2026-09-27 ~20:40, kullanıcı talebi)

Kullanıcı: *"sadece 3 tane şey koymuşsun … daha profesyonel scalada bir ayarlama alanı … ses uzayında daha fazla
ayarlanabilir ayarlar, profesyonel hazır profiller, grafikten oynamalar"*.

| AC | kriter | durum |
|---|---|---|
| B1 | 10 bant, 6 filtre tipi, frekans/kazanç/Q, tip dahil CANLI | ✅ R22, T-U03 |
| B2 | grafikten sürükle / tekerlek=Q / çift tık ekle-kaldır | ✅ T-U03 |
| B3 | ses uzayı: bs2b crossfeed (3 ön ayar + ince ayar), genişlik (mono uyumlu), denge | ✅ U32, T-L32 |
| B4 | ≥8 kaynaklı hazır profil | ✅ 11 profil (U35) |
| B5 | kırpılma yok (otomatik preamp) | ✅ U33 |
| B6 | profillerim (kaydet/yükle/sil), geri al/ileri al, A/B, kalıcı yap | ✅ T-U03 |
| B7 | yalnız bu kulaklık; eski bas filtresiyle çift EQ yok | ✅ T-L33 |
| B8 | ürün = model | ✅ T-L32 ±0,001 dB |
| B9 | canlı spektrum analizörü | ⏸ ertelendi (açık soru) |
| B10 | paylaşılabilir skill + süreç + profiller | ✅ `skill/bt-audio-hifi`, PROCESS, profiles |

---

# PRD-BTA03 — Konsol v2: profil yönetimi, tarz kütüphanesi, production-grade tasarım, canlı analizör, açık kaynağa hazırlık

| alan | değer |
|---|---|
| tarih | 2026-09-27 ~21:40 |
| tetik | kullanıcı: *"yapılan ayarları yeni profil olarak kaydet seçeneği olmalı mutlaka, hazır profillerde biraz daha tarz zenginliği (zengin bas gibi) … page'i profesyonel design et (ui-ux-pro-max, taste-skill, impeccable, designer-skills'ten öğrenerek) … opensource paylaşabiliriz … canlı müzik algılama feature'u"* |
| başlangıç durumu | commit `651d233` + çalışma ağacında kullanıcının 21:14'te "Kalıcı yap" ile ürettiği `60-bta-console.conf` (izlenen dosya — ürün/örnek verisi karışmış, C0'ın kanıtı) |

## Problem (ölçülmüş)

1. **Profil kaydı gizli:** kaydetme alanı sağ sütunun altında düz bir metin kutusu; "yeni profil olarak kaydet" eylemi,
   aktif profil ve "değişti" göstergesi yok. `profiles/` dizini hiç oluşmamış → kullanıcı hiç profil kaydetmemiş.
2. **Kullanıcı verisi repoda:** "Kalıcı yap" izlenen `config/…/60-bta-console.conf`'u ve `analysis/console/`'u yazıyor →
   her ayar değişikliği git'i kirletiyor; açık kaynak paylaşımında kişisel ayar/MAC sızar.
3. **Tarz kütüphanesi dar:** 11 profil, "zengin bas" gibi tür/karakter çeşitliliği yok; önizleme yok.
4. **Tasarım:** işlevsel ama "araç" kalitesinde değil (tipografi hiyerarşisi, bilgi yoğunluğu, klavye erişimi, odak, durum).
5. **Canlı analizör yok** (B9 ertelenmişti).
6. **Taşınabilirlik:** tarayıcı yolu (`~/.local/opt/zen/zen`) ve cihaz sabit.

## Özellikler → alt katmanlar

| id | özellik | alt katmanlar |
|---|---|---|
| **C0** | Ürün / kullanıcı verisi ayrımı (XDG) | C0.1 `btaudio/paths.py` (`$BTA_HOME` testte izole) · C0.2 profiller `~/.config/bt-audio-hifi/profiles/` · C0.3 kalıcı durum + üretilmiş config `~/.local/state/bt-audio-hifi/` · C0.4 göç (KOPYALA, silme) + idempotent · C0.5 izlenen config'i şablona çevir |
| **C1** | Profil yönetimi | C1.1 şema `bta.profile/1` (ad, oluşturma/güncelleme, not, durum) · C1.2 yeni-olarak-kaydet / üzerine-yaz (onaylı, 409) / yeniden adlandır / çoğalt / sil→çöp + geri al · C1.3 aktif profil + değişti (dirty) · C1.4 dışa/içe aktar (JSON, doğrulamalı, boyut sınırı) · C1.5 hazır profili "profillerime kopyala" |
| **C2** | Tarz kütüphanesi | C2.1 ≥22 profil, kategori + etiket · C2.2 her profilde `kind` (hedef-eğri / standart / tasarım) + kaynak · C2.3 niyet testleri (her profil vaat ettiği şekli verir) · C2.4 kırpılma yok · C2.5 mini önizleme eğrileri |
| **C3** | Production-grade arayüz | C3.1 `docs/DESIGN.md` (token, tip ölçeği, boşluk, hareket, erişilebilirlik; 4 tasarım reposundan kaynaklı) · C3.2 yerleşim: üst çubuk (cihaz, profil seçici+değişti, kaydet, A/B, kalıcı) · grafik+analizör · sağ ray sekmeleri (Profiller / Bant / Uzay) · C3.3 klavye (bant seçimi, ok tuşları, Q) + ARIA · C3.4 açık/koyu + WCAG AA kontrast testi · C3.5 duyarlı (390 px) |
| **C4** | Canlı analizör ("müzik algılama") | C4.1 DSP (Hann, dBFS kalibrasyonu, 1/N oktav, eğim, balistik, tepe tutma) · C4.2 seviye metresi (tepe/RMS, kırpılma sayacı) · C4.3 yakalama: EQ öncesi (`effect_input.bta_console` monitörü) + sonrası (kulaklık monitörü), **`node.autoconnect=false` + elle bağ** (R17) · C4.4 SSE akışı; abone yokken yakalama DURUR (kaynak disiplini) · C4.5 müzik var/yok algısı |
| **C5** | Açık kaynağa hazırlık | C5.1 cihaz otomatik algılama (`BTA_DEVICE` isteğe bağlı) · C5.2 taşınabilir tarayıcı açma · C5.3 `tools/oss-audit.sh` kapısı (ürün dosyalarında MAC/ev yolu yok) · C5.4 README paylaşım bölümü + NOTICE (üçüncü taraf lisansları) · C5.5 lisans seçimi = **kullanıcı kararı** |
| **C6** | Bilgi | PROCESS/lessons/golden-paths/findings/STATE-LOG/CHANGELOG 0.3.0/skill (RED→GREEN) |

## Bağımlılık zinciri

```
C0 ──► C1 ──┐
C2 ─────────┼──► C3 (UI, API'lere bağlı) ──► C5 ──► C6
C4 (backend bağımsız) ──┘
araştırma: tasarım (C3.1) · preset (C2) · analizör (C4) ── paralel ajanlar, ebeveyn yeniden doğrular
```

## Kabul kriterleri (V = karşılanmamış; hedef 0)

| AC | kriter | ölçüm |
|---|---|---|
| D1 | "Yeni profil olarak kaydet" tek tıkla erişilebilir; ad çakışmasında onay; aktif profil + değişti görünür | T-U04 |
| D2 | Kullanıcı verisi repoyu kirletmez (kalıcı yap sonrası `git status` temiz) | T-L37 |
| D3 | ≥22 kaynaklı/etiketli profil, niyet testleri yeşil, kırpılma yok | U43 |
| D4 | DESIGN.md kaynaklı; kontrast AA iki temada; klavye ile tüm bant işlemleri | U48, T-U04 |
| D5 | Analizör: 1 kHz 0 dBFS → 0±0,2 dB; post−pre = model ±0,5 dB (null sink); sayfa kapanınca yakalama süreci kalmaz | U44–U46, T-L34, T-L35 |
| D6 | Gerçek yol bozulmaz (analizör açıkken T-L33 geçer) | T-L35 |
| D7 | `oss-audit` temiz; cihaz sabit değil | T-L38 |
| D8 | Tüm birim + UI + canlı testler yeşil; headful ekran kanıtı | `tests/run.sh --live`, `analysis/ui/` |

---

# PRD-BTA04 — Otomatik ses zekâsı: Özel çalışma profilleri + anlık kayıt, tıksız geçiş motoru, müzik algılama, Auto Profile Changer, Auto Dynamic Live, yönetim sayfası, donanım sınırları

| alan | değer |
|---|---|
| tarih | 2026-09-27 ~22:30 |
| tetik (kullanıcı, özet) | *"otonom müziği algılayıp müzik karakterine/türüne/iç enstrüman bileşenlerine göre canlı custom ayarlar — adı Auto Dynamic Live … sabit profiller arası geçiş yapan: Auto Profile Changer … admin page (custom ses uzayı manipülasyonu, profil kayıtları) … kulaklığın materyal bilimi durumu ve potansiyeli"* + *"manuel dokunulduğu anda yeni profil alanı oluşsun (1, 2, 3), ana profiller hiç zarar görmesin, highlight'lı olsun, otomatik kaydolsun … her değişiklik ileri geri alınabilir … anlık kaydolur, 1 ms bile gecikme/donma olmadan, KB cinsinden"* |
| factory fazları | 02 kapsam → `.factory/02-scope.md` · 05 mimari → `docs/ARCHITECTURE.md` · 06 güvenlik → ARCHITECTURE §Güvenlik |
| araştırma | R28–R41 (`docs/research/findings.md`) — 3 paralel ajan + ebeveyn doğrulaması + fizibilite ölçümü (R33) |

## Yüzeyler (kullanıcının ayırdığı gibi)
1. **Derin ses mühendisliği** — tıksız geçiş motoru (D2), uyarlamalı EQ kontrolü (D5), seviyeye bağlı bas / sürücü koruma (D7).
2. **Yazılım entegrasyonu / optimizasyon** — anlık kayıt günlüğü (D1), sınıflayıcı çalışma zamanı (D3), kaynak disiplini.
3. **Yönetim sayfası** — profil kayıtları, sürüm geçmişi, otomasyon ayarları, sınıflayıcı izleme, ileri uzay (D6).
4. **Otonom modlar** — Auto Profile Changer (D4), Auto Dynamic Live (D5).

## Özellikler → alt katmanlar

| id | özellik | alt katmanlar |
|---|---|---|
| **D1** | Özel çalışma profilleri + anlık kayıt + kalıcı geçmiş | D1.1 ana profiller korumalı: hazır tarzlar koddadır (değişmez); adıyla kaydedilen/içe aktarılan profiller `locked` · D1.2 kilitli/hazır profil üzerinde İLK elle dokunuş → otomatik **"Özel N"** (sıradaki boş numara), `derived_from` · D1.3 her değişiklik **arka plan yazıcıya** kuyruklanır (istek yolu diske DOKUNMAZ) → ekle-yalnız günlük (`journal/<id>.jsonl`, sürüm başına ~2 KB) + atomik profil dosyası (birleştirme 300 ms) · D1.4 sunucu tarafı geri/ileri al (sayfa yenilense / sunucu kapansa bile) · D1.5 arayüzde vurgulu "Özel" rozeti + "kaydedildi ✓" durumu · D1.6 çalışma kopyasını adlandır (terfi) / kaynağına uygula |
| **D2** | Tıksız geçiş motoru (A/B zincir) | D2.1 graf: iki tam zincir (EQ + uzay + preamp) × 2 kanal; her zincir çıkışı `mult` × `ramp` · D2.2 geçiş: yeni durum SESSİZ zincire yüklenir → iki rampa eşzamanlı (varsayılan elle 40 ms, otomatik 1,5 s) · D2.3 sıralayıcı (bir geçiş bitmeden diğeri başlamaz, en sonuncu kazanır) · D2.4 bypass da rampalı |
| **D3** | Müzik algılama | D3.1 öznitelik katmanı (EQ öncesi dokunuş: sub/bas/alt-orta/orta/varlık/hava enerji oranı, ağırlık merkezi, crest, sinyal var) · D3.2 YAMNet ONNX (Apache-2.0, sha256 sabitli indirme, 16 kHz) → makro tür + enstrüman olasılıkları · D3.3 EMA + güven |
| **D4** | Auto Profile Changer | D4.1 profillere tür etiketi · D4.2 karar: EMA τ≈10 sn, marj ≥0,15, süre ≥8 sn, en az kalma 30 sn, belirsizde yedek profil · D4.3 geçiş D2 ile 1,5 sn · D4.4 geçiş günlüğü |
| **D5** | Auto Dynamic Live | D5.1 kişisel referans spektrumu (kendi dinlediklerinin uzun dönem ortalaması; TBC "özel eğri" kavramı) + ölü bölge ±2 dB · D5.2 4 geniş bant (bas rafı 80 Hz, alt-orta 300, varlık 3k, hava 10k) sınırlı düzeltme (bas +4/−3, diğer ±3 dB), ≤1 dB/s · D5.3 tür farkındalığı (bas ağır EDM'de bas artırma yok — Dolby IEQ ilkesi R37) · D5.4 seviyeye bağlı bas: yüksek seviyede azalt (sürücü), düşükte ISO 226 telafisi · D5.5 kullanıcı elle düzeltirse kişisel önyargı öğrenilir (α=0,2, ±6 dB sınır) · temel = aktif profil (kullanıcının zevki) |
| **D6** | Yönetim sayfası `/admin` | profil tablosu (etiket, kilit, çalışma kopyası, sürüm sayısı, boyut; terfi/sil/geri yükle/toplu dışa aktar) · sürüm zaman çizelgesi + geri yükle · otomasyon ayarları · sınıflayıcı canlı izleme · geçiş günlüğü · ileri uzay (kanal başına kazanç + Haas gecikmesi) |
| **D7** | Donanım potansiyeli | D7.1 `docs/profiles` kulaklık sınırları (R38–R41) · D7.2 sürücü koruma (toplam bas takviyesi üst sınırı, 17 kHz üstü takviye uyarısı) · D7.3 "oturma testi" (40–60 Hz ↔ 1 kHz, kullanıcı değerlendirir; ölçemediğimizi açıkça söyler) |

## Bağımlılık zinciri
```
D1 (bağımsız, EN ÖNCELİKLİ — kullanıcı talebi)
D2 (graf) ──► D4, D5 (otomasyon tıksız olmak ZORUNDA — R33)
analizör (C4) ──► D3 ──► D4, D5
D1 + D3 + D4 + D5 ──► D6 (yönetim yüzeyi hepsini gösterir)
R38–R41 ──► D7 ──► D5.4
```

## Kabul kriterleri
| AC | kriter | ölçüm |
|---|---|---|
| F1 | Hazır tarz / kilitli profil üzerinde ilk dokunuş → "Özel N" oluşur, kaynak DEĞİŞMEZ (sha) | U51, T-U05 |
| F2 | Her değişiklik kalıcı; istek gecikmesi kayıt açıkken artmaz (p95 farkı < 1 ms); disk yazımı istek iş parçacığında YOK | U52 (zamanlama + iş parçacığı kanıtı) |
| F3 | Sunucu yeniden başlasa da geri/ileri al çalışır; günlük satırı ≤ 4 KB | U53 |
| F4 | A/B geçişte >4 kHz artık ≤ −90 dBFS (doğrudan güncellemede −46); geçiş sonrası çıkış = model ±0,05 dB | T-L39 (null sink) |
| F5 | Sınıflayıcı: sentetik tür-temsili sinyallerde öznitelik karakteri doğru; YAMNet sha256 doğrulanmış, CPU ≤ %3 tek çekirdek | U54, T-L40 |
| F6 | Auto Profile Changer: sahte olasılık akışıyla histerezis/kalma/marj kuralları (salınım yok) | U55 |
| F7 | Auto Dynamic Live: sınırlar, ölü bölge, hız, tür kuralı, seviye koruması deterministik testli; gerçek yolda tık yok | U56, T-L41 |
| F8 | `/admin` tüm akışlar E2E, kontrast AA, JS hatası 0 | T-U06 |
| F9 | Tüm testler yeşil; headful gözlem | `tests/run.sh --live` |

## Durum (2026-09-28 00:20)

| id | durum | not | commit |
|---|---|---|---|
| D1 | ✅ | Özel N, arka plan günlük, kalıcı geri/ileri al, nav geri al, terfi / ana profile uygula | `722e6f0` |
| D2 | ✅ (tasarım değişti) | D2.1 `mult`×`ramp` → **mixer kazançları 12 ms adım** (R42: `ramp` portları 0'a kırpılır, E22) | `a14bab0` · T-L39, T-L41 |
| D3 | ✅ | D3.1 öznitelik: enerji oranı → **orta bölgeye göre dB** (oran doygunlaşıyordu); ağırlık merkezi/crest eklenmedi (gerek çıkmadı) · D3.2 YAMNet · hafif analizör modu (U62) | `9ba9ba9` `7ab3681` `9c48862` |
| D4 | ✅ | tür etiketleri + varsayılan tarz eşlemesi; varsayılan KAPALI (kullanıcı kararı) | `7ab3681` `25cdc7d` |
| D5 | ✅ | üst katman (profile yazılmaz, U58); konuşmada 0; bas yoklaması (öğrenme) | `7ab3681` `25cdc7d` |
| D6 | ✅ (ileri uzay hariç) | ileri uzay (kanal trim + Haas) YAPILMADI → gri G10 | `bb36260` |
| D7 | ✅ | D7.1 katman belgesi L1 · D7.2 uyarı (kırpma YOK — kullanıcının seçimi korunur) · D7.3 oturma testi | `c7b327c` |

| AC | sonuç | kanıt |
|---|---|---|
| F1 | ✅ | U51, T-U04 (D1 rozeti), T-U05 |
| F2 | ✅ p95 farkı < 1 ms, istek yolunda `open()` 0 | U52 |
| F3 | ✅ | U53 |
| F4 | ⚠️ **kısmen**: −90 dBFS hedefi TUTMADI; gerçekleşen: güncelleme başına tık yok (doğrudan −46 → A/B ≤ −60), 5–6 güncellemede 1–2 artık −68…−88 dBFS (R43, duyulmaz, kök neden açık); son seviye model ±0,05 dB | T-L39, T-L41 |
| F5 | ✅ %2,33 + %0,33 çekirdek (hedef ≤ %3), sınıflama 13,7 ms/2 sn | T-L40, T-L42 |
| F6 | ✅ | U55, U59 |
| F7 | ✅ | U56, U58, T-L41 (−83,9 dBFS) |
| F8 | ✅ (kontrast: yönetim sayfası konsolla aynı belirteçleri kullanır, U48 belirteçleri ölçer) | T-U06 |
| F9 | ⚠️ **kısmen**: birim 178 + tarayıcı 6 yeşil; salt-okuma/null-sink canlılar (T-L30…T-L43 arası yeni olanlar) yeşil; kulaklığı KOPARAN (T-L10) veya kulaklığa TON çalan (T-L12) canlılar bu turda koşulmadı — kullanıcı o an dinliyordu (K10); headful gözlem canlı sunucuda yapıldı (salt okuma) | STATE-LOG 23:51 |

---

# PRD-BTA05 — Kullanıcı kararlarını kolaylaştırma (kör test, radyo ölçümü, HRTF)

| alan | değer |
|---|---|
| tarih | 2026-09-28 |
| tetik (kullanıcı) | *"önce bu alana odaklanalım, tam olarak ne anlama geliyor ve bize ne avantajları olacak, her bir maddeyi açıkla, sonra adım adım halledelim"* — AAC/SBC kör test · radyo ölçümü · 3B/HRTF |
| sıra | E1 (sudo yok, en büyük karar) → E2 (yalnız kesilme duyulursa) → E3 (PipeWire 1.6.9 yükseltmesi gerektirir) |

## Özellikler → alt katmanlar

| id | özellik | alt katmanlar |
|---|---|---|
| **E1** | Konsolda düğmeli kör ABX testi (AAC ↔ SBC) | E1.1 test klibi: **kendi müziğinden** 12 sn (EQ ÖNCESİ dijital dokunuş, codec'ten önce) ya da hazır klip · E1.2 sunucu tarafı test motoru: denemeler dengeli karışık, her çalmada önce diğer codec'e sonra hedefe geçiş (geçiş ipucu olmasın), A/B/X istenildiği kadar tekrar, cevap ancak X dinlendikten sonra · E1.3 sonuç: 12'de ≥10 doğru (p<0,05) → tercih sorulur → "bunu kullan" (decision.json + codec) · E1.4 güvenlik: test boyunca otomasyon askıda, bitince/iptal edilince ORİJİNAL codec geri, EQ değişmez · E1.5 arayüz: sade dil, adım adım, ilerleme |
| **E2** | Radyo ölçümü rehberi | E2.1 tek komut (kullanıcının terminali, sudo) · E2.2 rapor yorumu sade dille (RSSI eşikleri, yeniden iletim) |
| **E3** | 3B/HRTF (isteğe bağlı) | E3.1 PipeWire 1.6.8 → 1.6.9 yükseltme etkisi (R33/R42/R46 yeniden ölçümü) · E3.2 SOFA veri seti seçimi (lisans) · E3.3 grafa isteğe bağlı "3B sahne" düğümü · E3.4 kör A/B crossfeed'e karşı |

## Bağımlılık zinciri
```
analizör halka tamponu (U61) ──► E1.1 klip yakalama
abx.py (U18) ──► E1.2 motor ──► E1.3 karar ──► decision.json (T-L02)
AutoEngine.manual (U59) ──► E1.4
PipeWire 1.6.9 (kullanıcı sudo) ──► E3 ──► tüm canlı testler yeniden
```

## Kabul kriterleri
| AC | kriter | ölçüm |
|---|---|---|
| G1 | klip kendi müziğinden: EQ öncesi dokunuştan tam 12 sn, sessizse REDDEDİLİR | U70, T-L44 |
| G2 | test motoru: dengeli karışık denemeler, geçiş sırası sabit, X dinlenmeden cevap yok, sonuç binom p ile, bitince/iptalde orijinal codec | U69 |
| G3 | arayüz: adım adım akış, JS hatası 0, 390 px taşmasız | T-U08 |
| G4 | canlı: codec gidiş-dönüşü (aac→sbc→aac) sink'i geri getirir, konsol grafı yolda kalır | T-L44 (yalnız sink boştayken — K10) |


# PRD-BTA06 — Süreklilik, çok aygıt, kulaklık kanalı

> 2026-10-15 · kullanıcı onayı (verbatim): *"onerilerini onayliyourm"* · kaynak analiz: sohbet + [vendor-recommendations](research/vendor-recommendations.md)
> Amaç (A): otomatik mod ve EQ, kullanıcı hiçbir şey açmadan **her zaman** doğru aygıtta çalışsın; bunu yaparken masaüstü
> uygulaması gibi kaynak yemesin; panel her çıkışı ayrı yönetebilsin; kulaklığın kendi kanalı güvenle tanınsın.

## Özellikler → alt katmanlar

| id | özellik | alt adımlar |
|---|---|---|
| G0 | **ADL salınım/kaynak düzeltmesi** (G1'in ön koşulu) | ölçüm: canlı uyarlama 20 sn'de 12 değişim, her biri 1,5 sn × 12 ms = 125 komut → `pw-cli` %8,5 + konsol %3,1 çekirdek (E31). Düzeltme: histerezis + en az bekleme süresi |
| G1 | **Otomatik mod arka plan servisi** | `--idle-timeout 0` (kapanmaz) · tek örnek (ikinci `bta console` yeni motor açmaz, var olanı açar) · `bta service install/uninstall/status` (systemd kullanıcı birimi, girişte başlar, tarayıcı gerekmez) |
| G2 | **Panelden aygıt seçimi** | aygıt başına profil haritası · her hedef için ayrı smart filter (`node_suffix`) · yeni aygıt varsayılan DOKUNULMAZ (opt-in) · koruma eşikleri/codec uyarıları aygıt türünden |
| G3 | **Kulaklık SPP kanalının kimliği (salt-okuma)** | SDP kaydı (servis adı → çip ailesi) · komut GÖNDERMEK kullanıcı kararı (§D: yıkıcı + belirsiz) |

## Bağımlılık zinciri

G0 → G1 (servis 7/24 koşacak; önce maliyet düşmeli) → G2 (servis tek motor; çok aygıt aynı motorda) · G3 bağımsız
(sudo: `bluez-deprecated` / `sdptool` kurulumu kullanıcıda).

## Test noktaları (koddan ÖNCE)

| id | ne | beklenen | neden |
|---|---|---|---|
| U73 | ADL nicemleme sınırında salınım | ham değer 1,24↔1,26 arasında gidip gelirken 30 tikte ≤ 1 uygulama | E31: sınırda her tik yeni 1,5 sn geçiş |
| U73 | ADL gerçek sürüklenme | ham 0 → 4 dB / 30 sn: son uygulanan ham değere ≤ 0,5 dB yakın; uygulama sayısı ≤ 30/ADL_MIN_S + 1 | düzeltme takibi öldürmemeli |
| U74 | boşta kapanma kapalı | `idle_timeout_s=0` → bekçi sunucuyu durdurmaz | servis kapanmamalı |
| U75 | tek örnek | portta bta konsolu varsa yeni süreç motor başlatmaz, URL döner; başka bir sunucu varsa None | iki motor aynı düğüme yazarsa çakışma |
| U76 | servis birimi | ExecStart mutlak yol + `--no-open --port 8766 --idle-timeout 0`; After=pipewire/wireplumber/filter-chain; Restart=on-failure; sır yok | girişte başlar, çökünce kalkar |
| T-L45 | canlı servis | birim etkin, 8766 cevap verir, ikinci `bta console` süreç sayısını artırmaz, CPU (10 sn) ≤ %3 çekirdek müzik çalarken | ürün katmanı kanıtı |

## Kabul kriterleri

G0: `pw-cli` + konsol toplamı müzik çalarken ≤ %3 çekirdek (önce %11,6) · G1: oturum açılınca kullanıcı hiçbir şey
yapmadan `/api/auto` cevap verir; 1 sa sessizlikte kapanmaz · G2/G3: ayrı kabul (başlarken yazılır).

## Durum

- 2026-10-15: plan yazıldı; G0 başladı.
- 2026-10-15 22:00: **G0 ✅** (U73, mutasyon öldü) · **G1 ✅ kuruldu** (`bta-console.service` etkin, 8766, tek örnek + port gaspı koruması E32). T-L45 kısmi: servis etkin, ikinci `bta console` motor açmıyor, yönlendirme + T-L25 PASS; CPU ölçümü sayfa GÖRÜNÜRKEN %33 çekirdek (iki dokunuşlu tam analizör — sekme gizlenince durur, `console.html:1109`); **arayüzsüz arka plan maliyeti henüz ölçülmedi** (sekme açık) · `pw-cli` G0 sonrası %8,5 → %2,4. Girişte kendiliğinden başlama: `default.target.wants` bağı kuruldu, yeniden oturumla henüz SINANMADI. G2 başlamadı · G3 `sdptool` (sudo) bekliyor.
