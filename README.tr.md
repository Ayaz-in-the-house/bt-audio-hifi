<p align="center"><img src="assets/icon.svg" width="96" alt="bt-audio-hifi"></p>

# bt-audio-hifi

[English](README.md) · **Türkçe**

Linux'ta (Fedora 44 · PipeWire 1.6.8 · WirePlumber 0.5.14) bir **Bluetooth kulaklığın** sesini ölçülebilir, geri
alınabilir ve kulağa göre en iyi hâle getiren araçlar: yüksek kalite profilde kalma, codec ölçümü, **profesyonel EQ
konsolu** (grafikten sürüklemeli 10 bant, uzay, 31 hazır tarz, canlı analizör), **dokunduğun an otomatik kaydedilen
çalışma kopyaları** (geri/ileri al), **müziği tanıyıp ayarı kendisi seçen otomatik mod**, yönetim sayfası.

Referans cihaz: Solix Nexus ANC (TWS, AAC/SBC). Başka Bluetooth kulaklıklarla da çalışır; hoparlör/HDMI/USB çıkışlarına
bilerek dokunmaz ([neden](docs/USER-DECISIONS.md#0-önce-kısa-cevap-bu-proje-tüm-çıkış-aygıtlarını-yönetir-mi)).

**Lisans: [MIT](LICENSE)** — herkes kullanabilir, değiştirebilir, dağıtabilir. Üçüncü taraf bileşenler: [NOTICE](NOTICE.md).

## Ekran görüntüleri

![Ses konsolu: grafikten sürüklemeli EQ, canlı analizör, hazır tarzlar](analysis/ui/console-v2-dark-1440.png)

| Kör dinleme testi (AAC ↔ SBC) | Yönetim: profiller, sürüm geçmişi, otomasyon |
|---|---|
| ![Kör dinleme testi](analysis/ui/abx-trial-dark.png) | ![Yönetim sayfası](analysis/ui/admin-dark-1440.png) |

<img src="analysis/ui/console-v2-mobile-390.png" width="260" alt="Telefonda konsol">

## Hızlı başlangıç

```bash
git clone <depo> bt-audio-hifi && cd bt-audio-hifi
ln -s "$PWD/bin/bta" ~/.local/bin/bta   # `bta` her klasörden çalışsın (aşağıda `bin/bta` = `bta`)
bin/bta status                 # kulaklık, profil, codec, akışlar
bin/bta check                  # kabul kontrolleri
bin/bta install                # config drop-in'leri (yedekli; yalnız bağlı Bluetooth kulaklığa)
bin/bta console                # ⭐ konsol — tarayıcıda açılır (yalnız 127.0.0.1)
bin/bta model fetch            # (isteğe bağlı) otomatik mod için yerel tür sınıflayıcısı (YAMNet, sha256 kilitli)
```

Gereken: Python 3.11+, numpy, scipy · otomatik mod için onnxruntime · testler için playwright.

## Ne yapar

| | özellik | nerede |
|---|---|---|
| 🎧 | Kulaklık hep A2DP (yüksek kalite); mikrofon açan uygulama sesi mono 16 kHz'e düşürmez | otomatik |
| 📡 | Codec ölçümü (AAC / SBC), bağlantı sağlığı, kör ABX dinleme testi | `bta bench` · `bta link-test` · `bta abx` |
| 🎛️ | 10 bant parametrik EQ (grafikten sürükle), crossfeed, genişlik, denge, 31 kaynaklı hazır tarz | konsol |
| 📈 | Canlı analizör: EQ öncesi/sonrası 1/6 oktav spektrum, metre, parça ortalaması | Analiz sekmesi |
| 💾 | İlk dokunuşta "Özel N" çalışma kopyası — ana profiller hiç değişmez; her değişiklik anında (< 1 ms) kaydedilir, geri/ileri alınır | otomatik |
| 🔇 | Tıksız ayar değişimi (A/B zincirli geçiş) | otomatik |
| 🤖 | Otomatik mod: türü tanır (elektronik, rock, konuşma…) → türe bağlı profili yükler; ince kayıtlarda sınırlı canlı bas/tiz uyarlaması; konuşmada dokunmaz | Otomatik sekmesi |
| 🗂️ | Yönetim: sürüm zaman çizelgesi + farklar, sürüme dön, çöp kutusu, toplu dışa/içe aktarma | `/admin` |
| 🛡️ | Sürücü koruma ve codec farkındalığı uyarıları, kulak tıkacı oturma testi | grafik altı · Analiz |

Tam katalog (gri alanlar dahil): [docs/FEATURES.md](docs/FEATURES.md).

## Belgeler

- **Buradan başla:** [docs/README.md](docs/README.md) (belge merkezi, ajanlar ve geliştiriciler için)
- Katmanlar: [kulaklık](docs/layers/L1-headphone.md) · [Bluetooth](docs/layers/L2-bluetooth.md) · [Linux](docs/layers/L3-linux-os.md) ·
  [PipeWire](docs/layers/L4-pipewire.md) · [yazılım](docs/layers/L5-bta-software.md) · [arayüz](docs/layers/L6-browser-ui.md)
- Mimari: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · modüller: [docs/modules/](docs/modules/README.md)
- Kararlar (sade Türkçe): [docs/USER-DECISIONS.md](docs/USER-DECISIONS.md) · gereksinimler: [docs/PRD.md](docs/PRD.md) ·
  testler: [docs/TEST-PLAN.md](docs/TEST-PLAN.md) · dersler: [docs/lessons/](docs/lessons/errors.md)

## Kurulu değişiklikler (`~/.config/pipewire/`)

| dosya | ne yapar |
|---|---|
| `pipewire-pulse.conf.d/60-bta-switch-on-connect.conf` | kulaklık bağlanınca varsayılan çıkış ona döner |
| `{client,pipewire-pulse}.conf.d/60-bta-resample.conf` | resampler kalitesi 4 → 10 |
| `filter-chain.conf.d/60-bta-console.conf` | konsol grafı (yalnız Bluetooth kulaklığa, smart filter) |

Oturum-dışı kalıcı ayarlar: kart profili `a2dp-sink` · `bluetooth.autoswitch-to-headset-profile=false`.
Kullanıcı verisi repo dışında: `~/.config/bt-audio-hifi/` · `~/.local/state/bt-audio-hifi/` · `~/.local/share/bt-audio-hifi/`.

## Geri alma

```bash
bin/bta uninstall                                                   # drop-in'ler (sha'sı eşleşenler) + yeniden başlatma
wpctl settings --save bluetooth.autoswitch-to-headset-profile true
```

## Test

```bash
tests/run.sh            # birim + tarayıcı (başsız, ses çıkmaz)
tests/run.sh --live     # + canlı/headful (gerçek PipeWire; ölçümler null sink'te, kulaklığa ton karıştırmaz)
```


## Yol haritası — henüz incelenmemiş katmanlar

Yazılım tarafı (L2'nin üst kısmı ile L3–L6) sınıflarıyla ve durumlarıyla çıkarıldı. Ama kulaklığın içi (çip, DSP, DAC,
ANC, TWS) ve radyo/protokol yığınının alt katmanları ayrıştırılmadı. "Donanım potansiyelini tam kullanıyor muyuz"
sorusunun cevabı da en çok orada; örneğin kulaklığın kendi içinde EQ ya da limiter uygulayıp uygulamadığını bilmiyoruz.

| katman | bilinen | eksik |
|---|---|---|
| Akustik / sürücü | — | Ayrı bir katman olarak incelenmedi. |
| Çip / mikrodenetleyici / DSP | Üretici belirlendi (Bluetrum, LMP'den) | İç DSP zinciri, kendi ses limiti, firmware sürümü. Ayrı bir katman olarak hiç yazılmadı, L1'in içinde iki satır kalıyor. |
| TWS (iki kulaklık arası aktarım) | — | Hiç incelenmedi: ses ana tekliğe mi gidiyor, öbürüne nasıl aktarılıyor, gecikme ve kayıp. |
| Bluetooth radyo / protokol yığını (radyo katmanı, LMP, L2CAP, AVDTP) | AX210 adaptör, BlueZ 5.87, profil ve kopma davranışı | Radyo kaydı (btmon) hiç alınmadı; sudo gerektiriyor. Wi-Fi ile çakışma ölçülmedi. Protokol durum makineleri belgelenmedi. |
| A2DP / codec | Güçlü: AAC ve SBC bayt bayt çözüldü, SBC-XQ ölçülüp elendi, kalite karşılaştırması yapıldı | AAC ↔ SBC kararı kör ABX testini bekliyor. |
| Linux / PipeWire / bta / arayüz (L3–L6) | Ayrıntılı: süreçler, graf, resampler, API, durum geçişleri | Küçük gri alanlar. |

Plan: L1 ve L2'yi ayrı katmanlara bölüp her birini aynı şablonla (seçenekler, durumlar, değişkenler, ölçüm yöntemi) doldurmak:

- [ ] **L1a** akustik ve sürücü
- [ ] **L1b** çip, firmware, DSP, DAC, amfi ve ANC — buradan başlanacak, en çok bilinmeyen burada
- [ ] **L1c** TWS aktarımı
- [ ] **L2a** radyo ve LMP
- [ ] **L2b** L2CAP ve AVDTP
- [ ] **L2c** A2DP ve codec

Kaynaklar: çip üreticisinin SDK belgeleri ve kılavuzları, Bluetooth çekirdek spesifikasyonu ve cihaz üzerindeki ölçümler.
Radyo kaydı için bir kez root komutu gerekir (`sudo bash tools/btmon-capture.sh 60`, ardından `bta btmon-report`).
