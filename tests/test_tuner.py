"""U29: canlı bas ayarlayıcı saf mantığı — bantlar, otomatik preamp, hazır ayarlar, pw-cli yükü, sınırlar."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import loudness, tuner  # noqa: E402


class TestTuner(unittest.TestCase):
    def test_u29_state_and_preamp(self):
        st = tuner.state({"deep": 8.0, "punch": 4.0, "warmth": -2.0})
        self.assertEqual([b["frequency"] for b in st["bands"]], [40, 90, 200])
        grid = loudness.eq_response_db(st["bands"], tuner.GRID)
        self.assertAlmostEqual(st["preamp_db"], -max(grid), places=2)     # kırpılma yok: tepe kadar kıs
        self.assertLessEqual(st["preamp_db"], 0)

    def test_clamp(self):
        st = tuner.state({"deep": 40.0, "punch": -40.0, "warmth": 0})
        g = {b["id"]: b["gain"] for b in st["bands"]}
        self.assertEqual(g["deep"], tuner.MAX_GAIN)
        self.assertEqual(g["punch"], tuner.MIN_GAIN)

    def test_neutral_is_transparent(self):
        st = tuner.state(tuner.PRESETS["notr"])
        self.assertEqual(st["preamp_db"], 0.0)
        self.assertTrue(all(b["gain"] == 0 for b in st["bands"]))

    def test_harman_preset_tracks_target(self):
        st = tuner.state(tuner.PRESETS["harman"])
        fr = [40, 63, 100, 160, 500, 1000]
        got = loudness.eq_response_db(st["bands"], fr)
        want = loudness.target_db("harman-ie-bass", fr)
        for f, g, w in zip(fr, got, want):
            self.assertAlmostEqual(g, w, delta=1.5, msg=f"{f} Hz")

    def test_values_on_slider_grid(self):
        # Kaydırıcı adımı 0,5: hazır ayar ve durum aynı ızgarada olmalı (T-U02 kusuru: 7,9 → sessizce 8,0)
        for p in tuner.PRESETS.values():
            for b in tuner.state(p)["bands"]:
                self.assertEqual(b["gain"] / tuner.STEP_DB, round(b["gain"] / tuner.STEP_DB))
        self.assertEqual(tuner.state({"deep": 7.9})["bands"][0]["gain"], 8.0)

    def test_params_payload(self):
        st = tuner.state({"deep": 6.0, "punch": 0.0, "warmth": 0.0})
        p = tuner.pw_params(st)
        self.assertIn('"eq_band_1:Gain" 6.0', p)
        self.assertIn('"preamp:Mult"', p)
        self.assertTrue(p.startswith("{ params = [") and p.endswith("] }"))

    def test_bypass_payload(self):
        p = tuner.pw_params(tuner.state({"deep": 9, "punch": 3, "warmth": 0}), bypass=True)
        self.assertIn('"eq_band_1:Gain" 0.0', p)
        self.assertIn('"preamp:Mult" 1.000000', p)


if __name__ == "__main__":
    unittest.main()
