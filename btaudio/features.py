"""D3.1 — Müzik karakteri öznitelikleri (domain, saf). Girdi: 1/6 okt bant gücü (dBFS, analizör LTAS'ı).

Ölçüt: her bölgenin 1/6 okt bantlarının GÜÇ ortalaması, orta bölgeye (500 Hz–2 kHz) göre dB. Bant-gücü gösteriminde
pembe gürültü düzdür (R31) → pembe = tüm bölgeler 0 dB. (İlk sürüm "pay oranı" kullanıyordu; pay doygunlaştığı için
+12 dB bas yalnız +3,8 dB görünüyordu — U54 yakaladı.) Türden bağımsız ölçülmüş tonal denge; R37 (Dolby IEQ) girdisi."""
from __future__ import annotations

import math

import numpy as np

REGIONS = {"sub": (20, 60), "bas": (60, 250), "alt_orta": (250, 500), "orta": (500, 2000),
           "varlık": (2000, 5000), "hava": (5000, 16000)}


def region_excess(bands_db, centers) -> dict | None:
    """Bölgelerin (sub…hava) orta bölgeye göre güç ortalaması farkı (dB); sessizlikte None."""
    b = np.asarray(bands_db, float)
    c = np.asarray(centers, float)
    if np.max(b) <= -100:
        return None                                 # sessizlik → karar yok
    lvl = {}
    for k, (lo, hi) in REGIONS.items():
        m = (c >= lo) & (c < hi)
        lvl[k] = 10 * math.log10(float(np.mean(10 ** (b[m] / 10))) + 1e-30)
    ref = lvl["orta"]
    return {k: round(v - ref, 2) for k, v in lvl.items()}


def character(ex: dict | None) -> list:
    """Okunur karakter etiketleri (arayüz + kontrolörler)."""
    if not ex:
        return []
    tags = []
    low = 10 * math.log10((10 ** (ex["sub"] / 10) + 10 ** (ex["bas"] / 10)) / 2)
    if low >= 6:
        tags.append("bas ağırlıklı")
    elif low <= -3:
        tags.append("bas az")
    if ex["sub"] >= 6:
        tags.append("derin sub")
    if max(ex["varlık"], ex["hava"]) >= 3:
        tags.append("parlak")
    elif max(ex["varlık"], ex["hava"]) <= -6:
        tags.append("tiz az")                       # koyu / boğuk kayıt (canlı ölçüm: konuşma kaydı −10 dB)
    if ex["varlık"] >= 3 and ex["bas"] < 6:
        tags.append("vokal öne")
    if not tags:
        tags.append("dengeli")
    return tags
