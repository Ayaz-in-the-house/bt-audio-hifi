"""T-U06: Yönetim sayfası (D6) uçtan uca — gerçek Session + AutoEngine (sahte analizör/sınıflayıcı), başsız Chromium.

1. Profil tablosu: ANA / ÖZEL rozetleri, aktif rozeti, sürüm sayısı, boyut.
2. Geçmiş: Özel profilin tüm sürümleri, en yeni üstte, "şu an" işaretli, her sürümde fark satırları (bant 1: …).
3. "Bu sürüme dön": ses o sürüme döner, geçmiş SİLİNMEZ (bir sürüm artar).
4. Sil → çöp kutusunda görünür → Geri yükle → tabloya döner.
5. Tümünü dışa aktar (paket) → içe aktar (dosya seçici) → sayılar tutar.
6. Otomasyon modu sayfadan değişir. Konsola dönüş bağlantısı + konsolda Yönetim bağlantısı. 390 px taşma yok. JS hatası 0."""
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
from btaudio import autoengine, console, consoleserver  # noqa: E402
from test_autoengine import FakeAnalyzer, FakeClassifier, Rec  # noqa: E402

CHROME = os.environ.get("BTA_CHROME") or next(iter(sorted(glob.glob(os.path.expanduser(
    "~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell")))[-1:]), None)
UI = os.path.join(os.path.dirname(__file__), "..", "..", "analysis", "ui")


def st_gain(g):
    s = console.default_state()
    s["bands"][0].update(type="bell", freq=1000.0, gain=float(g), q=1.0, enabled=True)
    return console.sanitize(s)


class TestAdminPage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.sess = consoleserver.Session(Rec(), lambda st: {"summary": "ok"}, profiles_dir=os.path.join(self.tmp, "p"))
        self.eng = autoengine.AutoEngine(self.sess, FakeAnalyzer(), classifier=FakeClassifier(),
                                         state_path=os.path.join(self.tmp, "auto.json"), autostart=False)
        self.locked = self.sess.store.save("Ana bas", st_gain(3))
        for g in (2, 4, 6):
            self.sess.set_state(st_gain(g), seal=True)
            time.sleep(0.01)
        self.wc = self.sess.active["id"]
        self.httpd, self.url, self.stop = consoleserver.serve(self.sess)
        os.makedirs(UI, exist_ok=True)

    def tearDown(self):
        self.stop.set()
        self.eng.close()

    def test_u06_admin_flow(self):
        sess, errors = self.sess, []
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True, executable_path=CHROME)
            ctx = b.new_context(viewport={"width": 1440, "height": 1000}, color_scheme="dark", bypass_csp=True, locale="tr-TR",
                                accept_downloads=True)
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            pg.goto(self.url + "admin")
            pg.wait_for_selector("#ptbl tr[data-id]")

            # 1 — tablo
            self.assertEqual(pg.locator("#ptbl tr[data-id]").count(), 2)
            row = pg.locator(f'#ptbl tr[data-id="{self.wc}"]')
            self.assertIn("ÖZEL", row.inner_text())
            self.assertIn("aktif", row.inner_text())
            self.assertIn("ANA", pg.locator(f'#ptbl tr[data-id="{self.locked}"]').inner_text())
            self.assertIn("4", row.locator("td").nth(3).inner_text())          # v0 + 3 düzenleme

            # 2 — geçmiş
            row.locator('button[data-a="hist"]').click()
            pg.wait_for_selector("#tl li[data-v]")
            self.assertEqual(pg.locator("#tl li[data-v]").count(), 4)
            self.assertEqual(pg.locator("#tl li[data-v]").first.get_attribute("data-v"), "3")   # en yeni üstte
            self.assertIn("şu an", pg.locator("#tl li.cur").inner_text())
            self.assertIn("bant 1", pg.inner_text("#tl"))
            pg.screenshot(path=os.path.join(UI, "admin-dark-1440-tr.png"), full_page=True)

            # 3 — sürüme dön (yıkıcı değil)
            pg.click('#tl [data-restore="1"]')
            pg.wait_for_function("document.querySelectorAll('#tl li[data-v]').length === 5", timeout=5000)
            self.assertEqual(sess.state, st_gain(2))
            self.assertIn("geri yüklendi", pg.inner_text("#toasts"))

            # 4 — sil → çöp → geri yükle
            pg.locator(f'#ptbl tr[data-id="{self.locked}"] button[data-a="del"]').click()
            pg.wait_for_selector("#trash [data-token]")
            self.assertIn("Ana bas", pg.inner_text("#trash"))
            self.assertEqual(pg.locator("#ptbl tr[data-id]").count(), 1)
            pg.click("#trash [data-token]")
            pg.wait_for_function("document.querySelectorAll('#ptbl tr[data-id]').length === 2")
            self.assertTrue(sess.store.exists(self.locked))

            # 5 — toplu dışa / içe aktar
            with pg.expect_download() as dl:
                pg.click("#b-export-all")
            path = dl.value.path()
            with open(path) as f:
                bundle = json.load(f)
            self.assertEqual(bundle["schema"], "bta-bundle/1")
            self.assertEqual(len(bundle["profiles"]), 2)
            pg.set_input_files("#f-import", path)
            pg.wait_for_function("document.getElementById('toasts').textContent.includes('2 profil içe aktarıldı')")
            self.assertEqual(pg.locator("#ptbl tr[data-id]").count(), 4)        # adlar çakıştı → "(içe aktarıldı)"

            # 6 — otomasyon
            pg.wait_for_selector('#mode button[data-m="adl"]')
            pg.click('#mode button[data-m="adl"]')
            pg.wait_for_function("document.querySelector('#mode button[data-m=adl]').getAttribute('aria-pressed') === 'true'")
            self.assertEqual(self.eng.mode, "adl")

            # mobil + gezinme
            pg.set_viewport_size({"width": 390, "height": 900})
            pg.wait_for_timeout(300)
            self.assertLessEqual(pg.evaluate("document.documentElement.scrollWidth"), 390)
            pg.screenshot(path=os.path.join(UI, "admin-mobile-390.png"), full_page=True)
            pg.click("#back")
            pg.wait_for_selector("#pgrid .pcard")
            self.assertEqual(pg.get_attribute("#b-admin", "href"), "/admin")
            self.assertEqual(errors, [])
            b.close()


if __name__ == "__main__":
    unittest.main()
