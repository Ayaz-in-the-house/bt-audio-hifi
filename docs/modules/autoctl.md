# `btaudio/autoctl.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [domain](../layers/L5-bta-software.md#domain) |
| rol | APC (otomatik profil) + ADL (canlı uyarlama) karar mantığı |
| boyut | 137 satır |
| içe aktarır (iç) | — |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__`, `copy`, `math` |
| kullanan modüller | [`autoengine`](autoengine.md), [`consoleserver`](consoleserver.md) |

## Amaç (modül docstring'i)

D4 Auto Profile Changer + D5 Auto Dynamic Live — karar mantığı (domain: saf, saat parametre).

Parametre kaynakları (docs/research/findings.md R35–R38; araştırma ajanı tabloları): histerezis/kalma/marj değerleri
için akademik kaynak YOK → "tasarım önerisi" olarak işaretli; ADL ilkeleri Dolby IEQ (R37: yeterince bas varsa dokunma),
iZotope TBC (hedef = aralık → ölü bölge), Harman bas tercihi (R38: +4–6 dB), ISO 226 (düşük seviyede bas telafisi).

## Sabitler

| ad | değer |
|---|---|
| `APC_DEFAULTS` | `{'tau_s': 10.0, 'margin': 0.15, 'sustain_s': 8.0, 'dwell_s': 30.0, …` |
| `ADL_BANDS` | `{'bas': ('lowshelf', 80.0, 0.7, 'sub', (-3.0, 4.0)), 'alt_orta': ('…` |
| `ADL_DEFAULTS` | `{'dead_db': 2.0, 'strength': 0.5, 'rate_db_s': 1.0, 'loud_db': -14.…` |

## Genel API

### `class ProfileChanger`

Tür olasılıkları (EMA) → türle etiketli profil. Salınım koruması: marj + süreklilik + en az kalma + elle askı.

- `__init__(self, mapping: dict, fallback: str | None=None, **cfg)`
- `manual(self, now)` — Elle dokunuş: `manual_pause_s` (10 sn) boyunca otomatik geçiş yapılmaz.
- `update(self, macro: dict | None, now: float)` — Makro tür olasılıklarını EMA'ya katar; marj + süreklilik + en az kalma koşulları sağlanınca hedef profil kimliğini döndürür, aksi hâlde None.

### `class DynamicEQ`

Ölçülen tonal denge (bölge fazlası, dB) ↔ kişisel referans → sınırlı, yavaş, ölü bölgeli düzeltme.

- `__init__(self, reference: dict | None=None, **cfg)`
- `learn_reference(self, excess: dict, weight: float=0.02)` — Kişisel tonal referansı (bölge fazlası) `weight` ağırlıklı üstel ortalama ile günceller.
- `manual(self, band: str, delta_db: float)` — Kullanıcı bant tercihini öğrenir: bias += learn·delta, ±bias_max ile sınırlı.
- `target(self, excess: dict, genre: str | None, level_db: float | None) -> dict` — Hedef düzeltme (dB, bant başına): ölü bölge, güç, tür kuralı (R37), seviye kuralları (ISO 226 / sürücü koruma), bant sınırları. Konuşmada tümü 0.
- `step(self, excess: dict | None, genre: str | None, level_db: float | None, now: float) -> dict` — Hedefe `rate_db_s` hızıyla yaklaşır; sessizlikte son değeri korur. Uygulanacak katmanı döndürür.

- `apply_offsets(state: dict, offsets: dict) -> dict` — Kullanıcının durumuna ADL bantlarını BOŞ (kapalı) yuvalara ekler — kullanıcının bantlarına dokunmaz.

## Testler

- [`tests/test_autoctl.py`](../../tests/test_autoctl.py) — T-L42, U54, U56
- [`tests/test_autoengine.py`](../../tests/test_autoengine.py) — U58, U59, U60, U73
