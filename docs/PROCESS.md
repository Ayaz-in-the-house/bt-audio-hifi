# Süreç — Bluetooth kulaklıkta hi-fi (2026-09-27, tek oturum)

Bu belge **ne denendiğini, neyin tuttuğunu, neyin tutmadığını ve nedenini** kronolojik anlatır. Kurallar/komutlar
için `skill/bt-audio-hifi/SKILL.md`; hata tablosu `docs/lessons/errors.md` (E1–E26); kanıt tablosu
`docs/research/findings.md`.

## Faz 0 — Şikâyet ve ilk ölçüm (≈5 dk)
- Şikâyet: "kalite kötü, paket sorunu mu?" → **tahmin yok, ölçüm**: `wpctl status` akışı `output_MONO` gösterdi.
- Kök neden: kart **HFP (mSBC mono 16 kHz)** profilinde; WirePlumber bunu `~/.local/state/wireplumber/default-profile`'a
  kalıcı yazmış + `bluetooth.autoswitch-to-headset-profile=true`.
- Düzeltme: `pactl set-card-profile … a2dp-sink` + `wpctl settings --save …autoswitch… false`. Sonuç AAC stereo 48 kHz.
- **Ders:** "Bluetooth sesi kötü" şikâyetlerinin çoğu codec değil **profil** sorunudur; önce profil.

## Faz 1 — Proje, test planı, kalıcılık (F0/F1)
- Repo + PRD-BTA01 + TEST-PLAN (test noktaları plan yapılır yapılmaz, beklenen sonuç + gerekçe ile).
- `bta` CLI: `status/check/snapshot/diff` → her durum geçişi JSON snapshot + diff (`state/snapshots/`).
- Headful yeniden bağlanma testi **gerçek bir yan etki** yakaladı: kopmada bir GNOME istemcisi varsayılan çıkışı
  hoparlöre yazıyor, geri gelince ses dönmüyor (E4). Çözüm: `module-switch-on-connect` (blocklist `^alsa_|hdmi`).
  Kanıt: `pw-metadata -m` ms damgaları.
- Yan kusurlar: SPA JSON'da iki nokta üst üstesiz `{ "name""x" }` (E5), TWS art arda reconnect sonrası ~40 sn
  page-timeout (E6), testin ses yönlendirmesini bozması (E8 → setUp/tearDown).

## Faz 2 — Bağlantı sağlığı + codec kararı (F6/F2)
- `bta link-test`: WirePlumber `spa.bluez5.sink.media` konusunu geçici debug'a alıp `reduce bitpool` (=atlanan paket)
  sayar — sudo'suz. AAC 60/90 sn **CLEAN**.
- Benchmark: aynı `libfdk-aac` (ffmpeg ↔ PipeWire aynı .so) + ctypes `libsbc`, CC0 Brahms. İlk koşuda ffmpeg SBC
  yanıltıcıydı (4 alt-bant seçmiş, E9) → libsbc'ye geçildi; formül gerçek kütüphaneyle çapraz doğrulandı (U17).
- Bulgular: AAC ~17 kHz'de kesiyor (kulaklığın `vbr=1` bayrağı PipeWire'ın 19,3 kHz dalını kapatıyor);
  **SBC-XQ bu bağlantıda DEGRADED** (13 atlama/90 sn) → elendi; AAC↔SBC kararı kör ABX'e (`bta abx`).
- **Ders:** yüksek bitrate codec'i bağlantı testi olmadan seçme; TWS kulaklıklar ikinci kulağa röle yapar.

## Faz 3 — Resampler (F4)
- Null sink üzerinde canlı ölçüm (kulaklık meşgul edilmedi): q4 44,1 kHz içerikte 19,5 kHz'i −8 dB kırpıyor;
  q10 düz, +%0,13 CPU → drop-in. Tarayıcı (Zen) sesi zaten 48k verdiği için etkilemez (dürüst kapsam notu).
- Teslimat zinciri kontrolü T-L24 ("kurulu ama etkin değil") eklendi; saniye hassasiyeti yanlış pozitifi (E10) düzeltildi.

## Faz 4 — Bas (F8): iki yöntem, biri başarısız
- v1: eşit-yükseklik eşleştirme + ISO 226 (IoSR ile doğrulandı). **Kullanıcı görevi anlamadı** (9/10 "tavan", E13).
  → Veri kalite kapısı (U28, gerçek dosya fixture) + yöntem değişikliği.
- v2: canlı tercih ayarı (3 kaydırıcı, müzikle). Filter-chain kontrolleri çalışırken değişir (ölçüldü +9,00 dB).
  İki gerçek UI kusuru testle yakalandı (E14 optimizasyon içinde yuvarlama, E15 kaydırıcı adımı).
- **Ders:** laik kullanıcıya psikoakustik görev verme; kendi müziğiyle anında duyulan ayar ver.

