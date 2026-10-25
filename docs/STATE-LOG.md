# Durum günlüğü (state transitions)

Her satır ölçülmüş bir geçiştir; ayrıntı `state/snapshots/*.json` + `bta diff A B`.

| zaman (2026-09-27) | durum | geçiş | kanıt |
|---|---|---|---|
| ~18:50 | **S0** | HFP `headset-head-unit`, mSBC mono 16 kHz; WP kalıcı kaydı HFP; autoswitch=true | `state/backups/wireplumber-state-20260927-pre-session/` |
| ~18:55 | **S1** | elle: `a2dp-sink` (AAC 48k stereo) + `autoswitch=false (Saved)` | snapshot `…191312-S1-a2dp-aac-manual-fix` |
| 19:13 | S1b | T-L10 reconnect testi → aynı codec geri; **yan etki**: GNOME varsayılanı hoparlöre çevirdi (E4) | diff S1→S1b · `pw-metadata -m` |
| 19:19 | **S2 → F1** | `60-bta-switch-on-connect.conf` kuruldu, `pipewire-pulse` yeniden başladı | snapshot `…191929-S2-pre…` → `…192051-F1-complete`; T-L13 |
| 19:23 | F6.1 | bağlantı baz çizgisi AAC 60 sn CLEAN | `analysis/link-health/…F6.1-baseline-aac.json` |
| 19:3x | F2 | codec deneyleri (sbc_xq/sbc/aac arasında geçişler), sonunda **AAC**'e dönüldü | `analysis/link-health/*`, `analysis/F2-codec-decision.md` |
| 19:4x | **F4** | `60-bta-resample.conf` (client + pulse) KURULDU; pulse kısmı **yeniden başlatma bekliyor** (kullanıcı dinliyor) | snapshot `…194754-F4-pre-install`; T-L24 FAIL (bilinçli, bekleyen) |
| 19:5x | F5/F8 | EasyEffects 8.2.9 kuruldu + `flatpak mask` ile sabitlendi (çalıştırılmadı) | snapshot `F8-tools-ready` (`easyeffects.installed true, running false`) |
| — | F8 | bas eşleştirme ölçümü kullanıcıda; smart-filter EQ mekanizması null-sink'te ±0,01 dB doğrulandı | T-L30 |

Not: `other_bt_devices` M96BT1 klavyesi 19:4x–19:5x arasında listeden düştü — bu oturumun işlemleriyle ilgisi
yok (klavye uykusu); kayda geçirildi, müdahale edilmedi.
| 21:14 | K1 | kullanıcı "Kalıcı yap" → izlenen repo config'i yazıldı (C0'ın kanıtı) | `git diff` o an |
| ~21:45 | **C0** | kullanıcı verisi XDG'ye göç (kopya, sha: repo=generated=kurulu); repo config izlenmez | `ecd2d9a` |
| ~22:05 | C3 canlı | konsol v2 yeniden başlatıldı (açılış durumu = 21:14 kalıcı) | `/api/state` is_default=true |
| ~22:40 | **D1** canlı | konsol yeniden başlatıldı; CANLI durum `--initial` ile aktarıldı (ses değişmedi: bant1 +2,0 dB, crossfeed 700/8,0) | önce/sonra `/api/state` |

