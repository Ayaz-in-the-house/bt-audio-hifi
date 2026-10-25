# TEST-PLAN — bt-audio-hifi (PRD-BTA01 … BTA04)

> **Kimlik kuralı (U67 kapısı):** her test kimliği bu dosyada TAM BİR KEZ tanımlanır; testlerde geçen her kimlik burada
> olmak zorundadır (`tests/test_docs_gate.py`). `U`=birim · `T-U`=tarayıcı (başsız) · `T-L`=canlı/headful ·
> `T-H`=tarihsel (emekli ya da hiç yazılmamış — gri alan, kimliği yeniden KULLANILMAZ).

İki katman: **birim** (`tests/test_*.py`, saf mantık, sistem durumuna dokunmaz) ve **canlı/headful**
(`tests/live/`, gerçek PipeWire grafı + gerçek kulaklık + gerçek ses çalma). Kanıt, şikâyetin katmanından gelir:
"ses kötü" şikâyeti ses grafında ve kulakta ölçülür — birim testi tek başına yetmez (observed-defect §5).

Koşum: `tests/run.sh` (birim) · `tests/run.sh --live` (birim + canlı). Canlı testler çıktıda `LIVE` etiketlidir.

## Birim testleri

| id | ne | beklenen | neden |
|---|---|---|---|
| U01 | AAC config `80 00 84 84 00 00` çöz | MPEG-2 LC, 48000, 2ch, vbr=1, 262144 | canlı transport'ta ölçülen gerçek bayt dizisi; yanlış çözüm yanlış karar demek |
| U02 | AAC caps `80 FF 8C 80 00 00` çöz | tüm 8k–48k hızlar, 1+2ch, vbr=1, bitrate=0 ("bilinmiyor") | uzak endpoint yetenekleri; bitrate 0 → PipeWire 320k varsayar (kaynak satır 132) |
| U03 | AAC 320000 set/get gidiş-dönüş | `84 E2 00` ↔ 320000 | makro eşdeğerliği (`AAC_SET_BITRATE`) |
| U04 | SBC caps `FF FF 02 35` çöz | 4 hız, 4 mod, 4 blok, 2 alt-bant, 2 alokasyon, bitpool 2–53 | sep1 gerçek bayt |
| U05 | SBC config dual/44.1k/bp43 çöz + bitrate hesabı | frame 184 B → 507 150 bps (A2DP SBC formülü: 4 + 4·sb·ch/8 + ⌈blk·ch·bp/8⌉) | SBC-XQ karşılaştırması için bitrate |
| U06 | Hatalı uzunluk | `ValueError` | kırpılmış D-Bus verisi sessizce yanlış sonuç üretmesin |
| U07 | snapshot diff: değişen/eklenen/silinen anahtar | 3 kategori doğru | durum geçişi analizi |
| U08 | diff uçucu anahtarları yok sayar | `taken_at`, pil % diff'e girmez | gürültüsüz diff |
| U09 | WirePlumber state dosyası ayrıştırma | `key=value` satırları, JSON değerli satırlar | `default-profile` doğrulaması |
| U10 | config drop-in manifest (sha256) | repo ↔ kurulu dosya eşleşme/sapma tespiti | install/uninstall doğrulaması |
| U11 | encoder analiz: kesim frekansı tespiti (sentetik) | 16 kHz alçak geçiren sinyalde ≈16 kHz | benchmark metriğinin kendisi test edilmeli |
| U12 | encoder analiz: SNR (bilinen gürültü) | enjekte edilen SNR ±0.5 dB | metrik doğruluğu |

## Canlı / headful testler

