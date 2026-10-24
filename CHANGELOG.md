# Changelog

## 0.4.0 — 2026-09-28 (PRD-BTA04 tamamlandı)
- **Lisans MIT.**
- **D2 tıksız geçiş:** A/B zincirli graf; yeni durum sessiz zincire, toplama kazançları 12 ms adımlarla (R42: `ramp`
  kullanılamaz); T-L39 (elle) + T-L41 (otomasyon deseni, −83,9 dBFS).
- **D3–D5 otomasyon:** yerel YAMNet tür/enstrüman tanıma (sha256 kilitli, `bta model fetch|verify`), otomatik profil
  (APC: tür → etiketli profil ya da tarz), canlı uyarlama (ADL: sınırlı, yavaş, konuşmada dokunmaz, **üst katman** —
  profile yazılmaz), Otomatik sekmesi, tür etiketleri. Hafif analizör modu: otomasyon maliyeti %2,3 çekirdek (T-L40).
- **D6 yönetim sayfası** `/admin`: sürüm zaman çizelgesi + satır satır farklar, yıkıcı olmayan sürüme dönüş, çöp kutusu,
  toplu dışa/içe aktarma (bta-bundle/1), otomasyon paneli.
- **D7:** sürücü koruma + codec farkındalığı uyarıları (bas > +12 dB, 20 Hz altı, AAC'de 17 kHz üstü), kulak tıkacı
  oturma testi.
- **E23 düzeltmesi:** yetim `pw-cli` (EOF'ta dönüyordu) — tüm alt süreçler ebeveynle ölür (`procs.spawn`).
- **Belgeler:** katman belgeleri (kulaklık → Bluetooth → Linux → PipeWire → yazılım → arayüz, gri alanlar dahil),
  özellik kataloğu, sade Türkçe kararlar, modül belgeleri kaynaktan üretilir; **U67 belge güncelliği kapısı**.
- Testler: birim 178 · tarayıcı 6 · canlı T-L40…T-L43.

## 0.4.0-dev — 2026-09-27 (PRD-BTA04 ara sürüm)
- **D1 Özel çalışma profilleri:** hazır tarz / kilitli profil üzerinde ilk dokunuş "Özel N" açar; ana kaynak asla değişmez;
  her değişiklik arka planda kalıcı (istek yolu diske dokunmaz), sunucu tarafı kalıcı geri/ileri al, yanlış tarz tıklaması
  geri alınır. Harman bas tarzı +7,5 → **+9,0 dB** (R28: veriden tam uydurma).
- Bulgu R33: PipeWire biquad'ları her güncellemede belleği sıfırlar → tık; A/B tıksız geçiş motoru (D2) planlandı.

## 0.3.0 — 2026-09-27 (PRD-BTA03)
- Konsol v2: production-grade arayüz (DESIGN.md), 31 tarz (kaynaklı/etiketli, niyet testli), profil yönetimi
  (kaydet/çakışma/yeniden adlandır/çoğalt/dışa-içe aktar/çöp), canlı analizör + metre, XDG kullanıcı verisi,
  açık kaynak kapısı (oss-audit, NOTICE), cihaz otomatik algılama. sashimi-ui kaldırıldı.

## 0.2.0 — 2026-09-27
- F9 profesyonel konsol (PRD-BTA02): 10 bant stereo PEQ (bq_raw, tip dahil canlı), birebir bs2b crossfeed, genişlik,
  denge, en-kötü-durum preamp, 11 hazır profil (kaynaklı), kullanıcı profilleri, geri al/ileri al, A/B, kalıcı yap.
  Doğrulama: null sink ±0,001 dB (T-L32), başsız E2E (T-U03), canlı yol (T-L33).
- sashimi-ui 2.1.0 CSS vendored (MIT, triage: script yok, dış istek yok).
- `streams_to_sink` smart filtreleri takip eder (apply-pending koruması doğru).
- Bas v2 canlı ayarlayıcı + veri kalite kapısı (E13). Skill `skill/bt-audio-hifi` + PROCESS + profiller.

## 0.1.0 — 2026-09-27
- F1: profil kalıcılığı (A2DP), autoswitch kapalı, **switch-on-connect** (GNOME'un kopmada varsayılanı hoparlöre
  çevirmesine karşı), reconnect headful testleri (T-L10/13).
- F2: encoder benchmark (aynı libfdk-aac + ctypes libsbc, CC0 Brahms), bağlantı testi; **SBC-XQ elendi** (DEGRADED);
  AAC ↔ SBC kararı kör ABX'e (`bta abx`) bırakıldı, varsayılan AAC.
- F4: resampler canlı ölçümü (null sink) → q10 drop-in'leri; teslimat zinciri kontrolü T-L24.
- F5/F8: smart filter-chain EQ üreticisi + ürün katmanı doğrulaması (±0,01 dB); EasyEffects 8.2.9 kurulu/sabit;
  kulakta bas eşleştirme sayfası + ISO 226 modeli + EQ tasarımcısı.
- F6: `bta link-test` (sudo'suz paket atlama sayacı), kullanıcı-çalıştırmalı btmon/RSSI betiği + ayrıştırıcı.
- Araçlar: `bta` CLI (status/check/snapshot/diff/install/uninstall/codec/link-test/bench/abx/bass-*/btmon-report).
