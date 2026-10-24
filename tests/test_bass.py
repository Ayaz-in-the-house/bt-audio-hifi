"""U26: bas analizi — iki oturma dosyası → yanıt, sızdırmazlık farkı, phon duyarlılığı, EQ tasarımı."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import bass, loudness  # noqa: E402

F = loudness.TEST_FREQS


def _file(d, fit, true_h, created):
    iso = dict(zip(F + [1000], loudness.iso226_spl(65, F + [1000])))
    m = {str(f): round(((iso[f] - iso[1000]) - true_h[f]) * 2) / 2 for f in F}
    p = os.path.join(d, f"bta-loudness-{created}-{fit}.json")
    json.dump({"tool": "bta-loudness-match", "version": 1, "created": created, "fit": fit, "assumed_phon": 65,
               "matches": m, "flags": {}, "order": F}, open(p, "w"))
    return p


class TestBass(unittest.TestCase):
    def test_u26_two_fits(self):
        d = tempfile.mkdtemp()
        normal = {f: -9.0 if f <= 63 else (-4.0 if f <= 125 else 0.0) for f in F}     # sızdıran oturma
        pressed = {f: -2.0 if f <= 63 else (-1.0 if f <= 125 else 0.0) for f in F}    # iyi sızdırmazlık
        a = bass.analyze([_file(d, "normal", normal, "2026-09-27T20:00"),
                          _file(d, "bastirilmis", pressed, "2026-09-27T20:10")])
        self.assertAlmostEqual(a["runs"]["normal"]["response_db"]["40"], -9.0, delta=0.3)
        self.assertAlmostEqual(a["seal_gain_db"]["40"], 7.0, delta=0.5)        # bastırınca 40 Hz'te +7 dB
        self.assertIn("seal", a["verdict"])                                    # kök neden: sızdırmazlık
        self.assertEqual(a["design_basis"], "normal")
        self.assertIn("bands", a["design"])
        self.assertGreater(a["phon_sensitivity_db"]["31.5"], 0)                # 60↔70 phon farkı raporlanır

    def test_single_fit(self):
        d = tempfile.mkdtemp()
        h = {f: -5.0 if f <= 80 else 0.0 for f in F}
        a = bass.analyze([_file(d, "normal", h, "2026-09-27T20:00")])
        self.assertIsNone(a["seal_gain_db"])
        self.assertEqual(a["design_basis"], "normal")


if __name__ == "__main__":
    unittest.main()


class TestQualityGate(unittest.TestCase):
    FIX = os.path.join(os.path.dirname(__file__), "fixtures", "loudness-2026-09-27-user-confused.json")

    def test_u28_rejects_real_confused_run(self):
        # Gerçek oturum: 9/10 frekansta "tavan" düğmesi, 500 Hz +40 dB (beklenen +2) → EQ ÜRETİLMEMELİ
        problems = bass.quality_problems(bass.load(self.FIX))
        self.assertTrue(problems)
        self.assertTrue(any("tavan" in p for p in problems), problems)
        self.assertTrue(any("500" in p for p in problems), problems)
        with self.assertRaises(bass.LowQualityRun):
            bass.analyze([self.FIX])

    def test_clean_run_passes(self):
        d = tempfile.mkdtemp()
        h = {f: -5.0 if f <= 80 else 0.0 for f in F}
        self.assertEqual(bass.quality_problems(bass.load(_file(d, "normal", h, "2026-09-27T20:00"))), [])
