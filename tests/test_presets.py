"""U43: tarz kütüphanesi (C2). İsim ≠ ses: her profilin vaat ettiği şekil ÖLÇÜLÜR; kaynaktan türetilenler kaynağa karşı
yeniden uydurma hatasıyla doğrulanır; hiçbiri preamp ile 0 dBFS'i aşmaz."""
import csv
import json
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import console, dsp, presetfit  # noqa: E402

UP = os.path.join(os.path.dirname(__file__), "..", "docs", "research", "upstream", "presets")


def r(pid, f):
    """Profilin EQ yanıtı (dB, preamp hariç) f frekansında."""
    return float(dsp.response_db(console.PRESETS[pid]["bands"], [f])[0])


def _csv(name):
    rows = [l for l in csv.reader(open(os.path.join(UP, name))) if l and l[0][0].isdigit()]
    return np.array([float(x[0]) for x in rows]), np.array([float(x[1]) for x in rows])


class TestLibrary(unittest.TestCase):
    def test_u43_size_and_metadata(self):
        P = console.PRESETS
        self.assertGreaterEqual(len(P), 22)
        labels = [p["label"] for p in P.values()]
        self.assertEqual(len(labels), len(set(labels)))
        for pid, p in P.items():
            with self.subTest(pid=pid):
                self.assertIn(p["group"], console.CATEGORIES)
                self.assertIn(p["kind"], console.KINDS)
                self.assertTrue(p["source"].strip() and p["desc"].strip())
                self.assertIsInstance(p["tags"], list)
                console.sanitize(console.apply_preset(console.default_state(), pid))   # geçerli durum

    def test_u43_no_clipping_with_preamp(self):
        for pid in console.PRESETS:
            with self.subTest(pid=pid):
                st = console.apply_preset(console.default_state(), pid)
                m = console.stereo_model(st, console.GRID, include_preamp=True)
                peak = max(max(m["LL"].values()), max(m["mono"].values()))
                self.assertLessEqual(peak, 0.01)

    def test_u43_catalog_has_preview_curves(self):
        cat = console.preset_catalog()
        self.assertEqual(set(cat), set(console.PRESETS))
        for pid, c in cat.items():
            self.assertEqual(len(c["preview"]), len(console.PREVIEW_F))
            self.assertIn("kind", c)


class TestProvenance(unittest.TestCase):
    def test_u43_vlc_derived_fit_within_1db(self):
        derived = [p for p in console.PRESETS.values() if p.get("ref", {}).get("kind") == "vlc"]
        self.assertGreaterEqual(len(derived), 6)
        for p in derived:
            with self.subTest(p=p["label"]):
                ref = p["ref"]
                err = presetfit.fit_error(p["bands"], presetfit.VLC_CENTERS, ref["values"], ref["scale"])
                self.assertLessEqual(err, 1.0)

    def test_u43_vlc_values_match_upstream_file(self):
        txt = open(os.path.join(UP, "vlc-equalizer_presets.h")).read().replace("-1.11022e-15f", "0.0f")
        for p in console.PRESETS.values():
            ref = p.get("ref", {})
            if ref.get("kind") != "vlc":
                continue
            with self.subTest(p=p["label"]):
                blk = txt[txt.index(f'"{ref["name"]}", 10,'):]
                nums = blk[blk.index("{") + 1:blk.index("}")].replace("f", "").split(",")
                self.assertEqual([float(x) for x in nums], [float(x) for x in ref["values"]])

    def test_u43_easyeffects_exact(self):
        for pid, fn in (("ee_bass_boosted", "easyeffects-presets-Bass Boosted.json"),
                        ("ee_boosted", "easyeffects-presets-Boosted.json")):
            with self.subTest(pid=pid):
                o = json.load(open(os.path.join(UP, fn)))["output"]
                L = o[[k for k in o if k.startswith("equalizer")][0]]["left"]
                ref = [(L[k]["frequency"], L[k]["gain"], round(L[k]["q"], 2))
                       for k in sorted((k for k in L if k.startswith("band")), key=lambda k: int(k[4:]))]
                got = [(b["freq"], b["gain"], b["q"]) for b in console.PRESETS[pid]["bands"] if b["enabled"]]
                self.assertEqual(got, ref)

    def test_u43_harman_bass_is_with_minus_without(self):
        for pid, a, b in (("harman_bas", "autoeq-Harman in-ear 2019.csv", "autoeq-Harman in-ear 2019 without bass.csv"),
                          ("harman_oe", "autoeq-Harman over-ear 2018.csv", "autoeq-Harman over-ear 2018 without bass.csv")):
            with self.subTest(pid=pid):
                F = np.geomspace(20, 2000, 60)
                fa, va = _csv(a)
                fb, vb = _csv(b)
                d = np.interp(np.log10(F), np.log10(fa), va) - np.interp(np.log10(F), np.log10(fb), vb)
                d -= d[-1]
                got = np.asarray(dsp.response_db(console.PRESETS[pid]["bands"], F))
                self.assertLessEqual(float(np.max(np.abs(got - d))), 0.3)


