"""F2.2 — Encoder benchmark. Kulaklığa giden encoder ile AYNI kütüphane (/lib64/libfdk-aac.so.2) ffmpeg üzerinden
sürülür; her aday kodlanır → çözülür → 48 kHz'e döner → referansla hizalanır + kazanç eşlenir → metrikler.

Dürüstlük notları (rapora da yazılır):
  * Metrikler algısal DEĞİL (PEAQ/ViSQOL kurulu değil); bant-SNR ve kesim frekansıdır. Nihai hakem kör A/B dinleme.
  * Kulaklığın DECODER'ı bilinmiyor; burada ffmpeg decoder'ı kullanılır.
  * SBC adayları ffmpeg ile DEĞİL, PipeWire'ın bağlandığı aynı libsbc (ctypes) ile, canlı transport'tan okunan
    parametrelerle kodlanır (ffmpeg SBC kanal modu/alt-bant seçtirmiyor — ölçüldü, E9).
"""
from __future__ import annotations

import json
import os
import subprocess

import numpy as np
from scipy.io import wavfile

from . import analysis, codecs

FS = 48000
BANDS = [(20, 4000), (4000, 10000), (10000, 16000), (16000, 20000)]

SBC_PARAMS = {  # ad → libsbc Codec argümanları
    "SBC-XQ(48k,dual,bp39)": dict(rate=48000, mode="dual", bitpool=39),
    "SBC(48k,joint,bp53)": dict(rate=48000, mode="joint", bitpool=53),
    "HFP-mSBC(baslangic)": dict(msbc=True),
}

# ad → (ffmpeg encoder argümanları, kodlama örnekleme hızı, kanal, konteyner uzantısı, açıklama)
CANDIDATES = {
    "PCM-kontrol": ([], FS, 2, "wav", "kayıpsız — hattın kendi hatası (≫100 dB beklenir)"),
    "PCM-44k1-gidis-donus": ([], 44100, 2, "wav", "yalnız 48→44.1→48 resample hatası (resampler kontrolü)"),
    "AAC-CBR-262k-oto-bant": (["-c:a", "libfdk_aac", "-b:a", "262144", "-afterburner", "1"], FS, 2, "adts",
                              "ŞU AN kulaklıkta çalışan: vbr=1 bayrağı → 19,3 kHz dalı atlanır"),
    "AAC-CBR-262k-bant19293": (["-c:a", "libfdk_aac", "-b:a", "262144", "-afterburner", "1", "-cutoff", "19293"],
                               FS, 2, "adts", "aynı bitrate, PipeWire'ın vbr=0 dalındaki bant"),
    "AAC-CBR-320k-bant19293": (["-c:a", "libfdk_aac", "-b:a", "320000", "-afterburner", "1", "-cutoff", "19293"],
                               FS, 2, "adts", "PipeWire AAC teorik tavanı"),
    **{f"AAC-VBR{m}": (["-c:a", "libfdk_aac", "-vbr", str(m), "-afterburner", "1"], FS, 2, "adts",
                       f"bluez5.a2dp.aac.bitratemode={m}") for m in (3, 4, 5)},
    # SBC: PipeWire'ın bağlandığı AYNI libsbc, canlı transport'tan okunan parametrelerle (2026-09-27 19:3x)
    "SBC-XQ(48k,dual,bp39)": ("libsbc", FS, 2, "sbc", "canlı sbc_xq transport: 48k dual bitpool 39 ≈504 kbps"),
    "SBC(48k,joint,bp53)": ("libsbc", FS, 2, "sbc", "canlı sbc transport: 48k joint bitpool 53 ≈357 kbps"),
    "HFP-mSBC(baslangic)": ("libsbc", 16000, 1, "sbc", "oturum başındaki durum: mSBC mono 16 kHz"),
}


def _ff(*args, timeout=300):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True, timeout=timeout)


def make_signals(out_dir: str, brahms: str | None = None, seconds: int = 10) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(20260927)
    n = FS * seconds
    sig = {}

    def pink(n_):
        X = np.fft.rfft(rng.standard_normal(n_))
        f = np.fft.rfftfreq(n_, 1 / FS)
        X[1:] /= np.sqrt(f[1:])
        X[0] = 0
        return np.fft.irfft(X, n=n_)

    def norm(x, rms_db):
        return x / np.sqrt(np.mean(x ** 2)) * 10 ** (rms_db / 20)

    sig["pembe-gurultu"] = np.stack([norm(pink(n), -20), norm(pink(n), -20)], 1)
    sig["beyaz-gurultu"] = np.stack([norm(rng.standard_normal(n), -20), norm(rng.standard_normal(n), -20)], 1)
    t = np.arange(n) / FS
    bed = norm(pink(n), -45)
    clicks = np.zeros(n)
    for k in range(0, n, FS // 4):                               # kastanyet benzeri geçici sesler (pre-echo)
        L = min(2400, n - k)
        env = np.exp(-np.arange(L) / 180.0)
        clicks[k:k + L] += env * np.sin(2 * np.pi * 3100 * np.arange(L) / FS) * 0.5
    sig["gecici-sesler"] = np.stack([bed + clicks, bed + np.roll(clicks, 37)], 1)
    freqs = np.geomspace(40, 18000, 31)
    mt = sum(np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi)) for f in freqs) * 10 ** (-30 / 20)
    sig["cok-tonlu"] = np.stack([mt, mt], 1)
    paths = {}
    for name, x in sig.items():
        p = os.path.join(out_dir, f"sig-{name}.wav")
        wavfile.write(p, FS, np.clip(x, -1, 1).astype(np.float32))
        paths[name] = p
    if brahms and os.path.exists(brahms):
        paths["brahms-senfoni1(CC0)"] = brahms
    return paths


