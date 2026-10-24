"""F2.4 — Kör ABX dinleme testi (ITU-R BS.1116 ruhunda: kör, dengeli, istatistiksel karar).

Her denemede A, B ve bilinmeyen X çalınır; dinleyici X'in A mı B mi olduğunu söyler. 12 denemede ≥10 doğru
(p < 0.05) → fark duyuluyor; ardından tercih sorulur. Profil geçişinin kendisi ipucu olmasın diye her çalmadan önce
ÖNCE diğer codec'e SONRA hedefe geçilir (her çalmada aynı geçiş dizisi = sabit ipucu).
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import os
import random
import subprocess
import tempfile
import time

from . import collect

PROFILES = {"aac": "a2dp-sink", "sbc": "a2dp-sink-sbc", "sbc_xq": "a2dp-sink-sbc_xq"}


def p_value(correct: int, n: int) -> float:
    """Tek yönlü binom: şansla (p=0.5) en az `correct` doğru olasılığı."""
    return sum(math.comb(n, k) for k in range(correct, n + 1)) / 2 ** n


def make_trials(n: int, seed=None) -> list:
    t = ["A"] * (n // 2) + ["B"] * (n - n // 2)
    random.Random(seed).shuffle(t)
    return t


def verdict(correct: int, n: int, alpha: float = 0.05) -> dict:
    p = p_value(correct, n)
    return {"correct": correct, "n": n, "p_value": round(p, 5), "distinguishable": p < alpha}


def switch_plan(target: str, other: str) -> list:
    return [other, target]


def _set_codec(codec: str, timeout=15) -> bool:
    subprocess.run(["pactl", "set-card-profile", collect.CARD, PROFILES[codec]], timeout=10)
    t0 = time.time()
    while time.time() - t0 < timeout:
        s = collect._safe(collect.sink)
        if s.get("present") and s.get("codec") == codec:
            return True
        time.sleep(0.3)
    return False


def excerpt(clip: str, start: float, dur: float) -> str:
    out = os.path.join(tempfile.gettempdir(), f"bta-abx-{os.path.basename(clip)}-{start}-{dur}.wav")
    if not os.path.exists(out):
        fade = f"afade=t=in:d=0.03,afade=t=out:st={dur - 0.05}:d=0.05"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-ss", str(start), "-t", str(dur),
                        "-i", clip, "-af", f"aresample=48000:resampler=soxr,{fade}",
                        "-ac", "2", "-c:a", "pcm_s16le", out], check=True, timeout=120)
    return out


def play_as(codec: str, other: str, wav: str):
    for c in switch_plan(codec, other):
        if not _set_codec(c):
            raise RuntimeError(f"codec {c} etkinleşmedi")
    time.sleep(0.8)                                   # transport otursun
    subprocess.run(["pw-play", "--target", collect.sink()["name"], wav], timeout=120)


def run(codec_a="aac", codec_b="sbc", clip=None, n=12, start=0.0, dur=8.0, answers=None, apply=False,
        out_dir=None, log=print, ask=input) -> dict:
    """answers: yalnız otomatik (headful duman) test için önceden verilmiş cevaplar listesi."""
    wav = excerpt(clip, start, dur)
    original = collect.sink().get("codec")
    trials = make_trials(n)
    got = []
    try:
        for i, x in enumerate(trials, 1):
            while True:
                log(f"\n— Deneme {i}/{n} —  A, sonra B, sonra X çalacak")
                log("  ▶ A");  play_as(codec_a, codec_b, wav)
                log("  ▶ B");  play_as(codec_b, codec_a, wav)
                log("  ▶ X");  play_as(codec_a if x == "A" else codec_b, codec_b if x == "A" else codec_a, wav)
                a = (answers[i - 1] if answers else ask("  X hangisi? [a/b, r=tekrar dinle]: ")).strip().lower()
                if a in ("a", "b"):
                    got.append(a.upper())
                    break
        correct = sum(1 for g, x in zip(got, trials) if g == x)
        v = verdict(correct, n)
        pref = None
        if v["distinguishable"] and not answers:
            pref = ask(f"  Fark duyuluyor (p={v['p_value']}). Hangisi DAHA İYİ? [a={codec_a}/b={codec_b}/e=eşit]: ")
            pref = {"a": codec_a, "b": codec_b}.get(pref.strip().lower())
        res = {"at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"), "codec_a": codec_a,
               "codec_b": codec_b, "clip": clip, "start": start, "dur": dur, "trials": trials, "answers": got,
               **v, "preference": pref, "scripted": bool(answers)}
    finally:
        final = res.get("preference") if (apply and "res" in locals()) else None
        _set_codec(final or original)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, f"{_dt.datetime.now():%Y%m%d-%H%M%S}-{codec_a}-vs-{codec_b}.json"), "w") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
    return res
