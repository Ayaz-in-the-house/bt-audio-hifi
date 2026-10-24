# L4 — Ses sunucusu: PipeWire 1.6.8 + WirePlumber 0.5.14 (graf, smart filter, resampler)

> Katman haritası: [00-overview](00-overview.md) · altı: [L3 Linux](L3-linux-os.md) · üstü: [L5 bta yazılımı](L5-bta-software.md) ·
> bulgular R17, R33, R42, R43: [findings](../research/findings.md)
>
> Son doğrulama: 2026-09-28 (`pactl list sinks short`: `effect_input.bta_console` RUNNING → `bluez_output.…` RUNNING)

## Rol

Uygulamaların sesini kulaklığa taşıyan graf. EQ, crossfeed, genişlik ve tıksız geçiş bu katmanda **gerçekten** çalışır;
bizim yazılımımız yalnız parametre yazar.

## Durum — ses yolu

```
uygulama (Zen 48 kHz F32) ─► effect_input.bta_console  ← WirePlumber smart filter: hedef = bluez_output.<MAC>
                              │ copyL/copyR
                              ├─ zincir A: pre·denge → eq1…eq10 (bq_raw) → hi/lo → mix(genişlik/crossfeed)
                              └─ zincir B: (aynısı)
                              sumL/sumR (mixer: Gain 1 = A, Gain 2 = B)
                           ─► effect_output.bta_console ─► bluez_output.<MAC> (AAC/SBC encoder) ─► radyo
```