| zaman (2026-09-27 → 28; commit saatleri `git log`'dan) | durum | geçiş | kanıt |
|---|---|---|---|
| 23:12 | lisans | MIT (`LICENSE`, NOTICE) | `c01b850` |
| 23:21 | **D3–D5 canlı** | otomasyon motoru + /api/auto + model CLI; konsol yeni kodla yeniden başlatıldı (Özel 1, mod kapalı, durum birebir) | `7ab3681` · `/api/state` karşılaştırma True |
| 23:25 | D3–D5 arayüz | Otomatik sekmesi, tür etiketleri, otomatik eğri | `25cdc7d` · T-U05 |
| 23:33 | D3 performans | hafif analizör: otomasyon maliyeti %15 → %2,3; anlatım videosu = konuşma %82 | `9c48862` · T-L40/T-L42 |
| 23:41 | E23 | eski sunucunun yetim `pw-cli`'si (1 sa, %22) → PID ile sonlandırıldı | `ps` STAT R, PPID 1619 |
| 23:49 | **D6** + E23 düzeltmesi | /admin + procs.spawn; konsol yeniden başlatıldı; ikinci yetim (eski koddan) PID ile sonlandırıldı | `bb36260` · `pgrep pw-cli` tek |
| 23:51 | headful gözlem | canlı sunucuda görünür pencere: konsol + /admin (Özel 1: 46 sürüm, 52,9 KB), JS hatası 0, mod değişmedi | ekran görüntüsü (scratchpad) |
| 23:55 | **D7** | koruma uyarıları + oturma testi | `c7b327c` · T-L43 −24,00 dBFS 50,1 Hz |
| 00:03 | T-L41 | otomasyon güncelleme deseni tıksız (−83,9 dBFS); E24 | `1a949bb` |
| 00:16→ | **belgeler** | katman belgeleri L1–L6, FEATURES, USER-DECISIONS, docs hub, ARCHITECTURE yenilendi, modül belgeleri üretildi, U67 kapısı | bu commit |
| 09-28 | **PRD-BTA05 E1** | konsolda kör dinleme testi (kendi müziğinden klip, düğmeli deneme, otomasyon askısı, iptalde orijinal codec); T-L44 kullanıcı dinlerken bilerek atlandı (K10) | U69 U70 T-U08 |
| 10-15 19:50 | **E29 / U71–U72** | kulaklık kimliği MAC'ten bağımsız: filtre hedefi ad tabanlı, `device.json` önbelleği, açılışta bayat hedef göçü, T-L25; canlı sunucu 8766 göç etti, otomatik mod yeniden dinliyor. Açık: T-L04 (yeni kart için WP default-profile kaydı yok) | bu commit |
| 10-15 21:50 | **analiz + PRD-BTA06** | sohbet analizi kalıcı: üretici önerileri V1–V10 (`docs/research/vendor-recommendations.md`), süreklilik eksikleri (otomatik mod konsola bağlı ve 1 sa'te kapanıyor · bağımlılık listesi yok → filoda tam paket koşmuyor · konsol MAC'i açılışta donduruyor · T-L04), Solix uygulaması YOK (R47), SPP + MAC değişimi (R48), RACE riski (R49), ADL salınımı %11,6 çekirdek (R50/E31). Kullanıcı planı onayladı: G0 → G1 → G2 → G3 | bu commit |
| 10-15 22:00 | **G0 + G1** | ADL histerezis (E31: `pw-cli` %8,5 → %2,4) · `bta service install` → `bta-console.service` etkin (girişte başlar, boşta kapanmaz, tek örnek, port gaspı koruması E32). Yeniden başlatma artık `systemctl --user restart bta-console` (eski `--initial` yolu yalnız elle konsolda) | `cca9b32` `34d7d14` `44cf7da` |
| 10-15 22:05 | **G3 salt-okuma** | `bluez-deprecated` kuruldu (kullanıcı) — yan etkisi bluez güncellemesi + bluetooth.service yeniden başlatma, kulaklık koptu (E34), `bluetoothctl connect` ile döndü. Çip **Bluetrum** (R51), SPP RFCOMM 1 (R52). Komut gönderen adım yok | bu commit |
| 10-15 22:16 | **G3 dinleme** | SPP kanal 1'e bağlanıldı, 60 sn yalnız dinlendi: 0 bayt (R53). Sıradaki: AB Link (iOS) kulaklığı tanıyor mu — kullanıcı telefonda dener. Komut gönderen adım YOK | bu commit |
| 10-24 19:16 | **U78 hi-fi dengeli ses** | Ölçüm: otomatik mod (APC+ADL) bas takviyesini +15,3 dB'ye (20–100 Hz) + 416 Hz +6,6 dB tümseğe taşımıştı → profil kuralı (> +12 dB DİKKAT) aşılıyordu. Otomatik mod KAPALI, tarz **Harman bas (kulakiçi 2019)** (profil belgesindeki önerilen başlangıç) açılışta kullan; preamp −9,0 dB; ses yükseltme = +9 dB (preamp'i dengeler → orta bölge kaynakla aynı seviye, sınırlayıcı yalnız bas taşmasında). Ölçüm 15 sn: kaynak RMS −14,9 / tepe −2,5 → çıkış RMS −15,7 / tepe −2,7 dBFS, sınırlama 0 örnek. Panelde canlı 'Ses +dB' kaydırıcısı (0–15) | bu commit |
| 10-25 10:30 | **açık kaynak yayını** | Ayaz-in-the-house/bt-audio-hifi: README'ye ikon + ekran görüntüleri (PR #1), README İngilizce + `README.tr.md` dil bağlantısıyla + yol haritası (PR #2). Yayın ağacı `git-zone ship` hattından, yalnız HEAD | `cd6f0e9` `b167ca9` `88f2079` |
| 10-25 16:00 | **defter onarımı (E35)** | `STATE-LOG.md` ve `lessons/errors.md` 14af43c'de ezilmişti → geri yüklendi (E1–E35, 44 satır); U79 kapısı eklendi | bu commit |

## Sıradaki (kullanıcı müsait olduğunda — 2026-10-25 itibarıyla iş DURDURULDU)

Ayrıntılı tablo: [README.tr.md § Yol haritası](../README.tr.md#yol-haritası--henüz-incelenmemiş-katmanlar).

1. **L1/L2 katman bölünmesi** — L1a akustik · **L1b çip/firmware/DSP/DAC/ANC (ilk)** · L1c TWS · L2a radyo/LMP · L2b L2CAP/AVDTP · L2c A2DP/codec; her biri aynı şablonla (seçenekler · durumlar · değişkenler · ölçüm yöntemi).
2. **Kör ABX** (`bta abx`) — AAC ↔ SBC kararı kullanıcıda.
3. **btmon radyo kaydı** — `sudo bash tools/btmon-capture.sh 60` → `bta btmon-report` (root: kullanıcı koşar).
4. **G3 devamı** — AB Link (iOS) kulaklığı tanıyor mu (kullanıcı telefonda dener).
5. Açık kalan: T-L04 (yeni kart için WP default-profile kaydı yok) · `pipewire-pulse` yeniden başlatma (q10 pulse kısmı, T-L24) — kullanıcı dinlerken YAPMA.