| id | ne | beklenen | neden |
|---|---|---|---|
| T-L01 | kart aktif profil | `a2dp-sink*` | HFP = mono 16 kHz (kök neden) |
| T-L02 | sink codec | PRD kararı (F2.4) | karar uygulanmış mı |
| T-L03 | sink formatı | 2 kanal, ≥44100 Hz | stereo/tam bant |
| T-L04 | kayıtlı varsayılan profil | `default-profile` → `a2dp-sink*` | yeniden bağlanmada geri gelmesin |
| T-L05 | autoswitch ayarı | `false (Saved: false)` | mikrofon açan uygulama düşürmesin |
| T-L06 | transport durumu | `State=active` çalarken | gerçekten veri akıyor |
| T-L10 | **headful**: BT disconnect → connect | ≤15 sn içinde A2DP + aynı codec, stereo | kalıcılık iddiasının ürün kanıtı |
| T-L11 | **headful**: BT kaynaktan kayıt açan istemci (pw-record bluez_input) | profil A2DP'de KALIR | autoswitch=false iddiasının kanıtı |
| T-L12 | **headful**: pw-play test sesi BT sink'e | akış `running`, sink'e bağlı, pw-top'ta xrun artmaz | uçtan uca yol |
| T-L20 | resample drop-in kurulu | sha repo ile eşit | config sapması yok |
| T-L21 | **headful**: 44.1 kHz dosya çal → akış düğümü `resample.quality` | drop-in değeri | ayar gerçekten akışa uygulanıyor |
| T-L22 | **headful**: sweep → monitor kaydı analizi | aliasing tabanı q4'e göre daha düşük | kalite iddiasının ölçümü |
| T-L23 | graf saat hızı | karar F4.2'ye göre | allowed-rates etkisi |
| T-H30 | *(emekli — EasyEffects yolu F8.3 kararıyla terk edildi; kimlik bugün T-L30 = smart filter)* EasyEffects kurulu + sürüm sabit | flatpak ref + commit eşleşir | tekrarlanabilirlik |
| T-H31 | *(emekli)* EasyEffects çalışıyor, BT sink zincirde | `easyeffects_sink` → BT sink link | EQ yolda |
| T-H32 | *(emekli)* preset yüklü | autoload dosyası BT sink'e bağlı | cihaza özel |
| T-H33 | *(emekli)* EasyEffects CPU | ölçülen değer raporlanır; eşik %5 tek çekirdek | kaynak maliyeti |
| T-H34 | *(emekli)* **headful**: EE kapalı/bypass → ses doğrudan BT'ye | link yok, ses var | geri dönüş yolu |
| T-H40 | *(GRİ — planlandı, hiç yazılmadı; kimlik bugün T-L40 = otomasyon CPU)* `bta uninstall` → `bta check --baseline` | kurulu dosyalar kaldırıldı, WP ayarları eski | geri alınabilirlik |
| T-L50 | bağlantı sağlığı: 60 sn çalma, debug log | bitrate düşürme olayı sayısı raporlanır | paket sorunu var mı |

## Durum-geçiş kaydı

Her özellik adımından önce ve sonra `bta snapshot <label>`; `bta diff` çıktısı `docs/STATE-LOG.md`'ye.

## PRD-BTA02 (konsol) ek testleri

| id | ne | beklenen | neden |
|---|---|---|---|
| T-L30 | **ürün katmanı**: smart filter-chain EQ'su (`eqverify`) | tasarım modeli ↔ gerçekten uygulanan yanıt ±0,01 dB | EQ yalnız kulaklıkta ve doğru |
| U30 | RBJ katsayıları (6 tip) | bell merkez=kazanç, raf köşe=½, LP/HP −3,01 dB, notch <−60 dB | bq_raw'a yazılacak değerler |
| U31–U35 | konsol modeli | varsayılan şeffaf; bs2b = bs2b.c formülleri; preamp ile 0 dBFS aşılmaz; genişlik mono-uyumlu; 11 profil geçerli+kaynaklı | güvenlik + sadakat |
| T-L32 | **null sink**: tam stereo graf | L/R her iki çıkış modelle ≤0,05 dB (ölçülen 0,001) | ürün katmanı kanıtı |
| T-L33 | **headful**: konsol yolu | app → effect_input.bta_console → effect_output → BT; eski bas filtresi yok | tek smart filter |
| T-U03 | başsız E2E | sürükle/tekerlek/çift tık/tip/crossfeed/genişlik/profil/geri al/A-B/kalıcı; JS=Python ≤0,01 dB; JS hatası 0 | kullanıcı etkileşimi |