class TestIntent(unittest.TestCase):
    """Her profil adının vaat ettiği tonal şekil (U43)."""
    def test_bass_family(self):
        self.assertGreaterEqual(r("zengin_bas", 40), 6)
        self.assertGreaterEqual(r("zengin_bas", 200), 1)                 # gövde / sıcaklık
        self.assertLessEqual(abs(r("zengin_bas", 1000)), 1)
        self.assertLessEqual(r("zengin_bas", 3000), 1.5)                # vokal bölgesi korunur
        self.assertGreaterEqual(r("derin_sub", 40), 6)
        self.assertGreaterEqual(r("derin_sub", 40) - r("derin_sub", 150), 3)
        self.assertGreaterEqual(r("vurucu_bas", 70), 4)
        self.assertGreaterEqual(r("vurucu_bas", 70) - r("vurucu_bas", 30), 1.5)   # tepe, raf değil
        self.assertLess(r("vurucu_bas", 300), 0)                          # çamur temizliği
        self.assertTrue(2 <= r("hafif_bas", 40) <= 5)
        self.assertGreaterEqual(r("guclu_bas", 50), 8)

    def test_character(self):
        self.assertGreaterEqual(r("vokal", 3000) - r("vokal", 1000), 2)
        self.assertLessEqual(r("vokal", 60), 0)
        self.assertGreaterEqual(r("gece", 50), 4)
        self.assertGreaterEqual(r("gece", 10000), 2)
        self.assertGreaterEqual(r("konusma", 3000) - r("konusma", 1000), 2)
        self.assertLessEqual(r("konusma", 60), -3)
        self.assertGreaterEqual(r("sicak", 180) - r("sicak", 8000), 3)
        self.assertGreaterEqual(r("parlak", 10000) - r("parlak", 1000), 2.5)
        self.assertGreaterEqual(r("v_sekli", 60) - r("v_sekli", 1000), 3)
        self.assertGreaterEqual(r("v_sekli", 10000) - r("v_sekli", 1000), 3)

    def test_genre_and_use(self):
        self.assertGreaterEqual(r("hiphop", 50), 5)
        self.assertGreaterEqual(r("hiphop", 50) - r("hiphop", 400), 4)
        self.assertGreaterEqual(r("akustik_caz", 10000), 1.5)
        self.assertGreaterEqual(r("akustik_caz", 150), 1)
        self.assertGreaterEqual(r("film", 50), 4)
        self.assertGreaterEqual(console.PRESETS["film"]["spatial"]["width"], 1.1)
        self.assertGreaterEqual(r("oyun", 3500) - r("oyun", 1000), 2)
        self.assertLess(r("oyun", 250), 0)
        self.assertLessEqual(r("klasik", 12000) - r("klasik", 1000), -2)   # VLC Classical: tiz yumuşak
        self.assertGreaterEqual(r("rock", 8000) - r("rock", 600), 3)

    def test_space_presets_enable_crossfeed(self):
        for pid in ("sahne", "studyo", "dogal_crossfeed"):
            self.assertTrue(console.PRESETS[pid]["spatial"]["crossfeed"]["enabled"], pid)


if __name__ == "__main__":
    unittest.main()
