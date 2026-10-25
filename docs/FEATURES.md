# Özellik kataloğu

> Durum: ✅ yapıldı ve ölçüldü · 🟡 araç hazır, kullanıcı kararı/eylemi bekliyor · ⬜ gri (henüz girilmedi/geliştirilmedi).
> Test kimlikleri [TEST-PLAN](TEST-PLAN.md)'de tanımlıdır (U67 kapısı buradaki her kimliğin var olduğunu doğrular).
> Katmanlar: [L1 kulaklık](layers/L1-headphone.md) · [L2 Bluetooth](layers/L2-bluetooth.md) · [L3 Linux](layers/L3-linux-os.md) ·
> [L4 PipeWire](layers/L4-pipewire.md) · [L5 yazılım](layers/L5-bta-software.md) · [L6 arayüz](layers/L6-browser-ui.md)
>
> Son güncelleme: 2026-09-28

## Ses yolu ve bağlantı (PRD-BTA01)

| # | özellik | durum | nasıl kullanılır | katman | modüller | testler |
|---|---|---|---|---|---|---|
| F1 | Kulaklık hep yüksek kalite profilde (A2DP), mikrofon açan uygulama HFP'ye düşürmez | ✅ | otomatik (kurulum) | L2, L4 | collect, state | T-L01 T-L04 T-L05 T-L10 T-L11 |
| F2 | Codec seçimi ve ölçümü (AAC / SBC; SBC-XQ elendi) | 🟡 kulakla karar | konsol → Analiz → Kör dinleme testi (F32) · `bta abx aac sbc` | L2 | codecs, bench, sbclib, abx | U01 U05 U16 U17 U18 T-L02 T-L14 |
| F3 | Resampler kalite 10 (44,1 kHz kaynakta tiz kaybı yok) | ✅ | otomatik (kurulum) | L4 | resample | U19 T-L21 T-L22 |
| F4 | Bağlantı sağlığı (paket atlama / bitrate düşürme) | ✅ | `bta link-test 60` | L2 | link | U15 T-L50 |
| F5 | Kopma sonrası varsayılan çıkış kulaklığa döner | ✅ | otomatik | L4 | — (config) | T-L13 |
| F6 | Radyo katmanı ölçümü (RSSI, yeniden iletim) | 🟡 sudo gerekir | `sudo bash tools/btmon-capture.sh 60` | L2 | btmon | U27 |
| F7 | Durum anlık görüntüsü + fark (kurulum geçişleri) | ✅ | `bta snapshot <ad>` · `bta diff` | L3–L4 | state, collect | U07 U08 U10 T-L20 |

## Konsol (PRD-BTA02/03)

| # | özellik | durum | nasıl | katman | modüller | testler |
|---|---|---|---|---|---|---|
| F10 | 10 bant parametrik EQ, grafikten sürükle, 6 filtre tipi | ✅ | `bta console` | L4–L6 | console, dsp, consoleserver | U30 T-L32 T-U04 |
| F11 | Uzay: crossfeed (bs2b), stereo genişlik, denge | ✅ | Uzay sekmesi | L4–L6 | console | U31–U35 T-L32 |
| F12 | 32 hazır tarz (Harman, VLC, AutoEq, EasyEffects kaynaklı + tasarım), kaynaklı ve ölçülmüş | ✅ | Profiller sekmesi | L5 | console, presetfit | U43 |
| F13 | Canlı analizör (1/6 okt, EQ öncesi/sonrası, metre, parça ortalaması) | ✅ | Analiz sekmesi | L4–L6 | analyzer | U44 U45 U46 T-L34 T-L35 |
| F14 | "Açılışta kullan" — ayar kalıcı config olur, repo kirlenmez | ✅ | üst çubuk | L3–L5 | cli, paths | U49 T-L37 |
| F15 | Kullanıcı verisi repo dışında (XDG), paylaşılabilir profil (dışa/içe aktar) | ✅ | Profillerim menüsü | L3, L5 | paths, profiles | U40 U41 |
| F16 | Güvenli yerel sunucu (Host/CSRF/boyut/CSP) | ✅ | — | L5–L6 | consoleserver | U36 U47 |
| F17 | Açık kaynak sızıntı kapısı (MAC/ev yolu/e-posta yok) + MIT lisansı | ✅ | `tools/oss-audit.sh` | — | — | U50 T-L38 |

## Çalışma kopyaları ve otomasyon (PRD-BTA04)

