"""T-U08: konsoldaki kör dinleme testi (PRD-BTA05 E1) uçtan uca — gerçek Session + AbxSession, sahte codec değiştirici /
çalar / kaydedici (ses çıkmaz, PipeWire'a dokunmaz).

1. Analiz → "Testi başlat…" → pencere; klip yokken "Teste başla" pasif.
2. "Çalan müzikten 12 sn al" → klip hazır; başka ses çalıyorsa uyarı görünür.
3. Deneme: X dinlenmeden "X = A/B" pasif; ▶X → etkin; 12 deneme (10 doğru) → sonuç "10/12 doğru" + tercih düğmeleri.
4. "SBC daha iyi" → "SBC kalıcı olsun" → karar kaydı SBC, codec SBC, pencere kapanır, bildirim.
5. İkinci test: başlat → ▶B → "Testi iptal et" → codec testten önceki hâline döner; otomasyon serbest.
6. 390 px taşma yok, JS hatası 0."""
import glob
import os
import sys
import tempfile
import unittest

import numpy as np
from playwright.sync_api import sync_playwright
from scipy.io import wavfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from btaudio import abxsession, autoengine, consoleserver  # noqa: E402
from test_abxsession import FakeCodec, FakePlayer  # noqa: E402
from test_autoengine import FakeAnalyzer, FakeClassifier, Rec  # noqa: E402

CHROME = os.environ.get("BTA_CHROME") or next(iter(sorted(glob.glob(os.path.expanduser(
    "~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell")))[-1:]), None)
UI = os.path.join(os.path.dirname(__file__), "..", "..", "analysis", "ui")


def recorder(path, seconds):
    t = np.arange(int(48000 * seconds)) / 48000
    x = 0.2 * np.sin(2 * np.pi * 440 * t)
    wavfile.write(path, 48000, np.stack([x, x], 1).astype(np.float32))


class TestAbxPage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.sess = consoleserver.Session(Rec(), lambda st: {"summary": "ok"}, profiles_dir=os.path.join(self.tmp, "p"),
                                          device={"name": "Test Kulaklık", "codec": "aac", "rate": 48000})
        self.eng = autoengine.AutoEngine(self.sess, FakeAnalyzer(), classifier=FakeClassifier(),
                                         state_path=os.path.join(self.tmp, "auto.json"), autostart=False)
        self.codec, self.decisions = FakeCodec("aac"), []
        self.sess.abx = abxsession.AbxSession(switcher=self.codec, player=FakePlayer(), current_codec=lambda: self.codec.current,
                                              results_dir=os.path.join(self.tmp, "abx", "results"), automation=self.eng,
                                              on_apply=self.decisions.append, seed=3)
        self.sess.abx_recorder = recorder
        self.other = ["Zen"]
        self.sess.abx_env = lambda: {"other_audio": list(self.other)}
        self.httpd, self.url, self.stop = consoleserver.serve(self.sess)
        os.makedirs(UI, exist_ok=True)

    def tearDown(self):
        self.stop.set()
        self.eng.close()

    def test_u08_blind_test_flow(self):
        sess, errors = self.sess, []
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True, executable_path=CHROME)
            pg = b.new_page(viewport={"width": 1440, "height": 1000}, color_scheme="dark", bypass_csp=True, locale="tr-TR")
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" and "409" not in m.text else None)
            pg.goto(self.url)
            pg.wait_for_selector("#pgrid .pcard")
            pg.click("#tab-an")

            # 1–2 klip
            pg.click("#abx-open")
            pg.wait_for_selector("#abx-dlg[open]")
            self.assertTrue(pg.is_disabled("#abx-go"))
            pg.click("#abx-rec")
            pg.wait_for_function("document.getElementById('abx-clipst').textContent.includes('Klip hazır')", timeout=8000)
            self.assertTrue(pg.locator("#abx-other").is_visible())            # Zen hâlâ çalıyor → uyarı
            self.assertIn("Zen", pg.inner_text("#abx-other"))
            self.other.clear()
            pg.wait_for_function("document.getElementById('abx-other').hidden", timeout=5000)
            self.assertFalse(pg.is_disabled("#abx-go"))
            pg.screenshot(path=os.path.join(UI, "abx-step1-dark.png"))

            # 3 denemeler
            pg.click("#abx-go")
            pg.wait_for_selector("#abx-s2:not([hidden])")
            self.assertEqual(self.eng.status()["held"], "kör test")          # otomasyon askıda
            trials = list(sess.abx._trials)
            for i, x in enumerate(trials):
                pg.wait_for_function(f"document.getElementById('abx-k').textContent === '{i + 1}'", timeout=5000)
                self.assertTrue(pg.is_disabled('[data-ans="A"]'))           # X dinlenmeden cevap yok
                if i == 0:
                    pg.click('[data-play="A"]')
                    pg.wait_for_function("document.querySelector('[data-play=\"A\"]').classList.contains('done')", timeout=5000)
                    pg.screenshot(path=os.path.join(UI, "abx-trial-dark-tr.png"))
                pg.click('[data-play="X"]')
                pg.wait_for_function("!document.querySelector('[data-ans=\"A\"]').disabled", timeout=5000)
                ans = x if i < 10 else ("B" if x == "A" else "A")
                pg.click(f'[data-ans="{ans}"]')

            # sonuç + tercih + kalıcı
            pg.wait_for_selector("#abx-s3:not([hidden])", timeout=5000)
            self.assertIn("10/12 doğru", pg.inner_text("#abx-score"))
            self.assertIn("Fark gerçekten duyuluyor", pg.inner_text("#abx-verdict"))
            self.assertTrue(pg.is_disabled("#abx-go"))                     # tercih seçilmeden bitmez
            pg.click('[data-pref="sbc"]')
            pg.wait_for_function("document.getElementById('abx-go').textContent.includes('SBC kalıcı')", timeout=5000)
            pg.screenshot(path=os.path.join(UI, "abx-result-dark.png"))
            pg.click("#abx-go")
            pg.wait_for_function("!document.getElementById('abx-dlg').open", timeout=5000)
            self.assertEqual(self.codec.current, "sbc")
            self.assertEqual(self.decisions[-1]["codec"], "sbc")
            self.assertIn("SBC kalıcı", pg.inner_text("#toasts"))
            self.assertIsNone(self.eng.status()["held"])

            # 5 iptal → orijinal
            pg.click("#abx-open")
            pg.wait_for_selector("#abx-dlg[open]")
            pg.wait_for_function("!document.getElementById('abx-go').disabled", timeout=5000)   # klip hâlâ hazır
            pg.click("#abx-go")
            pg.wait_for_selector("#abx-s2:not([hidden])")
            pg.click('[data-play="B"]')
            pg.wait_for_function("document.querySelector('[data-play=\"B\"]').classList.contains('done')", timeout=5000)
            pg.click("#abx-cancel")
            pg.wait_for_function("!document.getElementById('abx-dlg').open", timeout=5000)
            self.assertEqual(self.codec.current, "sbc")                     # testten önceki hâl (az önce kalıcı yapılan)
            self.assertEqual(sess.abx.status()["phase"], "idle")
            self.assertIsNone(self.eng.status()["held"])

            pg.set_viewport_size({"width": 390, "height": 900})
            pg.click("#abx-open")
            pg.wait_for_selector("#abx-dlg[open]")
            pg.wait_for_timeout(300)
            self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth"), 390)
            pg.screenshot(path=os.path.join(UI, "abx-mobile-390.png"))
            self.assertEqual(errors, [])
            b.close()


if __name__ == "__main__":
    unittest.main()