## Faz 5 — Profesyonel konsol (F9 / PRD-BTA02)
- Cartography haritası + 2 paralel araştırma ajanı; **ebeveyn doğrulaması** ajanın Harman CSV değerlerini yanlış
  aktardığını yakaladı (1 kHz +2,8 dedi, gerçek 0,0; bas rafı +7,6 dB) → cartography dersine işlendi.
- `bq_raw` kaynağı: katsayılar her blokta okunur → **filtre TİPİ dahil canlı** değişir (ölçüldü: 6 tip, ≤0,008 dB).
- bs2b crossfeed birinci dereceden → `bq_raw` ile **birebir** (bs2b.c formülleri, U32).
- Tam stereo graf (10 bant × 2 + bs2b + genişlik + denge + preamp) null sink'te modelle **±0,001 dB** (T-L32).
- UI: sashimi-ui (MIT, triage edildi, vendored) + SVG grafik (sürükle/tekerlek/çift tık), 11 hazır profil, profiller,
  geri al, A/B. Başsız E2E (T-U03) + görsel kontrol; bir kusur (hazır ayar seçimi) görselden yakalandı.
- Canlıda: `streams_to_sink` filtreleri takip etmiyordu → çalan uygulama görünmüyordu (koruma yanlış) → düzeltildi.

## Faz 6 — Konsol v2 (PRD-BTA03)
- Kullanıcı verisi repo dışına (XDG, kopyalayarak göç), 31 kaynaklı tarz (niyet testli), profil yönetimi, canlı analizör
  (ölçü aleti önce sayısal test, sonra null sink ürün testi), tasarım sözleşmesi + ölçülen kontrast, açık kaynak kapısı.

## Faz 7 — Otomatik ses zekâsı (PRD-BTA04)
- D1 çalışma kopyaları: istek yolu diske yazmaz (arka plan günlük), kalıcı geri/ileri al (E21: eski günlük karışması).
- Fizibilite ölçümü önce: canlı biquad güncellemesi TIK üretiyor (R33) → A/B zincir; `ramp` kullanılamaz (R42/E22) → mixer adımları.
- Otomasyon: tür tanıma yerel (YAMNet), APC/ADL saf karar mantığı (sahte saatle test), motor ince bağlayıcı; ADL **üst katman**.
- Maliyet ölçüldü (T-L40 %15) → hafif analizör → %2,3. Ölçüm sırasında yetim `pw-cli` (E23) ve sunucunun boşta
  kapanması (K19) bulundu — ikisi de sınıf olarak düzeltildi (tüm alt süreçler, tüm etkinlik kaynakları).
- T-L41 yanlış alarm verdi (E24): hipotezler sırayla ÖLÇÜLEREK çürütüldü (gecikme, parametre sızıntısı, yük) →
  kök neden ölçütün kendisi + analiz artefaktı.

## Faz 8 — Belgeler kapıya bağlandı (2026-09-28)
- Kullanıcı: "docs güncelliği çok kritik bir disiplin süreci". Ölçülen borç: çakışan test kimlikleri, planda olmayan
  30'a yakın test, bayat mimari (E25). Çözüm hatırlatma değil **test**: U67.
- Katman belgeleri (L1 kulaklık → L6 arayüz) aynı iskelet: Rol · Durum · Değişkenler · Gri alanlar · Testler · Nasıl ölçülür.
- Modül belgeleri kaynaktan üretilir (`tools/gen-docs.py`); açıklama = docstring (çekirdek API'ye 124 docstring eklendi).
- Kullanıcıya dönük açıklamalar araç çıktısına karşı doğrulanır (E26: ABX eşiği ve SBC iddiası hafızadan yanlış yazılmıştı).

## Çalışma kuralı (her iş için)
1. Ölç (`bta status/check`) → ilgili katman belgesini oku.
2. Plan → **test noktaları** (TEST-PLAN satırı: kimlik, beklenen, neden) KODDAN ÖNCE.
3. RED (testin kırmızı olduğunu gör; mümkünse mutasyonla testin yakaladığını kanıtla) → GREEN → REFACTOR.
4. Ürün katmanı kanıtı (null sink / canlı salt-okuma / headful gözlem) — kullanıcı dinliyorsa sesine ton karıştırma.
5. Belgeler: katman belgesi (durum/değişken/gri alan) + FEATURES + lessons + STATE-LOG + `python3 tools/gen-docs.py`.
6. Kapı: `tests/run.sh` rc=0 (U67 dahil) → commit (rc'ye bağlı, E18).

## Açık kalanlar (kullanıcıda)
Tam ve sade açıklama: [USER-DECISIONS](USER-DECISIONS.md) — kör ABX (AAC ↔ SBC) · root btmon/RSSI (yalnız kesilme
duyulursa) · HRTF paketi (kişisel tercih; kafa takibi yok) · otomatik modu açma.
