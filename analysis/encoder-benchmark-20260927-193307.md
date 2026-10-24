# Encoder benchmark 20260927-193307

F2.2 — Encoder benchmark. Kulaklığa giden encoder ile AYNI kütüphane (/lib64/libfdk-aac.so.2) ffmpeg üzerinden
sürülür; her aday kodlanır → çözülür → 48 kHz'e döner → referansla hizalanır + kazanç eşlenir → metrikler.

Dürüstlük notları (rapora da yazılır):
  * Metrikler algısal DEĞİL (PEAQ/ViSQOL kurulu değil); bant-SNR ve kesim frekansıdır. Nihai hakem kör A/B dinleme.
  * Kulaklığın DECODER'ı bilinmiyor; burada ffmpeg decoder'ı kullanılır.
  * SBC adayları ffmpeg ile DEĞİL, PipeWire'ın bağlandığı aynı libsbc (ctypes) ile, canlı transport'tan okunan
    parametrelerle kodlanır (ffmpeg SBC kanal modu/alt-bant seçtirmiyor — ölçüldü, E9).


### pembe-gurultu

| aday | snr_20_20k | cutoff_hz | snr_20_4k | snr_4k_10k | snr_10k_16k | snr_16k_20k | kbps |
|---|---|---|---|---|---|---|---|
| PCM-kontrol | 79.4 | 24000 | 85.3 | 75.9 | 73.0 | 71.5 | None |
| PCM-44k1-gidis-donus | 66.9 | 21211 | 68.3 | 66.2 | 64.7 | 59.7 | None |
| AAC-CBR-262k-oto-bant | 15.3 | 17039 | 26.0 | 18.2 | 17.1 | 1.3 | 263 |
| AAC-CBR-262k-bant19293 | 18.2 | 19336 | 24.5 | 15.8 | 14.7 | 6.8 | 263 |
| AAC-CBR-320k-bant19293 | 20.3 | 19336 | 27.5 | 20.0 | 18.9 | 7.4 | 322 |
| AAC-VBR3 | 10.6 | 15797 | 16.0 | 8.1 | 6.7 | -0.0 | 133 |
| AAC-VBR4 | 13.0 | 16547 | 19.9 | 12.1 | 11.1 | 0.6 | 185 |
| AAC-VBR5 | 18.4 | 19336 | 24.1 | 16.2 | 15.3 | 7.1 | 267 |
| SBC-XQ(48k,dual,bp39) | 28.6 | 24000 | 39.5 | 25.1 | 21.4 | 19.3 | 504 |
| SBC(48k,joint,bp53) | 19.7 | 24000 | 29.3 | 15.3 | 13.0 | 11.1 | 357 |
| HFP-mSBC(baslangic) | 8.0 | 7746 | 20.0 | 4.3 | -0.0 | -0.0 | 61 |

### beyaz-gurultu

| aday | snr_20_20k | cutoff_hz | snr_20_4k | snr_4k_10k | snr_10k_16k | snr_16k_20k | kbps |
|---|---|---|---|---|---|---|---|
| PCM-kontrol | 81.1 | 24000 | 81.1 | 81.1 | 81.1 | 81.1 | None |
| PCM-44k1-gidis-donus | 46.1 | 21270 | 46.1 | 46.0 | 46.0 | 46.4 | None |
| AAC-CBR-262k-oto-bant | 7.8 | 17045 | 19.5 | 17.8 | 17.8 | 1.2 | 263 |
| AAC-CBR-262k-bant19293 | 12.0 | 19342 | 18.1 | 15.1 | 15.1 | 6.8 | 263 |
| AAC-CBR-320k-bant19293 | 13.3 | 19342 | 21.3 | 19.5 | 19.4 | 7.2 | 322 |
| AAC-VBR3 | 5.1 | 15809 | 10.7 | 8.9 | 7.9 | -0.0 | 139 |
| AAC-VBR4 | 6.6 | 16553 | 14.3 | 12.6 | 12.6 | 0.5 | 192 |
| AAC-VBR5 | 12.6 | 19342 | 18.9 | 16.9 | 16.9 | 7.0 | 280 |
| SBC-XQ(48k,dual,bp39) | 23.7 | 24000 | 29.4 | 24.6 | 24.5 | 20.3 | 504 |
| SBC(48k,joint,bp53) | 13.0 | 24000 | 20.4 | 15.4 | 12.6 | 9.4 | 357 |
| HFP-mSBC(baslangic) | 1.9 | 7758 | 16.1 | 3.5 | -0.0 | 0.0 | 61 |

### gecici-sesler

