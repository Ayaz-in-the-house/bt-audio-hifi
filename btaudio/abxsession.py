"""PRD-BTA05 E1 — Konsoldaki kör ABX testi (application): terminal soru-cevabı yerine düğmeli, adım adım test.

Akış: klip (kullanıcının KENDİ müziğinden 12 sn, EQ öncesi dijital dokunuş = codec'ten önce) → 12 deneme (A, B, X
istenildiği kadar dinlenir; X dinlenmeden cevap verilemez) → sonuç (binom p; 12'de ≥10 doğru → fark duyuluyor) →
fark varsa tercih → "uygula" (karar kaydı + codec) ya da orijinal codec'e dönüş.

Kurallar (abx.py ile aynı istatistik): denemeler 6A/6B karışık; her çalmada ÖNCE diğer codec'e SONRA hedefe geçilir
→ her çalmada aynı geçiş dizisi = geçişin kendisi ipucu olamaz. Test boyunca otomasyon askıdadır (test sesi türü
değiştirmesin). Codec değiştirici / çalar / otomasyon dışarıdan verilir (testlerde sahte; U69)."""
from __future__ import annotations

import datetime as _dt
import json
import os
import threading

import numpy as np
from scipy.io import wavfile

from . import abx

MUSIC_MIN_DBFS = -60.0            # klibin RMS'i bunun altındaysa "müzik çalmıyor" (analizör eşiği −80; klip için daha sıkı)
FADE_S = 0.03


class NotReady(Exception):
    """İstenen adımın ön koşulu yok (ör. X dinlenmeden cevap)."""


class Busy(Exception):
    """Bir çalma/codec geçişi sürüyor."""


class NoMusic(Exception):
    """Klip sessiz — müzik çalarken tekrar dene."""


def capture_clip(recorder, out_dir: str, seconds: float = 12.0) -> str:
    """`recorder(path, seconds)` EQ öncesi dokunuştan stereo 48 kHz kaydeder. Klip seviyesi ölçülür (sessizse NoMusic),
    uçlar 30 ms yumuşatılır (açma/kapama tıkı ABX'e ipucu olmasın), 16 bit wav olarak saklanır."""
    os.makedirs(out_dir, exist_ok=True)
    stamp = _dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    raw = os.path.join(out_dir, f"raw-{stamp}.wav")
    recorder(raw, seconds)
    fs, y = wavfile.read(raw)
    os.remove(raw)
    scale = 32768.0 if y.dtype.kind == "i" else 1.0                 # int16 kayıt → ±1 ölçeği
    y = y.astype(np.float64) / scale
    if y.ndim == 1:
        y = np.stack([y, y], 1)
    n = int(fs * seconds)
    y = y[-n:] if len(y) >= n else y
    rms = 10 * np.log10(max(float(np.mean(y ** 2)), 1e-30))
    if rms < MUSIC_MIN_DBFS:
        raise NoMusic(f"klip seviyesi {rms:.0f} dBFS — müzik çalmıyor ya da çok kısık")
    k = int(FADE_S * fs)
    ramp = 0.5 - 0.5 * np.cos(np.pi * np.arange(k) / k)
    y[:k] *= ramp[:, None]
    y[len(y) - k:] *= ramp[::-1][:, None]
    path = os.path.join(out_dir, f"clip-{stamp}.wav")
    wavfile.write(path, fs, np.clip(y * 32767, -32768, 32767).astype(np.int16))
    return path


