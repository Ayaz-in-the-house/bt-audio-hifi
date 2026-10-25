"""U80: ilk kurulumun varsayılanı — kuran kişi işlemsiz 'Nötr' ile değil, ölçülmüş dengeli ayarla başlar.

Neden (kullanıcı, 2026-10-25): "kuran kişi için bu ilk varsayılan olsun". Ayar: Harman kulakiçi 2019 bas bileşeni
(105 Hz raf) + bs2b varsayılan crossfeed (700 Hz / 4,5 dB) + genişlik 1,1; ses yükseltme = −preamp.
Kullanıcı aynı gün: "nötrün yanına koyabilirsin, 2. seçenek olarak" + "bası biraz daha azaltabiliriz" → +9 → +6 dB (Harman kulaküstü miktarı); konsolda Nötr'den sonra 2. hazır tarz.
Var olan kurulumun durumu ve ses ayarı DEĞİŞMEZ; 'Nötr' (default_state) şeffaf referans olarak kalır."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import cli, console  # noqa: E402


class TestFirstRun(unittest.TestCase):
    def test_u80_recommended_state_is_harman_bass_with_gentle_space(self):
        st = console.recommended_state()
        on = [b for b in st["bands"] if b["enabled"]]
        self.assertEqual(on, [{"type": "lowshelf", "freq": 105.0, "gain": 6.0, "q": 0.7, "enabled": True}])
        self.assertEqual(st["crossfeed"], {"enabled": True, "fcut": 700, "feed": 4.5})
        self.assertEqual((st["width"], st["balance"]), (1.1, 0.0))
        self.assertEqual(console.sanitize(st), st)                       # sözleşmeye uygun
        self.assertFalse(any(b["enabled"] for b in console.default_state()["bands"]))   # Nötr şeffaf kalır
        self.assertEqual(list(console.PRESETS)[:2], ["notr", console.RECOMMENDED_PRESET])  # Nötr'ün yanında, 2. seçenek
        self.assertEqual(console.apply_preset(console.default_state(), console.RECOMMENDED_PRESET), st)  # preset = varsayılan

    def test_u80_fresh_install_starts_recommended_existing_keeps_its_state(self):
        with mock.patch.object(cli, "_latest_console_state", return_value=None), \
             mock.patch.object(cli, "_latest_tuned", return_value=(None, None)):
            st, fresh = cli._initial_state()
        self.assertTrue(fresh)
        self.assertEqual(st, console.recommended_state())
        mine = console.default_state()
        with mock.patch.object(cli, "_latest_console_state", return_value=mine):
            st, fresh = cli._initial_state()
        self.assertFalse(fresh)
        self.assertEqual(st, console.sanitize(mine))

    def test_u80_loudness_seeded_only_on_fresh_install_without_a_setting(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "loudness.json")
            cli._seed_first_run_loud(False, p)
            self.assertFalse(os.path.exists(p))                            # var olan kurulum: dokunulmaz
            cli._seed_first_run_loud(True, p)
            self.assertEqual(console.load_loud_db(p), console.RECOMMENDED_LOUD_DB)
            console.save_loud_db(3.0, p)
            cli._seed_first_run_loud(True, p)
            self.assertEqual(console.load_loud_db(p), 3.0)                 # kullanıcının ayarı ezilmez
        self.assertEqual(console.RECOMMENDED_LOUD_DB, 6.0)


if __name__ == "__main__":
    unittest.main()
