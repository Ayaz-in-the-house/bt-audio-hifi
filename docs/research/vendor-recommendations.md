# Üreticiye öneriler — Solix Nexus ANC (Audeeo Innovations, model SX-EANC4)

> 2026-10-15 · kaynak: bu projenin ölçümleri (R-kimlikleri [findings](findings.md)'de) + dış kaynaklar (aşağıda).
> Amaç: üretim maliyetine ~0 (yalnız firmware) ya da birkaç cent eklenerek çok daha iyi yönetim/deneyim.
> Güven sütunu: **ölçüldü** = bu makinede çalıştırılan araçla · **kaynak** = belge/makale · **tahmin** = doğrulanmadı.

## Uygulama durumu (kullanıcı sorusu: "Solix'in app'ini bulamadım, var mı?")

**Yok.** Üç bağımsız kaynakta hiçbir eşlik uygulaması geçmiyor:

| kaynak | bulgu |
|---|---|
| resmî kılavuz (manuals.plus, model SX-EANC4, item 3212577) | yalnız düğme kontrolleri: sağ 2 sn = ANC → şeffaflık; sol 2 sn = asistan; üçlü dokunuş = ses. Uygulama, QR, EQ, firmware güncellemesi YOK |
| solixco.com | uygulama/indirme bağlantısı yok |
| App Store / Google Play araması | Solix adına yayıncı bulunamadı |

Sonuç: ANC/şeffaflık yalnız düğmeyle, EQ hiç yok (kulaklık içinde). Kulaklığın sunduğu **SPP (Serial Port)**
kanalı kullanıcıya dönük bir uygulama için değil; büyük olasılıkla çip üreticisinin genel kanalı (fabrika testi /
OTA / çip SDK protokolü). Çip: **Bluetrum Technology** (R51, `hcitool info`); SPP kaydı genel ad "SPP", RFCOMM 1 (R52).
Bluetrum'un SPP protokolü için açık belge/proje bulunamadı (2026-10-15 araması) — bkz. [PRD-BTA06 G3](../PRD.md#prd-bta06--süreklilik-çok-aygıt-kulaklık-kanalı).

## Öneriler (öncelik sırası)

| # | öneri | maliyet | kazanç | güven |
|---|---|---|---|---|
| V1 | **AAC `vbr=1` bayrağını kaldır / 320 kbps CBR kabul et** | 0 (firmware) | kesim 17,0 → 19,3 kHz; bant-SNR 15,3 → 18,2 dB (262k) / 20,3 dB (320k) | ölçüldü (`analysis/encoder-benchmark-20260927-193307.md`, R4) |
| V2 | **Sabit genel (public) Bluetooth adresi + Device ID (DIS/Modalias)** | 0 | yeniden eşleşmede MAC değişmez; işletim sistemi modeli tanır → otomatik profil. Bu projede E29 arızasının kökü | ölçüldü (10-15: MAC `…2B:17:4E:B5` → `…E9:DF:09:A6`, Modalias yok) |
| V3 | **SPP kanalını kimlik doğrulamalı yap ya da kapat** (kullanıcı uygulaması yoksa açık bırakmanın faydası yok) | 0 | Airoha tabanlı kulaklıklarda kimlik doğrulamasız çip protokolü (RACE) bellek okuma/yazma ve bağlantı anahtarı sızdırmaya izin verdi (CVE-2025-20700/20701/20702, ERNW). Bu kulaklığın çipi **Bluetrum** (R51) → o CVE'ler doğrudan geçerli değil; Bluetrum SPP protokolünün yetkilendirmesi `open` | kaynak (ERNW) + R51 |
| V4 | **Belgelenmiş kontrol protokolü** (ya da standart GATT servisi): ANC modu, ANC seviyesi, kulak içi EQ | 0 | masaüstü/Linux'tan ANC + kulaklık içinde EQ (telefonda da geçerli kalır) | tahmin |
| V5 | **Kulak tıkacı oturma testi** (mevcut 4 mikrofonla, firmware) | 0 | bası en çok sızdırmazlık belirler; kullanıcı yanlış boy tıkaçla "bas zayıf" der | kaynak (R40, Olive/Welti AES) |
| V6 | **ANC açıkken sessizlikte 5 dk otomatik kapanmayı kaldır** (ya da ayarlanabilir yap) | 0 | kullanıcı şikâyeti: "ANC ile 5 dk sonra kapanıyor, seyahatte can sıkıcı" | kaynak (manuals.plus Q&A, 2026-10-03) |
| V7 | **Frekans yanıtı ölçümü yayımla** (ya da AutoEQ'ya örnek gönder) | 0 | topluluk EQ'su; AutoEQ indeksinde 0 eşleşme | ölçüldü (AutoEq INDEX 8854 satır) |
| V8 | **Kutuya köpük + 3 boy silikon tıkaç** | birkaç cent | V5 ile aynı kazanç, firmware olmadan | tahmin (maliyet ölçülmedi) |
| V9 | SBC-XQ'yu taşıyamayan bağlantı (13 düşürme / 90 sn): anten / TWS aktarım ayarı | belirsiz | yüksek bitrate kararlılığı | ölçüldü (belirti) · kök neden `open` |
| V10 | LE Audio / LC3 (BT 5.4 çipi destekliyorsa) | lisans/çip bağımlı | daha iyi codec, düşük gecikme | `open` |

## Bu kulaklık için bizim tarafta yapılabilecekler

1. Oturma testi + tıkaç denemesi (konsol, T-L43) — kullanıcıda.
2. Kör dinleme testi AAC ↔ SBC (F32) — kullanıcıda.
3. Otomatik modu arka plan servisi yapmak (PRD-BTA06 G1) — onaylandı 2026-10-15.
4. Panelden cihaz seçimi (G2) — onaylandı.
5. SPP kanalının çip kimliği, yalnız salt-okuma (G3) — onaylandı; komut gönderen her adım kullanıcı kararı.
6. **Yeni fikir (V6'dan):** ANC kullanılırken müzik yokken PipeWire kulaklık sink'ini askıya alıyor olabilir →
   kulaklık "boşta" sanıp 5 dk'da kapanıyor olabilir. `session.suspend-timeout-seconds = 0` (yalnız bu sink) ile
   çözülebilir. **Hipotez, ölçülmedi.**

## Dış kaynaklar

- Kılavuz: <https://manuals.plus/solix/nexus-true-wireless-earphones-manual> (Scrapling ile okundu, 2026-10-15)
- Üretici: <https://solixco.com>
- ERNW RACE araştırması: <https://ernw.de/en/whitepapers/issue-74.html> · CVE: <https://cvefeed.io/vuln/detail/CVE-2025-20700>
- Basın özeti: <https://cyberinsider.com/exploit-tool-for-bluetooth-flaws-impacting-millions-of-headphones-now-available/>
- SPP üzerinden ANC komutu çözme yöntemi (başka marka, yöntem referansı): <https://gist.github.com/CallMeTak/f6fefe522401e435e083de1b854f2197>
