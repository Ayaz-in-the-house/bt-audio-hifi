"""U57: A/B tıksız geçiş motoru (D2) — graf yapısı, parametre yükü, sıralayıcı (sahte saat/uygulayıcı)."""
import os
import re
import sys
import threading
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import console, crossfade  # noqa: E402


def st_gain(g):
    s = console.default_state()
    s["bands"][0].update(type="bell", freq=1000.0, gain=float(g), q=1.0, enabled=True)
    return console.sanitize(s)


class TestGraph(unittest.TestCase):
    def test_u57_ab_graph_is_consistent(self):
        conf = console.render_graph_ab("bluez_output.TEST.1", st_gain(3), source="t")
        names = set(re.findall(r"name = (\w+) (?:label|plugin)", conf))     # U77: lim = ladspa düğümü
        for ch in "LR":
            for c in "AB":
                for n in [f"pre{c}{ch}", f"hi{c}{ch}", f"lo{c}{ch}", f"mix{c}{ch}"] + [f"eq{c}{ch}_{i}" for i in range(1, 11)]:
                    self.assertIn(n, names)
            self.assertIn(f"copy{ch}", names)
            self.assertIn(f"sum{ch}", names)
        self.assertFalse([n for n in names if n.startswith(("ramp", "mult"))])      # R42: ramp kullanılamaz
        for out, inp in re.findall(r'output = "(\w+):[^"]+" input = "(\w+):', conf):
            self.assertIn(out, names)
            self.assertIn(inp, names)
        self.assertIn('inputs  = [ "copyL:In" "copyR:In" ]', conf)
        self.assertIn('outputs = [ "lim:Output L" "lim:Output R" ]', conf)          # U77: toplam → sınırlayıcı → çıkış
        self.assertIn('name = sumL label = mixer control = { "Gain 1" = 1.0 "Gain 2" = 0.0 }', conf)

    def test_u57_chain_params_prefixed_and_equal_to_single(self):
        single = console.pw_params(st_gain(4))
        a = console.pw_params_ab(st_gain(4), "A")
        self.assertIn('"eqAL_1:b0"', a)
        self.assertNotIn('"eqBL_1', a)
        norm = re.sub(r'"(\w+?)A([LR])', r'"\1\2', a)
        self.assertEqual(sorted(norm.split('" ')), sorted(single.split('" ')))

    def test_u57_crossfade_steps_monotonic_constant_sum(self):
        steps = console.crossfade_steps("B", 10)
        vals = [[float(x) for x in re.findall(r'"sumL:Gain \d" ([\d.]+)', p)] for p in steps]
        self.assertEqual(vals[-1], [0.0, 1.0])
        for (a1, b1), (a2, b2) in zip(vals, vals[1:]):
            self.assertLessEqual(a2, a1)
            self.assertGreaterEqual(b2, b1)
        for a, b in vals:
            self.assertAlmostEqual(a + b, 1.0, places=4)                           # ilişkili sinyalde sabit genlik


class Rec:
    def __init__(self):
        self.calls = []

    def apply_payload(self, p):
        self.calls.append((time.monotonic(), p))


class TestSequencer(unittest.TestCase):
    def test_u57_loads_inactive_chain_then_crossfades(self):
        rec = Rec()
        xf = crossfade.Crossfader(rec, fade_s=0.2)
        try:
            xf.submit(st_gain(6))
            self.assertTrue(xf.wait_idle(3))
            self.assertEqual(xf.active, "B")
            p = next(c for _, c in rec.calls if '"eqBL_1:b0"' in c)
            self.assertIn('"eqBL_1:b0"', p)                  # yeni durum SESSİZ zincire (B) yüklendi
            self.assertNotIn('"eqAL_1:b0"', p)               # çalan zincire (A) dokunulmadı → sıfırlama duyulmaz
            self.assertIn('"sumL:Gain 2" 1.00000', rec.calls[-1][1])     # son adım: yalnız B duyulur
        finally:
            xf.close()

    def test_u57_never_reloads_a_chain_that_is_still_fading(self):
        rec = Rec()
        xf = crossfade.Crossfader(rec, fade_s=0.3)
        try:
            for g in (1, 2, 3, 4, 5):                         # hızlı ardışık istekler
                xf.submit(st_gain(g))
                time.sleep(0.02)
            self.assertTrue(xf.wait_idle(5))
            loads = [(t, c) for t, c in rec.calls if '"eqAL_1:b0"' in c or '"eqBL_1:b0"' in c]
            for (t1, c1), (t2, c2) in zip(loads, loads[1:]):
                self.assertGreaterEqual(t2 - t1, 0.3 - 0.02)   # bir geçiş bitmeden diğer zincir yüklenmez
            self.assertLessEqual(len(loads), 3)              # ara durumlar atlanır (en sonuncu kazanır)
            self.assertEqual(loads[-1][1], console.pw_params_ab(st_gain(5), xf.active))
        finally:
            xf.close()

    def test_u57_submit_never_blocks_caller(self):
        class Slow(Rec):
            def apply_payload(self, p):
                time.sleep(0.2)
                super().apply_payload(p)
        xf = crossfade.Crossfader(Slow(), fade_s=0.05)
        try:
            t0 = time.perf_counter()
            for g in range(20):
                xf.submit(st_gain(g % 12))
            self.assertLess(time.perf_counter() - t0, 0.01)
        finally:
            xf.close()


class TestSettle(unittest.TestCase):
    def test_u68_settle_pins_mixer_to_active_chain_before_first_load(self):
        """U68: süreç bir geçişin ORTASINDA ölürse iki zincir de yarı kazançla duyulur (ör. 0,5/0,5). Açılışta ilk
        yükleme 'sessiz' sanılan ama duyulan zincire gider → bellek sıfırlanması tık. Açılışta settle(): karışım etkin
        zincire sabitlenir, SONRA yükleme yapılır (GREEN skill testinin REFACTOR bulgusu, 2026-09-28)."""
        for active, gains in (("A", (1.0, 0.0)), ("B", (0.0, 1.0))):
            rec = Rec()
            xf = crossfade.Crossfader(rec, fade_s=0.05, active=active)
            try:
                xf.settle()
                xf.submit(st_gain(3))
                self.assertTrue(xf.wait_idle(3))
                self.assertEqual(rec.calls[0][1], console.mix_gains(*gains))       # ÖNCE sabitle
                self.assertIn('"eq' + ("B" if active == "A" else "A") + 'L_1:b0"', rec.calls[1][1])   # sonra sessize yükle
            finally:
                xf.close()


if __name__ == "__main__":
    unittest.main()
