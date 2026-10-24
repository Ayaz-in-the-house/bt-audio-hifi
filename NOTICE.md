# Üçüncü taraf bildirimleri

Bu depo kendi kodunu içerir; aşağıdakiler **kopyalanmış kod değil**, referans / veri / araştırma kopyasıdır.
Projenin kendi lisansı: **MIT** (`LICENSE`, sahibin kararı 2026-09-27). Aşağıdakilerin kendi lisansları geçerlidir.

| kaynak | lisans | nasıl kullanılıyor | yer |
|---|---|---|---|
| libbs2b (Boris Mikhaylov) | MIT | crossfeed filtre formülleri `btaudio/console.py`'de yeniden yazıldı (birinci derece filtre katsayıları) | araştırma kopyası `docs/research/upstream/bs2b.{c,h}` |
| PipeWire / WirePlumber | MIT | davranış doğrulaması için kaynak okundu; kod kopyalanmadı | `docs/research/upstream/*.c` |
| EasyEffects 8.2.9 | GPL-3.0 | yalnız şema/davranış okundu (kurulu uygulama isteğe bağlı) | `docs/research/upstream/easyeffects-8.2.9/` |
| AutoEq hedef eğrileri (Harman) | MIT (AutoEq) | Harman bas rafları CSV'den ölçülerek türetildi | `docs/research/upstream/presets/` |
| JackHack96/EasyEffects-Presets | MIT | "Bass Boosted", "Boosted" 10 bant değerleri | aynı |
| VLC `equalizer_presets.h` | LGPL-2.1+ | tür presetlerinin sayısal değerleri → parametrik uydurma (kod kopyalanmadı) | aynı |
| ISO 226:2003 katsayıları (IoSR Surrey `iso226.m` üzerinden) | standart / araştırma | `btaudio/loudness.py` | — |
| YAMNet modeli (`yamnet.onnx`) + `yamnet_class_map.csv` (TensorFlow Models / AudioSet sınıf adları) | Apache-2.0 | yerel tür/enstrüman sınıflayıcısı; **depoda YOK** — kullanıcı `bta model fetch` ile indirir, `models.lock.json` sha256'sıyla doğrulanmadan yüklenmez | `~/.local/share/bt-audio-hifi/models/` |
| onnxruntime | MIT | sınıflayıcı çalışma zamanı (isteğe bağlı bağımlılık, pip) | — |
| Essentia müzik modelleri | CC BY-NC-SA | **REDDEDİLDİ** (ticari olmayan lisans MIT projeyle uyumsuz) | — |
| Musopen Brahms Senfoni 1 | CC0 | yalnız yerel benchmark (depoda YOK, `analysis/tmp` git dışı) | — |