def _read(path):
    fs, x = wavfile.read(path)
    if x.dtype.kind == "i":                     # tamsayı PCM → [-1, 1] (kontrol dönüşümden ÖNCE)
        return fs, x.astype(np.float64) / np.iinfo(x.dtype).max
    return fs, x.astype(np.float64)


def run_candidate(name: str, ref_path: str, tmp: str) -> str:
    args, rate, ch, ext, _ = CANDIDATES[name]
    stem = os.path.join(tmp, f"{os.path.basename(ref_path)[:-4]}__{name.replace('/', '_')}")
    enc = f"{stem}.{ext}"
    pre = ["-af", f"aresample={rate}:resampler=soxr:precision=28,aformat=sample_fmts=s16:channel_layouts="
           + ("mono" if ch == 1 else "stereo")]
    if ext == "wav":
        _ff("-i", ref_path, *pre, "-c:a", "pcm_s16le", enc)
    elif args == "libsbc":
        from . import sbclib
        src = f"{stem}.src.wav"
        _ff("-i", ref_path, *pre, "-c:a", "pcm_s16le", src)
        _, pcm = wavfile.read(src)
        c = sbclib.Codec(**SBC_PARAMS[name])
        data = c.encode(pcm)
        c.close()
        with open(enc, "wb") as f:
            f.write(data)
        d = sbclib.Codec(**SBC_PARAMS[name])
        y = d.decode(data)
        d.close()
        raw_dec = f"{stem}.sbcdec.wav"
        wavfile.write(raw_dec, rate, y)
        dec = f"{stem}.dec.wav"
        _ff("-i", raw_dec, "-af", f"aresample={FS}:resampler=soxr:precision=28,aformat=sample_fmts=flt:"
            "channel_layouts=stereo", "-c:a", "pcm_f32le", dec)
        return enc, dec
    else:
        _ff("-i", ref_path, *pre, *args, "-f", ext, enc)
    dec = f"{stem}.dec.wav"
    _ff("-i", enc, "-af", f"aresample={FS}:resampler=soxr:precision=28,aformat=sample_fmts=flt:channel_layouts=stereo",
        "-c:a", "pcm_f32le", dec)
    return enc, dec


def metrics(ref_path: str, dec_path: str) -> dict:
    _, ref = _read(ref_path)
    _, dec = _read(dec_path)
    r, d = analysis.align(ref, dec)
    r, d = analysis.gain_matched(r, d)
    m = {"snr_20_20k": round(analysis.band_snr_db(r, d, FS, 20, 20000), 1),
         "cutoff_hz": round(analysis.cutoff_frequency(d, FS))}
    for lo, hi in BANDS:
        m[f"snr_{lo // 1000 if lo >= 1000 else lo}k_{hi // 1000}k".replace("20k_4k", "20_4k")] = round(
            analysis.band_snr_db(r, d, FS, lo, hi), 1)
    return m


def run(signals: dict, tmp: str, candidates=None) -> dict:
    res = {}
    for sname, spath in signals.items():
        res[sname] = {}
        for cname in (candidates or CANDIDATES):
            enc, dec = run_candidate(cname, spath, tmp)
            dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                                        "csv=p=0", spath], capture_output=True, text=True).stdout.strip() or 0)
            m = metrics(spath, dec)
            m["kbps"] = round(os.path.getsize(enc) * 8 / dur / 1000) if dur and not enc.endswith(".wav") else None
            res[sname][cname] = m
    return res


def to_markdown(res: dict) -> str:
    out = []
    for sname, rows in res.items():
        out.append(f"\n### {sname}\n")
        cols = list(next(iter(rows.values())).keys())
        out.append("| aday | " + " | ".join(cols) + " |")
        out.append("|---|" + "---|" * len(cols))
        for cname, m in rows.items():
            out.append(f"| {cname} | " + " | ".join(str(m[c]) for c in cols) + " |")
    return "\n".join(out)


def save(res: dict, out_dir: str, stamp: str):
    with open(os.path.join(out_dir, f"encoder-benchmark-{stamp}.json"), "w") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
