"""T-U09: arayüz dili uçtan uca (başsız; sahte uygulayıcı/analizör/codec — PipeWire'a dokunmaz, gerçek ayar yok).
I3 `en-US` ilk açılış → EN · I4 `tr-TR` → TR · I5 TR/EN düğmesi + yeniden yükleme → seçim korunur · `?lang=` geçici
geçersiz kılma · I8 EN'de 1440 ve 390 px yatay taşma yok · JS hatası 0. README'nin İngilizce görselleri de buradan
üretilir (sahte veri: kişisel ad, makine adı, IP, MAC yok): console-v2-dark-1440 · console-v2-mobile-390 ·
admin-dark-1440 · abx-trial-dark (TR karşılıkları `*-tr.png`, T-U04/T-U06/T-U08)."""
import glob
import os
import re
import sys
import tempfile
import time
import unittest

import numpy as np
from playwright.sync_api import sync_playwright
from scipy.io import wavfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from btaudio import abxsession, analyzer, autoengine, console, consoleserver  # noqa: E402
from test_abxsession import FakeCodec, FakePlayer  # noqa: E402
from test_analyzer import FakeSource  # noqa: E402
from test_autoengine import FakeAnalyzer, FakeClassifier, Rec  # noqa: E402

CHROME = os.environ.get("BTA_CHROME") or next(iter(sorted(glob.glob(os.path.expanduser(
    "~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell")))[-1:]), None)
UI = os.path.join(os.path.dirname(__file__), "..", "..", "analysis", "ui")
TR_RE = re.compile("[çğıöşüÇĞİÖŞÜ]")


def recorder(path, seconds):
    t = np.arange(int(48000 * seconds)) / 48000
    x = 0.2 * np.sin(2 * np.pi * 440 * t)
    wavfile.write(path, 48000, np.stack([x, x], 1).astype(np.float32))


