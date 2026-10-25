"""T-U07: sürücü koruma uyarıları + oturma testi (D7) sayfada — gerçek Session, sahte ton çalar (ses çıkmaz).

1. AAC'de 'Elektronik' tarzı → BİLGİ şeridi (17 kHz üstü + preamp maliyeti). SBC'de gösterilmez (birim: U65).
2. Aşırı bas (grafikten değil API'den kurulur) → DİKKAT şeridi; nötre dönünce şerit boşalır.
3. Oturma testi: 'Bas tonu' → çalar çağrılır (50 Hz, −24 dBFS), EQ'suz rozeti + durum yazısı; 'Durdur' → EQ geri gelir.
4. 390 px taşma yok, JS hatası 0."""
import glob
import json
import os
import sys
import tempfile
import unittest

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from btaudio import console, consoleserver  # noqa: E402
from test_protection import FakePlayer, Rec  # noqa: E402

CHROME = os.environ.get("BTA_CHROME") or next(iter(sorted(glob.glob(os.path.expanduser(
    "~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell")))[-1:]), None)
UI = os.path.join(os.path.dirname(__file__), "..", "..", "analysis", "ui")


class TestProtectionPage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.pl = FakePlayer()
        self.sess = consoleserver.Session(Rec(), lambda st: {"summary": "ok"}, profiles_dir=os.path.join(self.tmp, "p"),
                                          device={"name": "Test Kulaklık", "codec": "aac", "rate": 48000},
                                          tone_player=self.pl)
        self.httpd, self.url, self.stop = consoleserver.serve(self.sess)

    def tearDown(self):
        self.sess.stop_tone()
        self.stop.set()

    def test_u07_warnings_and_seal_test(self):
        sess, errors = self.sess, []
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True, executable_path=CHROME)
            pg = b.new_page(viewport={"width": 1440, "height": 1000}, color_scheme="dark", bypass_csp=True, locale="tr-TR")   # CSP eval yasaklar
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            pg.goto(self.url)
            pg.wait_for_selector("#pgrid .pcard")
            self.assertEqual(pg.locator("#warns .w").count(), 0)

            # 1 — AAC + 17 kHz üstü takviye
            pg.click('#pgrid .pcard[data-p="elektronik"]')
            pg.wait_for_selector('#warns .w[data-code="hf_aac"]')
            t = pg.inner_text('#warns .w[data-code="hf_aac"]')
            self.assertIn("BİLGİ", t)
            self.assertIn("7,3 dB kısıyor", t)

            # 2 — aşırı bas
            s = console.default_state()
            s["bands"][0].update(type="lowshelf", freq=60.0, gain=12.0, q=0.7, enabled=True)
            s["bands"][1].update(type="bell", freq=45.0, gain=6.0, q=1.0, enabled=True)
            sess.set_state(s)
            pg.reload()
            pg.wait_for_selector('#warns .w.warn[data-code="bass_high"]')
            self.assertIn("DİKKAT", pg.inner_text('#warns .w[data-code="bass_high"]'))
            pg.screenshot(path=os.path.join(UI, "console-v2-warnings-dark-1440.png"))
            pg.click('#pgrid .pcard[data-p="notr"]')
            pg.wait_for_function("document.querySelectorAll('#warns .w').length === 0")

            # 3 — oturma testi
            pg.click("#tab-an")
            pg.click('[data-tone="bass"]')
            pg.wait_for_function("!document.getElementById('tone-stop').hidden")
            self.assertEqual(self.pl.calls[-1], (50.0, 4.0, -24.0))
            self.assertTrue(sess.bypass)
            self.assertIn("Bas tonu çalıyor", pg.inner_text("#tone-st"))
            self.assertIn("bypass", pg.get_attribute("#gwrap", "class"))
            pg.click("#tone-stop")
            pg.wait_for_function("document.getElementById('tone-stop').hidden")
            self.assertFalse(sess.bypass)
            self.assertGreaterEqual(self.pl.stopped, 1)

            pg.set_viewport_size({"width": 390, "height": 900})
            pg.wait_for_timeout(300)
            self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth"), 390)
            self.assertEqual(errors, [])
            b.close()


if __name__ == "__main__":
    unittest.main()
