"""U22–U24: ISO 226:2003 modeli, eşit-yükseklik eşleşmesinden kulaklık yanıtı çıkarımı, PEQ uydurma."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import loudness  # noqa: E402

TEST_F = [31.5, 40, 50, 63, 80, 100, 125, 160, 250, 500]


class TestIso226(unittest.TestCase):
    def test_u22_phon_definition_at_1k(self):
        # phon tanımı: 1 kHz'te SPL = phon (ISO 226 modeli bunu ~0.3 dB içinde sağlar)
        for phon in (20, 40, 60, 80, 90):
            self.assertAlmostEqual(loudness.iso226_spl(phon, [1000])[0], phon, delta=0.3)

    def test_threshold_is_tf(self):
        self.assertEqual(loudness.iso226_spl(0, [20])[0], 78.5)

    def test_bass_needs_more_spl(self):
        s = loudness.iso226_spl(60, [31.5, 100, 1000])
        self.assertGreater(s[0], s[1])
        self.assertGreater(s[1], s[2])

    def test_unknown_frequency_rejected(self):
        with self.assertRaises(ValueError):
            loudness.iso226_spl(60, [37])


class TestResponse(unittest.TestCase):
    def test_u23_roundtrip_synthetic_listener(self):
        # kulaklık gerçek yanıtı (1k'ya göre): bası eksik bir earbud
        true_h = {f: -12 + 12 * np.log10(f / 31.5) / np.log10(500 / 31.5) for f in TEST_F}
        phon = 65
        iso = dict(zip(TEST_F + [1000], loudness.iso226_spl(phon, TEST_F + [1000])))
        # ideal dinleyici: eşit yükseklik için dijital kazanç g_f = ΔL_iso(f) − H(f)
        matches = {f: (iso[f] - iso[1000]) - true_h[f] for f in TEST_F}
        h = loudness.response_from_matches(matches, phon)
        for f in TEST_F:
            self.assertAlmostEqual(h[f], true_h[f], places=6)


class TestPeqFit(unittest.TestCase):
    def test_u24_fit_reaches_target(self):
        h = {f: -4 + 4 * np.log10(f / 31.5) / np.log10(500 / 31.5) for f in TEST_F}   # 31.5 Hz'te −4 dB (istek ≤ tavan)
        design = loudness.design_eq(h, target="harman-ie-bass", max_boost_db=12)
        resp = loudness.eq_response_db(design["bands"], TEST_F)
        target = loudness.target_db("harman-ie-bass", TEST_F)
        for f, r in zip(TEST_F, resp):
            achieved = h[f] + r
            self.assertAlmostEqual(achieved, target[TEST_F.index(f)], delta=1.5, msg=f"{f} Hz")
        self.assertLessEqual(design["preamp_db"], -max(0, max(resp)) + 0.01)   # clipping önleme

    def test_boost_is_capped(self):
        h = {f: -30.0 for f in TEST_F}
        h[500] = 0.0
        design = loudness.design_eq(h, target="flat", max_boost_db=12)
        self.assertLessEqual(max(loudness.eq_response_db(design["bands"], TEST_F)), 12.5)


if __name__ == "__main__":
    unittest.main()
