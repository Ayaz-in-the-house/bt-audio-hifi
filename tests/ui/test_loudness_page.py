"""T-U01: bas eşleştirme sayfası uçtan uca (başsız, SES KAPALI): JS hatası yok, akış tamamlanıyor, JSON doğru."""
import json
import os
import sys
import tempfile
import unittest

from playwright.sync_api import sync_playwright

# Playwright istemcisinin beklediği build yerine KURULU olanı kullan (yeni indirme yok — sürüm sabitleme kuralı)
CHROME = os.environ.get("BTA_CHROME") or next(iter(sorted(__import__("glob").glob(os.path.expanduser(
    "~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell")))[-1:]), None)
PAGE = "file://" + os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "tools", "loudness-match.html"))


class TestLoudnessPage(unittest.TestCase):
    def test_u_full_flow(self):
        errors = []
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True, executable_path=CHROME, args=["--mute-audio", "--autoplay-policy=no-user-gesture-required"])
            pg = b.new_page(accept_downloads=True)
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            pg.goto(PAGE)
            pg.check("input[value=bastirilmis]")
            pg.click("#b-start")
            pg.click("#b-cal-ok")
            first = pg.inner_text("#t-gain")
            pg.keyboard.press("ArrowUp")          # +3
            pg.keyboard.press("ArrowLeft")        # -1
            self.assertNotEqual(first, pg.inner_text("#t-gain"))
            for i in range(9):
                pg.click("#b-equal")
            with pg.expect_download() as dl:
                pg.click("#b-max")                # 31.5 Hz: tavan bayrağı
            path = os.path.join(tempfile.mkdtemp(), dl.value.suggested_filename)
            dl.value.save_as(path)
            b.close()
        self.assertEqual(errors, [])
        d = json.load(open(path))
        self.assertEqual(d["tool"], "bta-loudness-match")
        self.assertEqual(d["fit"], "bastirilmis")
        self.assertEqual(len(d["matches"]), 10)
        self.assertEqual(d["flags"], {"31.5": "max"})
        self.assertEqual(d["matches"]["31.5"], 40)
        self.assertAlmostEqual(d["matches"]["500"], d["expected_flat"]["500"] + 2, delta=0.01)   # +3 −1
        print(f"\n    T-U01: {os.path.basename(path)} · 500 Hz={d['matches']['500']} beklenen={d['expected_flat']['500']}",
              file=sys.stderr)


if __name__ == "__main__":
    unittest.main()
