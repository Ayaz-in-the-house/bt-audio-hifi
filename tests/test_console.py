"""U31–U35: profesyonel konsol modeli — durum doğrulama, bs2b katsayıları, stereo yanıt modeli, preamp güvenliği,
canlı parametre yükü, graf config'i, hazır profiller."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import console, dsp  # noqa: E402


class TestState(unittest.TestCase):
    def test_u31_default_is_transparent(self):
        st = console.default_state()
        self.assertEqual(len(st["bands"]), console.N_BANDS)
        m = console.stereo_model(st, [100, 1000, 10000])
        for f in (100, 1000, 10000):
            self.assertAlmostEqual(m["LL"][f], 0.0, places=6)      # L girişi → L çıkışı 0 dB
            self.assertLess(m["LR"][f], -150)                      # L girişi → R çıkışı yok
        self.assertEqual(console.preamp_db(st), 0.0)

    def test_sanitize_clamps(self):
        st = console.default_state()
        st["bands"][0].update(type="bell", freq=5, gain=40, q=99, enabled=True)
        st["width"] = 9
        st["balance"] = -3
        s = console.sanitize(st)
        b = s["bands"][0]
        self.assertEqual((b["freq"], b["gain"], b["q"]), (console.F_MIN, console.G_MAX, console.Q_MAX))
        self.assertEqual((s["width"], s["balance"]), (console.W_MAX, -1.0))
        with self.assertRaises(ValueError):
            console.sanitize({**st, "bands": [{**b, "type": "wobble"}] + st["bands"][1:]})


class TestBs2b(unittest.TestCase):
    def test_u32_bs2b_matches_reference_formulas(self):
        # bs2b.c:156-179 — default 700 Hz / 4.5 dB
        k = console.bs2b_coeffs(700, 4.5, 48000)
        level = 4.5
        gb_lo, gb_hi = level * -5 / 6 - 3, level / 6 - 3
        g_lo, g_hi = 10 ** (gb_lo / 20), 1 - 10 ** (gb_hi / 20)
        fc_hi = 700 * 2 ** ((gb_lo - 20 * np.log10(g_hi)) / 12)
        x = np.exp(-2 * np.pi * 700 / 48000)
        self.assertAlmostEqual(k["lo"]["b0"], g_lo * (1 - x), places=12)
        self.assertAlmostEqual(k["lo"]["a1"], -x, places=12)
        xh = np.exp(-2 * np.pi * fc_hi / 48000)
        self.assertAlmostEqual(k["hi"]["b0"], 1 - g_hi * (1 - xh), places=12)
        self.assertAlmostEqual(k["hi"]["b1"], -xh, places=12)
        self.assertAlmostEqual(k["hi"]["a1"], -xh, places=12)
        self.assertAlmostEqual(k["gain"], 1 / (1 - g_hi + g_lo), places=12)

    def test_crossfeed_leaks_lows_not_highs(self):
        st = console.default_state()
        st["crossfeed"] = {"enabled": True, "fcut": 700, "feed": 4.5}
        m = console.stereo_model(st, [100, 8000])
        self.assertGreater(m["LR"][100], m["LR"][8000] + 10)     # bas karşı kulağa geçer, tiz geçmez
        self.assertLess(m["LR"][100], m["LL"][100])


class TestSafety(unittest.TestCase):
    def test_u33_preamp_prevents_clipping(self):
        st = console.default_state()
        st["bands"][0].update(type="lowshelf", freq=105, gain=10, q=0.7, enabled=True)
        st["bands"][1].update(type="bell", freq=60, gain=6, q=1.0, enabled=True)
        st["width"] = 1.4
        pre = console.preamp_db(st)
        f = np.geomspace(20, 20000, 300)
        m = console.stereo_model({**st, "preamp_override": pre}, f, include_preamp=True)
        worst = max(max(m["mono"].values()), max(m["LL"].values()))
        self.assertLessEqual(worst, 0.05)                        # hiçbir frekansta 0 dBFS aşılmaz

    def test_width_mono_compatible(self):
        st = console.default_state()
        st["width"] = 1.5
        m = console.stereo_model(st, [1000])
        self.assertAlmostEqual(m["mono"][1000], 0.0, places=6)   # L=R içerik genişlikten etkilenmez


class TestLive(unittest.TestCase):
    def test_u34_params_payload(self):
        st = console.default_state()
        st["bands"][2].update(type="bell", freq=1000, gain=3, q=1, enabled=True)
        p = console.pw_params(st)
        k = dsp.coeffs(st["bands"][2])
        self.assertIn(f'"eqL_3:b0" {k["b0"]:.10f}', p)
        self.assertIn(f'"eqR_3:b0" {k["b0"]:.10f}', p)
        self.assertIn('"mixL:Gain 1"', p)
        self.assertTrue(p.startswith("{ params = [") and p.endswith("] }"))
        pb = console.pw_params(st, bypass=True)
        self.assertIn('"eqL_3:b0" 1.0000000000', pb)

    def test_graph_config(self):
        c = console.render_graph("bluez_output.X.1")
        self.assertEqual(c.count("label = bq_raw"), 2 * console.N_BANDS + 4)
        self.assertIn('inputs  = [ "preL:In" "preR:In" ]', c)
        self.assertIn('outputs = [ "mixL:Out" "mixR:Out" ]', c)
        self.assertIn('filter.smart.target = { node.name = "bluez_output.X.1" }', c)
        self.assertEqual(c.count("{"), c.count("}"))


class TestPresets(unittest.TestCase):
    def test_u35_presets_valid_and_safe(self):
        self.assertGreaterEqual(len(console.PRESETS), 8)
        for pid, p in console.PRESETS.items():
            st = console.apply_preset(console.default_state(), pid)
            self.assertEqual(console.sanitize(st), st, pid)
            self.assertTrue(p["source"], f"{pid}: kaynak/gerekçe yok")
            self.assertLessEqual(max(console.stereo_model(st, np.geomspace(20, 20000, 200))["LL"].values()), 12.5, pid)


if __name__ == "__main__":
    unittest.main()
