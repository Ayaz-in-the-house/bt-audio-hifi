# Kenar durumlar

| id | durum | davranış | not |
|---|---|---|---|
| K1 | Çalarken zorla disconnect | WP günlüğü `connection … terminated unexpectedly` + `running -> error` | Zararsız; kopmanın beklenen izi. Gerçek hata ile karıştırma. |
| K2 | `autoswitch=false` | Sanal `bluez_input.*` kaynağı hiç oluşmaz → hiçbir uygulama HFP'yi tetikleyemez | Görüşmede kulaklık mikrofonu gerekiyorsa profil elle `headset-head-unit` yapılmalı. |
| K3 | `bluetoothctl connect` | A2DP transport kurulana dek bloklar (~4 sn ölçüldü) | Süreyi connect başlangıcından ölç. |
| K4 | AAC konfigürasyonu kulaklık tarafından seçiliyor | Uzak caps bitrate=0 (→ PipeWire 320k varsayar) ama transport'ta 262 144 bps | PipeWire'ın `select_config` çıktısıyla aynı değil; bayt dizisi transport'tan okunmalı, tahmin edilmemeli. |
| K5 | `vbr=1` AAC konfigürasyonu | PipeWire CBR'de 19,3 kHz bant zorlamasını (a2dp-codec-aac.c:400) atlar → FDK otomatik kesim | F2 ölçüm konusu. |
| K6 | Çoklu BT cihaz | Aynı radyoda klavye (M96BT1) + fare (MX Master 3S) bağlı | F6 bağlantı sağlığında hesaba kat. |
| K7 | `module-switch-on-connect` | Dahili PCI (hoparlör, NVIDIA HDMI-PCI hariç HDMI olmayanlar) zaten hariç; kartsız RAOP hariç; USB dock `blocklist` ile hariç | Başka bir BT kulaklık (78:66…, 70:99…) bağlanırsa o da varsayılan olur — beklenen. |
| K8 | WirePlumber smart filter | Hedef sink'i **monitörleyen** yakalama akışları da filtrenin GİRİŞİNE yönlendirilir → EQ öncesi sinyal kaydedilir | Ölçümde `node.autoconnect=false` + `pw-link <sink>:monitor_FL …` ile elle bağlan (eqverify). Kullanıcı tarafı: pavucontrol'de kulaklık "monitörü" EQ öncesini gösterebilir. |
| K9 | Zen/Firefox | Sesi PipeWire'a grafik hızında (48k F32) verir; kendi resampler'ını kullanır | PipeWire `resample.quality` tarayıcı sesini etkilemez. |
| K10 | Kullanıcı dinlerken canlı test | Test tonu kulağına karışır (−45 dB bile) | T-L35: sink'te `running` akış varsa ton ÇALMA, mevcut müziği gözle. |
| K11 | "Çalan" tarayıcı akışı ≠ ses | Zen'de sessiz bir X sekmesi akışı `running` tutar; veri dijital sıfır (−300 dB) | "müzik algılandı" kararı akış durumundan değil sinyal seviyesinden (> −80 dBFS) verilir — analizör doğru "Sessiz" dedi. |
| K12 | `hidden` + bileşen `display` | Kendi `display` kuralı olan her bileşen `hidden`ı ezer | Global `[hidden]{display:none!important}` (E17). |
| K13 | CSP `script-src` `unsafe-eval` yok | Playwright `wait_for_function("…string…")` eval kullanır → test patlar | Testte `bypass_csp=True`; üretimde CSP aynen (kanıt: CSP gerçekten uygulanıyor). |
| K14 | "Müzik var" eşiği | Uygulama/akış ses düzeyi (WirePlumber hatırlar) sinyali filtre ÖNCESİNDE kısar: −45 dBFS ton −66 dBFS'e indi; −60 eşiği kısık dinlemeyi "sessiz" sandı | Eşik −80 dBFS (gerçek sessizlik dijital sıfır). Kulaklık/sistem sesi filtre SONRASINDA uygulanır → ölçümü etkilemez. |
| K15 | Tarayıcı testleri ağır bellek baskısında | Makine yükü 20–50 (bellek PSI %40–55) iken tam takım 30 sn zaman aşımlarıyla düşer; tek tek koşunca 5–10 sn'de geçer | Kod hatası sanma: `uptime` + `/proc/pressure/memory` bak, düşük yükte tekrar koş; kapı tam takımın yeşilidir. |
| K16 | `pw-cli` stdin EOF | Çıkmaz, döner (R durumu, %20+ çekirdek) — `/dev/null` girdisinde ise abort (rc 134) | Kalıcı oturumu `quit\n` ile kapat (E23). |
| K17 | `PR_SET_PDEATHSIG` | Ebeveyn SÜRECİ değil, fork eden İŞ PARÇACIĞI ölünce tetiklenir | Kısa ömürlü iş parçacığından doğan çocuk hemen ölür → tüm doğurmalar tek, uzun ömürlü doğurucu iş parçacığında (`procs.spawn`, U64). |
| K18 | A/B geçişte küçük artık | 5–6 güncellemede 1–2 olay, −68…−88 dBFS, B zincirine yüklemelerle eşleşiyor; güncellemesiz 0 | Duyulmaz; R43 açık. Geçişin tıksızlığını değerlendirirken başlangıç penceresini (süzgeç artefaktı) dışla (E24). |
| K19 | Otomasyon açık, sayfa kapalı | Sunucu "boşta" sayılıp 1 saatte kapanıyordu (analizör karesi yok = etkinlik yok) | Otomasyon tick'i etkinlik sayılır (U59). |
| K20 | Konsol süreci bir A/B geçişinin ORTASINDA ölür | İki zincir yarı kazançla duyulur; açılıştaki ilk yükleme duyulan zincire gidebilir → tık | Açılışta `Crossfader.settle()` karışımı etkin zincire sabitler (U68). Kaynak: skill GREEN testinde alt ajanın sorusu. |
| K21 | "Sesi fulledim ama yetmiyor" | Sistem + kulaklık %100 iken uygulama akışı (Firefox) %82 kalmıştı (≈ −5 dB; WirePlumber uygulama başına hatırlar); çıkış tepesi −10 dBFS idi. 2026-10-23 | ÖNCE akış seviyesini ölç: `wpctl get-volume <akış id>` + konsol çıkışından tepe/RMS. Akış %100 → tepe −2,3 dBFS. Bundan sonraki kazanç ancak sınırlayıcıyla (preamp −3,5 dB bas yükseltmesi için). |
| K22 | "Ses kısık" + otomatik mod açık | APC bas ağırlıklı tarz seçip üstüne ADL +4 dB bas ekleyince bas toplamı +15 dB'ye çıktı, preamp −11,5 dB → her şey kısıldı; çare yükseltmek değil EQ'yu belgeli hedefe (Harman IE) indirmekti. 2026-10-24 | ÖNCE `/api/state` `warnings` + 20–100 Hz eğrisine bak; `bass_high` varsa önce tonu düzelt, sonra ses yükseltme = −preamp |
