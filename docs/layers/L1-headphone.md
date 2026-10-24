# L1 — Kulaklık (donanım): Solix Nexus ANC

> Katman haritası: [00-overview](00-overview.md) · üstü: [L2 Bluetooth](L2-bluetooth.md) · kanıt defteri:
> [findings R38–R41](../research/findings.md) · cihaz kartı: [profiles/headphone-solix-nexus-anc](../profiles/headphone-solix-nexus-anc.md)
>
> Son doğrulama: 2026-09-28 (`bta check` 7/7, `bta status`)

## Rol

Sesin fiziksel olarak üretildiği yer. Yazılım bu katmanı **yönetemez, yalnız besler**: ne EQ ne otomasyon sürücüyü,
ANC'yi ya da kulak tıkacının oturmasını değiştirebilir. Bu yüzden bu katmanın sınırları üst katmanlara **kural** olarak
taşınır (sürücü koruma uyarısı, AAC kesimi uyarısı, oturma testi).

## Durum

| özellik | değer | kanıt (güven) |
|---|---|---|
| model | Audeeo Innovations — SOLIX Nexus ANC, TWS kulak içi, BT 5.4 | ürün sayfası + kılavuz (official, 0.85) |
| sürücü | 12 mm dinamik; empedans 32 Ω (?); 20–20 000 Hz (tolerans yayımlanmamış) | kılavuz (R39, 0.85) |
| diyafram malzemesi | **YAYIMLANMAMIŞ** | R39 — `open` |
| ANC | −25 dB (üretici iddiası), modları uygulamadan değiştirilemez (AVRCP'de yok) | kılavuz |
| codec yetenekleri | SBC (bitpool 2–53) + AAC (MPEG-2 LC, VBR) · aptX / LDAC / LC3 YOK | `MediaEndpoint1.Capabilities` (executable, 0.95) |
| AAC gerçek bağlantı | 48 kHz · 2 kanal · vbr=1 · kulaklık 262 144 bps seçer → **~17 kHz üstü kesilir** | transport baytları + benchmark (R41, 0.9) |
| frekans yanıtı ölçümü | YOK (AutoEq indeksinde 8854 satırda 0 eşleşme) | AutoEq INDEX.md |
| bası belirleyen ana etken | kulak tıkacının **sızdırmazlığı** (seal) — EQ'dan önce gelir | Olive/Welti AES (R40, 0.8) |
| kullanıcı gözlemi | varsayılan akordu bası kısık; +dB'ye iyi tepki | kullanıcı, 2026-09-27 |

## Değişkenler

| değişken | nerede ayarlanır | yazılım okuyabilir mi | yazılım değiştirebilir mi |
|---|---|---|---|
| kulak tıkacı boyu / oturma | kullanıcının kulağı | hayır (mikrofon yok) | hayır → **oturma testi** ile kullanıcı karar verir (D7.3) |
| ANC açık/kapalı/şeffaf | kulaklıktaki dokunmatik | hayır | hayır |
| ses seviyesi (mutlak) | AVRCP mutlak ses / sistem sesi | evet (`pactl` sink %) | evet (sistem) — bta DOKUNMAZ |
| aktif codec | A2DP anlaşması | evet | evet (`bta codec`), karar kullanıcıda ([USER-DECISIONS](../USER-DECISIONS.md)) |
| pil | BlueZ Battery1 | evet (`bta status`) | — |

## Kurallar (bu katmandan yukarı taşınan)

- **Bas > +12 dB (20–100 Hz)** → DİKKAT uyarısı: 12 mm sürücü yüksek seste bozulabilir. Eşik ölçümden: 31 hazır
  tarzın en büyüğü +10,9 dB, yani hazır tarzlar yanlış alarm vermez (U65).
- **20 Hz altı takviye** → DİKKAT: duyulmaz, yalnız diyafram gezinmesi (U65).
- **AAC'de 17 kHz üstü takviye** → BİLGİ: duyulmaz ama preamp tüm sesi kısar (Elektronik tarzında −7,3 dB) (U65, R41).
- ADL (canlı uyarlama) bas sınırı −3…+4 dB; yüksek seviyede (> −14 dBFS) bas **azaltılır** (sürücü koruma, R38/R40).

## Gri alanlar

| alan | neden gri | ne gerekir |
|---|---|---|
| gerçek frekans yanıtı | ölçüm yok, AutoEq'da yok | ölçüm düzeneği (kulak simülatörü) — bu projede yok |
| diyafram malzemesi / "malzeme bilimi" potansiyeli | üretici yayımlamamış | üreticiden veri ya da söküm; o olmadan iddia YAZILMAZ (R39 `open`) |
| ANC modunun yanıta etkisi | modlar yazılımdan görünmez | ölçüm düzeneği |
| mikrofonla otomatik oturma ölçümü (AirPods "Ear Tip Fit Test") | kulak içi mikrofon erişimi yok (HFP mikrofon dış mikrofondur) | donanım desteği |
| başka kulaklıklar | yalnız bu model ölçüldü | [L4 aygıt kapsamı](L4-pipewire.md#aygıt-kapsamı) |

## Testler

T-L01…T-L06 (profil, codec, format, kalıcılık, transport) · T-L10 (kopma/bağlanma) · T-L13 (varsayılan çıkış geri gelir) ·
U65/T-U07 (koruma uyarıları) · U66/T-L43 (oturma tonu) — hepsi [TEST-PLAN](../TEST-PLAN.md).

## Nasıl ölçülür

```bash
bin/bta status                 # codec, transport baytları, pil, profil
bin/bta check                  # kabul kontrolleri (T-L01..05, T-L20, T-L24)
busctl --system introspect org.bluez /org/bluez/hci0/dev_XX_XX_XX_XX_XX_XX   # BlueZ nesnesi (MAC kendi cihazın)
```
Oturma: konsol → Analiz sekmesi → **Kulak tıkacı oturma testi** (EQ'suz 50 Hz ↔ 1 kHz, −24 dBFS).
