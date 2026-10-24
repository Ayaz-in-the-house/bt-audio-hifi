# bt-audio-hifi

Linux'ta (Fedora 44 · PipeWire 1.6.8 · WirePlumber 0.5.14) bir **Bluetooth kulaklığın** sesini ölçülebilir, geri
alınabilir ve kulağa göre en iyi hâle getiren araçlar: yüksek kalite profilde kalma, codec ölçümü, **profesyonel EQ
konsolu** (grafikten sürüklemeli 10 bant, uzay, 31 hazır tarz, canlı analizör), **dokunduğun an otomatik kaydedilen
çalışma kopyaları** (geri/ileri al), **müziği tanıyıp ayarı kendisi seçen otomatik mod**, yönetim sayfası.

Referans cihaz: Solix Nexus ANC (TWS, AAC/SBC). Başka Bluetooth kulaklıklarla da çalışır; hoparlör/HDMI/USB çıkışlarına
bilerek dokunmaz ([neden](docs/USER-DECISIONS.md#0-önce-kısa-cevap-bu-proje-tüm-çıkış-aygıtlarını-yönetir-mi)).

**Lisans: [MIT](LICENSE)** — herkes kullanabilir, değiştirebilir, dağıtabilir. Üçüncü taraf bileşenler: [NOTICE](NOTICE.md).

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

## In English (short)

**bt-audio-hifi** makes a Bluetooth headphone on Linux (PipeWire ≥ 1.6, WirePlumber ≥ 0.5) sound its best — measurably
and reversibly. It keeps the headset on A2DP (no mono 16 kHz HFP fallback), measures codecs (AAC/SBC) and link health,
and ships a local web **EQ console** (draggable 10-band parametric EQ, crossfeed, width, 31 sourced presets, live
spectrum analyzer) with **auto-saved working copies** and persistent undo/redo, **click-free parameter changes** (A/B
chain crossfade — PipeWire biquads reset their state on every update), an optional **auto mode** (on-device YAMNet genre
recognition → per-genre profiles; bounded live tonal adaptation that leaves speech untouched) and an **admin page**
(version timeline with diffs, trash, bundle export/import). The EQ targets only the connected Bluetooth headphone
(WirePlumber smart filter); speakers/HDMI/USB are intentionally untouched. The UI and docs are Turkish; an English UI is a
planned gray area. License: **MIT**.
