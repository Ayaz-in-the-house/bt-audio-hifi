# Preset kaynakları (C2) — indirildi 2026-09-27, değerler python ile okundu

| dosya | kaynak URL | lisans | kullanım |
|---|---|---|---|
| `vlc-equalizer_presets.h` | https://raw.githubusercontent.com/videolan/vlc/master/modules/audio_filter/equalizer_presets.h | LGPL-2.1+ (dosya başlığı) | tür presetlerinin 10 bant değerleri → `presetfit` ile parametrik uydurma (×0,5, 1 kHz'e göre) |
| `autoeq-Harman in-ear 2019*.csv` | https://github.com/jaakkopasanen/AutoEq/tree/master/targets | MIT (AutoEq) · veri Harman araştırması | "with − without bass" = bas rafı → lowshelf 105 Hz Q0,7 **+9,0 dB** (max hata 0,06 dB) |
| `autoeq-Harman over-ear 2018*.csv` | aynı | aynı | aynı yöntem → **+6,0 dB** (max hata 0,04 dB) |
| `easyeffects-presets-Bass Boosted.json`, `…-Boosted.json` | https://github.com/JackHack96/EasyEffects-Presets | MIT | 10 bell bant birebir (Q 1,5048) |
