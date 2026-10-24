# `btaudio/presetfit.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [domain](../layers/L5-bta-software.md#domain) |
| rol | Grafik EQ presetlerini parametrik EQ'ya uydurma |
| boyut | 70 satır |
| içe aktarır (iç) | [`dsp`](dsp.md) |
| içe aktarır (dış) | `numpy`, `scipy` |
| standart kitaplık | `__future__` |
| kullanan modüller | — |

## Amaç (modül docstring'i)

C2 — Grafik EQ presetlerini (ör. VLC 10 bant) kompakt parametrik EQ'ya dönüştürme.

Neden: yayımlanmış grafik presetler 10 sabit bant kullanır; konsolda 10 bandın hepsini doldurmak kullanıcıya ince ayar
için yer bırakmaz. AutoEQ'nun yaptığı gibi hedef eğriye az sayıda parametrik bantla uydururuz.

Hedef eğri: bant değerleri log-frekansta doğrusal ara değerlenir (grafik EQ'nun alışılmış gösterimi), 1 kHz'e göre
sıfırlanır (tonal denge biçimi; genel seviye otomatik preamp'ın işi) ve `scale` ile ölçeklenir.
Uydurma YALNIZ tasarım anında koşar; sonuç `console.PRESETS`'e sabit sayı olarak yazılır ve U43 aynı hedefe karşı
hata ≤ 1 dB'yi yeniden ÖLÇER (kaynak → ses zinciri çalıştırılabilir kanıt).

## Sabitler

| ad | değer |
|---|---|
| `VLC_CENTERS` | `(60, 170, 310, 600, 1000, 3000, 6000, 12000, 14000, 16000)` |
| `FIT_GRID` | `np.geomspace(30, 16000, 160)` |

## Genel API

- `target_curve(centers, values, scale=1.0, freqs=FIT_GRID)` — Grafik EQ merkez/değerlerinden sürekli hedef eğri (log-frekans ara değer).
- `fit(centers, values, scale=0.5, max_err_db=1.0, max_bands=7)` — En az bantla max|hata| ≤ max_err_db. Dönüş: (bantlar, max_hata). Deterministik (sabit başlangıçlar).
- `fit_error(bands, centers, values, scale=0.5) -> float` — Uydurulan parametrik EQ ile hedef arasındaki en büyük mutlak hata (dB).

## Testler

- [`tests/test_presets.py`](../../tests/test_presets.py) — U43
