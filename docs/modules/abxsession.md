# `btaudio/abxsession.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [application](../layers/L5-bta-software.md#application) |
| rol | Konsoldaki kör ABX testi: klip (kendi müziğinden), 12 deneme, sonuç, tercih, uygula/iptal |
| boyut | 197 satır |
| içe aktarır (iç) | [`abx`](abx.md) |
| içe aktarır (dış) | `numpy`, `scipy` |
| standart kitaplık | `__future__`, `datetime`, `json`, `os`, `threading` |
| kullanan modüller | [`cli`](cli.md), [`consoleserver`](consoleserver.md) |

## Amaç (modül docstring'i)

PRD-BTA05 E1 — Konsoldaki kör ABX testi (application): terminal soru-cevabı yerine düğmeli, adım adım test.

Akış: klip (kullanıcının KENDİ müziğinden 12 sn, EQ öncesi dijital dokunuş = codec'ten önce) → 12 deneme (A, B, X
istenildiği kadar dinlenir; X dinlenmeden cevap verilemez) → sonuç (binom p; 12'de ≥10 doğru → fark duyuluyor) →
fark varsa tercih → "uygula" (karar kaydı + codec) ya da orijinal codec'e dönüş.

Kurallar (abx.py ile aynı istatistik): denemeler 6A/6B karışık; her çalmada ÖNCE diğer codec'e SONRA hedefe geçilir
→ her çalmada aynı geçiş dizisi = geçişin kendisi ipucu olamaz. Test boyunca otomasyon askıdadır (test sesi türü
değiştirmesin). Codec değiştirici / çalar / otomasyon dışarıdan verilir (testlerde sahte; U69).

## Sabitler

| ad | değer |
|---|---|
| `MUSIC_MIN_DBFS` | `-60.0` |
| `FADE_S` | `0.03` |

## Genel API

### `class NotReady(Exception)`

İstenen adımın ön koşulu yok (ör. X dinlenmeden cevap).

### `class Busy(Exception)`

Bir çalma/codec geçişi sürüyor.

### `class NoMusic(Exception)`

Klip sessiz — müzik çalarken tekrar dene.

### `class AbxSession`

Tek kullanıcılı kör test durum makinesi: idle → trial (12 deneme) → result → (finish) idle.

- `__init__(self, switcher, player, current_codec, results_dir, n=12, seed=None, automation=None, on_apply=None)`
- `start(self, codec_a, codec_b, clip)`
- `play(self, which)`
- `answer(self, which)`
- `prefer(self, codec)`
- `finish(self, apply=False)`
- `abort(self)`
- `status(self)`

- `capture_clip(recorder, out_dir: str, seconds: float=12.0) -> str` — `recorder(path, seconds)` EQ öncesi dokunuştan stereo 48 kHz kaydeder. Klip seviyesi ölçülür (sessizse NoMusic), uçlar 30 ms yumuşatılır (açma/kapama tıkı ABX'e ipucu olmasın), 16 bit wav olarak saklanır.

## Testler

- [`tests/test_abxsession.py`](../../tests/test_abxsession.py) — U69, U70
- [`tests/ui/test_abx_page.py`](../../tests/ui/test_abx_page.py) — T-U08
- [`tests/ui/test_i18n_page.py`](../../tests/ui/test_i18n_page.py) — T-U04, T-U06, T-U08, T-U09
