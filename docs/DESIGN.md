# DESIGN — Ses Konsolu v2 (PRD-BTA03 / C3)

Tasarım sözleşmesi. Her karar: **bağlam → seçim → neden → kaynak**. Kaynak kısaltmaları:
**IMP** = pbakaus/impeccable (Apache-2.0) `skill/reference/*.md` · **TASTE** = Leonxlnx/taste-skill (MIT) `skills/taste-skill/SKILL.md`
· **UUPM** = nextlevelbuilder/ui-ux-pro-max-skill (MIT) `cli/assets/data/*.csv` · **DS** = Owl-Listener/designer-skills (MIT)
· **WIG** = vercel-labs/web-interface-guidelines `command.md` · **UXR** = ux-dimensional-reasoning (yerel referans).
Repolar yalnız OKUNDU (klonla-oku; hiçbir betik çalıştırılmadı). Pro-audio'ya özel kural bu repolarda **yok**
(grep: spectrum/fabfilter/vu meter → 0) — o bölümdeki kararlar alan pratiğine (FabFilter Pro-Q, Voxengo SPAN, Friture) dayanır.

## 1. Ontoloji (UXR aşama 1)

| soru | cevap |
|---|---|
| yüzey türü | tek kullanıcılı, yerel, **tekrar-kullanılan** pro araç (kokpit yoğunluğu — TASTE `VISUAL_DENSITY` 8–10, UUPM styles.csv:29 "Data-Dense Dashboard") |
| birincil görev | müzik çalarken sesi **kulakla** ayarlamak → gözün işi: eğriyi ve müziği aynı anda görmek |
| birincil nesne | frekans grafiği (EQ eğrisi + canlı spektrum). Ekranın en büyük alanı ona |
| ikincil | profil (kaydet/yükle), hazır tarzlar, ses uzayı, analiz ayarı → **sağ ray sekmeleri** (aşamalı açıklama) |
| sık hata riski | "kaydettim mi?", "şu an ne dinliyorum?", "bilgisayar açılınca bu mu gelecek?" → üç ayrı, her an görünür durum |

## 2. Üç durum, üç kelime (en önemli karar)

Kullanıcı eski arayüzde "Kaydet" ile "Kalıcı yap"ı ayırt edemiyordu. Artık:

| kavram | arayüz | anlam |
|---|---|---|
| **Aktif** | üst çubukta profil adı | şu an kulağında olan ayarın kaynağı (profil / hazır tarz / "kaydedilmemiş ayar") |
| **Değişti** | adın yanında nokta + "değişti" metni | aktif profilden sapıldı (renk + metin, yalnız renk DEĞİL — IMP colorize.md:47, UUPM ux-guidelines.csv:38) |
| **Profil olarak kaydet** | birincil düğme (Ctrl+S) | adlandırılmış anlık görüntü → Profillerim |
| **Açılışta kullan** | ikincil düğme ("Varsayılan ✓" durum) | yeniden başlatmada gelecek ses (eski "Kalıcı yap") |

## 3. Yerleşim

```
┌ üst çubuk ─ Ses Konsolu · cihaz çipi · [Aktif: <ad> ● değişti]      ↶ ↷  [EQ'suz dinle]  [Açılışta kullan] [Profil olarak kaydet ▾]
├ grafik (canvas: spektrum · SVG: ızgara, bant eğrileri, toplam eğri, düğümler) ───────────────┬ sağ ray (340 px)
│  araç şeridi: ● Müzik algılandı · Analiz [Açık] · Hız · Parça ortalaması · Tepe tutma          │ [Profiller][Uzay][Analiz]
│  metre: L/R tepe+RMS, true-peak, KIRPILMA sayacı (grafiğin sağında)                           │  arama + kategori + kartlar
├ bant şeridi (10 hücre: tip simgesi · frekans · kazanç · Q) + seçili bant denetçisi (satır içi) │  Profillerim listesi
```
- **Modal yok**, yalnız "Profil olarak kaydet" iletişim kutusu (ad girişi odak gerektirir; `<dialog>` yerel odak tuzağı + ESC — UXR responsive/a11y).
- Bitişik yüzeyler ayrışır: bg < surface1 < surface2 < surface3 (UXR `differentiate-adjacent-surfaces`, DS dark-mode-design SKILL.md:11-18).
- < 900 px: sağ ray grafiğin altına iner, bant denetçisi tek sütun (UXR compact kuralı; WIG taşma kuralları).

## 4. Token'lar

