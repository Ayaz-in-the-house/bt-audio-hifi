# Araştırma bulguları — (iddia, kanıt, güven)

Kaynak dosyaların birebir kopyaları `docs/research/upstream/` altında, `SHA256SUMS` ile. "executable" = bu makinede
çalıştırılıp çıktısı okunmuş ölçüm.

| # | iddia | kanıt | tip | güven |
|---|---|---|---|---|
| R1 | Başlangıçta kart HFP (mSBC mono 16 kHz) profilindeydi ve WP bunu kalıcı kaydetmişti | `pactl list cards` Active Profile · `state/backups/…/default-profile` | executable + filesystem | 0.99 |
| R2 | Kulaklık codec'leri: SBC (bitpool 2–53) + AAC (MPEG-2 LC, VBR, bitrate alanı 0); aptX/LDAC/LC3 yok | D-Bus `MediaEndpoint1.Capabilities` (sep1/sep2) + `bluetoothctl info` UUID'leri (LE Audio PACS yok) | executable ×2 | 0.95 |
| R3 | Canlı AAC konfigürasyonu 48k/2ch/vbr=1/262 144 bps | `MediaTransport1.Configuration = 80 00 84 84 00 00` + U01 çözücü (caps.h LE düzeni) | executable + source | 0.97 |
| R4 | vbr=1 iken PipeWire 19,3 kHz bant zorlamasını atlar | `a2dp-codec-aac.c:400` + benchmark: AAC kesimi 17,0 kHz (5 sinyal), 19293 zorlanınca 19,3 kHz | source + executable | 0.97 |
| R5 | PipeWire AAC eklentisi ve ffmpeg aynı libfdk-aac'ı kullanır | `ldd` iki ikili → `/lib64/libfdk-aac.so.2` | executable | 0.99 |
| R6 | SBC-XQ bu kulaklıkta 48k dual bitpool 39 (~504 kbps) açılır | canlı transport `sbc_xq` → rates [48000] dual max_bitpool 39 | executable | 0.97 |
| R7 | ffmpeg SBC encoder PipeWire SBC-XQ'yu temsil etmez | çerçeve başlığı: "XQ" isteğinde 4 alt-bant + joint + bp42 | executable | 0.99 |
| R8 | libsbc çerçeve uzunluğu formülüm doğru | U17: gerçek `libsbc.so.1` ↔ `codecs.sbc_frame_length` 4 konfig birebir | executable ×2 | 0.99 |
| R9 | SBC-XQ bu bağlantıda paket atlatıyor; AAC ve SBC temiz | `bta link-test` 90 sn: XQ 13 reduce (bitpool 39→30), AAC 0 (×2), SBC 0 | executable | 0.9 |
| R10 | `reduce bitpool` = en az bir atlanan paket | `media-sink.c:1080-1100` (EAGAIN → reduce → "glitch in any case") | source | 0.95 |
| R11 | Kopmada bir GNOME istemcisi varsayılan çıkışı hoparlöre yazıyor | `pw-metadata -m` zaman damgaları, 2 bağımsız tekrar (19:15:08, 19:19:40) | executable ×2 | 0.95 (hangi GNOME süreci: ADLANDIRILMADI — gnome-shell / gsd-media-keys / gnome-control-center adayları) |
| R12 | `module-switch-on-connect` yalnız bluez'i geri alır (blocklist `^alsa_\|hdmi`) | kaynak (PCI/kartsız/sanal hariç) + T-L13 headful | source + executable | 0.95 |
| R13 | Resampler q4, 44.1k içerikte 19,5 kHz'i −8,3 dB, 21 kHz'i −28 dB zayıflatır; q10 19,5 kHz'e dek düz | null-sink canlı ölçüm, 5 kalite | executable | 0.95 |
| R14 | Zen/Firefox sesi 48k F32 verir → PipeWire resampler'ı tarayıcı sesini etkilemez | `pw-dump` akış Format 48000 F32LE (defalarca) | executable | 0.9 |
| R15 | PipeWire `bq_peaking` = RBJ cookbook | `audioconvert/biquad.c:223` + T-L30 ölçüm ↔ model ±0,01 dB | source + executable | 0.99 |
| R16 | WP 0.5 smart filter yalnız hedef sink'in akışlarına EQ uygular, varsayılanı değiştirmez | `filter-utils.lua` + T-L30 bağ listesi | source + executable | 0.95 |
| R17 | Smart filter hedefi monitörleyen yakalamayı da filtre girişine yönlendirir | T-L30 ilk koşu bağ listesi (`effect_input → pw-record`) | executable | 0.95 |
| R18 | ISO 226:2003 katsayıları | IoSR Surrey `iso226.m` + bellek tablosu birebir; phon tanımı (1 kHz'te SPL=phon) U22 | spec-impl ×2 + executable | 0.95 |
| R19 | Bu model AutoEQ veritabanında yok | `results/INDEX.md` (8854 satır) "solix/nexus" 0 eşleşme | executable | 0.95 |
| R20 | EasyEffects 8.2.9 Flathub: GPL-3, ağ yok, ev dizini yok, commit 12b796b3 | `flatpak remote-info --show-metadata` + kurulu commit eşleşmesi | executable ×2 | 0.97 |
| R21 | EE preset yükleyicisi eksik alanlarda varsayılana düşer | `presets_macros.hpp` UPDATE_PROPERTY → `.value(key, default)` | source | 0.9 |

| R22 | `bq_raw` katsayıları çalışırken değişir → filtre tipi canlı | `plugin_builtin.c:275,545-556` + null sink 6 tip ≤0,008 dB | source + executable | 0.99 |
| R23 | bs2b birinci dereceden filtreler → bq_raw ile birebir; sabitler 700/4,5 · 700/6,0 · 650/9,5 | `bs2b.c:131-214`, `bs2b.h:36-58` + U32 | source + executable | 0.97 |
| R24 | Harman IE 2019: 20 Hz +7,6 dB, 3 kHz +9,3, 16 kHz −10,2 (1 kHz'e göre) | AutoEq CSV, np.interp ile okundu (ajan değeri yanlıştı) | executable | 0.97 |
| R25 | sashimi-ui 2.1.0 MIT, yalnız CSS, dış istek yok | npm registry + tarball taraması | executable | 0.95 |
| R26 | Tam konsol grafı (EQ+bs2b+genişlik+denge+preamp) ürün = model | T-L32 ±0,001 dB | executable | 0.99 |
| R27 | HRTF: `pipewire-module-filter-chain-sofa` kurulu değil (libmysofa var); kafa takibi yok | ajan B (`rpm`, `ls`) | executable | 0.9 |

## Harici kaynaklar

- PipeWire 1.6.8 kaynak (GitHub aynası; gitlab.freedesktop.org Anubis ile engelli): `a2dp-codec-aac.c`,
  `a2dp-codec-sbc.c`, `a2dp-codec-caps.h`, `media-sink.c`, `module-switch-on-connect.c`, `audioconvert/biquad.c`,
  `filter-graph/plugin_builtin.c`.
- PipeWire resmî dokümanı: `pipewire-props(7)` (bluez5.a2dp.aac.bitratemode, resample.quality 0–14 vars. 4),
  `pipewire.conf(5)` (allowed-rates "Bluetooth sorunları nedeniyle varsayılan kapalı").
- BlueZ sbc `sbc.h` (git.kernel.org).
- EasyEffects v8.2.9 kaynak (kcfg şemaları, preset yöneticisi).
- IoSR Surrey MatlabToolbox `iso226.m`.
- AutoEq `results/INDEX.md`.
- Musopen Brahms Senfoni 1 premix (archive.org, **CC0**) — benchmark referansı.
- Ürün: Solix Nexus ANC (Audeeo Innovations), solixco.com ürün sayfası / manuals.plus kılavuzu (BT 5.4, 12 mm).

## PRD-BTA03/04 bulguları

| # | iddia | kanıt | tip | güven |
|---|---|---|---|---|
| R28 | Harman bas bileşeni = lowshelf 105 Hz Q0,7: kulakiçi 2019 **+9,0 dB** (max hata 0,06), kulaküstü 2018 **+6,0 dB** (0,04) | AutoEq CSV "with − without bass", ızgara uydurma (çalıştırıldı) | executable | 0.97 |
| R29 | VLC tür presetleri 10 bant (60…16k) — değerler dosyadan; parametrik uydurma ≤1 dB | `upstream/presets/vlc-equalizer_presets.h` + U43 | source + executable | 0.95 |
| R30 | Oyun/ayak sesi EQ için ölçüme dayalı açık kaynak bulunamadı | araştırma ajanı + ebeveyn doğrulaması yok | — | open |
| R31 | 1/6 okt bant gücü: tam ölçek sinüs 0,0 dBFS; pembe gürültü eğimi 0,03 dB/okt (düz) → 4,5 dB/okt eğim gereksiz | `btaudio/analyzer.py` + ölçüm çıktısı; SPAN/Pro-Q eğimi FFT-bin görünümü için | executable | 0.97 |
| R32 | Analizör ürün katmanı: post−pre = model, max hata 0,042 dB; EQ öncesi mutlak −30,0 dBFS | T-L34 | executable | 0.97 |
| R33 | **PipeWire yerleşik biquad'ları her parametre değişiminde filtre belleğini sıfırlar** → canlı güncelleme başına tık (≈ −46 dBFS, −12 dBFS sinüste; adım boyundan BAĞIMSIZ: 0,5/0,25/0,1 dB aynı) | `plugin_builtin.c:322` (`bq_raw_update`: `x1=x2=0`), `biquad.c:340-341` (`biquad_set`) + `btaudio/zipperverify.py` ölçümü | source + executable | 0.97 |
| R34 | PipeWire filter-graph'ta örnek-doğru `ramp` (Start/Stop/Duration → ses hızında çıkış) ve `mult` (ses×ses) düğümleri var → iki paralel zincir arasında tıksız crossfade kurulabilir | `plugin_builtin.c:2467-2545` (ramp), `:1739+` (mult) | source | 0.9 (ürün doğrulaması D2'de) |
| R35 | YAMNet: AudioSet 521 sınıf, ~40 müzik türü + konuşma + enstrüman; 16 kHz mono 0,96 sn; ONNX dönüşümü 16 MB Apache-2.0 (üçüncü taraf); onnxruntime 1.24.3 bu makinede KURULU | TF models `yamnet_class_map.csv`, HF API, `import onnxruntime` | official + executable | 0.9 |
| R36 | Essentia MTG modelleri CC BY-NC-SA 4.0 → açık kaynak/ticari paylaşımda KULLANILMAZ | essentia.upf.edu/models.html | official | 0.95 |
| R37 | Dolby Intelligent EQ: içerikte yeterince bas varsa dokunmaz, eksikse artırır; iZotope TBC: hedef = bant ARALIĞI (ölü bölge) | Dolby PC v4 whitepaper (özet), iZotope docs | official | 0.7–0.9 |
| R38 | Harman: bas seven dinleyici grubu hedefe **+4–6 dB** ekler; fazlasına karşı uyarı | Olive, Acoustics Today (PDF okundu) | official/paper | 0.9 |
| R39 | Solix Nexus: 12 mm, 32 Ω(?), 20–20k (toleranssız), ANC −25 dB; diyafram malzemesi YAYIMLANMAMIŞ | kılavuz (manuals.plus/ManualsLib), solixco.com | official | 0.85 (malzeme: open) |
| R40 | Kulak içi basın ana belirleyicisi sızdırmazlık (seal); sızıntı ayrı değişken | Olive/Welti/Khonsaripour AES | paper | 0.8 |
| R41 | Android FDK-AAC 192 kbps üstünde ~17 kHz lowpass (bizim ölçümümüzle birebir) → 17 kHz üstü EQ etkisiz | Archimago + SoundGuys + R4 | 2 bağımsız + executable | 0.9 |
| R42 | PipeWire 1.6.8 `ramp` düğümünün denetim portları (Start/Stop/Duration) aralıksız → hem config hem `set-param` değeri **0'a kırpılır** → kullanılamaz | canlı `pw-dump` PropInfo/Props: `rampAL:Start 0.0` (1,0 gönderildi); `sumL:Gain 1` ise min −10/max 10 ve 0,7 kabul | executable ×2 | 0.95 |
| R43 | A/B + 12 ms'lik mixer kazanç adımları: 5 güncellemede **1 olay ≈ −68…−72 dBFS** (−12 dBFS sinüste; doğrudan güncellemede HER güncelleme ≈ −46); son seviye model ±0,00 dB. Kalan olayın kök nedeni **ADLANDIRILMADI** (adaylar: kalıcı pw-cli oturumunun ilk komutu, Props'un kısmi döngüde uygulanması) | `zipperverify.run_ab` × 4 koşu | executable | 0.9 (ölçüm) / open (kök neden) |
| R44 | R43 ek veri (2026-09-28, kontrol deneyi): güncellemesiz 3 koşuda **0 olay**; 1,5 sn geçişli 6 güncellemede 3 koşunun 2'sinde −79 dBFS olay, ikisi de **B zincirine yükleme anında** (7,9 sn); T-L41'de 2 olay −84/−88 dBFS (B yüklemeleri). A yüklemelerinde olay yok → artık, sessiz zincir B'ye parametre yazımıyla ilişkili; kök neden hâlâ AÇIK (pw-cli gecikmesi ~0,03 sn ölçüldü → dışlandı; B yükü A düğümlerine dokunmuyor → dışlandı) | `clickprobe.py` (scratchpad) + T-L41 `max_time_s` | executable ×2 | 0.8 (kök neden `open`) |
| R45 | Otomasyon maliyeti: tam analizör (2 dokunuş, kare başına FFT 1,6 ms + true-peak 1,4 ms, 20 kare/sn) %15 çekirdek; hafif mod (tek dokunuş, halka tampon, istek anında 4 pencere FFT) %2,33 + pw-record %0,33; YAMNet 12,9–13,7 ms / 2 sn ses | T-L40 canlı + blok başına `perf_counter` | executable | 0.95 |
| R46 | `pw-cli` 1.6.8 stdin EOF'ta çıkmaz, R durumunda döner (%20+ çekirdek); `quit` komutuyla 0,0 sn'de rc 0; `/dev/null` girdisinde abort (rc 134) | yetim süreç `ps` + tekrar üretim betiği | executable ×2 | 0.95 |

