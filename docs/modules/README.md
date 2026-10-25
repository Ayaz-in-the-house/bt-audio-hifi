# Modül dizini (üretilmiş)

> `tools/gen-docs.py` üretir; U67 bayatlığı yakalar. Katmanların anlamı: [ARCHITECTURE](../ARCHITECTURE.md) · [L5 yazılım katmanı](../layers/L5-bta-software.md).

## domain

| modül | rol | satır |
|---|---|---|
| [`analysis`](analysis.md) | Encoder/resampler kalite metrikleri | 70 |
| [`autoctl`](autoctl.md) | APC (otomatik profil) + ADL (canlı uyarlama) karar mantığı | 137 |
| [`bass`](bass.md) | Bas analizi: eşleştirme → kulakta yanıt → EQ tasarımı (F8) | 93 |
| [`codecs`](codecs.md) | A2DP codec bayt çözücüleri (AAC/SBC) | 124 |
| [`console`](console.md) | Konsol durumu, sanitize, stereo model, hazır tarzlar, A/B graf üretimi, koruma uyarıları | 778 |
| [`dsp`](dsp.md) | RBJ biquad katsayıları + frekans yanıtı (numpy) | 72 |
| [`eqconf`](eqconf.md) | EQ tasarımı → filter-chain config metni | 89 |
| [`features`](features.md) | Müzik karakteri öznitelikleri (bölge fazlası, karakter etiketleri) | 50 |
| [`history`](history.md) | Sürüm yığını (geri/ileri al) + günlük yeniden oynatma + zaman çizelgesi | 126 |
| [`loudness`](loudness.md) | Eşit-yükseklik (ISO 226) ile kulakta bas yanıtı (F8) | 113 |
| [`presetfit`](presetfit.md) | Grafik EQ presetlerini parametrik EQ'ya uydurma | 70 |
| [`profiles`](profiles.md) | Profil deposu mantığı: kaydet/kilit/çalışma kopyası/çöp/içe-dışa aktar | 288 |
| [`state`](state.md) | Snapshot diff, WirePlumber durum ayrıştırma, config manifesti | 88 |
| [`tuner`](tuner.md) | Eski canlı bas ayarlayıcı mantığı (PRD-BTA01 F8 v2) | 65 |

## application

| modül | rol | satır |
|---|---|---|
| [`abxsession`](abxsession.md) | Konsoldaki kör ABX testi: klip (kendi müziğinden), 12 deneme, sonuç, tercih, uygula/iptal | 197 |
| [`autoengine`](autoengine.md) | Otomasyon motoru: analizör → öznitelik/sınıflayıcı → APC/ADL → Session | 281 |
| [`consoleserver`](consoleserver.md) | Session (tek durum sahibi) + yerel HTTP API + güvenlik kapıları | 852 |
| [`tunerserver`](tunerserver.md) | Eski bas ayarlayıcı sunucusu + PwApplier (pw-cli ile canlı yazım) | 162 |

## infrastructure

| modül | rol | satır |
|---|---|---|
| [`analyzer`](analyzer.md) | Canlı analizör: pw-record dokunuşları, 1/6 okt spektrum, metre, SSE, hafif mod | 477 |
| [`bench`](bench.md) | Encoder benchmark (fdk-aac / libsbc) | 175 |
| [`btmon`](btmon.md) | btmon/RSSI kaydı ayrıştırma (root kaydı kullanıcıdan) | 73 |
| [`classifier`](classifier.md) | YAMNet ONNX tür/enstrüman sınıflayıcı (sha256 kilitli, yerel) | 118 |
| [`collect`](collect.md) | Canlı sistem durumu toplayıcı (salt-okuma: pactl, bluez, systemd) | 284 |
| [`crossfade`](crossfade.md) | Tıksız A/B geçiş sıralayıcı + kalıcı pw-cli oturumu | 174 |
| [`identity`](identity.md) | Cihaz kimliği: ad + bilinen MAC kümesi önbelleği, kulaklık seçici, MAC'siz filtre hedefi (U72) | 105 |
| [`journal`](journal.md) | Arka plan disk yazıcı (ekle-yalnız günlük + atomik profil yazımı) | 159 |
| [`link`](link.md) | Bağlantı sağlığı (bitrate düşürme olayları) | 95 |
| [`paths`](paths.md) | XDG kullanıcı verisi yerleşimi + göç | 92 |
| [`procs`](procs.md) | Alt süreç doğurma: ebeveynle ölen çocuklar (E23) | 62 |
| [`resample`](resample.md) | Resampler ölçümü + geçici null sink yardımcıları | 111 |
| [`sbclib`](sbclib.md) | libsbc ctypes sarmalayıcı (SBC-XQ ölçümü) | 95 |
| [`tones`](tones.md) | Oturma testi tonları (pw-play) | 58 |

## ölçüm

| modül | rol | satır |
|---|---|---|
| [`abx`](abx.md) | Kör ABX dinleme testi (kullanıcı kararı için) | 106 |
| [`analyzerverify`](analyzerverify.md) | T-L34: analizörün ürün katmanında doğrulaması | 80 |
| [`consoleverify`](consoleverify.md) | T-L32: tam stereo konsol grafı null sink'te model ±0,05 dB | 69 |
| [`eqverify`](eqverify.md) | T-L30: smart filter EQ'sunun ürün katmanında doğrulanması | 130 |
| [`zipperverify`](zipperverify.md) | D0/T-L39/T-L41: canlı güncelleme tık ölçümü (null sink) | 164 |

## cli

| modül | rol | satır |
|---|---|---|
| [`cli`](cli.md) | `bta` komutları (durum, kurulum, konsol, ölçümler, model) | 857 |
