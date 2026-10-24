"""T-U02: canlı bas ayarlayıcı sayfası + sunucu uçtan uca (başsız, SES YOK — sahte uygulayıcı; PipeWire'a dokunmaz)."""
import glob
import os
import sys
import time
import unittest

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from btaudio import tuner, tunerserver  # noqa: E402

CHROME = os.environ.get("BTA_CHROME") or next(iter(sorted(glob.glob(os.path.expanduser(
    "~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell")))[-1:]), None)


class FakeApplier:
    def __init__(self):
        self.calls = []

    def apply(self, st, bypass=False):
        self.calls.append((tuner.pw_params(st, bypass=bypass), bypass))


class TestBassTunePage(unittest.TestCase):
    def test_u02_flow(self):
        app, saved = FakeApplier(), []
        sess = tunerserver.Session(app, on_save=lambda st: saved.append(st) or {"summary": "ok"})
        httpd, url, stop, _ = tunerserver.serve(sess)
        errors = []
        try:
            with sync_playwright() as p:
                b = p.chromium.launch(headless=True, executable_path=CHROME)
                pg = b.new_page()
                pg.on("pageerror", lambda e: errors.append(str(e)))
                pg.goto(url)
                pg.wait_for_selector("#r-deep")
                pg.click("button[data-p=harman]")                           # hazır ayar
                pg.wait_for_function("document.querySelector('#v-deep').textContent.startsWith('+8.0')")
                pg.fill("#r-punch", "6")                                     # kaydırıcı
                pg.dispatch_event("#r-punch", "input")
                time.sleep(0.4)
                hold = pg.locator("#b-hold")
                hold.hover(); pg.mouse.down(); time.sleep(0.3); pg.mouse.up(); time.sleep(0.3)   # EQ'suz karşılaştır
                pg.click("#b-save")
                pg.wait_for_function("document.querySelector('#status').textContent.includes('Kaydedildi')")
                curve_pts = pg.eval_on_selector("#curve polyline", "e => e.getAttribute('points').split(' ').length")
                pg.click("#b-quit")
                b.close()
        finally:
            stop.set()
        self.assertEqual(errors, [])
        self.assertEqual(curve_pts, len(tuner.GRID))
        payloads = [c[0] for c in app.calls]
        self.assertTrue(any('"eq_band_1:Gain" 8.0' in x for x in payloads), payloads)      # harman uygulandı
        self.assertTrue(any('"eq_band_2:Gain" 6.0' in x for x in payloads), payloads)      # kaydırıcı uygulandı
        self.assertTrue(any(bp for _, bp in app.calls), "bypass açılmadı")
        self.assertFalse(app.calls[-1][1], "bypass bırakınca kapanmadı")
        self.assertEqual(len(saved), 1)
        g = {x["id"]: x["gain"] for x in saved[0]["bands"]}
        self.assertEqual(g["punch"], 6.0)
        self.assertEqual(g["deep"], 8.0)


if __name__ == "__main__":
    unittest.main()