| # | özellik | durum | nasıl | katman | modüller | testler |
|---|---|---|---|---|---|---|
| F20 | İlk dokunuşta "Özel N" çalışma kopyası — ana profiller/tarzlar hiç değişmez | ✅ | otomatik | L5 | consoleserver, profiles | U51 U42 |
| F21 | Anlık arka plan kayıt (istek yolu diske yazmaz, < 1 ms) + kalıcı geri/ileri al | ✅ | Ctrl+Z / Ctrl+Shift+Z | L5 | journal, history | U52 U53 |
| F22 | Tıksız geçiş (A/B zincir) — ayar değişince tık yok | ✅ | otomatik | L4–L5 | crossfade | U57 U68 T-L39 T-L41 |
| F23 | Otomatik profil (APC): tür tanıma → türe bağlı profil | ✅ (varsayılan kapalı) | Otomatik sekmesi | L5–L6 | autoengine, autoctl, classifier | U55 U59 T-U05 T-L42 |
| F24 | Canlı uyarlama (ADL): ince kayıtlarda sınırlı bas/tiz düzeltmesi, konuşmada dokunmaz | ✅ (varsayılan kapalı) | Otomatik sekmesi | L5 | autoengine, autoctl, features | U56 U58 U59 T-L41 |
| F25 | Tür/karakter/enstrüman canlı gösterimi (yerel YAMNet, internet yok) | ✅ | Otomatik sekmesi | L5–L6 | classifier, features | U54 U61 T-L42 |
| F26 | Otomasyonun düşük maliyeti (hafif analizör: %2,3 çekirdek) | ✅ | otomatik | L5 | analyzer | U62 T-L40 |
| F27 | Yönetim sayfası: sürüm zaman çizelgesi + farklar, sürüme dön, çöp kutusu, toplu dışa/içe aktarma | ✅ | `/admin` | L5–L6 | consoleserver, history | U63 T-U06 |
| F28 | Sürücü koruma + codec farkındalığı uyarıları | ✅ | grafik altı şerit | L1, L5 | console | U65 T-U07 |
| F29 | Kulak tıkacı oturma testi | ✅ | Analiz sekmesi | L1, L5 | tones | U65 U66 T-U07 T-L43 |
| F30 | Yetim süreç koruması (ebeveynle ölen alt süreçler) | ✅ | otomatik | L3 | procs | U64 |
| F32 | **Konsolda kör dinleme testi** (AAC ↔ SBC): kendi müziğinden 12 sn klip, düğmeli 12 deneme, sade sonuç, tercih → kalıcı | ✅ (kullanıcı testi bekliyor) | Analiz → Kör dinleme testi | L2, L5–L6 | abxsession, abx | U69 U70 T-U08 T-L44 |
| F31 | Belge güncelliği kapısı (modül belgeleri kaynaktan) | ✅ | `python3 tools/gen-docs.py` | — | — | U67 |

## Gri alanlar (girilmedi / geliştirilmedi / ölçülemedi)

| # | alan | neden | ne gerekir | katman |
|---|---|---|---|---|
| G1 | **Çok çıkış aygıtı** (hoparlör, HDMI, USB, ikinci BT) — aygıt başına profil | EQ bilerek tek hedefli | `devices.json` + aygıt başına smart filter + aygıt seçici ([tasarım](layers/L4-pipewire.md#aygıt-kapsamı)) | L4–L5 |
| G2 | 3B / HRTF sahnesi | ek paket + SOFA veri seti | kullanıcı kararı ([USER-DECISIONS §3](USER-DECISIONS.md#3-3b--hrtf-paketi)) | L4 |
| G3 | Kafa takibi | kulaklıkta sensör yok | donanım | L1 |
| G4 | Mikrofonla otomatik oturma/yanıt ölçümü | kulak içi mikrofon erişimi yok | donanım | L1 |
| G5 | Kulaklığın gerçek frekans yanıtı / sürücü malzemesi | ölçüm/üretici verisi yok | ölçüm düzeneği | L1 |
| G6 | LE Audio / LC3, aptX, LDAC | kulaklık desteklemiyor | farklı kulaklık | L2 |
| G7 | Uygulama başına EQ | smart filter sink başına | ayrı filter düğümleri + akış yönlendirme | L4 |
| G8 | İngilizce / çok dilli arayüz | metinler Türkçe | i18n katmanı | L6 |
| G9 | Diğer dağıtımlar (Ubuntu/Arch/Debian) | denenmedi | CI matrisi | L3 |
| G10 | Yönetimde gelişmiş uzay (kanal trim, Haas gecikmesi) | opsiyonel bırakıldı | graf düğümü + arayüz | L4–L6 |
| G11 | `bta uninstall` uçtan uca testi | planlandı, yazılmadı | T-H40 | L3 |
| G12 | A/B geçişte küçük artığın (R43, −68…−88 dBFS) kök nedeni | duyulmaz; açık | PipeWire kaynak incelemesi | L4 |
| G13 | Askıya alma/uyanma sonrası graf davranışı | test edilmedi | canlı test | L3–L4 |
| G14 | Konsolun sistem servisi olarak her açılışta çalışması (otomasyon sürekli) | konsol elle açılır | `systemd --user` birimi | L3 |

## Süreklilik ve aygıtlar (PRD-BTA06)

| # | özellik | durum | nasıl kullanılır | katman | modüller | testler |
|---|---|---|---|---|---|---|
| F33 | **Otomatik mod arka plan servisi** — girişte başlar, tarayıcı gerekmez, boşta kapanmaz, tek motor | ✅ (arayüzsüz CPU ölçümü açık) | `bta service install` · `bta service status` · panel http://127.0.0.1:8766/ | L5 | cli, consoleserver, autoengine | U73 U74 U75 U76 T-L45 |
| F34 | Panelden aygıt seçimi (her çıkışa ayrı profil, yeni aygıt varsayılan dokunulmaz) | ⬜ planlandı (G2) | — | L4/L6 | — | — |
| F35 | Kulaklık SPP kanalının çip kimliği (salt-okuma) | ✅ çip Bluetrum (R51), SPP RFCOMM 1 (R52); protokol `open` | `hcitool info <MAC>` · `sdptool browse <MAC>` | L1/L2 | — | — |
