# L2 — Bluetooth radyo + BlueZ + codec

> Katman haritası: [00-overview](00-overview.md) · altı: [L1 kulaklık](L1-headphone.md) · üstü: [L3 Linux](L3-linux-os.md) ·
> kararlar: [USER-DECISIONS](../USER-DECISIONS.md) · bulgular R1–R21, R41: [findings](../research/findings.md)
>
> Son doğrulama: 2026-09-28 (`bta check` 7/7 — codec=aac, profil=a2dp-sink, autoswitch=false)

## Rol

Sesi kablosuz taşır. Bu katmanda **kalite iki yerde kaybolur**: (1) yanlış profil (HFP: mono, 16 kHz — projenin çıkış
noktası olan kök neden), (2) codec sıkıştırması (AAC ~17 kHz üstünü keser; SBC başka tür artık bırakır).

## Durum

| öğe | değer | kanıt |
|---|---|---|
| adaptör | Intel AX210 (Wi-Fi 6E + Bluetooth kombo kart; aynı antenleri paylaşır) | `lspci` |
| BlueZ | 5.87 | `bluetoothctl --version` |
| profil | **A2DP sink** (kalıcı: WirePlumber `default-profile`) | T-L01, T-L04 |
| HFP'ye otomatik geçiş | **kapalı** (`bluetooth.autoswitch-to-headset-profile=false`, kayıtlı) | T-L05, T-L11 |
| codec | **AAC** 48 kHz 2 kanal vbr, ~262 kbps (kulaklık seçer) | T-L02, U01 |
| alternatif | SBC 48 kHz joint bitpool 53 (~357 kbps) — bağlantıda TEMİZ | `bta link-test` |
| elenen | SBC-XQ (dual bitpool 39, ~504 kbps) — bu bağlantıda 90 sn'de 13 paket atlama → DEGRADED | F6, U15 |
| yeniden bağlanma | art arda kopma/bağlanma sonrası ~40 sn page-timeout | E6 |

## Değişkenler

| değişken | değer | nerede |
|---|---|---|
| kart profili | `a2dp-sink` | `~/.local/state/wireplumber/default-profile` |
| autoswitch | `false (Saved)` | `wpctl settings --save …` |
| codec | `aac` (karar: `decision.json`) | `bta codec aac\|sbc` |
| SBC bitpool | ≤ 53 (kulaklık sınırı) | A2DP anlaşması |
| AAC bitrate | kulaklık seçer (262 144 bps gözlendi) | A2DP anlaşması — değiştirilemez |

## Gri alanlar

| alan | durum | ne gerekir |
|---|---|---|
| **AAC mı SBC mi** (kulakla) | ölçümle ikisi de temiz; duyulur fark kör ABX ile karar verilecek | kullanıcı: `bin/bta abx aac sbc` — [USER-DECISIONS §1](../USER-DECISIONS.md#1-aac-mı-sbc-mi) |
| radyo katmanı (RSSI, yeniden iletim) | araç hazır, kayıt alınmadı | root: `sudo bash tools/btmon-capture.sh 60` — [§2](../USER-DECISIONS.md#2-radyo-ölçümü-btmon-sudo-ister) |
| LE Audio / LC3 | kulaklık desteklemiyor | farklı kulaklık |
| aptX / LDAC | kulaklık desteklemiyor | farklı kulaklık |
| Wi-Fi ↔ BT birlikte yaşama (AX210 kombo) | ölçülmedi | btmon kaydı + Wi-Fi yükü altında link-test |

## Testler

U01–U06 (codec bayt çözücüler) · U15 (bağlantı sağlığı ayrıştırıcı) · U16/U17 (encoder/libsbc) · U18 + T-L14 (ABX) ·
U27 (btmon ayrıştırıcı) · T-L01…T-L06, T-L10, T-L11 · T-L50 (bağlantı sağlığı).

## Nasıl ölçülür

```bash
bin/bta status                      # transport baytları çözülmüş hâliyle
bin/bta link-test 60                # paket atlama / bitrate düşürme (sudo'suz)
bin/bta bench                       # AAC / SBC / SBC-XQ / HFP kalite karşılaştırması (aynı kitaplıklar)
bin/bta abx aac sbc                 # kör dinleme (etkileşimli, kendi terminalinde)
```
