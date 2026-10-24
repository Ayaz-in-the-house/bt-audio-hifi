# Belge merkezi — buradan başla

> Ajanlar ve geliştiriciler için tek giriş noktası. **Kural:** kod değişikliği aynı commit'te ilgili belgeyi günceller;
> `tests/test_docs_gate.py` (U67) modül belgeleri bayatsa, bir test kimliği planda yoksa ya da bağlantı kırıksa KIRMIZI olur.

## 5 dakikada yönelim

1. **Ne yapıyor?** [README](../README.md) → [FEATURES](FEATURES.md) (✅ yapıldı · 🟡 kullanıcıda · ⬜ gri).
2. **Nasıl kurulu?** [layers/00-overview](layers/00-overview.md) — kulaklıktan tarayıcıya 6 katman.
3. **Kod nerede?** [ARCHITECTURE](ARCHITECTURE.md) (sözleşme) → [modules/](modules/README.md) (modül başına üretilmiş kart).
4. **Neyi kıramam?** ARCHITECTURE §Geçilmez çizgiler + [lessons/errors](lessons/errors.md) + [lessons/edge-cases](lessons/edge-cases.md).
5. **Nasıl doğrularım?** [TEST-PLAN](TEST-PLAN.md) · `tests/run.sh [--live]` · [PROCESS](PROCESS.md).

## Belgeler

| belge | ne | kim günceller / ne zaman |
|---|---|---|
| [PRD](PRD.md) | gereksinimler, fazlar, kabul ölçütleri (BTA01…04) | her yeni iş kolunda; durum sütunları iş bitince |
| [ARCHITECTURE](ARCHITECTURE.md) | katmanlar, geçilmez çizgiler, veri akışı, hata kipleri, güvenlik | mimari değişen her commit |
| [layers/](layers/00-overview.md) | L1 kulaklık · L2 Bluetooth · L3 Linux · L4 PipeWire · L5 yazılım · L6 arayüz | katmanda durum/değişken/gri alan değişince ("Son doğrulama" tarihi) |
| [modules/](modules/README.md) | modül başına API, bağımlılık, testler | **ÜRETİLİR**: `python3 tools/gen-docs.py` |
| [FEATURES](FEATURES.md) | özellik kataloğu + gri alanlar | özellik eklenince/durum değişince |
| [USER-DECISIONS](USER-DECISIONS.md) | kullanıcıdan bekleyen kararlar, sade Türkçe | karar eklenince / verilince |
| [TEST-PLAN](TEST-PLAN.md) | her test kimliği, beklenen, neden (kodu yazmadan ÖNCE) | her yeni test |
| [DESIGN](DESIGN.md) | arayüz tasarım sözleşmesi (belirteçler, kontrast) | arayüz değişince |
| [PROCESS](PROCESS.md) | çalışma süreci: plan → test noktaları → RED → GREEN → belge → commit | süreç değişince |
| [STATE-LOG](STATE-LOG.md) | durum geçişleri (ne zaman, ne değişti, kanıt) | her anlamlı geçiş |
| [lessons/](lessons/errors.md) | hatalar (E), kenar durumlar (K), altın yollar (GP) | her yeni ders |
| [research/findings](research/findings.md) | kanıt defteri R1…R50 (kaynak + güven) | her araştırma bulgusu |
| [research/vendor-recommendations](research/vendor-recommendations.md) | üreticiye öneriler V1–V10, uygulama durumu, SPP/RACE riski | yeni ölçüm/kaynak geldikçe |
| [profiles/](profiles/headphone-solix-nexus-anc.md) | cihaz ve ana makine kartları | ölçüm değişince |

## Ajanlar için kısa sözleşme

- Önce ölç: `bin/bta status` + `bin/bta check`. Sonra oku: bu dosya → ilgili katman belgesi → modül kartı.
- Test kimliği uydurma: yeni test = önce TEST-PLAN satırı (kimlik tek). Tarihsel kimlikler `T-H*` yeniden kullanılmaz.
- Kullanıcı dinlerken sesine test tonu karıştırma (K10); ölçümleri null sink'te yap (`*verify` modülleri).
- Kullanıcının uygulamalarını asla kapatma; yalnız kendi alt süreçlerimiz (`procs.spawn`).
- Canlı sunucuyu yeniden başlatırken sesi koru: `GET /api/state` → `state` JSON → `POST /api/quit` →
  `bin/bta console --initial <json> --profile <aktif id>`.
