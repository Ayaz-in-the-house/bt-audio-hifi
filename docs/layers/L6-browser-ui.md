# L6 — Tarayıcı ve arayüz (Zen + yerel konsol / yönetim sayfaları)

> Katman haritası: [00-overview](00-overview.md) · altı: [L5 bta yazılımı](L5-bta-software.md) · tasarım sözleşmesi:
> [DESIGN](../DESIGN.md)
>
> Son doğrulama: 2026-09-28 (canlı sunucuda görünür pencereyle gözlem: konsol + /admin, JS hatası 0; Zen akışları ölçüldü)

## Rol

İki ayrı işi var: (1) **ses kaynağı** — kullanıcının müziği/videosu çoğunlukla tarayıcıdan gelir; (2) **denetim yüzeyi** —
konsol (`/`) ve yönetim (`/admin`) sayfaları yerel sunucuya bağlanır.

## Durum

| öğe | değer | kanıt |
|---|---|---|
| tarayıcı | Mozilla Zen 1.22.3b (Firefox tabanlı) | `zen --version` |
| tarayıcı ses akışı | **float32 · 2 kanal · 48 kHz** (6 akış, 1'i çalıyor) — kaynak zaten 48 kHz, resampler devreye girmez | `pactl list sink-inputs` |
| konsol | `tools/console.html` — tek dosya, dış bağlantı YOK; grafikten sürüklemeli 10 bant EQ, analizör, profiller, uzay, otomatik, uyarı şeridi, oturma testi | T-U04, T-U05, T-U07 |
| yönetim | `tools/admin.html` — profil tablosu, sürüm zaman çizelgesi + farklar, çöp kutusu, paket dışa/içe aktarma, otomasyon paneli | T-U06 |
| güvenlik | CSP `default-src 'self'` (satır içi betik/stil tek dosya için), `frame-ancestors 'none'`, Host kontrolü, JSON-only POST | U36, U47, U63 |
| erişilebilirlik | WCAG AA kontrast iki temada (ölçülür), ARIA sekmeler, klavye ile bant düzenleme | U48, T-U04 |
| yerleşim | 1440 px masaüstü + 390 px telefon: yatay taşma yok | T-U04…T-U07 |

## Değişkenler

| değişken | nerede | not |
|---|---|---|
| sunucu portu | `bta console --port N` (varsayılan rastgele) | canlı oturum 8766 |
| açılacak tarayıcı | `$BTA_BROWSER` → Zen → sistem varsayılanı | `cli._open_url` |
| tema | `localStorage["bta.theme"]` = auto/dark/light (iki sayfa ortak) | kişisel kolaylık |
| konsol tercihleri | `bta.tab`, `bta.cat`, `bta.an-en`, `bta.sh-{post,pre,hold,ltas}` | kişisel kolaylık, sunucuya gitmez |
| yönetim seçimi | `bta.admin.sel` | son bakılan profil |
| yoklama | otomatik sekmesi / mod açıkken 1 sn (`GET /api/auto`); sekme gizliyken DURUR | kaynak disiplini |
| analizör | SSE yalnız sekme görünür + "canlı göster" açıkken | kimse bakmıyorken yakalama yok |

**Kalıcı durum tarayıcıda DEĞİL**: profiller, sürümler, otomasyon ayarı sunucuda (XDG). `localStorage` yalnız görünüm tercihi.

## Gri alanlar

| alan | durum |
|---|---|
| İngilizce / çok dilli arayüz | yok (metinler Türkçe) — açık kaynak erişimi için sıradaki |
| telefonda dokunmatik sürükleme ince ayarı | çalışır, ayrı test edilmedi |
| ekran okuyucu ile tam gezinti | ARIA var, gerçek ekran okuyucu testi yok |
| uzaktan erişim (başka cihazdan konsol) | bilerek YOK (yalnız 127.0.0.1; DNS rebinding koruması) |
| tarayıcı sesinin kendi işlemesi (Zen ses ayarları) | ölçülmedi; 48 kHz F32 doğrudan geliyor |

## Testler

T-U04 (konsol uçtan uca) · T-U05 (otomatik sekmesi) · T-U06 (yönetim) · T-U07 (uyarılar + oturma testi) ·
T-L36 (headful: gerçek ekranda sayfa + analizör) · U36/U47 (sunucu güvenliği) · U48 (kontrast).

## Nasıl ölçülür

```bash
python3 -m unittest discover -s tests/ui -p 'test_*.py'     # başsız Chromium, ses çıkmaz, ekran görüntüleri analysis/ui/
pactl -f json list sink-inputs | python3 -c 'import json,sys; [print(s["properties"].get("application.name"), s["sample_specification"]) for s in json.load(sys.stdin)]'
```
Headful gözlem: Playwright Chromium `headless=False` (kullanıcının açık tarayıcısına DOKUNULMAZ), sayfa yalnız okunur —
mod değiştirilmez (kullanıcının sesi değişmesin).
