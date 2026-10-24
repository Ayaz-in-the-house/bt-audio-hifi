# `btaudio/features.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [domain](../layers/L5-bta-software.md#domain) |
| rol | Müzik karakteri öznitelikleri (bölge fazlası, karakter etiketleri) |
| boyut | 50 satır |
| içe aktarır (iç) | — |
| içe aktarır (dış) | `numpy` |
| standart kitaplık | `__future__`, `math` |
| kullanan modüller | [`autoengine`](autoengine.md) |

## Amaç (modül docstring'i)

D3.1 — Müzik karakteri öznitelikleri (domain, saf). Girdi: 1/6 okt bant gücü (dBFS, analizör LTAS'ı).

Ölçüt: her bölgenin 1/6 okt bantlarının GÜÇ ortalaması, orta bölgeye (500 Hz–2 kHz) göre dB. Bant-gücü gösteriminde
pembe gürültü düzdür (R31) → pembe = tüm bölgeler 0 dB. (İlk sürüm "pay oranı" kullanıyordu; pay doygunlaştığı için
+12 dB bas yalnız +3,8 dB görünüyordu — U54 yakaladı.) Türden bağımsız ölçülmüş tonal denge; R37 (Dolby IEQ) girdisi.

## Sabitler

| ad | değer |
|---|---|
| `REGIONS` | `{'sub': (20, 60), 'bas': (60, 250), 'alt_orta': (250, 500), 'orta':…` |

## Genel API

- `region_excess(bands_db, centers) -> dict | None` — Bölgelerin (sub…hava) orta bölgeye göre güç ortalaması farkı (dB); sessizlikte None.
- `character(ex: dict | None) -> list` — Okunur karakter etiketleri (arayüz + kontrolörler).

## Testler

- [`tests/test_autoctl.py`](../../tests/test_autoctl.py) — T-L42, U54, U56
- [`tests/test_autoengine.py`](../../tests/test_autoengine.py) — U58, U59, U60, U73
- [`tests/ui/test_auto_page.py`](../../tests/ui/test_auto_page.py) — T-U05