## PRD-BTA03 (konsol v2) — plan, KODDAN ÖNCE yazıldı

| id | katman | ne | beklenen | neden |
|---|---|---|---|---|
| U40 | C0 | `paths` `$BTA_HOME` altında izole; göç kopyalar (kaynak kalır), ikinci koşu no-op | dosyalar hedefte, kaynak sha'ları aynı | testler kullanıcı verisine dokunmasın; göç veri kaybettirmesin |
| U41 | C1 | kaydet/üzerine-yaz(409)/yeniden-adlandır/çoğalt/sil→çöp→geri al/içe-dışa aktar | şema `bta.profile/1`; Türkçe ad; `../x` yolu hedef dizinden ÇIKAMAZ; bozuk JSON 400; 257 KB 413 | kullanıcı talebinin çekirdeği + yol güvenliği |
| U42 | C1 | aktif profil + değişti | kayıt sonrası dirty=false; 1 bant değişince true; geri alınca false | "kaydettim mi?" sorusu arayüzde cevaplanmalı |
| U43 | C2 | profil kütüphanesi | ≥22; her birinde kategori/kind/kaynak; niyet: zengin bas 40 Hz ≥ +6 dB ve 1–3 kHz ≤ +1 dB; vokal 3 kHz − 1 kHz ≥ +2 dB; gece 50 Hz ≥ +4 & 10 kHz ≥ +2; tüm profiller preamp ile ≤ 0 dBFS | vaat edilen şekli ölçerek doğrula, isim ≠ ses |
| U44 | C4 | analizör kalibrasyonu | 1 kHz 0 dBFS → 0±0,2; −20 dBFS → −20±0,2; tam ölçek sinüs RMS −3,01±0,05 dBFS; kırpılma sayacı ≥0,999 örnekleri sayar | ölçü aletinin kendisi test edilir (U11 geleneği) |
| U45 | C4 | balistik | tepe tutma sinyal kesilince release hızında düşer (±10 %) | görsel davranışın sayısal sözleşmesi |
| U46 | C4 | abone yaşam döngüsü (sahte kaynak) | ilk abone → süreç başlar; son abone gidince ≤2 sn içinde süreç yok; SSE çerçeveleri geçerli JSON | kimse bakmıyorken bedel ödenmez |
| U47 | güvenlik | yeni uçlar Host/JSON/boyut kapısından geçer; SSE GET de Host kontrollü | 403/415/413 | E16 sınıfı yeni uçlarda tekrarlanmasın |
| U48 | C3 | kontrast | metin ≥4,5:1, UI ≥3:1, iki temada | erişilebilirlik ölçülür, göze bırakılmaz |
| T-U04 | C1–C4 UI | başsız E2E: yeni-olarak-kaydet diyaloğu, çakışma onayı, dirty noktası, yeniden adlandır, dışa/içe aktar (indirme olayı), profil arama/süzme, önizleme, klavye ile bant, analizör açık (sahte kaynak) → spektrum çiziliyor; JS=Python ≤0,01 dB; konsol hatası 0; 1440 ve 390 px, açık/koyu ekran görüntüleri | kullanıcı etkileşiminin tamamı |
| T-L34 | C4 canlı | null sink: +6 dB 1 kHz bell grafında 1 kHz ve 100 Hz ton; analizör post−pre | model (preamp dahil) ±0,5 dB | ürün katmanı kanıtı |
| T-L35 | C4 canlı | gerçek kulaklık yolunda analizör açık | yakalama akışları yalnız monitör portlarına bağlı; app→effect_input→effect_output→BT yolu değişmez (T-L33 yeşil); sayfa kapanınca yakalama süreci yok | R17 tuzağı + kaynak disiplini |
| T-L36 | headful | Zen/gerçek ekranda sayfa + analizör; ekran görüntüsü | görünür spektrum, konsol hatası yok | kullanıcı katmanı |
| T-L37 | C0 canlı | "Kalıcı yap" | `git status` temiz; `~/.local/state/bt-audio-hifi/` yeni dosya; kurulu config = durumdan üretilen | D2 |
| T-L38 | C5 | `tools/oss-audit.sh` | ürün dosyalarında MAC/ev yolu/host adı 0 | açık kaynak sızıntısı |

