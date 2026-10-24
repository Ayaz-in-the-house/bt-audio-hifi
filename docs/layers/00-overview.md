# Katmanlar — genel bakış

> Her katmanın belgesi aynı iskeleti taşır (U67 zorlar): **Rol · Durum · Değişkenler · Gri alanlar · Testler · Nasıl ölçülür**
> + "Son doğrulama" tarihi. Gri alan = henüz girilmemiş/geliştirilmemiş ya da ölçülememiş bölge — gizlenmez, yazılır.

```
 L7  kullanıcı            kulak, tercih, karar (ABX, oturma, otomatik mod açık/kapalı)
 ─────────────────────────────────────────────────────────────────────────────────────
 L6  tarayıcı + arayüz    Zen (ses kaynağı, 48 kHz F32) · konsol / yönetim sayfaları      → L6-browser-ui.md
 L5  bta yazılımı         Session · otomasyon · geçiş · günlük · analizör · ölçüm araçları → L5-bta-software.md
 L4  ses sunucusu         PipeWire 1.6.8 + WirePlumber 0.5.14: smart filter A/B grafı     → L4-pipewire.md
 L3  işletim sistemi      Fedora 44, systemd kullanıcı servisleri, XDG dosya yerleşimi     → L3-linux-os.md
 L2  Bluetooth            AX210 · BlueZ 5.87 · A2DP · AAC/SBC codec                         → L2-bluetooth.md
 L1  kulaklık             Solix Nexus ANC: 12 mm sürücü, kulak tıkacı oturması, ANC         → L1-headphone.md
```

| katman | belge | "iyi" ne demek (ölçüt) | en önemli gri alan |
|---|---|---|---|
| L1 | [kulaklık](L1-headphone.md) | A2DP'de, iyi oturmuş, sürücü sınırları içinde | frekans yanıtı / malzeme bilinmiyor |
| L2 | [Bluetooth](L2-bluetooth.md) | A2DP + AAC/SBC temiz bağlantı (paket atlama 0) | AAC↔SBC kulakla karar; radyo kaydı |
| L3 | [Linux](L3-linux-os.md) | servisler aktif, config sapması yok, yetim süreç yok | diğer dağıtımlar |
| L4 | [PipeWire](L4-pipewire.md) | graf model ile ±0,05 dB, geçişler tıksız | **çok aygıt**, HRTF, R43 |
| L5 | [bta yazılımı](L5-bta-software.md) | tüm testler yeşil, istek yolu diske yazmaz, kullanıcı verisi kaybolmaz | aygıt başına profil, gelişmiş uzay |
| L6 | [tarayıcı/arayüz](L6-browser-ui.md) | JS hatası 0, AA kontrast, 390 px taşmasız | çok dilli arayüz |

**Bir şikâyet hangi katmanda?** "Ses kısık/bas yok" → önce L1 (oturma testi), sonra L5 (EQ). "Cızırtı/kesilme" → L2
(`bta link-test`, radyo kaydı). "Tık sesi ayar değişince" → L4 (R33/A/B). "Sayfa açılmıyor" → L6 → L5 (`/api/state`).
"Hoparlörden EQ'suz geliyor" → L4 aygıt kapsamı (bilerek).
