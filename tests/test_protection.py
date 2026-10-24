"""U65: sürücü koruma + codec farkındalığı uyarıları (D7.2) ve oturma testi tonu (D7.3).

Eşikler ölçümden (hazır tarzların 20–100 Hz en büyük takviyesi +10,9 dB → uyarı > +12 dB, hazır tarz yanlış alarm vermez).
AAC bu bağlantıda ~17 kHz'de keser (R4/R41) → 17 kHz üstü takviye DUYULMAZ ama preamp'i (toplam sesi) düşürür."""
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import console, consoleserver  # noqa: E402


def st(*bands):
    s = console.default_state()
    for i, (t, f, g, q) in enumerate(bands):
        s["bands"][i].update(type=t, freq=float(f), gain=float(g), q=float(q), enabled=True)
    return console.sanitize(s)


def codes(w):
    return sorted(x["code"] for x in w)


class TestWarnings(unittest.TestCase):
    def test_u65_stock_presets_do_not_false_alarm_for_driver(self):
        for k in console.PRESETS:
            w = console.protection_warnings(console.apply_preset(console.default_state(), k), codec="sbc")
            self.assertNotIn("bass_high", codes(w), k)
            self.assertNotIn("sub_infra", codes(w), k)

    def test_u65_bass_high_and_infrasonic(self):
        w = console.protection_warnings(st(("lowshelf", 60, 12, 0.7), ("bell", 45, 6, 1.0)), codec="aac")
        self.assertIn("bass_high", codes(w))
        self.assertEqual(next(x for x in w if x["code"] == "bass_high")["level"], "warn")
        w = console.protection_warnings(st(("lowshelf", 15, 12, 0.7)), codec="aac")
        self.assertIn("sub_infra", codes(w))

    def test_u65_hf_boost_is_codec_aware(self):
        s = console.apply_preset(console.default_state(), "elektronik")          # 17k+ +7,3 dB (VLC kaynaklı)
        w = console.protection_warnings(s, codec="aac")
        hf = next(x for x in w if x["code"] == "hf_aac")
        self.assertEqual(hf["level"], "info")
        self.assertIn("preamp", hf["text"])
        self.assertNotIn("hf_aac", codes(console.protection_warnings(s, codec="sbc")))
        self.assertEqual(console.protection_warnings(console.default_state(), codec="aac"), [])

    def test_u65_view_uses_effective_state_including_adl(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess = consoleserver.Session(Rec(), lambda s: None, profiles_dir=tmp, device={"codec": "aac"})
            sess.set_state(st(("lowshelf", 60, 10, 0.7)))
            self.assertNotIn("bass_high", codes(sess.view()["warnings"]))
            sess.set_auto_offsets({"bas": 4.0})                                   # ADL üstüne eklenince eşik aşılır
            self.assertIn("bass_high", codes(sess.view()["warnings"]))


class Rec:
    def __init__(self):
        self.n = 0

    def apply_payload(self, p):
        self.n += 1


class FakePlayer:
    def __init__(self):
        self.calls, self.stopped = [], 0

    def __call__(self, freq, seconds, level_db):
        self.calls.append((freq, seconds, level_db))
        return self

    def stop(self):
        self.stopped += 1


class TestSealTone(unittest.TestCase):
    def test_u65_seal_tone_bypasses_eq_then_restores(self):
        with tempfile.TemporaryDirectory() as tmp:
            pl = FakePlayer()
            sess = consoleserver.Session(Rec(), lambda s: None, profiles_dir=tmp, tone_player=pl)
            v = sess.play_tone("bass", seconds=0.3)
            self.assertEqual(pl.calls[-1][0], 50.0)
            self.assertTrue(v["bypass"])                                           # EQ kapalı: kulaklığın kendi basını duyarsın
            self.assertEqual(v["tone"]["kind"], "bass")
            time.sleep(0.6)
            self.assertFalse(sess.bypass)                                          # süre bitti → önceki hâle döndü
            self.assertIsNone(sess.view()["tone"])
            sess.set_bypass(True)                                                  # kullanıcı zaten EQ'suzdaysa…
            sess.play_tone("ref", seconds=0.2)
            self.assertEqual(pl.calls[-1][0], 1000.0)
            time.sleep(0.5)
            self.assertTrue(sess.bypass)                                           # …öyle kalır
            with self.assertRaises(KeyError):
                sess.play_tone("uçak")
            sess.set_bypass(False)
            sess.play_tone("bass", seconds=5)
            sess.stop_tone()
            self.assertGreaterEqual(pl.stopped, 1)
            self.assertFalse(sess.bypass)


if __name__ == "__main__":
    unittest.main()


class TestToneSignal(unittest.TestCase):
    def test_u66_tone_level_frequency_and_click_free_edges(self):
        import numpy as np
        from btaudio import tones
        x = tones.tone(50.0, 1.0, -24.0)[:, 0].astype(np.float64)
        self.assertAlmostEqual(20 * np.log10(np.max(np.abs(x))), -24.0, delta=0.05)
        f = np.fft.rfftfreq(len(x), 1 / tones.FS)[np.argmax(np.abs(np.fft.rfft(x)))]
        self.assertAlmostEqual(f, 50.0, delta=1.0)
        self.assertLess(abs(x[0]), 1e-6)                                      # sessizlikten başlar
        self.assertLess(abs(x[-1]), 1e-3)                                     # sessizliğe biter (tık yok)
        self.assertLess(np.max(np.abs(np.diff(x[:1440]))), 10 ** (-24 / 20) * 2 * np.pi * 50 / tones.FS * 1.6)
