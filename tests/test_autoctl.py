"""U54–U56: müzik karakteri öznitelikleri, Auto Profile Changer, Auto Dynamic Live (sahte saat, deterministik)."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import analyzer, autoctl, console, features  # noqa: E402

C = analyzer._centers()


def spectrum(tilt_db_per_oct=0.0, boost=None):
    b = np.full(len(C), -40.0) + tilt_db_per_oct * np.log2(C / 1000)
    for (lo, hi), g in (boost or {}).items():
        b[(C >= lo) & (C < hi)] += g
    return b.tolist()


class TestFeatures(unittest.TestCase):
    def test_u54_pink_is_balanced(self):
        ex = features.region_excess(spectrum(), C)
        self.assertTrue(all(abs(v) < 0.7 for v in ex.values()), ex)
        self.assertEqual(features.character(ex), ["dengeli"])

    def test_u54_bass_heavy_and_bright_and_silence(self):
        ex = features.region_excess(spectrum(boost={(20, 250): 12}), C)
        self.assertIn("bas ağırlıklı", features.character(ex))
        ex = features.region_excess(spectrum(boost={(2000, 16000): 6}), C)
        self.assertIn("parlak", features.character(ex))
        ex = features.region_excess(spectrum(boost={(2000, 16000): -10}), C)     # T-L42 canlı ölçümü: koyu kayıt
        self.assertIn("tiz az", features.character(ex))
        self.assertNotIn("dengeli", features.character(ex))
        self.assertIsNone(features.region_excess([-300.0] * len(C), C))
        self.assertEqual(features.character(None), [])


class TestAPC(unittest.TestCase):
    def feed(self, apc, macro, t0, t1):
        out = []
        for t in range(t0, t1):
            r = apc.update(macro, float(t))
            if r:
                out.append((t, r))
        return out

    def test_u55_switch_rules(self):
        apc = autoctl.ProfileChanger({"elektronik": "p-edm", "rock": "p-rock"}, fallback="p-def")
        E = {"elektronik": 0.8, "rock": 0.05}
        R = {"elektronik": 0.05, "rock": 0.8}
        sw = self.feed(apc, E, 0, 20)
        self.assertEqual([s[1] for s in sw], ["p-edm"])
        self.assertEqual(self.feed(apc, R, 20, 25) + self.feed(apc, E, 25, 60), [])     # 5 sn patlama → geçiş YOK
        sw = self.feed(apc, R, 60, 100)
        self.assertEqual([s[1] for s in sw], ["p-rock"])
        t_rock = sw[0][0]
        self.assertGreaterEqual(t_rock - 60, 8)                                     # süreklilik ≥ 8 sn
        self.assertEqual(self.feed(apc, E, 100, t_rock + 29), [])                   # en az kalma 30 sn

    def test_u55_low_confidence_uses_fallback_and_manual_pauses(self):
        apc = autoctl.ProfileChanger({"elektronik": "p-edm"}, fallback="p-def")
        sw = self.feed(apc, {"elektronik": 0.1, "rock": 0.1}, 0, 20)
        self.assertEqual([s[1] for s in sw], ["p-def"])
        apc2 = autoctl.ProfileChanger({"elektronik": "p-edm"})
        apc2.manual(0.0)
        self.assertEqual(self.feed(apc2, {"elektronik": 0.9}, 0, 10), [])            # elle dokunuş → askı
        self.assertTrue(self.feed(apc2, {"elektronik": 0.9}, 10, 40))


class TestADL(unittest.TestCase):
    def run_steps(self, dyn, ex, genre, level, n):
        o = None
        for t in range(n):
            o = dyn.step(ex, genre, level, float(t))
        return o

    def test_u56_dead_zone_bounds_rate_genre_level(self):
        ref = {k: 0.0 for k in features.REGIONS}
        d = autoctl.DynamicEQ(ref)
        self.assertEqual(self.run_steps(d, {**ref, "sub": 1.5}, "pop", -20, 10)["bas"], 0.0)   # ölü bölge
        d = autoctl.DynamicEQ(ref)
        o = [d.step({**ref, "sub": -20.0}, "pop", -20, float(t))["bas"] for t in range(10)]
        self.assertEqual(o[-1], 4.0)                                             # üst sınır +4
        self.assertTrue(all(b - a <= 1.0 + 1e-9 for a, b in zip(o, o[1:])))       # ≤ 1 dB/sn
        d = autoctl.DynamicEQ(ref)
        self.assertLessEqual(self.run_steps(d, {**ref, "sub": 3.0, "hava": -9}, "elektronik", -20, 10)["bas"], 0.0)
        d = autoctl.DynamicEQ(ref)
        loud = self.run_steps(d, {**ref, "sub": -8.0}, "pop", -6, 20)["bas"]
        d = autoctl.DynamicEQ(ref)
        normal = self.run_steps(d, {**ref, "sub": -8.0}, "pop", -20, 20)["bas"]
        self.assertLess(loud, normal)                                             # yüksek seviyede bas azalır
        d = autoctl.DynamicEQ(ref)
        self.assertEqual(self.run_steps(d, None, "pop", -20, 5)["bas"], 0.0)     # sessizlik → karar yok

    def test_u56_learning_and_apply_offsets(self):
        d = autoctl.DynamicEQ({})
        for _ in range(100):
            d.manual("bas", 10.0)
        self.assertEqual(d.bias["bas"], 6.0)                                     # öğrenme sınırlı
        st = console.apply_preset(console.default_state(), "zengin_bas")        # 3 bant kullanıyor
        new = autoctl.apply_offsets(st, {"bas": 2.0, "alt_orta": 0.0, "varlık": -1.0, "hava": 0.0})
        self.assertEqual(new["bands"][:3], st["bands"][:3])                      # kullanıcının bantları DOKUNULMAZ
        self.assertEqual((new["bands"][3]["type"], new["bands"][3]["gain"], new["bands"][3]["enabled"]), ("lowshelf", 2.0, True))
        self.assertFalse(new["bands"][4]["enabled"])
        console.sanitize(new)


if __name__ == "__main__":
    unittest.main()
