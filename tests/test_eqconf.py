"""U25: tasarım → PipeWire smart filter-chain config + EasyEffects 8 preset JSON."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import eqconf  # noqa: E402

DESIGN = {"target": "harman-ie-bass", "preamp_db": -6.5,
          "bands": [{"type": "Bell", "frequency": 35, "gain": 6.5, "q": 1.0},
                    {"type": "Bell", "frequency": 90, "gain": 3.0, "q": 1.0}]}
SINK = "bluez_output.02_00_00_00_00_02.1"


class TestFilterChain(unittest.TestCase):
    def test_u25_filter_chain(self):
        c = eqconf.render_filter_chain(DESIGN, SINK)
        self.assertIn('filter.smart = true', c)
        self.assertIn(f'filter.smart.target = {{ node.name = "{SINK}" }}', c)
        self.assertEqual(c.count("label = bq_peaking"), 2)
        self.assertIn('"Freq" = 35.0 "Q" = 1.0 "Gain" = 6.5', c)
        self.assertIn('label = linear', c)
        self.assertIn('"Mult" = 0.473151', c)                 # 10^(−6.5/20)
        self.assertIn('{ output = "preamp:Out" input = "eq_band_1:In" }', c)
        self.assertEqual(c.count("{"), c.count("}"))          # SPA-JSON parantez dengesi

    def test_ee_preset(self):
        p = eqconf.render_ee_preset(DESIGN)
        out = p["output"]
        self.assertEqual(out["plugins_order"], ["equalizer#0", "limiter#0"])
        eq = out["equalizer#0"]
        self.assertEqual(eq["num-bands"], 2)
        self.assertEqual(eq["input-gain"], -6.5)
        self.assertEqual(eq["left"]["band0"]["frequency"], 35)
        self.assertEqual(eq["left"], eq["right"])
        self.assertEqual(eq["left"]["band1"]["type"], "Bell")
        self.assertEqual(out["limiter#0"]["threshold"], -1.0)


if __name__ == "__main__":
    unittest.main()
