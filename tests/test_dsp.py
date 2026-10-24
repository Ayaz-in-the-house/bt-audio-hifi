"""U30: RBJ cookbook katsayıları — tüm filtre tipleri analitik özelliklerini sağlar (bq_raw'a yazılacak değerler)."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import dsp, loudness  # noqa: E402

FS = 48000


def db_at(band, f):
    return dsp.response_db([band], [f])[0]


class TestRbj(unittest.TestCase):
    def test_u30_bell_center_gain(self):
        for g in (-9.0, 3.0, 12.0):
            self.assertAlmostEqual(db_at({"type": "bell", "freq": 1000, "gain": g, "q": 1.4}, 1000), g, places=6)

    def test_shelves(self):
        lo = {"type": "lowshelf", "freq": 105, "gain": 8.0, "q": 0.7}
        self.assertAlmostEqual(db_at(lo, 20), 8.0, delta=0.3)
        self.assertAlmostEqual(db_at(lo, 5000), 0.0, delta=0.05)
        self.assertAlmostEqual(db_at(lo, 105), 4.0, delta=0.2)          # RBJ raf: köşe = yarı kazanç
        hi = {"type": "highshelf", "freq": 8000, "gain": -6.0, "q": 0.7}
        self.assertAlmostEqual(db_at(hi, 20000), -6.0, delta=0.4)
        self.assertAlmostEqual(db_at(hi, 100), 0.0, delta=0.05)

    def test_pass_and_notch(self):
        q = 1 / np.sqrt(2)
        self.assertAlmostEqual(db_at({"type": "lowpass", "freq": 2000, "gain": 0, "q": q}, 2000), -3.01, delta=0.02)
        self.assertAlmostEqual(db_at({"type": "highpass", "freq": 30, "gain": 0, "q": q}, 30), -3.01, delta=0.02)
        self.assertLess(db_at({"type": "lowpass", "freq": 2000, "gain": 0, "q": q}, 16000), -30)
        self.assertLess(db_at({"type": "notch", "freq": 3000, "gain": 0, "q": 4}, 3000), -60)
        self.assertAlmostEqual(db_at({"type": "notch", "freq": 3000, "gain": 0, "q": 4}, 300), 0.0, delta=0.1)

    def test_normalized(self):
        for t in dsp.TYPES:
            c = dsp.coeffs({"type": t, "freq": 500, "gain": 3.0, "q": 1.0}, FS)
            self.assertEqual(c["a0"], 1.0)
            self.assertEqual(set(c), {"b0", "b1", "b2", "a0", "a1", "a2"})

    def test_bypass_band_is_identity(self):
        c = dsp.coeffs({"type": "bell", "freq": 500, "gain": 0.0, "q": 1.0, "enabled": False}, FS)
        self.assertEqual((c["b0"], c["b1"], c["b2"], c["a1"], c["a2"]), (1.0, 0.0, 0.0, 0.0, 0.0))

    def test_matches_legacy_bell(self):
        # loudness.eq_response_db (T-L30 ile ürün doğrulanmış) ile birebir
        f = [40, 90, 500, 4000]
        a = dsp.response_db([{"type": "bell", "freq": 90, "gain": 6.0, "q": 1.0}], f)
        b = loudness.eq_response_db([{"type": "Bell", "frequency": 90, "gain": 6.0, "q": 1.0}], f)
        for x, y in zip(a, b):
            self.assertAlmostEqual(x, y, places=9)

    def test_unknown_type(self):
        with self.assertRaises(ValueError):
            dsp.coeffs({"type": "wobble", "freq": 1, "gain": 0, "q": 1}, FS)


if __name__ == "__main__":
    unittest.main()
