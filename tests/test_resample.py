"""U19: resampler ölçüm analizinin doğruluğu (bilinen sahte bileşen seviyesi geri okunmalı)."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import resample  # noqa: E402

FS = 48000


class TestSfdr(unittest.TestCase):
    def _sig(self, spur_db=None, spur_f=23100.0, seconds=4):
        t = np.arange(FS * seconds) / FS
        x = sum(np.sin(2 * np.pi * f * t) * 10 ** (-20 / 20) for f in resample.TONES_441)
        if spur_db is not None:
            x = x + np.sin(2 * np.pi * spur_f * t) * 10 ** (spur_db / 20)
        return np.stack([x, x], 1)

    def test_u19_recovers_injected_spur(self):
        r = resample.analyze(self._sig(spur_db=-100), FS)
        self.assertAlmostEqual(r["tone_level_db"], -20.0, delta=0.5)
        self.assertAlmostEqual(r["worst_spur_db"], -100.0, delta=1.5)
        self.assertAlmostEqual(r["image_23100_db"], -100.0, delta=1.5)
        self.assertAlmostEqual(r["sfdr_db"], 80.0, delta=2.0)

    def test_clean_signal_high_sfdr(self):
        r = resample.analyze(self._sig(), FS)
        self.assertGreater(r["sfdr_db"], 120)


if __name__ == "__main__":
    unittest.main()
