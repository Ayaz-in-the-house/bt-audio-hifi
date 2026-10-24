"""U77: ses yükseltici + sınırlayıcı (2026-10-23, kullanıcı: "biraz daha artırabilir misin" — basları kaybetmeden).
Zincir sonunda stereo bağlı, ileri bakışlı LSP limiter: yükseltme yalnız ayardan gelir, tavan −1 dBFS, yavaş seviye
düzenleme (ALR) bası dalga biçimi içinde modüle etmez."""
import json
import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import console  # noqa: E402

T = "bluez_output.test.1"


def _gain(conf):
    return float(re.search(r'"Input gain \(G\)" = ([0-9.]+)', conf).group(1))


class TestLoudLimiter(unittest.TestCase):
    def test_limiter_is_last_stage(self):
        conf = console.render_graph_ab(T, console.default_state(), source="t", loud_db=0.0)
        self.assertIn("limiter_stereo", conf)
        self.assertIn('outputs = [ "lim:Output L" "lim:Output R" ]', conf)
        self.assertIn('{ output = "sumL:Out" input = "lim:Input L" }', conf)
        self.assertIn('{ output = "sumR:Out" input = "lim:Input R" }', conf)

    def test_boost_gain_and_clamp(self):
        self.assertAlmostEqual(_gain(console.render_graph_ab(T, None, loud_db=0.0)), 1.0, places=4)
        self.assertAlmostEqual(_gain(console.render_graph_ab(T, None, loud_db=6.0)), 10 ** (6 / 20), places=4)
        self.assertAlmostEqual(_gain(console.render_graph_ab(T, None, loud_db=40.0)), 10 ** (console.LOUD_MAX_DB / 20), places=4)
        self.assertAlmostEqual(_gain(console.render_graph_ab(T, None, loud_db=-5.0)), 1.0, places=4)

    def test_ceiling_and_no_auto_boost(self):
        conf = console.render_graph_ab(T, None, loud_db=5.0)
        self.assertIn('"Threshold (G)" = %.6f' % 10 ** (console.LIMIT_CEIL_DB / 20), conf)
        self.assertIn('"Gain boost" = 0', conf)

    def test_setting_file_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "loudness.json")
            self.assertEqual(console.load_loud_db(p), 0.0)          # dosya yok → yükseltme yok
            with open(p, "w") as f:
                json.dump({"loud_db": 5}, f)
            self.assertEqual(console.load_loud_db(p), 5.0)
            with open(p, "w") as f:
                f.write("bozuk")
            self.assertEqual(console.load_loud_db(p), 0.0)          # bozuk ayar sessizce yükseltmez



class Rec:
    def __init__(self):
        self.payloads = []

    def apply_payload(self, p):
        self.payloads.append(p)


class TestLoudPanel(unittest.TestCase):
    """U78: panelde canlı ses yükseltme (2026-10-24, kullanıcı: "biraz daha aç … panele bak açmamı istediğin ayarlar")."""

    def setUp(self):
        from btaudio import consoleserver
        self.tmp = tempfile.TemporaryDirectory()
        self.rec = Rec()
        self.sess = consoleserver.Session(self.rec, lambda st: None, profiles_dir=os.path.join(self.tmp.name, "p"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_view_reports_loud(self):
        v = self.sess.view()["loud"]
        self.assertEqual(v, {"db": 0.0, "max": console.LOUD_MAX_DB})       # test dizininde ayar yok → 0

    def test_set_loud_live_and_persisted(self):
        self.rec.payloads.clear()
        v = self.sess.set_loud(12)
        self.assertEqual(v["loud"]["db"], 12.0)
        self.assertEqual(self.rec.payloads[-1], '{ params = [ "lim:Input gain (G)" %.6f ] }' % 10 ** (12 / 20))
        self.assertEqual(console.load_loud_db(self.sess.loud_file), 12.0)    # yeniden başlatmada aynı
        self.assertTrue(self.sess.loud_file.startswith(self.tmp.name))      # test gerçek XDG'ye yazmaz

    def test_set_loud_clamped(self):
        self.assertEqual(self.sess.set_loud(99)["loud"]["db"], console.LOUD_MAX_DB)
        self.assertEqual(self.sess.set_loud(-3)["loud"]["db"], 0.0)
        with self.assertRaises((TypeError, ValueError)):
            self.sess.set_loud("çok")

    def test_max_is_balanced_cap(self):
        self.assertEqual(console.LOUD_MAX_DB, 15.0)          # ölçüldü: 14 dB'de sınırlama yok, bas korunuyor


if __name__ == "__main__":
    unittest.main()
