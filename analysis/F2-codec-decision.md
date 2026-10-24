# F2 — Codec kararı (2026-09-27)

## Girdi 1 — Encoder benchmark (`encoder-benchmark-*.json`, son koşu)

Aynı encoder kütüphaneleri (`libfdk-aac.so.2`, `libsbc.so.1`), canlı transport'tan okunan parametreler.
Metrik: hizalanmış + kazanç eşlenmiş bant-SNR (dB) ve kesim frekansı. **Algısal değil.**

| sinyal | AAC CBR 262k (şu an) | SBC joint bp53 357k | SBC-XQ dual bp39 504k | HFP mSBC (başlangıç) |
|---|---|---|---|---|
| kesim frekansı (pembe gürültü) | **17 039 Hz** | 24 000 | 24 000 | 7 746 |
| Brahms (CC0) 20–20k | 35,0 | 44,9 | 53,6 | 27,4 |
| Brahms 4–10k / 10–16k | 23,9 / 17,6 | 23,7 / 11,6 | 32,8 / 20,8 | 7,8 / 0 |
| geçici sesler 20–20k | 26,2 | 32,2 | 35,5 | 16,4 |
| çok tonlu 20–20k | 14,9 (16–20k=0) | 45,4 | 33,8 | 7,7 |

Ek AAC varyantları: 19 293 Hz zorlanmış bant (PipeWire'ın vbr=0 dalı) kesimi 19,3 kHz'e çıkarır ama bu dalı
kulaklığın seçtiği `vbr=1` bayrağı kapatıyor — kullanıcı tarafında değiştirilemez. VBR 3–5 modları bant-içi SNR'yi
düşürdü (Brahms 4–10k: VBR5 20,3 < CBR 23,9) → **`bitratemode=0` (CBR) kalır** (F2.3 kararı).

## Girdi 2 — Bağlantı sağlığı (`link-health/*.json`, 90 sn, −50 dBFS pembe gürültü)

| codec | karar | reduce (atlanan paket olayı) | bitpool/bitrate |
|---|---|---|---|
| AAC 262k | CLEAN ×2 (60 sn + 90 sn) | 0 | tavanda |
| SBC bp53 | CLEAN | 0 | tavanda |
| SBC-XQ bp39 | **DEGRADED** | **13** | 39→30 testere dişi (`recoveries` dizisi) |

## Karar

1. **SBC-XQ ELENDİ** — bu TWS kulaklık ~504 kbps'yi sürekli taşıyamıyor; her `reduce` en az bir atlanan paket
   (media-sink.c:1094 yorumu: "There will be a sound glitch in any case").
2. **AAC CBR (bitratemode 0) ↔ SBC bp53** — ikisi de temiz bağlantı. Nesnel SNR SBC'yi gösteriyor, fakat SNR AAC'nin
   algısal gürültü şekillendirmesini cezalandırır ve 17 kHz üstü çoğu yetişkin için duyulmaz. Nesnel veri bu ikisini
   ayıramaz → **kör ABX dinleme testi** (F2.4, `bta abx`) nihai karardır. O zamana kadar varsayılan **AAC** (mevcut,
   kullanıcı tarafından HFP'ye göre iyi bulunan durum).
3. HFP/mSBC'nin kaybı sayısal olarak kanıtlandı: 7,7 kHz bant + tüm üst bantlarda 0 dB SNR.
