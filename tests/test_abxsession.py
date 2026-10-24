"""U69–U70: konsoldaki kör ABX testi (PRD-BTA05 E1) — sahte codec değiştirici / çalar / kaydedici (ses çıkmaz).

U69 motor: 12 deneme 6A/6B karışık · her çalma = [diğer codec, hedef codec] (geçişin kendisi ipucu olmasın) · X
    dinlenmeden cevap YOK · 10/12 → ayırt edilebilir + tercih · 9/12 → tercih sorulmaz · bitişte/iptalde ORİJİNAL codec
    (uygula seçilmediyse) · "uygula" → tercih edilen codec + karar kaydı · test boyunca otomasyon askıda.
U70 klip: kendi müziğinden 12 sn (EQ öncesi dokunuş) · sessizse ret · uçlar yumuşatılmış (tık yok) · klip XDG'de."""
import os
import sys
import tempfile
import threading
import time
import unittest

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import abxsession  # noqa: E402


class FakeCodec:
    def __init__(self, current="aac"):
        self.current, self.log = current, []

    def __call__(self, codec):
        self.log.append(codec)
        self.current = codec
        return True


class FakePlayer:
    def __init__(self):
        self.played = []

    def __call__(self, wav):
        self.played.append(wav)
        return self

    def wait(self, timeout=None):
        return 0

    def stop(self):
        pass


class Hold:
    def __init__(self):
        self.held = 0

    def hold(self, reason):
        self.held += 1

    def release(self):
        self.held -= 1


def session(tmp, seed=7, **kw):
    codec, player, hold, decisions = FakeCodec(), FakePlayer(), Hold(), []
    s = abxsession.AbxSession(switcher=codec, player=player, current_codec=lambda: codec.current,
                              results_dir=os.path.join(tmp, "results"), seed=seed, automation=hold,
                              on_apply=decisions.append, **kw)
    return s, codec, player, hold, decisions


def wait_idle(s, t=3.0):
    t0 = time.time()
    while s.status()["busy"] and time.time() - t0 < t:
        time.sleep(0.01)


def play_all(s):
    for w in ("A", "B", "X"):
        s.play(w)
        wait_idle(s)


class TestEngine(unittest.TestCase):
    def test_u69_trials_balanced_switch_order_and_x_before_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, codec, player, hold, _ = session(tmp)
            s.start("aac", "sbc", clip="/k.wav")
            self.assertEqual(hold.held, 1)                                   # otomasyon askıda
            self.assertEqual(sorted(s._trials), ["A"] * 6 + ["B"] * 6)
            with self.assertRaises(abxsession.NotReady):
                s.answer("A")                                                # X dinlenmedi
            s.play("A")
            wait_idle(s)
            self.assertEqual(codec.log[-2:], ["sbc", "aac"])                # A=aac: önce diğeri, sonra hedef
            s.play("X")
            wait_idle(s)
            x = s._trials[0]
            self.assertEqual(codec.log[-2:], ["sbc", "aac"] if x == "A" else ["aac", "sbc"])
            st = s.answer("A")
            self.assertEqual(st["trial"], 2)
            self.assertFalse(st["x_played"])                                 # yeni denemede X yeniden dinlenmeli

    def test_u69_verdict_preference_and_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, codec, player, hold, decisions = session(tmp)
            s.start("aac", "sbc", clip="/k.wav")
            for i, x in enumerate(list(s._trials)):
                play_all(s)
                s.answer(x if i < 10 else ("B" if x == "A" else "A"))        # 10/12 doğru
            st = s.status()
            self.assertEqual((st["phase"], st["result"]["correct"], st["result"]["distinguishable"]), ("result", 10, True))
            s.prefer("sbc")
            res = s.finish(apply=True)
            self.assertEqual(codec.current, "sbc")                           # tercih uygulandı
            self.assertEqual(decisions[-1]["codec"], "sbc")
            self.assertEqual(hold.held, 0)                                   # otomasyon serbest
            self.assertTrue(os.listdir(os.path.join(tmp, "results")))        # sonuç kaydı
            self.assertEqual(res["preference"], "sbc")

    def test_u69_not_distinguishable_keeps_original_and_abort_restores(self):
        with tempfile.TemporaryDirectory() as tmp:
            s, codec, player, hold, decisions = session(tmp)
            s.start("aac", "sbc", clip="/k.wav")
            for i, x in enumerate(list(s._trials)):
                play_all(s)
                s.answer(x if i < 9 else ("B" if x == "A" else "A"))         # 9/12
            self.assertFalse(s.status()["result"]["distinguishable"])
            with self.assertRaises(abxsession.NotReady):
                s.prefer("sbc")                                              # fark kanıtlanmadıysa tercih yok
            s.finish(apply=True)
            self.assertEqual(codec.current, "aac")                           # orijinal
            self.assertEqual(decisions, [])
            s2, codec2, _, hold2, _ = session(tmp)
            s2.start("aac", "sbc", clip="/k.wav")
            s2.play("B")
            wait_idle(s2)
            self.assertEqual(codec2.current, "sbc")
            s2.abort()
            self.assertEqual(codec2.current, "aac")                          # iptal → orijinal
            self.assertEqual(hold2.held, 0)
            self.assertEqual(s2.status()["phase"], "idle")

    def test_u69_busy_rejects_parallel_play(self):
        with tempfile.TemporaryDirectory() as tmp:
            gate = threading.Event()

            class SlowPlayer(FakePlayer):
                def wait(self, timeout=None):
                    gate.wait(2)
            s, codec, _, _, _ = session(tmp)
            s.player = SlowPlayer()
            s.start("aac", "sbc", clip="/k.wav")
            s.play("A")
            with self.assertRaises(abxsession.Busy):
                s.play("B")
            gate.set()
            wait_idle(s)
            s.abort()


class TestClip(unittest.TestCase):
    def fake_recorder(self, signal):
        def rec(path, seconds):
            n = int(48000 * seconds)
            t = np.arange(n) / 48000
            x = signal(t)
            wavfile.write(path, 48000, np.stack([x, x], 1).astype(np.float32))
        return rec

    def test_u70_clip_from_music_and_silence_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            music = self.fake_recorder(lambda t: 0.2 * np.sin(2 * np.pi * 440 * t))
            path = abxsession.capture_clip(music, os.path.join(tmp, "clips"), seconds=12.0)
            fs, y = wavfile.read(path)
            self.assertEqual((fs, y.shape[1]), (48000, 2))
            self.assertAlmostEqual(len(y) / fs, 12.0, delta=0.01)
            self.assertLess(abs(float(y[0, 0])), 1e-3)                       # yumuşak giriş (tık yok)
            self.assertLess(abs(float(y[-1, 0])), 1e-3)                      # yumuşak çıkış
            def int16_rec(path, seconds):                                   # 16 bit kaydedici de doğru ölçeklenmeli
                t = np.arange(int(48000 * seconds)) / 48000
                x = (0.2 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
                wavfile.write(path, 48000, np.stack([x, x], 1))
            p16 = abxsession.capture_clip(int16_rec, os.path.join(tmp, "clips"), seconds=12.0)
            _, y16 = wavfile.read(p16)
            self.assertAlmostEqual(float(np.max(np.abs(y16))) / 32767, 0.2, delta=0.01)
            silent = self.fake_recorder(lambda t: 1e-5 * np.sin(2 * np.pi * 440 * t))
            with self.assertRaises(abxsession.NoMusic):
                abxsession.capture_clip(silent, os.path.join(tmp, "clips"), seconds=12.0)


if __name__ == "__main__":
    unittest.main()