class TestI18nPage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.an = analyzer.Analyzer({"pre": {"cmd": FakeSource.CMD}, "post": {"cmd": FakeSource.CMD}}, linger_s=0.3)
        self.sess = consoleserver.Session(Rec(), lambda st: {"summary": "ok"}, profiles_dir=os.path.join(self.tmp, "p"),
                                          analyzer=self.an, device={"name": "Demo Headphones", "codec": "aac", "rate": 48000})
        self.eng = autoengine.AutoEngine(self.sess, FakeAnalyzer(), classifier=FakeClassifier(),
                                         state_path=os.path.join(self.tmp, "auto.json"), autostart=False)
        self.codec = FakeCodec("aac")
        self.sess.abx = abxsession.AbxSession(switcher=self.codec, player=FakePlayer(), current_codec=lambda: self.codec.current,
                                              results_dir=os.path.join(self.tmp, "abx", "results"), automation=self.eng,
                                              on_apply=lambda d: None, seed=3)
        self.sess.abx_recorder = recorder
        self.sess.abx_env = lambda: {"other_audio": []}
        self.httpd, self.url, self.stop = consoleserver.serve(self.sess)
        os.makedirs(UI, exist_ok=True)

    def tearDown(self):
        self.stop.set()
        self.eng.close()
        self.an.close()

    def body_has_no_turkish(self, pg):
        txt = pg.evaluate("document.body.innerText")
        self.assertIsNone(TR_RE.search(txt), [ln for ln in txt.splitlines() if TR_RE.search(ln)][:5])

    def test_u09_language_selection_and_layout(self):
        errors = []
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True, executable_path=CHROME)

            # I4 — tr-TR: Türkçe, bugünkü görünüm
            tr = b.new_context(viewport={"width": 1440, "height": 1000}, color_scheme="dark", bypass_csp=True, locale="tr-TR")
            pg = tr.new_page()
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.goto(self.url)
            pg.wait_for_selector("#pgrid .pcard")
            self.assertEqual(pg.evaluate("document.documentElement.lang"), "tr")
            self.assertEqual(pg.inner_text(".brand h1"), "Ses Konsolu")
            self.assertEqual(pg.inner_text("#tab-prof"), "Profiller")
            self.assertIn("Zengin bas", pg.inner_text("#pgrid"))
            # ?lang=en geçici geçersiz kılar, kaydedilmez
            pg.goto(self.url + "?lang=en")
            pg.wait_for_selector("#pgrid .pcard")
            self.assertEqual(pg.inner_text(".brand h1"), "Audio Console")
            pg.goto(self.url)
            pg.wait_for_selector("#pgrid .pcard")
            self.assertEqual(pg.inner_text(".brand h1"), "Ses Konsolu")
            tr.close()

            # I3 — en-US ilk açılış: İngilizce, görünür metinde Türkçe harf yok
            en = b.new_context(viewport={"width": 1440, "height": 1000}, color_scheme="dark", bypass_csp=True, locale="en-US")
            pg = en.new_page()
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            pg.goto(self.url)
            pg.wait_for_selector("#pgrid .pcard")
            self.assertEqual(pg.evaluate("document.documentElement.lang"), "en")
            self.assertEqual(pg.inner_text(".brand h1"), "Audio Console")
            self.assertEqual(pg.title(), "Audio Console")
            self.body_has_no_turkish(pg)
            pg.click('#pgrid .pcard[data-p="zengin_bas"]')
            pg.wait_for_function("document.getElementById('active-name').textContent === 'Preset: Rich bass'")
            self.assertIn("Source:", pg.inner_text("#pdesc"))
            # uyarı şeridi: sunucu metni EN (text_en)
            self.sess.set_state(console.sanitize({**console.default_state(), "bands": [
                {"enabled": True, "type": "lowshelf", "freq": 60, "gain": 12, "q": 0.7},
                {"enabled": True, "type": "bell", "freq": 45, "gain": 6, "q": 1.0}] + console.default_state()["bands"][2:]}), seal=True)
            pg.reload()
            pg.wait_for_selector("#warns .w")
            self.assertIn("CAUTION", pg.inner_text("#warns"))
            self.body_has_no_turkish(pg)
            for tab in ("#tab-space", "#tab-an", "#tab-auto", "#tab-prof"):
                pg.click(tab)
                self.body_has_no_turkish(pg)
            self.assertLessEqual(pg.evaluate("document.scrollingElement.scrollWidth"), 1440)      # I8
            pg.click("#b-undo")                                                                 # uyarısız hâle dön
            pg.wait_for_function("!document.querySelector('#warns .w')", timeout=5000)
            pg.click('#pgrid .pcard[data-p="zengin_bas"]')
            pg.wait_for_function("document.getElementById('active-name').textContent === 'Preset: Rich bass'")
            pg.click("#b-save-new")
            self.assertEqual(pg.input_value("#save-name"), "Rich bass (mine)")
            pg.click("#save-ok")
            pg.wait_for_function("!document.getElementById('save-dlg').open")
            pg.click('label:has(#an-en)') if not pg.is_checked("#an-en") else None
            pg.wait_for_function("document.getElementById('sig').classList.contains('on')", timeout=8000)
            pg.wait_for_function("!document.querySelector('#toasts .toast')", timeout=8000)   # bildirimler görüntüyü örtmesin
            pg.screenshot(path=os.path.join(UI, "console-v2-dark-1440.png"), full_page=True)

            # I8 — 390 px
            m = en.new_page()
            m.on("pageerror", lambda e: errors.append(str(e)))
            m.set_viewport_size({"width": 390, "height": 900})
            m.goto(self.url)
            m.wait_for_selector("#pgrid .pcard")
            self.assertLessEqual(m.evaluate("document.scrollingElement.scrollWidth"), 390)
            self.body_has_no_turkish(m)
            m.wait_for_timeout(600)
            m.screenshot(path=os.path.join(UI, "console-v2-mobile-390.png"), full_page=True)
            m.close()

            # kör test penceresi (EN)
            pg.click("#tab-an")
            pg.click("#abx-open")
            pg.wait_for_selector("#abx-dlg[open]")
            pg.click("#abx-rec")
            pg.wait_for_function("document.getElementById('abx-clipst').textContent.includes('Clip ready')", timeout=8000)
            pg.click("#abx-go")
            pg.wait_for_selector("#abx-s2:not([hidden])")
            pg.click('[data-play="A"]')
            pg.wait_for_function("document.querySelector('[data-play=\"A\"]').classList.contains('done')", timeout=5000)
            self.assertIn("Trial 1 of 12", pg.inner_text("#abx-s2"))
            self.body_has_no_turkish(pg)
            pg.wait_for_function("!document.querySelector('#toasts .toast')", timeout=8000)
            pg.screenshot(path=os.path.join(UI, "abx-trial-dark.png"))
            pg.click("#abx-cancel")
            pg.wait_for_function("!document.getElementById('abx-dlg').open", timeout=5000)

            # yönetim (EN): sürüm farkları diff_en
            a = en.new_page()
            a.on("pageerror", lambda e: errors.append(str(e)))
            for g in (2, 4):
                self.sess.set_state(console.sanitize({**console.default_state(), "bands": [
                    {"enabled": True, "type": "lowshelf", "freq": 105, "gain": g, "q": 0.7}] + console.default_state()["bands"][1:]}), seal=True)
                time.sleep(0.05)
            a.goto(self.url + "admin")
            a.wait_for_selector("#ptbl tr[data-id]")
            self.assertEqual(a.inner_text("h1"), "Manage")
            a.locator("#ptbl tr:has(.badge.act) button[data-a='hist']").click()              # aktif çalışma kopyası
            a.wait_for_selector("#tl li[data-v='2']")
            self.assertIn("band 1:", a.inner_text("#tl"))                                    # diff_en
            a.wait_for_timeout(300)
            self.body_has_no_turkish(a)
            self.assertLessEqual(a.evaluate("document.scrollingElement.scrollWidth"), 1440)
            a.screenshot(path=os.path.join(UI, "admin-dark-1440.png"), full_page=True)
            a.close()

            # I5 — TR düğmesi → yeniden yüklemede de TR; EN düğmesi → EN
            pg.click('[data-lang="tr"]')
            pg.wait_for_function("document.documentElement.lang === 'tr'")
            pg.wait_for_selector("#pgrid .pcard", state="attached")   # Analiz sekmesi açık kalır (kayıtlı)
            self.assertEqual(pg.inner_text(".brand h1"), "Ses Konsolu")
            pg.reload()
            pg.wait_for_selector("#pgrid .pcard", state="attached")   # Analiz sekmesi açık kalır (kayıtlı)
            self.assertEqual(pg.inner_text(".brand h1"), "Ses Konsolu")
            self.assertEqual(pg.get_attribute('[data-lang="tr"]', "aria-pressed"), "true")
            pg.click('[data-lang="en"]')
            pg.wait_for_function("document.documentElement.lang === 'en'")
            pg.wait_for_selector("#pgrid .pcard", state="attached")   # Analiz sekmesi açık kalır (kayıtlı)
            self.assertEqual(pg.inner_text(".brand h1"), "Audio Console")
            en.close()
            b.close()
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
