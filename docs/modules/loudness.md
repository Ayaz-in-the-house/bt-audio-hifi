# `btaudio/loudness.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [domain](../layers/L5-bta-software.md#domain) |
| rol | Eşit-yükseklik (ISO 226) ile kulakta bas yanıtı (F8) |
| boyut | 113 satır |
| içe aktarır (iç) | — |
| içe aktarır (dış) | `numpy`, `scipy` |
| standart kitaplık | `__future__` |
| kullanan modüller | [`bass`](bass.md), [`eqverify`](eqverify.md), [`tuner`](tuner.md), [`tunerserver`](tunerserver.md) |

## Amaç (modül docstring'i)

F8 — Kulağında (in-situ) bas yanıtı: eşit-yükseklik eşleşmesi + ISO 226:2003 → kulaklık yanıtı → PEQ.

Yöntem: dinleyici her test tonunun dijital seviyesini (1 kHz referansa göre g_f dB) eşit yükseklikte duyana dek
ayarlar. Eşit yükseklikte SPL_f − SPL_1k = L_iso(f) − L_iso(1k) (ISO 226, aynı phon). SPL = S(dijital)+yanıt ⇒
    H(f) − H(1k) = [L_iso(f) − L_iso(1k)] − g_f
Geçerlilik: < 1 kHz (bas/alt-orta). Üstünde kulak kanalı/rezonans etkileri ISO 226 serbest-alan varsayımını bozar.
ISO 226 katsayıları: IoSR Surrey MatlabToolbox iso226.m ile birebir doğrulandı (docs/research/findings.md).

## Sabitler

| ad | değer |
|---|---|
| `FS` | `48000` |
| `TEST_FREQS` | `[31.5, 40, 50, 63, 80, 100, 125, 160, 250, 500]` |
| `PEQ_CENTERS` | `[(35, 1.0), (55, 1.0), (90, 1.0), (150, 1.0), (250, 1.0), (450, 1.0)]` |
| `ANCHORS` | `{1000: 0.0, 2000: 0.0, 4000: 0.0}` |

## Genel API

- `iso226_spl(phon: float, freqs) -> list`
- `response_from_matches(matches: dict, phon: float) -> dict`
- `eq_response_db(bands, freqs, fs=FS) -> list`
- `target_db(name: str, freqs) -> list` — Hedef eğri, 1 kHz'e göre. harman-ie-bass: AutoEQ'nun Harman IE hedefi için kullandığı 105 Hz Q0.7 low-shelf biçiminde +8 dB bas rafı (tam Harman eğrisinin yalnız bas bölgesi yaklaşığı).
- `design_eq(h: dict, target='harman-ie-bass', max_boost_db=12.0, max_cut_db=-12.0) -> dict`

## Testler

- [`tests/test_bass.py`](../../tests/test_bass.py) — U26
- [`tests/test_dsp.py`](../../tests/test_dsp.py) — T-L30, U30
- [`tests/test_loudness.py`](../../tests/test_loudness.py) — U22, U24
- [`tests/test_tuner.py`](../../tests/test_tuner.py) — T-U02, U29
