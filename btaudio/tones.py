"""D7.3 — oturma (seal) testi tonları (infrastructure).

Kısa sinüs, 30 ms yükseltilmiş-kosinüs giriş/çıkış (açma/kapama tıkı olmasın), sabit seviye (dBFS tepe).
Çalma: pw-play → hedef sink (kulaklık). Alt süreç `procs.spawn` ile (ebeveynle ölür, E23)."""
from __future__ import annotations

import os
import subprocess
import tempfile

import numpy as np
from scipy.io import wavfile

from . import procs

FS = 48000
FADE_S = 0.03


def tone(freq: float, seconds: float, level_db: float) -> np.ndarray:
    """Stereo float32 sinüs: seviye dBFS tepe, 30 ms yükseltilmiş-kosinüs giriş/çıkış."""
    n = int(FS * seconds)
    t = np.arange(n) / FS
    x = 10 ** (level_db / 20) * np.sin(2 * np.pi * freq * t)
    k = int(FADE_S * FS)
    ramp = 0.5 - 0.5 * np.cos(np.pi * np.arange(k) / k)
    x[:k] *= ramp
    x[n - k:] *= ramp[::-1]
    return np.stack([x, x], 1).astype(np.float32)


class _Handle:
    def __init__(self, proc, path):
        self.proc, self.path = proc, path

    def stop(self):
        p, self.proc = self.proc, None
        if p and p.poll() is None:
            p.terminate()                                 # yalnız KENDİ alt sürecimiz
            try:
                p.wait(timeout=2)
            except subprocess.TimeoutExpired:
                p.kill()
        try:
            os.remove(self.path)
        except OSError:
            pass


def player(target: str | None):
    """Session.tone_player için çağrılabilir: (freq, seconds, level_db) → durdurulabilir tanıtıcı."""
    def play(freq, seconds, level_db):
        fd, path = tempfile.mkstemp(prefix="bta-tone-", suffix=".wav")
        os.close(fd)
        wavfile.write(path, FS, tone(freq, seconds, level_db))
        cmd = ["pw-play"] + (["--target", target] if target else []) + [path]
        return _Handle(procs.spawn(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL), path)
    return play