class AbxSession:
    """Tek kullanıcılı kör test durum makinesi: idle → trial (12 deneme) → result → (finish) idle."""

    def __init__(self, switcher, player, current_codec, results_dir, n=12, seed=None, automation=None, on_apply=None):
        self.switcher, self.player, self.current_codec = switcher, player, current_codec
        self.results_dir, self.n, self.seed = results_dir, n, seed
        self.automation, self.on_apply = automation, on_apply
        self.lock = threading.Lock()
        self._reset()

    def _reset(self):
        self.phase, self.codec_a, self.codec_b, self.clip, self.original = "idle", None, None, None, None
        self._trials, self._answers, self.i = [], [], 0
        self.played, self.busy, self.now_playing, self.error = set(), False, None, None
        self.result, self.preference, self._handle = None, None, None

    # ── akış ──
    def start(self, codec_a, codec_b, clip):
        with self.lock:
            if self.phase != "idle":
                raise Busy("test zaten sürüyor")
            if not clip:
                raise NotReady("önce test klibi seç")
            self.codec_a, self.codec_b, self.clip = codec_a, codec_b, clip
            self.original = self.current_codec()
            self._trials = abx.make_trials(self.n, self.seed)
            self.phase = "trial"
        if self.automation is not None:
            self.automation.hold("kör test")
        return self.status()

    def play(self, which):
        with self.lock:
            if self.phase != "trial":
                raise NotReady("test başlamadı")
            if which not in ("A", "B", "X"):
                raise KeyError(which)
            if self.busy:
                raise Busy("bir çalma sürüyor")
            x = self._trials[self.i]
            target = {"A": self.codec_a, "B": self.codec_b, "X": self.codec_a if x == "A" else self.codec_b}[which]
            other = self.codec_b if target == self.codec_a else self.codec_a
            self.busy, self.now_playing, self.error = True, which, None
        threading.Thread(target=self._play, args=(which, target, other), daemon=True, name="bta-abx").start()
        return self.status()

    def _play(self, which, target, other):
        try:
            for c in abx.switch_plan(target, other):                  # önce diğeri, sonra hedef: sabit ipucu
                if not self.switcher(c):
                    raise RuntimeError(f"codec {c} etkinleşmedi")
            h = self.player(self.clip)
            self._handle = h
            h.wait(timeout=120)
            with self.lock:
                self.played.add(which)
        except Exception as e:                                        # hata görünür, test bozulmaz
            self.error = str(e)[:200]
        finally:
            with self.lock:
                self.busy, self.now_playing, self._handle = False, None, None

    def answer(self, which):
        with self.lock:
            if self.phase != "trial":
                raise NotReady("test başlamadı")
            if self.busy:
                raise Busy("çalma bitmeden cevap verilemez")
            if "X" not in self.played:
                raise NotReady("önce X'i dinle")
            if which not in ("A", "B"):
                raise KeyError(which)
            self._answers.append(which)
            self.i += 1
            self.played = set()
            if self.i >= self.n:
                correct = sum(1 for a, x in zip(self._answers, self._trials) if a == x)
                self.result = abx.verdict(correct, self.n)
                self.phase = "result"
        return self.status()

    def prefer(self, codec):
        with self.lock:
            if self.phase != "result" or not self.result["distinguishable"]:
                raise NotReady("fark kanıtlanmadan tercih sorulmaz")
            if codec not in (self.codec_a, self.codec_b, "eşit"):
                raise KeyError(codec)
            self.preference = None if codec == "eşit" else codec
        return self.status()

    def finish(self, apply=False):
        with self.lock:
            if self.phase != "result":
                raise NotReady("test bitmedi")
            res = {"at": _dt.datetime.now().astimezone().isoformat(timespec="seconds"), "codec_a": self.codec_a,
                   "codec_b": self.codec_b, "clip": os.path.basename(self.clip), "trials": self._trials,
                   "answers": self._answers, **self.result, "preference": self.preference,
                   "applied": bool(apply and self.preference), "source": "console"}
            final = self.preference if (apply and self.preference) else self.original
        self.switcher(final)
        if apply and self.preference and self.on_apply:
            self.on_apply({"codec": self.preference, "evidence": res})
        os.makedirs(self.results_dir, exist_ok=True)
        with open(os.path.join(self.results_dir, f"{_dt.datetime.now():%Y%m%d-%H%M%S}-{self.codec_a}-vs-{self.codec_b}.json"), "w") as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        self._end()
        return res

    def abort(self):
        h = self._handle
        if h is not None:
            try:
                h.stop()
            except Exception:
                pass
        orig = self.original
        if self.phase != "idle" and orig:
            self.switcher(orig)
        self._end()
        return self.status()

    def _end(self):
        if self.phase != "idle" and self.automation is not None:
            self.automation.release()
        self._reset()

    def status(self):
        return {"phase": self.phase, "trial": self.i + 1 if self.phase == "trial" else None, "n": self.n,
                "codecs": [self.codec_a, self.codec_b] if self.codec_a else None,
                "clip": os.path.basename(self.clip) if self.clip else None,
                "x_played": "X" in self.played, "played": sorted(self.played), "busy": self.busy,
                "now_playing": self.now_playing, "error": self.error, "result": self.result,
                "preference": self.preference, "original": self.original}