| öğe | değer | kanıt |
|---|---|---|
| graf şablonu | `console.render_graph_ab` → `~/.config/pipewire/filter-chain.conf.d/60-bta-console.conf` | T-L30, T-L32, T-L33 |
| model ↔ ürün | null sink'te iki kanal ±0,001 dB (eşik 0,05) | T-L32 |
| geçiş | yeni durum SESSİZ zincire, toplama kazançları 12 ms adımla (elle 40 ms, otomasyon 1,5 sn) | U57, T-L39, T-L41 |
| resampler | kalite 10 (varsayılan 4: 44,1 kHz'de 19,5 kHz −8 dB idi) | F4, T-L21/22 |
| kopmada varsayılan çıkış | kulaklık geri gelir (switch-on-connect, `^alsa_|hdmi` hariç) | T-L13 |

### PipeWire sınırları (ölçülmüş — bu katmanın tuzakları)

| kod | sınır | sonucu |
|---|---|---|
| R33 | `bq_raw` ve tüm biquad'lar HER parametre güncellemesinde belleğini sıfırlar (`plugin_builtin.c:322`) | doğrudan canlı güncelleme = tık (−46 dBFS) → A/B zincir zorunlu |
| R42 | `ramp` düğümünün denetim portları aralıksız → değer 0'a kırpılır | geçiş `mixer` kazançlarıyla yapılır (mixer yumuşatmaz → küçük adım) |
| R43 | A/B geçişte 5 güncellemede ≈1 küçük artık (−68…−88 dBFS), B yüklemeleriyle eşleşiyor | duyulmaz; kök neden AÇIK |
| R17 | smart filter, hedefi monitörleyen kaydı da filtre GİRİŞİNE çeker | ölçüm/analizör monitör portlarına ELLE bağlanır |
| — | `pw-cli` 1.6.8 stdin EOF'ta çıkmaz, döner (E23) | kalıcı oturum `quit` ile kapanır |

## Aygıt kapsamı

**Soru (kullanıcı, 2026-09-27): "Bu proje tüm çıkış aygıtlarını yönetebilir mi, yoksa sadece bu kulaklığa mı özel?"**

**Cevap (koddan kanıtlı):** EQ/uzay/otomasyon grafı WirePlumber *smart filter* olarak **tek bir sink'e** bağlanır:
`filter.smart.target = { media.class = "Audio/Sink" device.api = "bluez5" node.description = "<kulaklık adı>" }`
(`console.render_graph_ab`, E29/U72 — 2026-10-15'e kadar `node.name = bluez_output.<MAC>` idi; yeniden eşleşmede MAC
değişti, filtre sessizce devre dışı kaldı). Kulaklık `identity.choose` ile seçilir: bilinen MAC > aynı ad > kulaklık
biçimli; hoparlör asla. Kimlik önbelleği `~/.config/bt-audio-hifi/device.json` (ad + görülen MAC'ler). WP hedefi birebir
eşler (regex yok); hedef yazılı ama eşleşmiyorsa filtre HİÇ kullanılmaz → `bta check` T-L25 bunu yakalar.

| çıkış | bugün | not |
|---|---|---|
| bu kulaklık (Solix Nexus) | ✅ tam destek, ölçülmüş | tüm testler |
| **başka bir Bluetooth kulaklık** (A2DP) | ✅ çalışır — kurulum/konsol bağlı olanı algılar | ölçüm + kulaklık kartı yok; koruma eşikleri bu kulaklıktan; codec yetenekleri farklı olabilir |
| aynı anda iki BT kulaklık | ❌ tek hedef | gri |
| dizüstü hoparlörü, HDMI, USB dock (bu makinede 6 sink) | ❌ EQ UYGULANMAZ (bilerek: smart filter hedefi değil) | gri — aşağıya bak |
| kablolu kulaklık / USB DAC | ❌ | gri |

**Neden tek aygıt:** EQ bir kulaklığın *yanıtını* düzeltir; aynı EQ hoparlörde yanlış olur. Smart filter bu yüzden
hedefli: kulaklığı çıkarınca hoparlörden **ham** ses gelir (istenen davranış).

**Genişletme yolu (gri, tasarım notu):** aygıt başına profil haritası — `devices.json: {sink adı → profil}`, her hedef
için ayrı smart filter düğümü (`node_suffix` zaten parametrik: `render_graph_ab(..., node_suffix=…)`), konsolda aygıt
seçici. Koruma eşikleri ve codec uyarıları aygıt kartından okunmalı (bugün bu kulaklığa sabit).

## Değişkenler

| değişken | değer | nerede |
|---|---|---|
| `filter.smart.target` | `bluez_output.<MAC>` | üretilmiş graf |
| düğüm adları | `effect_input.bta_console` / `effect_output.bta_console` | graf |
| örnekleme hızı / kuantum | 48 kHz / 1024 | PipeWire varsayılanı |
| `resample.quality` | 10 | `60-bta-resample.conf` (istemci + pulse) |
| canlı parametreler | `eqAL_1:b0`… `sumL:Gain 1/2` | `pw-cli set-param <id> Props …` (yalnız `Crossfader`) |

## Gri alanlar

Çok aygıt (yukarıda) · 3B/HRTF (`pipewire-module-filter-chain-sofa` paketi + SOFA veri seti — [USER-DECISIONS §3](../USER-DECISIONS.md#3-3b--hrtf-paketi)) ·
kafa takibi (sensör yok) · uygulama başına EQ (smart filter sink başına) · R43 kök nedeni.

## Testler

T-L30 (smart filter ürün katmanı) · T-L32/T-L33 (tam stereo graf, yol) · T-L34/T-L35 (analizör, salt-okuma) ·
T-L39/T-L41 (tıksız geçiş) · T-L21/T-L22 (resampler) · T-L13 (varsayılan çıkış) · U57 (graf yapısı).

## Nasıl ölçülür

```bash
pactl list sinks short                               # hangi sink RUNNING, hedef hangisi
pw-dump | python3 -c 'import json,sys; [print(o["info"]["props"]["node.name"]) for o in json.load(sys.stdin) if o.get("type")=="PipeWire:Interface:Node" and "bta" in o["info"]["props"].get("node.name","")]'
pw-link -l | grep -A2 bta_console                    # bağ yapısı
python3 -c 'from btaudio import consoleverify; print(consoleverify.verify())'    # null sink ürün doğrulaması (kulaklığa dokunmaz)
```
