"""U11–U12: encoder benchmark metriklerinin kendisinin doğruluğu."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import analysis  # noqa: E402

FS = 48000


def _lowpassed_noise(cutoff, seconds=2.0, seed=1):
    rng = np.random.default_rng(seed)
    x = rng.standard_normal(int(FS * seconds))
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / FS)
    X[f > cutoff] = 0
    return np.fft.irfft(X, n=len(x)) * 0.1


class TestCutoff(unittest.TestCase):
    def test_u11_detects_cutoff(self):
        for fc in (15000, 16000, 19300):
            y = _lowpassed_noise(fc)
            est = analysis.cutoff_frequency(y, FS)
            self.assertAlmostEqual(est, fc, delta=250, msg=f"fc={fc} est={est}")

    def test_full_band(self):
        rng = np.random.default_rng(3)
        y = rng.standard_normal(FS * 2) * 0.1
        self.assertGreater(analysis.cutoff_frequency(y, FS), 23000)


class TestSNR(unittest.TestCase):
    def test_u12_known_snr(self):
        rng = np.random.default_rng(7)
        ref = rng.standard_normal(FS * 2) * 0.1
        for target in (20.0, 40.0, 60.0):
            noise = rng.standard_normal(len(ref))
            noise *= np.sqrt(np.mean(ref ** 2) / np.mean(noise ** 2)) / (10 ** (target / 20))
            got = analysis.snr_db(ref, ref + noise)
            self.assertAlmostEqual(got, target, delta=0.5)

    def test_alignment_recovers_delay(self):
        rng = np.random.default_rng(9)
        ref = rng.standard_normal(FS) * 0.1
        delayed = np.concatenate([np.zeros(1024), ref])[: len(ref)]
        a, b = analysis.align(ref, delayed)
        self.assertGreater(analysis.snr_db(a, b), 60)

    def test_band_snr_ignores_out_of_band(self):
        rng = np.random.default_rng(11)
        ref = _lowpassed_noise(10000, seed=12)
        hf = _lowpassed_noise(23000, seed=13) - _lowpassed_noise(18000, seed=13)
        self.assertGreater(analysis.band_snr_db(ref, ref + hf * 5, FS, hi=16000), 60)


if __name__ == "__main__":
    unittest.main()