| aday | snr_20_20k | cutoff_hz | snr_20_4k | snr_4k_10k | snr_10k_16k | snr_16k_20k | kbps |
|---|---|---|---|---|---|---|---|
| PCM-kontrol | 65.2 | 24000 | 72.0 | 55.3 | 48.6 | 46.9 | None |
| PCM-44k1-gidis-donus | 62.4 | 21158 | 69.5 | 53.1 | 46.4 | 42.3 | None |
| AAC-CBR-262k-oto-bant | 26.2 | 17016 | 37.0 | 28.8 | 28.8 | 1.3 | 263 |
| AAC-CBR-262k-bant19293 | 30.7 | 19312 | 34.9 | 31.0 | 28.5 | 7.7 | 263 |
| AAC-CBR-320k-bant19293 | 31.3 | 19312 | 37.0 | 29.4 | 28.9 | 7.7 | 322 |
| AAC-VBR3 | 19.4 | 16770 | 22.3 | 12.5 | 7.7 | -0.0 | 86 |
| AAC-VBR4 | 22.1 | 16734 | 26.2 | 15.7 | 11.7 | 0.6 | 114 |
| AAC-VBR5 | 26.9 | 19324 | 29.5 | 20.7 | 16.4 | 7.1 | 159 |
| SBC-XQ(48k,dual,bp39) | 35.5 | 24000 | 42.9 | 24.6 | 19.8 | 17.3 | 504 |
| SBC(48k,joint,bp53) | 32.2 | 24000 | 37.5 | 20.0 | 20.7 | 15.9 | 357 |
| HFP-mSBC(baslangic) | 16.4 | 7723 | 21.7 | 6.5 | -0.0 | -0.0 | 61 |

### cok-tonlu

| aday | snr_20_20k | cutoff_hz | snr_20_4k | snr_4k_10k | snr_10k_16k | snr_16k_20k | kbps |
|---|---|---|---|---|---|---|---|
| PCM-kontrol | 83.8 | 24000 | 89.6 | 81.1 | 77.1 | 75.9 | None |
| PCM-44k1-gidis-donus | 67.5 | 21445 | 73.6 | 65.8 | 62.2 | 57.0 | None |
| AAC-CBR-262k-oto-bant | 14.9 | 17145 | 36.3 | 33.0 | 33.3 | 0.0 | 263 |
| AAC-CBR-262k-bant19293 | 35.1 | 20953 | 36.4 | 32.9 | 32.8 | 31.0 | 263 |
| AAC-CBR-320k-bant19293 | 35.1 | 20953 | 36.4 | 32.9 | 32.8 | 31.0 | 322 |
| AAC-VBR3 | 14.2 | 17145 | 23.2 | 20.9 | 21.4 | 0.0 | 44 |
| AAC-VBR4 | 14.6 | 16723 | 26.8 | 23.4 | 24.1 | -0.0 | 50 |
| AAC-VBR5 | 29.4 | 20250 | 30.2 | 27.9 | 27.8 | 26.0 | 66 |
| SBC-XQ(48k,dual,bp39) | 33.8 | 22436 | 43.2 | 31.2 | 25.7 | 25.8 | 504 |
| SBC(48k,joint,bp53) | 45.4 | 24000 | 54.8 | 43.3 | 38.0 | 35.6 | 357 |
| HFP-mSBC(baslangic) | 7.7 | 7500 | 23.2 | 3.6 | 0.0 | 0.0 | 61 |

### brahms-senfoni1(CC0)

| aday | snr_20_20k | cutoff_hz | snr_20_4k | snr_4k_10k | snr_10k_16k | snr_16k_20k | kbps |
|---|---|---|---|---|---|---|---|
| PCM-kontrol | 74.9 | 17783 | 81.9 | 55.5 | 37.9 | 28.6 | None |
| PCM-44k1-gidis-donus | 74.5 | 17783 | 81.5 | 55.1 | 37.5 | 28.2 | None |
| AAC-CBR-262k-oto-bant | 35.0 | 16986 | 35.2 | 23.9 | 17.6 | 2.5 | 262 |
| AAC-CBR-262k-bant19293 | 34.7 | 17777 | 35.0 | 23.2 | 16.3 | 7.9 | 262 |
| AAC-CBR-320k-bant19293 | 36.0 | 17771 | 36.1 | 26.0 | 21.5 | 10.3 | 320 |
| AAC-VBR3 | 25.4 | 15744 | 25.9 | 10.1 | 4.8 | 0.0 | 108 |
| AAC-VBR4 | 29.5 | 16377 | 30.1 | 13.9 | 5.6 | 0.6 | 138 |
| AAC-VBR5 | 33.4 | 17771 | 33.7 | 20.3 | 11.7 | 5.1 | 209 |
| SBC-XQ(48k,dual,bp39) | 53.6 | 18006 | 57.8 | 32.8 | 20.8 | 11.0 | 504 |
| SBC(48k,joint,bp53) | 44.9 | 18000 | 49.4 | 23.7 | 11.6 | 3.5 | 357 |
| HFP-mSBC(baslangic) | 27.4 | 7658 | 29.2 | 7.8 | 0.0 | 0.0 | 61 |
