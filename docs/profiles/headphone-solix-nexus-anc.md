# Kulaklık profili — Solix Nexus ANC

| alan | değer | kanıt |
|---|---|---|
| üretici | Audeeo Innovations (SOLIX markası), TWS, BT 5.4, 12 mm sürücü, ANC, 4 mikrofon | solixco.com ürün sayfası, manuals.plus |
| çip | **Bluetrum Technology** (LMP üretici 1602), LMP 0x0E alt 0x3 · eşlik uygulaması YOK (R47) | `hcitool info` (R51) |
| MAC | **değişken** — 09-27 `02:00:00:00:00:02`, 10-15 yeniden eşleşme sonrası `02:00:00:00:00:04` · class 0x240404 · kimlik ad tabanlı (E29) | `bluetoothctl info` |
| profiller | A2DP sink, HFP (mSBC/CVSD), AVRCP (mutlak ses) · **SPP (Serial Port)** — üretici uygulamasının ANC/EQ kontrol kanalı olması muhtemel (protokol `open`) · LE Audio YOK · DIS/Modalias yok | UUID listesi |
| codec yetenekleri | **SBC** bitpool 2–53 (tüm modlar) · **AAC** MPEG-2 LC, 8–48 kHz, VBR, bitrate alanı 0 | `MediaEndpoint1.Capabilities` sep1/sep2 |
| aptX / LDAC / LC3 | yok | — |
| AAC gerçek konfig | 48 kHz · 2ch · vbr=1 · 262 144 bps (kulaklık seçer) → PipeWire kesimi ~17 kHz | transport baytları `80 00 84 84 00 00`, benchmark |
| SBC-XQ | 48 kHz dual bitpool 39 (~504 kbps) → **bu bağlantıda paket atlıyor** | `bta link-test` 13 reduce/90 sn |
| SBC | 48 kHz joint bitpool 53 (~357 kbps) → temiz | link-test CLEAN |
| AutoEQ ölçümü | yok (8854 satırlık indekste 0 eşleşme) | AutoEq INDEX.md |
| bas | varsayılan akorda kısık; +dB ile iyi tepki (kullanıcı gözlemi) | kullanıcı, 2026-09-27 |
| önerilen başlangıç | tarz **Harman bas (kulakiçi 2019)** (+9,0 dB low-shelf 105 Hz Q0,7) + önce kulak tıkacı oturma testi | Harman IE 2019 CSV (R28) |
| davranış | art arda reconnect sonrası ~40 sn page-timeout | E6 |
| sürücü | 12 mm dinamik, 32 Ω (?), 20–20 kHz (tolerans yok) · **diyafram malzemesi yayımlanmamış** | R39 (malzeme `open`) |
| bas sınırı (yazılım kuralı) | 20–100 Hz toplam takviye > +12 dB → DİKKAT; 20 Hz altı > +10 dB → DİKKAT; ADL bas ≤ +4 dB, yüksek seviyede azaltır | R38 (bas sevenler +4–6 dB), U65 |
| tiz sınırı (AAC) | 17 kHz üstü takviye duyulmaz, preamp'i düşürür → BİLGİ uyarısı | R41, U65 |
| hi-fi dengeli seviye | ses yükseltme = −preamp (Harman'da +9 dB): orta bölge kaynak seviyesinde, sınırlayıcı (tavan −1 dBFS) yalnız bas taşmasında çalışır. Daha fazlası = sürekli sınırlama (dinamik aralık kaybı) | U78 ölçümü 2026-10-24 |
| bası belirleyen | kulak tıkacı sızdırmazlığı (EQ'dan önce) → konsoldaki oturma testi | R40, T-L43 |

Katman belgesi (durum · değişkenler · gri alanlar): [../layers/L1-headphone.md](../layers/L1-headphone.md).

