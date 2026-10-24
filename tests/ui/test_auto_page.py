"""T-U05: Otomatik sekmesi (D3–D5) uçtan uca — gerçek Session + gerçek AutoEngine, sahte analizör/sınıflayıcı/saat
(motor adımları testten sürülür; PipeWire'a dokunmaz). Sayfanın 1 sn yoklaması üzerinden gözlenir:

1. 4 mod düğmesi, varsayılan Kapalı; mod seçimi sunucuya ulaşır, üst çubukta "Oto:" rozeti belirir.
2. Konuşma sesi → APC "Konuşma / podcast" tarzını yükler → aktif ad + bildirim + "Son geçişler" sayfada görünür.
3. İkisi birden + ince bassız müzik → ADL bas düzeltmesi: sütunda +, grafikte kesikli "otomatik" eğri + açıklama.
4. "+ Daha çok bas" yoklaması öğrenilen tercihe yazılır.
5. Tür etiketleri penceresi: profile "elektronik" etiketi → eşleme tablosunda o profil görünür.
6. Kapalı → rozet, eğri, düzeltme kalkar. 390 px taşma yok. JS hatası 0."""
import glob
import json
import os
import sys
import tempfile
import time
import unittest

from playwright.sync_api import sync_playwright

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from btaudio import autoengine, console, consoleserver, features  # noqa: E402
from test_autoengine import FakeAnalyzer, FakeClassifier, Rec, bands, snap  # noqa: E402

CHROME = os.environ.get("BTA_CHROME") or next(iter(sorted(glob.glob(os.path.expanduser(
    "~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell")))[-1:]), None)
UI = os.path.join(os.path.dirname(__file__), "..", "..", "analysis", "ui")


class TestAutoPage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.sess = consoleserver.Session(Rec(), lambda st: {"summary": "ok"}, profiles_dir=os.path.join(self.tmp, "p"),
                                          device={"name": "Test Kulaklık", "codec": "aac", "rate": 48000})
        self.an, self.clf, self.t = FakeAnalyzer(), FakeClassifier(), [0.0]
        self.eng = autoengine.AutoEngine(self.sess, self.an, classifier=self.clf, clock=lambda: self.t[0],
                                         state_path=os.path.join(self.tmp, "auto.json"), autostart=False)
        self.httpd, self.url, self.stop = consoleserver.serve(self.sess)
        os.makedirs(UI, exist_ok=True)

    def tearDown(self):
        self.stop.set()
        self.eng.close()

    def ticks(self, n):
        for _ in range(n):
            self.t[0] += 1.0
            self.eng.tick()

    def test_u05_auto_tab(self):
        sess, eng, errors = self.sess, self.eng, []
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True, executable_path=CHROME)
            ctx = b.new_context(viewport={"width": 1440, "height": 1000}, color_scheme="dark", bypass_csp=True)
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            pg.goto(self.url)
            pg.wait_for_selector("#pgrid .pcard")
            pg.click("#tab-auto")
            pg.wait_for_selector("#auto-mode button")

            # 1 — modlar
            self.assertEqual(pg.locator("#auto-mode button").count(), 4)
            self.assertEqual(pg.get_attribute('#auto-mode button[data-m="off"]', "aria-pressed"), "true")
            self.assertTrue(pg.locator("#auto-chip").is_hidden())
            pg.click('#auto-mode button[data-m="apc"]')
            pg.wait_for_function("!document.getElementById('auto-chip').hidden")
            self.assertEqual(eng.mode, "apc")
            self.assertIn("Otomatik profil", pg.inner_text("#auto-chip"))
            self.assertIn("türünü", pg.inner_text("#auto-help"))

            # 2 — konuşma → Konuşma tarzı
            self.an.snap = snap(bands())
            self.clf.macro = {"konuşma": 0.9, "elektronik": 0.05}
            self.ticks(40)
            self.assertEqual(sess.active["id"], "konusma")
            pg.wait_for_function("document.getElementById('active-name').textContent.includes('Konuşma')", timeout=5000)
            pg.wait_for_function("document.getElementById('auto-genre').textContent === 'Konuşma'", timeout=5000)
            self.assertIn("Konuşma", pg.inner_text("#auto-log"))
            self.assertIn("Otomatik:", pg.inner_text("#toasts"))
            self.assertGreaterEqual(pg.locator("#auto-scores .gbar").count(), 1)

            # 3 — ikisi birden + ince bassız müzik → ADL
            pg.click('#auto-mode button[data-m="both"]')
            pg.wait_for_function("!document.getElementById('auto-adl').hidden")
            eng.dyn.ref = {k: 0.0 for k in features.REGIONS}
            eng.ref_n = 10 ** 6
            self.an.snap = snap(bands({(20, 60): -10}))
            self.clf.macro = {"pop": 0.9, "konuşma": 0.0}
            self.ticks(15)
            self.assertGreater(sess.auto_offsets["bas"], 1.0)
            pg.wait_for_selector("#graph polyline.autoc", timeout=5000)
            self.assertTrue(pg.locator("#lg-auto").is_visible())
            self.assertIn("+", pg.inner_text("#auto-offs"))
            pg.screenshot(path=os.path.join(UI, "console-v2-auto-dark-1440.png"), full_page=True)

            # 4 — bas tercihi yoklaması
            pg.click('[data-nudge="2"]')
            pg.wait_for_function("document.getElementById('auto-bias').textContent.includes('+0,4')")
            self.assertAlmostEqual(eng.dyn.bias["bas"], 0.4)

            # 5 — tür etiketi
            pid = sess.store.save("Benim derin basım", console.apply_preset(console.default_state(), "derin_sub"))
            pg.reload()                                   # açık sekme hatırlanır (Otomatik) → profillere geç
            pg.wait_for_selector("#tab-prof")
            pg.click("#tab-prof")
            pg.wait_for_selector("#plist li button.load")
            pg.click("#plist details.menu summary")
            pg.click(f'#plist button[data-a="genres"][data-id="{pid}"]')
            pg.check('#genre-list input[value="elektronik"]')
            pg.click('#genre-form button[type="submit"]')
            pg.wait_for_function("!document.getElementById('genre-dlg').open")
            self.assertEqual(sess.store.get(pid)["genres"], ["elektronik"])
            pg.click("#tab-auto")
            pg.wait_for_function("document.getElementById('auto-map').textContent.includes('Benim derin basım')", timeout=5000)

            # 6 — kapat
            pg.click('#auto-mode button[data-m="off"]')
            pg.wait_for_function("document.getElementById('auto-chip').hidden")
            self.assertIsNone(sess.auto_offsets)
            self.assertEqual(pg.locator("#graph polyline.autoc").count(), 0)
            self.assertEqual(len(self.an.subs), 0)

            # mobil
            pg.set_viewport_size({"width": 390, "height": 900})
            pg.wait_for_timeout(300)
            self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth"), 390)
            pg.screenshot(path=os.path.join(UI, "console-v2-auto-mobile-390.png"), full_page=True)
            self.assertEqual(errors, [])
            b.close()


if __name__ == "__main__":
    unittest.main()
