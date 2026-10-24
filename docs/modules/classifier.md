# `btaudio/classifier.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [infrastructure](../layers/L5-bta-software.md#infrastructure) |
| rol | YAMNet ONNX tür/enstrüman sınıflayıcı (sha256 kilitli, yerel) |
| boyut | 118 satır |
| içe aktarır (iç) | — |
| içe aktarır (dış) | `numpy`, `onnxruntime`, `scipy` |
| standart kitaplık | `__future__`, `csv`, `hashlib`, `json`, `os`, `urllib` |
| kullanan modüller | [`cli`](cli.md) |

## Amaç (modül docstring'i)

D3.2 — Yerel müzik türü + enstrüman sınıflayıcısı (infrastructure; YAMNet ONNX, Apache-2.0).

Model depoda DEĞİL: `~/.local/share/bt-audio-hifi/models/` (XDG data). Dosyalar `models.lock.json` sha256'sıyla
doğrulanmadan YÜKLENMEZ (tedarik zinciri). Ses verisi makineden çıkmaz. Model yoksa `available=False` → sistem
öznitelik katmanıyla (features.py) çalışır.

## Sabitler

| ad | değer |
|---|---|
| `REPO` | `os.path.dirname(os.path.dirname(os.path.abspath(__file__)))` |
| `LOCK` | `os.path.join(REPO, 'models.lock.json')` |
| `MACRO` | `{'elektronik': ['Electronic music', 'House music', 'Techno', 'Dubst…` |
| `INSTRUMENTS` | `['Bass guitar', 'Electric guitar', 'Acoustic guitar', 'Drum kit', '…` |

## Genel API

### `class YamnetClassifier`

YAMNet ONNX çalıştırıcı (tek iş parçacığı); model doğrulanamazsa available=False, reason dolu.

- `__init__(self, directory: str | None=None)`
- `available(self)` — Oturum hazır mı (model doğrulandı + onnxruntime yüklendi).
- `predict(self, audio48k_mono: np.ndarray) -> dict | None` — 48 kHz mono ses (≥1 sn) → 16 kHz'e indir → çerçeve skorlarının ortalaması → macro_scores; yetersizse None.

- `model_dir() -> str` — Model dizini: $XDG_DATA_HOME/bt-audio-hifi/models (depoda DEĞİL).
- `verify(directory: str | None=None) -> dict` — Model dosyalarını models.lock.json sha256'larıyla karşılaştırır: {dosya: ok|missing|sha-mismatch}.
- `fetch(directory: str | None=None) -> dict` — Kullanıcı komutu (`bta model fetch`): indir → sha256 doğrula → yanlışsa SİL (zehirli dosya kalmaz).
- `macro_scores(scores: np.ndarray, names: list) -> dict` — 521 AudioSet skoru → makro tür skorları + müzik skoru + ilk 5 enstrüman.

## Testler

- [`tests/live/test_live_auto.py`](../../tests/live/test_live_auto.py) — T-L39, T-L40, T-L41, T-L42, U62
