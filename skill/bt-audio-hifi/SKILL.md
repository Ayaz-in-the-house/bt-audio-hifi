---
name: bt-audio-hifi
description: Use when Bluetooth headphones/earbuds sound bad, muffled, mono, bassless or "phone-call quality" on Linux PipeWire/WirePlumber (Fedora, Arch, Ubuntu), when choosing AAC/SBC/SBC-XQ/LDAC/aptX, when audio stays on laptop speakers after a headset reconnects, when adding EQ/bass/crossfeed only for one headphone, or when someone asks for a headphone EQ console/presets. Turkish triggers: kulaklık sesi kötü, bas yok, bluetooth kalite, codec, telefon modu, ses uzayı.
---

# Bluetooth kulaklık hi-fi (PipeWire)

## Overview
Bluetooth ses sorunlarının çoğu codec değil **profil/yönlendirme** sorunudur; kalanı **ölçülmeden** yanlış çözülür.
Her iddia çalıştırılabilir kanıtla: transport baytları, paket-atlama sayacı, null-sink üzerinde ölçülen EQ yanıtı.
Referans uygulama + araçlar: `~/projects/bt-audio-hifi` (`bin/bta`), süreç: `docs/PROCESS.md`.

## Quick Reference (sıra önemli)

| # | adım | komut / kanıt |
|---|---|---|
| 1 | Profil HFP mi? (mono 16 kHz = "telefon sesi") | `pactl list cards` → `Active Profile`; akış `output_MONO` |
| 2 | Kalıcı kaydı düzelt | `pactl set-card-profile <kart> a2dp-sink` (WP `~/.local/state/wireplumber/default-profile`'a kendisi yazar) |
| 3 | Mikrofon açılınca HFP'ye düşmesin | `wpctl settings --save bluetooth.autoswitch-to-headset-profile false` (sanal `bluez_input` kaynağı kalkar) |
| 4 | GERÇEK codec parametresi | `busctl --json=short get-property org.bluez <…/sepN/fdM> org.bluez.MediaTransport1 Configuration` → çöz (`btaudio/codecs.py`) |
| 5 | Bağlantı sağlığı (sudo'suz) | `wpctl set-log-level '2,spa.bluez5.sink.media:4'` + çal → `reduce bitpool` sayısı (=atlanan paket); sonra `wpctl set-log-level 2` · `bta link-test 90` |
| 6 | Codec kararı | Yalnız cihazın endpoint'lerindeki codec'ler; yüksek bitrate'li adayı **link-test CLEAN** değilse ele; AAC↔SBC arası kör ABX (`bta abx`) |
| 7 | Kopunca hoparlörde kalıyor | GNOME `default.configured.audio.sink`'i yazar (ölç: `pw-metadata -n default -m 0`) → `pipewire-pulse.conf.d`: `load-module module-switch-on-connect blocklist=^alsa_|hdmi` |
| 8 | Bas yok | Önce **tıkaç sızdırmazlığı** (bastırınca bas geliyorsa tıkaç); sonra EQ |
| 9 | EQ yalnız bu kulaklığa | filter-chain + WirePlumber **smart filter** (`filter.smart = true`, `filter.smart.target = { node.name = "bluez_output.…" }`) · ayrı `filter-chain.service` (tüm PipeWire yeniden başlamaz) |
| 10 | Canlı ayar | `bq_raw` katsayıları her blokta okunur → tip dahil canlı: `pw-cli set-param <effect_input id> Props '{ params = [ "eq_1:b0" … ] }'` · konsol: `bta console` |
| 11 | Kırpılma | preamp = −(en kötü durum tepe); konsol otomatik |
| 12 | "Düzeldi" kanıtı | null sink'te ölçülen yanıt ↔ model (T-L30/T-L32), gerçek yolda bağ listesi `app → effect_input → effect_output → bluez_output` |

### Smart filter iskeleti (anahtarların YERİ önemli)
```
capture.props  = { node.name = "effect_input.X"  media.class = Audio/Sink
                   filter.smart = true  filter.smart.name = "X"
                   filter.smart.target = { node.name = "bluez_output.<MAC_>.1" } }
playback.props = { node.name = "effect_output.X"  node.passive = true }
```
`filter.smart*` `capture.props` DIŞINDA (ör. `node.properties`) → EQ **sessizce** uygulanmaz. Kanıt: `pw-link -l`'de
`app → effect_input.X → effect_output.X → bluez_output…`. Tam üretici: `btaudio/console.py::render_graph`.

## Canlı parametre değişimi / otomasyon (PipeWire 1.6.8 — ölçülmüş)

| kural | neden (kanıt) |
|---|---|
| EQ'yu müzik çalarken değiştirecekse **A/B çift zincir** kur: yeni durumu SESSİZ zincire yükle, toplama `mixer` kazançlarını ~12 ms adımlarla kaydır | `bq_raw` ve tüm biquad'lar HER `set-param`'da belleğini sıfırlar → her güncelleme −46 dBFS tık; katsayıyı küçük adımlarla "yumuşatmak" her adımda YENİ tık demek (R33) |
| `ramp` düğümünü geçiş için kullanma | 1.6.8'de denetim portları aralıksız → değer 0'a kırpılır, sessizlik (R42) |
| bir geçiş bitmeden sessizleşen zinciri yeniden yükleme; bekleyen istekleri birleştir (en sonuncu kazanır) | hâlâ duyulan zincirin belleği sıfırlanır → tık |
| açılışta etkin zinciri PipeWire'dan OKU (`sum:Gain 2 > 0,5` → B) ve ilk yüklemeden önce karışımı ona SABİTLE | süreç yarı geçişte öldüyse iki zincir de duyulur; sabitlemeden yükleme = tık (U68) |
| otomatik düzeltme = **üst katman**; kullanıcı profiline/geçmişine yazma; elle dokunuş otomasyonu askıya alır | profil kirlenir, kullanıcı ayarını kaybeder |
| kalıcı `pw-cli` oturumunu `quit\n` ile kapat — stdin'i kapatmak YETMEZ | 1.6.8 stdin EOF'ta çıkmaz, R durumunda döner (%20+ çekirdek, yetim kalır) (R46) |
| ebeveynle ölme: `setpriv --pdeathsig TERM -- cmd`, ama çocuğu **uzun ömürlü tek bir iş parçacığından** doğur | PDEATHSIG fork eden İŞ PARÇACIĞI ölünce tetiklenir → HTTP istek iş parçacığından doğan çocuk istek bitince ölür |
| tık ölçümü null sink'te: kaydı `node.autoconnect=false` + monitör portlarına ELLE `pw-link`; yüksek geçiren artıkta kaydın İLK penceresini dışla | smart filter monitör yakalamayı filtre girişine çeker (R17); süzgecin başlangıç tepkisi tık sanılır (E24) |
| otomasyonun CPU'sunu önce ÖLÇ (süreç + çocuk CPU zamanı, 30 sn); darboğaz genelde kare başına FFT/true-peak — yalnız otomasyon dinliyorsa tek dokunuş + istek anında FFT | ölçülen: %15 → %2,3 (R45); `nice`/`CPUQuota` işi azaltmaz |

## Common Mistakes

| hata | gerçek |
|---|---|
| "module-switch-on-connect eski PulseAudio tarifi" | pipewire-pulse onu uygular; kaynak: `module-switch-on-connect.c` (PCI/sanal hariç) — çalışıyor, ölçüldü |
| `bluez5.enable-sbc-xq` + codec sırası "LDAC>aptX>AAC>SBC-XQ" | TWS kulaklıkta SBC-XQ (~504 kbps) paket atlayabilir; karar link-test ile |
| codec'i `pactl` satırından okuyup bitrate'i varsaymak | kulaklık konfigürasyonu kendisi seçer (ör. AAC 262144 bps, vbr=1 → ~17 kHz kesim); baytları oku |
| EQ'yu yeni bir "sink" yapıp varsayılanı değiştirmek | smart filter varsayılanı değiştirmez, yalnız hedef cihaza uygulanır |
| ffmpeg SBC ile SBC-XQ ölçmek | ffmpeg kanal modu/alt-bant seçtirmez → `libsbc` ctypes |
| sink monitörünü kaydedip EQ'yu doğrulamak | smart filter monitör yakalamayı filtre GİRİŞİNE çeker → `node.autoconnect=false` + `pw-link <sink>:monitor_FL …` |
| laik kullanıcıya eşit-yükseklik testi | anlaşılmadı (9/10 "tavan"); canlı tercih ayarı + veri kalite kapısı |
| `filter.smart` anahtarlarını `node.properties`'e koymak | yalnız `capture.props`; aksi hâlde filtre bağlanmaz, hata da vermez |
| katsayıyı 5–10 adımda interpolasyonla "tıksız" değiştirmek | 1.6.8'de her adım belleği sıfırlar → tık sayısı artar; A/B zincir tek yol |
| sohbete yazılan sudo şifresini kullanmak | kullanma, değiştirmesini öner; root adımını betik olarak ver (`tools/btmon-capture.sh`) |

## Implementation
Araçlar ve testler repo'da; `bin/bta --help` tüm komutları listeler. Hata/çözüm tablosu: `lessons/errors.md` (E1–E26),
kanıtlanmış yollar: `lessons/golden-paths.md`, tuhaflıklar: `lessons/edge-cases.md`. Kulaklık/makine profilleri:
`docs/profiles/` · katman belgeleri: `docs/layers/` · belge merkezi: `docs/README.md`. Başka makine/kulaklık: repo'yu kopyala, `ln -s <repo>/skill/bt-audio-hifi ~/.claude/skills/`,
`BTA_DEVICE=<MAC> bin/bta status` ile başla (araç yoksa Quick Reference'daki çıplak komutlar yeterli).