## PRD-BTA04 — plan, KODDAN ÖNCE

| id | katman | ne | beklenen | neden |
|---|---|---|---|---|
| U51 | D1 | hazır tarz aktifken ilk değişiklik | "Özel 1" oluşur, aktif = Özel 1, `derived_from`=tarz; ikinci dokunuş YENİ çatal açmaz; kilitli profilde aynı; hazır tarz ve kilitli profil dosyası sha'sı DEĞİŞMEZ; numara boşluğu: Özel 1 silinse bile sonraki Özel 3 (çakışma yok) | "ana profiller hiç zarar görmesin" |
| U52 | D1 | kayıt istek yolunu yavaşlatmaz | 500 set_state: istek iş parçacığında `open()` çağrısı 0 (izleme); yazıcı kapatılınca son durum diskte; p95 istek süresi kayıt açık/kapalı farkı < 1 ms | "1 ms bile gecikme/donma yok" |
| U53 | D1 | kalıcı geri/ileri al | 5 değişiklik → yeni Session (yeniden başlatma benzetimi) → 3 geri al = 2. sürüm; ileri al çalışır; yeni değişiklik ileri dalı keser; günlük satırı ≤ 4 KB; bozuk son satır (çökme) yok sayılır | "saatlerce uğraş boşa gitmesin" |
| U54 | D3 | öznitelik karakteri | sentetik: 50 Hz ağır + az tiz → bas_ağırlıklı; pembe gürültü → dengeli; 3 kHz ağır → parlak/vokal; sessizlik → karar yok | sınıflayıcının deterministik katmanı |
| U55 | D4 | APC karar mantığı (sahte saat) | tür A 20 sn → A profili; kısa B patlaması (5 sn) → geçiş YOK; B 12 sn sürekli + marj → geçiş; 30 sn dolmadan C → geçiş YOK; düşük güven → yedek profil; elle dokunuş → 10 sn askı | salınım/pompalama olmaz |
| U56 | D5 | ADL kontrol (sahte saat) | referansla aynı spektrum → düzeltme 0 (ölü bölge); bas eksik şarkı → bas ↑ en çok +4; bas fazla + elektronik → bas ↑ YOK; değişim hızı ≤ 1 dB/s; yüksek seviye → bas azalır; elle düzeltme → önyargı α=0,2 ile öğrenilir | sınırlı, öngörülebilir otomasyon |
| T-L39 | D2 canlı | null sink: A/B geçiş (0→+6 dB, 1,5 sn) sırasında >4 kHz artık | ≤ −90 dBFS (doğrudan güncellemede −46); geçiş sonrası çıkış modeli ±0,05 dB; statik T-L32 eşdeğeri korunur | R33 kök nedeninin ürün çözümü |
| T-L40 | D3 canlı | otomasyon motoru gerçek akışta (kararlar SAHTE uygulayıcıya — kullanıcının sesi değişmez) | motor ≤ %3, yakalama ≤ %2 tek çekirdek; sınıflama medyanı ≤ 50 ms/2 sn. **Ölçüldü:** ilk %15 (tam analizör) → hafif mod (U62) sonrası **%2,33 + %0,33**, 13,7 ms | kaynak disiplini |
| T-L41 | D4/D5 canlı | otomasyonun gerçek güncelleme deseni (0,5 dB kuantalı adım, 1,5 sn A/B) null sink'te | başlangıç artefaktı dışında en büyük artık ≤ −70 dBFS, olay ≤ güncelleme/3, son seviye model ±0,05 dB. **Ölçüldü:** −83,9 dBFS (−38,3 tepe = kaydın ilk penceresi, `max_time_s` ile kanıtlı) | kullanıcı katmanında tık yok |
| T-U05 | D3–D5 UI | Otomatik sekmesi: 4 mod, konuşma → Konuşma tarzı (aktif ad + bildirim + son geçişler), ikisi birden + ince bas → ADL sütunu + grafikte kesikli eğri, bas yoklaması, tür etiketi penceresi → eşleme tablosu, kapatınca katman/abonelik kalkar; 390 px; JS hatası 0 | otomasyon kullanıcıya görünür ve geri alınabilir. *(Plandaki ilk anlamı — D1 "Özel 1" rozeti/kalıcılık — T-U04'e eklendi.)* |
| T-U06 | D6 UI | /admin: profil tablosu, sürüm geri yükleme, otomasyon ayarı, sınıflayıcı paneli, geçiş günlüğü; JS hatası 0; 390 px | ikinci yüzey |

## PRD-BTA01/02 — yazılmış ama planda EKSİK olan testler (U67 kapısı 2026-09-28'de yakaladı)

| id | ne | beklenen | neden |
|---|---|---|---|
| U15 | bağlantı sağlığı günlük ayrıştırıcısı (`media-sink.c` reduce/increase satırları) | olaylar ve bitrate değerleri doğru sayılır | SBC-XQ eleme kararının kanıtı (F6) |
| U16 | encoder benchmark hattının kendi hatası | kayıpsız kontrol adayı ≫100 dB; HFP-mSBC ≤ 20 kHz'de çöker | ölçü aleti doğru mu |
| U17 | gerçek libsbc ↔ `codecs.sbc_frame_length` | çapraz doğrulama + gidiş-dönüş | SBC bitrate hesabı |
| U18 | ABX saf mantığı | denemeler dengeli/tekrarlanabilir; binom p-değeri doğru | kör dinleme kararının istatistiği |
| U19 | resampler ölçüm analizi | bilinen sahte bileşen seviyesi geri okunur | F4 ölçümünün doğruluğu |
| U22–U24 | ISO 226:2003 modeli, eşit-yükseklik eşleşmesinden yanıt çıkarımı, PEQ uydurma | kaynak tablolarla birebir; sentetik yanıt geri bulunur | F8 bas analizi |
| U25 | tasarım → smart filter-chain config + EasyEffects preset JSON | geçerli config + geçerli JSON | F8 uygulaması |
| U26 | bas analizi: iki oturma dosyası → yanıt, sızdırmazlık farkı, phon duyarlılığı, EQ | bilinen girdilerde beklenen tasarım | F8 |
| U27 | btmon metin + btmgmt conn-info ayrıştırıcı | BlueZ biçim satırları doğru ayrışır | kullanıcının root radyo kaydı (gri: kayıt henüz alınmadı) |
| U29 | eski canlı bas ayarlayıcı saf mantığı | bantlar, otomatik preamp, hazır ayarlar, pw-cli yükü, sınırlar | PRD-BTA01 F8 v2 |
| U36 | yerel sunucu güvenliği | yol geçişi, CSRF (basit istek), DNS rebinding (Host) reddedilir | E16 sınıfı |
| T-L13 | **headful**: kopma/bağlanma sonrası varsayılan çıkış | tekrar kulaklık (switch-on-connect) | GNOME hoparlöre yazıyordu (tuzak) |
| T-L14 | **headful**: senaryolu ABX | 2 deneme × 3 çalma, geri dönüş | ABX aracının gerçek çalma yolu |
| T-U01 | bas eşleştirme sayfası (başsız, ses kapalı) | akış tamamlanır, JSON doğru, JS hatası 0 | F8 v1 arayüzü |
| T-U02 | eski canlı bas ayarlayıcı sayfası | uçtan uca, sahte uygulayıcı | F8 v2 arayüzü |

## PRD-BTA03/04 — uygulama sırasında eklenen testler (sonuçlarıyla)

| id | katman | ne | beklenen | sonuç |
|---|---|---|---|---|
| U49 | C0 | "Açılışta kullan" repoyu kirletmez (T-L37'nin izole karşılığı) | durum + üretilmiş config XDG'de, repo temiz | ✅ |
| U50 | C5 | açık kaynak sızıntı kapısı regresyonu | gönderilen kümede MAC/ev yolu/makine adı/e-posta/özel IP 0 | ✅ |
| U57 | D2 | A/B graf yapısı + parametre yükü + sıralayıcı | yalnız sessiz zincire yükleme; ara istekler birleşir; `submit` bloklamaz | ✅ |
| U58 | D5 | ADL üst katmanı | sese eklenir; kullanıcı durumuna/çalışma kopyasına/geçmişine YAZILMAZ | ✅ |
| U59 | D3–D5 | motor kararları (sahte saat) | konuşma → Konuşma tarzı; etiketli profil öncelikli; elle dokunuş 10 sn askı; sessizlik no-op; konuşmada bas eklenmez; kapatınca katman+abonelik kalkar; otomasyon = etkinlik; kapanışta katman kalkar; ayar kalıcı | ✅ |
| U60 | D3–D5 | `/api/auto` | mod değişir, geçersiz mod 400, bas yoklaması öğrenmeye yazılır | ✅ |
| U61 | D3 | analizör halka tamponu + `snapshot()` | son N sn mono float32, seviye −9,03 dBFS (0,5 sinüs), halka dönüşünde en yeni ses | ✅ (mutasyonla kanıtlı) |
| U62 | D3 | yalnız otomasyon abonesi → hafif tek dokunuş | yalnız `pre` süreci, kare başına FFT yok, istek anında spektrum −6,02 dBFS; arayüz gelince tam, gidince hafif | ✅ |
| U63 | D6 | yönetim arka ucu | zaman çizelgesi yeniden oynatmayla aynı; sürüme dönüş yıkıcı değil (+1 sürüm, geri alınabilir); tablo; çöp; paket; /admin CSP | ✅ |
| U64 | E23 | yetim alt süreç | `pw-cli` close ≤ 0,5 sn (`quit` yolu); ebeveyn ani ölünce pw-cli + pw-record ≤ 3 sn'de ölür; doğuran iş parçacığı bitince çocuk YAŞAR | ✅ (mutasyonla kanıtlı) |
| U65 | D7.2/3 | koruma uyarıları + oturma tonu | hazır tarzlar yanlış alarm vermez; bas > +12 dB / 20 Hz altı / AAC'de 17 kHz üstü; ADL dahil; ton EQ'suz çalar, bitince önceki hâl | ✅ |
| U66 | D7.3 | ton sinyali | −24,00 dBFS tepe, 50 Hz, uçlar sessiz (tık yok) | ✅ |
| U68 | D2 | açılışta karışımı etkin zincire sabitle (`Crossfader.settle`) | ilk yazım = etkin zincirin kazancı (A → 1/0, B → 0/1), sonra sessiz zincire yükleme | ✅ (skill GREEN testinin REFACTOR bulgusu) |
| U67 | belge | belge güncelliği kapısı | her modül katmanlı; modül belgeleri güncel; test kimlikleri planda tek; katman belgeleri bölümlü; bağlantılar sağlam | ✅ |
| T-U06 | D6 UI | /admin uçtan uca | tablo, geçmiş (fark satırları), sürüme dön (+1 sürüm), sil→çöp→geri yükle, paket dışa/içe aktar, otomasyon modu, 390 px, JS hatası 0 | ✅ |
| T-U07 | D7 UI | uyarı şeridi + oturma testi | AAC+Elektronik → BİLGİ; aşırı bas → DİKKAT; bas tonu → EQ'suz + durum; Durdur → geri | ✅ |
| T-L42 | D3 canlı | ürün katmanı tanıma | ses varken tür tahmini + tonal denge + karar; yoksa "sessizlik". **Ölçüldü:** anlatım videosu → konuşma %82–92, ADL katkısı 0 | ✅ |
| T-L43 | D7 canlı | oturma tonu gerçek PipeWire'da (null sink) | tepe −24 ± 0,5 dBFS, 50 ± 1,5 Hz. **Ölçüldü:** −24,00 dBFS, 50,1 Hz | ✅ |

## PRD-BTA05 — plan, KODDAN ÖNCE (2026-09-28)

| id | katman | ne | beklenen | neden |
|---|---|---|---|---|
| U69 | E1.2–E1.4 | ABX test motoru (sahte codec değiştirici + çalar) | 12 deneme 6A/6B karışık; her çalma = [diğer, hedef] geçişi; X dinlenmeden cevap 409; 10/12 → ayırt edilebilir + tercih; 9/12 → tercih sorulmaz; bitiş ve iptalde orijinal codec; test boyunca otomasyon askıda | kör testin istatistiği ve kullanıcının sesini bozmaması |
| U70 | E1.1 | kendi müziğinden klip | EQ öncesi halka tampondan 12 sn stereo 48 kHz wav; sinyal −60 dBFS altındaysa ret ("müzik çalmıyor"); klip XDG'de | kullanıcının müziği ziller/vokal içerir; sessiz klip testi anlamsız kılar |
| T-U08 | E1.5 | kör test penceresi uçtan uca (sahte arka uç) | klip seç → 12 deneme → sonuç ekranı sade dil; ▶A ▶B ▶X, X dinlenmeden cevap düğmesi pasif; iptal → orijinal; JS hatası 0; 390 px | kullanıcı teknik bilgi olmadan testi bitirebilmeli |
| T-L44 | E1 canlı | codec gidiş-dönüşü + klip yakalama gerçek PipeWire'da | aac→sbc→aac ≤ 15 sn her biri, sink geri gelir, `effect_input.bta_console` yolu korunur | ürün katmanı; YALNIZ sink'te çalan akış yokken (K10) |


### Cihaz kimliği (E29 · 2026-10-15)

| id | katman | ne | beklenen | neden |
|---|---|---|---|---|
| U71 | konsol kurulumu | kurulu smart filter hedefinin bayatlığı | eski `node.name` (MAC) hedefi ya da adı değişmiş kulaklık → bayat; kimlik hedefi → bayat değil; kulaklık bağlı değil → bayat değil (son hedef korunur) | E29: hedef eski MAC'te kaldı, akışlar filtreyi atladı (EQ yok, otomatik mod sessiz) |
| U72 | cihaz kimliği | MAC'siz kimlik + önbellek + seçici | bilinen MAC > aynı ad > kulaklık biçimli; hoparlör asla; önbellek MAC kümesi büyür, atomik yazım, bozuk dosya çökertmez, eski düz-MAC dosyası göç eder; filtre hedefinde MAC yok; güvensiz ad (`"` `\` `{}` `[]` kontrol karakteri, >128) ne önbelleğe ne config'e girer, `target_spa` her değeri doğrular | yeniden eşleştirme / TWS birincil tek değişimi yeni MAC verir; JBL ile çakışma olmamalı |
| T-L25 | canlı | `bta check`: kurulu konsol hedefi = bağlı kulaklığın kimlik hedefi | PASS | U71'in ürün katmanındaki karşılığı |

### PRD-BTA06 (2026-10-15)

| id | katman | ne | beklenen | neden |
|---|---|---|---|---|
| U73 | otomasyon | ADL histerezis + en az bekleme | sınırda salınım (1,24↔1,26) 30 tikte ≤ 1 uygulama; gerçek sürüklenme 0→4 dB takip edilir (≤ 0,5 dB), uygulama ≤ 30/ADL_MIN_S + 1 | E31/R50: sürekli geçiş %11,6 çekirdek |
| U74 | sunucu | `idle_timeout_s=0` | bekçi sunucuyu durdurmaz | arka plan servisi kapanmamalı |
| U75 | cli | tek örnek | portta bta konsolu varsa URL döner (yeni motor yok); başka sunucu → None; aynı JSON'u taklit eden ama bizim `bta console` sürecimiz olmayan dinleyici (başka uid ya da başka komut) → None | iki motor aynı düğüme yazmasın |
| U76 | cli | systemd kullanıcı birimi metni | mutlak ExecStart + `--no-open --port 8766 --idle-timeout 0`, After=pipewire/wireplumber/filter-chain, Restart=on-failure | girişte başlar, çökünce kalkar |
| U77 | console | ses yükseltici + sınırlayıcı (`test_loud_limiter`, `test_crossfade` U57) | zincirin son düğümü LSP `limiter_stereo` (toplam → lim → çıkış); yükseltme `~/.config/bt-audio-hifi/loudness.json` `loud_db` 0–9 dB (dosya yok/bozuk → 0); tavan −1 dBFS; otomatik yükseltme kapalı; ALR 10/300 ms; eski kurulum konsol açılışında bir kez göç eder (u77-limiter) | bas yükseltmeli tarzlarda ön kazanç −11 dB inince ses kısılıyordu; düz kazanç bas vuruşunda kırpar |
| U78 | console | panelde canlı ses yükseltme (`test_loud_limiter` TestLoudPanel) | `view()["loud"]` = {db, max}; `POST /api/loud` → değer 0–15 dB sınırlanır, ayar atomik yazılır, `lim:Input gain (G)` canlı yüklenir (A/B geçişsiz, müzik kesilmez); test dizininde gerçek XDG'ye yazılmaz; konsol açılışında kayıtlı değer canlıya basılır | kullanıcı panelden ayarlamak istedi; dosya + yeniden başlatma 2–3 sn kesinti veriyordu; ölçüm: 14 dB'de sakin parçada sınırlama yok |
| U79 | docs | kayıt defterleri yalnız eklenir (`test_docs_gate` test_u79) | `errors.md` E1…En ve `findings.md` R1…Rn kimlikleri kesintisiz; `STATE-LOG.md` başlığıyla başlar | 14af43c üç defteri tek satırla ezmişti, on gün fark edilmedi (E35) |
| U80 | console | ilk kurulum varsayılanı (`test_first_run`) | hiç durumu olmayan kurulum `hifi_uzay` ile başlar (105 Hz +6 dB raf, crossfeed 700/4,5, genişlik 1,1) ve ses yükseltme 6 dB'ye tohumlanır; var olan durum/ayar DEĞİŞMEZ; preset Nötr'den sonra 2. sırada | kullanıcı: "kuran kişi için bu ilk varsayılan olsun" · "nötrün yanına, 2. seçenek" · "bası biraz azalt" |
| U81 | analyzer | dokunuş bağlantısı doğrulanır ve onarılır (`test_analyzer` TestLinkHeal) | kaynak portlar geç belirse de bağlanır (30 sn); `pw-link -l` ile doğrulanmayan bağlantı başarısızlıktır; canlı ama bağlantısız dokunuş yeni abonede onarılır | 10-25: yeniden başlatma sonrası dokunuşlar bağlantısız kaldı, panel müzik çalarken boştu (E36) |
| T-L45 | canlı | servis | birim etkin · 8766 cevap · ikinci `bta console` süreç sayısını artırmaz · müzikte ≤ %3 çekirdek | ürün katmanı |