| R47 | Solix Nexus ANC'nin eşlik uygulaması YOK: kılavuz (SX-EANC4) yalnız düğme kontrolleri, solixco.com bağlantı yok, mağaza aramasında yayıncı yok | manuals.plus kılavuzu (Scrapling) + solixco.com + 2 web araması | official + 2 bağımsız | 0.85 |
| R48 | Kulaklık SPP (Serial Port, 0x1101) sunuyor; DIS/Modalias yok; MAC yeniden eşleşmede değişti | `bluetoothctl info` UUID listesi + D-Bus `Modalias` yok + iki tarihli MAC | executable ×2 | 0.95 |
| R49 | Airoha tabanlı kulaklıklarda kimlik doğrulamasız çip protokolü RACE (BLE GATT + Classic): RAM/flash okuma-yazma, bağlantı anahtarı sızıntısı — CVE-2025-20700/20701/20702 (ERNW). Bu kulaklığın çipi BİLİNMİYOR | ERNW whitepaper 74 + cvefeed + basın | official + paper | 0.85 (bu cihaza uygulanabilirlik: open) |
| R50 | Canlı uyarlama (ADL) 20 sn'de 12 kez değişti (0,5 dB nicemleme sınırında salınım dahil); her değişim 125 `set-param` → `pw-cli` %8,5 + konsol %3,1 çekirdek | `/api/auto` 0,5 sn yoklama + `/proc/<pid>/stat` 10 sn tik farkı + `/proc/<pid>/io` syscr ≈ 6100/sn | executable ×3 | 0.95 |
| R51 | Kulaklık çipi **Bluetrum Technology** (LMP üretici kimliği 1602 = 0x0642), LMP sürümü 0x0E, alt sürüm 0x3. Airoha DEĞİL → RACE açıkları (R49, Airoha SDK) doğrudan uygulanmaz | `hcitool info` (LMP_version_req, salt-okuma) | executable | 0.95 |
| R52 | SDP: SPP kaydı genel ad "SPP", RFCOMM kanal 1 (sürüm 1.2); HFP kanal 2. Üretici/servis adı yok | `sdptool browse` | executable | 0.95 |
| R53 | SPP kanal 1 salt-dinleme: bağlantı 0,09 sn'de kabul, 60 sn'de 0 bayt (kulaklık kendiliğinden konuşmuyor → istek/yanıt protokolü), A2DP kopmadı. Bluetrum'un genel uygulaması **AB Link** (iOS, Bluetrum Limited; EQ + kaynak kontrolü, BLE) var; Android sürümü / açık SDK bulunamadı | `scratchpad/spp_listen.py` (send YOK) + App Store kaydı id1440600431 | executable + official | 0.8 |
| R54 | Harman IE 2019 hâlâ güncel: Olive 2024 AES (B&K 5128) 5 kulakiçi hedefi kör testi → SoundGuys HPC ile Harman IE2019 istatistiksel BERABERE en çok tercih edilen. 2025 kalabalık testi (PEQdB, 403 kişi) PEQdB/HiFiEndgame'i öne koyuyor ama metodu tartışmalı; Crinacle IEF 2025 topluluk hedefi. Hepsi kulaklığın ÖLÇÜLMÜŞ tepkisine göre uygulanır — bu kulaklığın ölçümü yok (R39/AutoEq) → biz yalnız bas bileşenini (R28) kullanabiliyoruz | soundguys.com/harman-target-soundguys-preference-curve-validated-125420 · headphonesty.com 2024/10 + 2025/05 · crinacle.com 2025/02 · arxiv 2512.08313 | 2 bağımsız ikincil + paper özeti | 0.75 |