| token | koyu | açık | not |
|---|---|---|---|
| `--bg` | oklch(0.16 0.008 255) | oklch(0.975 0.003 255) | koyu tema varsayılan: karanlık odada müzik (IMP craft-floor.md:42 "ortama göre") |
| `--s1/2/3` | L 0.20 / 0.24 / 0.285 | L 1.0 / 0.965 / 0.93 | koyuda yükseklik = açıklık, gölge yok (DS dark-mode:11) |
| `--line` | L 0.33 | L 0.86 | 1 px ayraç; kart-gölge ile birlikte DEĞİL (IMP craft-floor.md:46) |
| `--text` | oklch(0.93 0.005 255) | oklch(0.22 0.01 255) | kırık beyaz (DS dark-mode:20) |
| `--text-2` | oklch(0.76 0.01 255) | oklch(0.42 0.01 255) | ≥ 4,5:1 (U48 ölçer) |
| `--acc` | oklch(0.80 0.13 85) (amber) | oklch(0.55 0.13 70) | **tek vurgu**: EQ eğrisi, seçim, birincil eylem (IMP colorize.md:10 "rarity gives force"). Amber: pro-audio'da eğri/tutamak geleneği, mavi spektrumdan ayrışır |
| `--spec-post` | oklch(0.72 0.08 240) | oklch(0.55 0.1 245) | EQ sonrası spektrum (çizgi) |
| `--spec-pre` | text-3 %14 dolgu | aynı | EQ öncesi (arka plan dolgusu) |
| `--ok/--warn/--bad` | yeşil / amber / kırmızı | | metre bölgeleri; her zaman etiketle (UUPM styles.csv:29, IMP colorize.md:47) |
| tip ölçeği | 12 / 13 / 14 / 16 / 20 px | | tek aile (IMP typeset.md:8), sayılar `tabular-nums` (IMP typeset.md:51, WIG) |
| boşluk | 4 · 8 · 12 · 16 · 24 · 32 | | 4 tabanlı (IMP layout.md:49) |
| radius | 6 (kontrol) · 10 (panel) | | tek ölçek (TASTE SHAPE CONSISTENCY LOCK) |
| hareket | 120 ms / 200 ms, `cubic-bezier(0.16,1,0.3,1)` | | yalnız color/opacity/transform (IMP animate.md:54-61,71; WIG); `prefers-reduced-motion` → kapalı |

## 5. Etkileşim

| eylem | fare | klavye |
|---|---|---|
| bant seç | düğüme / şerit hücresine tıkla | `1`…`9`, `0` |
| frekans / kazanç | sürükle (Shift = ince) | ← → (1/24 okt; Shift 1/96) · ↑ ↓ (0,5 dB; Shift 0,1) |
| Q | düğüm üstünde tekerlek | `[` `]` |
| bant ekle / kapat | boş yere / düğüme çift tık | `Delete` = kapat · `E` = aç/kapat |
| EQ'suz dinle (A/B) | düğmeyi basılı tut | `B` basılı tut |
| profil olarak kaydet | düğme | `Ctrl+S` (aktif profil değiştiyse üzerine; değilse yeni) · `Ctrl+Shift+S` yeni |
| geri / ileri al | ↶ ↷ | `Ctrl+Z` / `Ctrl+Shift+Z` |
| kısayol listesi | `?` düğmesi | `?` |
Sürükleme her zaman klavye alternatifine sahip (WIG "gesture needs keyboard alternative"). Düğümler ≥ 24×24 px isabet alanı
(UUPM ux-guidelines.csv:105), görünür odak halkası (UUPM :103, WIG). Asenkron bildirimler `aria-live` (UUPM :45, WIG).

## 6. Analizör görseli (alan pratiği)

- EQ öncesi = soluk dolgu, sonrası = ince çizgi, tepe tutma = küçük çentik. 1/6 oktav bant gücü → pembe gürültü düz görünür
  (ölçüldü: eğim 0,03 dB/okt) → FFT-bin analizörlerindeki 4,5 dB/okt eğime gerek yok (SPAN kılavuzu, Pro-Q belgesi: o eğim
  bin-yoğunluğunu telafi eder).
- Ölçek: sol eksen EQ kazancı (dB), analizör kendi ölçeğinde (−90…0 dBFS) — ikisi aynı eksene zorlanmaz (FabFilter geleneği).
- Kaynak disiplini: sekme gizliyken `EventSource.close()` → sunucu son abone gidince yakalamayı durdurur (MDN visibilitychange).

## 7. Yapmayacaklarımız (kaynaklı)

Mor/neon gradyan, glow, glassmorphism (TASTE :39,187,356; IMP craft-floor.md:10,33-34) · emoji ikon (IMP :40, TASTE :148) →
satır içi SVG · iç içe kart (IMP :25) · kenarlık + geniş gölge birlikte (IMP :46) · gereksiz modal (IMP :29) · `transition: all`
(WIG) · yalnız renkle durum (IMP colorize.md:47) · bounce easing (IMP animate.md:61).
sashimi-ui (v0.2.0'da eklenmişti) **kaldırıldı**: kendi token sistemiyle iki farklı radius/renk dili yan yana olurdu (TASTE shape lock);
lisans/kaynak kaydı git geçmişinde ve findings R25'te.

## 8. Doğrulama

U48 kontrast (iki tema, tüm metin/UI çiftleri) · T-U04 başsız E2E (tüm akışlar + klavye + 1440/390 px + açık/koyu ekran görüntüsü)
· T-L36 headful (gerçek ekran, gerçek müzik, analizör canlı) · WIG denetimi (`docs/research/wig-audit.md`).
