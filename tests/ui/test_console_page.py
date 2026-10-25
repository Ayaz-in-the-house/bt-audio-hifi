"""T-U04: Ses Konsolu v2 — sunucu + sayfa uçtan uca (başsız; sahte uygulayıcı + sahte analizör kaynağı; PipeWire'a
dokunmaz). Kapsam: yeni-olarak-kaydet / çakışma / üzerine-yaz / değişti göstergesi / yeniden adlandır / çoğalt /
dışa-içe aktar / sil + geri al, tarz arama-süzme, klavye ile bant, sekmeler, uzay tarzı EQ'yu korur, geri al, A/B,
açılışta kullan, canlı analizör çizimi + kapatınca yakalama durur, tema, 390 px taşma, JS=Python ≤0,01 dB, JS hatası 0."""
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
from btaudio import analyzer, console, consoleserver, dsp  # noqa: E402
from test_analyzer import FakeSource  # noqa: E402

CHROME = os.environ.get("BTA_CHROME") or next(iter(sorted(glob.glob(os.path.expanduser(
    "~/.cache/ms-playwright/chromium_headless_shell-*/*/chrome-headless-shell")))[-1:]), None)
UI = os.path.join(os.path.dirname(__file__), "..", "..", "analysis", "ui")


class Fake:
    def __init__(self):
        self.payloads = []

    def apply_payload(self, p):
        self.payloads.append(p)


def wait(cond, t=5.0):
    t0 = time.time()
    while time.time() - t0 < t:
        if cond():
            return True
        time.sleep(0.05)
    return False


class TestConsolePage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.commits = []
        self.an = analyzer.Analyzer({"pre": {"cmd": FakeSource.CMD}, "post": {"cmd": FakeSource.CMD}}, linger_s=0.3)
        self.sess = consoleserver.Session(Fake(), on_commit=lambda st: self.commits.append(st) or {"summary": "ok"},
                                          profiles_dir=os.path.join(self.tmp, "p"), analyzer=self.an,
                                          device={"name": "Test Kulaklık", "codec": "aac", "rate": 48000})
        self.httpd, self.url, self.stop = consoleserver.serve(self.sess)
        os.makedirs(UI, exist_ok=True)

    def tearDown(self):
        self.stop.set()
        self.an.close()

    def test_u04_full_flow(self):
        sess, errors = self.sess, []
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True, executable_path=CHROME)
            ctx = b.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True, color_scheme="dark", locale="tr-TR",
                                bypass_csp=True)   # CSP üretimde eval yasaklar; Playwright wait_for_function eval kullanır
            pg = ctx.new_page()
            pg.on("pageerror", lambda e: errors.append(str(e)))
            pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            pg.goto(self.url)
            pg.wait_for_selector("#pgrid .pcard")
            self.assertGreaterEqual(pg.locator("#pgrid .pcard").count() + pg.locator("#space-presets .pcard").count(), 22)
            self.assertIn("Test Kulaklık", pg.inner_text("#dev-chip"))

            # ── tarz seç → aktif = tarz, değişmedi ──
            pg.click('#pgrid .pcard[data-p="zengin_bas"]')
            pg.wait_for_function("document.getElementById('active-name').textContent.includes('Zengin bas')")
            self.assertEqual(sess.active["id"], "zengin_bas")
            self.assertFalse(pg.locator("#active-pill").evaluate("e => e.classList.contains('is-dirty')"))
            self.assertIn("Kaynak:", pg.inner_text("#pdesc"))
            # JS önizleme ↔ Python DSP paritesi (toplam EQ)
            fs = [30, 105, 200, 1000, 9000]
            js = pg.evaluate(f"() => window.__bta_jsCurve({fs})")
            py = dsp.response_db([b for b in sess.state["bands"] if b["enabled"]], fs)
            for a, c in zip(js, py):
                self.assertAlmostEqual(a, c, delta=0.01)

            # ── sürükle → "Özel 1" çalışma kopyası (tarz DEĞİŞMEZ, vurgulu, otomatik kayıt) ──
            box = pg.locator('#graph .node[data-i="0"] .dot').bounding_box()
            cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
            pg.mouse.move(cx, cy); pg.mouse.down(); pg.mouse.move(cx + 40, cy - 20, steps=5); pg.mouse.up()
            self.assertTrue(wait(lambda: sess.state["bands"][0]["freq"] > 120))
            pg.wait_for_function("document.getElementById('active-pill').classList.contains('is-auto')")
            self.assertEqual(pg.inner_text("#active-name"), "Özel 1")
            self.assertIn("Zengin bas", pg.inner_text("#active-from"))
            pg.wait_for_function("document.getElementById('saved').textContent.includes('kaydedildi')", timeout=4000)
            self.assertEqual(console.PRESETS["zengin_bas"]["bands"][0]["gain"], 7.0)            # tarz dokunulmadı
            self.assertIn("auto", pg.get_attribute("#plist li:first-child", "class"))            # listede vurgulu

            # ── geri al (sunucu tarafı) → tarzın kendisi; ileri al ──
            pg.click("#b-undo")
            self.assertTrue(wait(lambda: sess.state["bands"] == console.PRESETS["zengin_bas"]["bands"]))
            pg.click("#b-redo")
            self.assertTrue(wait(lambda: sess.state["bands"][0]["freq"] > 120))

            # ── çalışma kopyasını adlandır (önerilen ad) → ana profil ──
            pg.click("#b-save-new")
            self.assertTrue(pg.locator("#save-dlg").evaluate("d => d.open"))
            self.assertIn("Özel 1", pg.inner_text("#save-title"))
            self.assertEqual(pg.input_value("#save-name"), "Zengin bas (benim)")
            pg.fill("#save-notes", "orta boy kulak ucu")
            pg.click("#save-ok")
            pg.wait_for_function("!document.getElementById('save-dlg').open")
            self.assertEqual([x["name"] for x in sess.store.list()], ["Zengin bas (benim)"])
            self.assertEqual(sess.store.list()[0]["notes"], "orta boy kulak ucu")
            self.assertEqual((sess.active["kind"], sess.active["locked"], sess.dirty()), ("profile", True, False))
            self.assertTrue(pg.locator("#b-save-over").is_hidden())
            pg.screenshot(path=os.path.join(UI, "console-v2-dark-1440-tr.png"), full_page=True)

            # ── klavye: ana profilde ↑↑ → Özel 2 (ana DEĞİŞMEZ) → "ana profile uygula" ──
            g0 = sess.state["bands"][0]["gain"]
            pg.locator('#graph .node[data-i="0"]').focus()
            pg.keyboard.press("ArrowUp"); pg.keyboard.press("ArrowUp")
            self.assertTrue(wait(lambda: abs(sess.state["bands"][0]["gain"] - (g0 + 1.0)) < 1e-6), sess.state["bands"][0])
            pg.wait_for_function("document.getElementById('active-name').textContent === 'Özel 2'")
            sess.writer.flush()
            self.assertEqual(sess.store.get("zengin-bas-benim")["state"]["bands"][0]["gain"], g0)   # ana korunuyor
            pg.wait_for_function("!document.getElementById('b-save-over').hidden")
            pg.click("#b-save-over")
            self.assertTrue(wait(lambda: sess.store.get("zengin-bas-benim")["state"]["bands"][0]["gain"] == g0 + 1.0))
            self.assertEqual(sess.active["id"], "zengin-bas-benim")
            # klavye: 3 → bant 3, E ile aç/kapat (→ Özel 3)
            pg.keyboard.press("3")
            pg.wait_for_function("document.getElementById('insp-title').textContent === 'Bant 3'")
            on0 = sess.state["bands"][2]["enabled"]
            pg.keyboard.press("e")
            self.assertTrue(wait(lambda: sess.state["bands"][2]["enabled"] != on0))

            # ── var olan adla adlandır → çakışma → üzerine yaz ──
            pg.keyboard.press("Control+Shift+s")
            pg.fill("#save-name", "zengin BAS (benim)")
            pg.click("#save-ok")
            pg.wait_for_selector("#save-conflict.show")
            self.assertIn("zaten var", pg.inner_text("#save-conflict"))
            pg.click("#save-overwrite")
            pg.wait_for_function("!document.getElementById('save-dlg').open")
            self.assertEqual(sorted(x["name"] for x in sess.store.list()), ["zengin BAS (benim)", "Özel 2"])   # yazılan ad

            # ── menü: adlandır (çalışma kopyası) / çoğalt / dışa aktar / sil + geri al ──
            def menu(pid, action):
                li = f'#plist li:has(button.load[data-id="{pid}"])'
                pg.click(f"{li} summary")
                pg.click(f'{li} button[data-a="{action}"]')
            menu("özel-2", "rename")
            pg.fill("#plist li input", "Akşam bası")
            pg.keyboard.press("Enter")
            self.assertTrue(wait(lambda: sorted(x["name"] for x in sess.store.list()) == ["Akşam bası", "zengin BAS (benim)"]))
            self.assertTrue(sess.store.get("akşam-bası")["locked"])
            menu("akşam-bası", "duplicate")
            self.assertTrue(wait(lambda: len(sess.store.list()) == 3))
            with pg.expect_download() as dl:
                menu("akşam-bası", "export")
            doc = json.load(open(dl.value.path()))
            self.assertEqual(doc["schema"], "bta.profile/1")
            self.assertEqual(doc["name"], "Akşam bası")
            menu("akşam-bası", "delete")
            self.assertTrue(wait(lambda: len(sess.store.list()) == 2))
            pg.click("#toasts .toast button:has-text('Geri al')")
            self.assertTrue(wait(lambda: len(sess.store.list()) == 3))

            # ── içe aktar (arkadaştan gelen dosya) ──
            doc["name"] = "Arkadaşımın profili"
            f = os.path.join(self.tmp, "friend.json")
            json.dump(doc, open(f, "w"), ensure_ascii=False)
            pg.set_input_files("#f-import", f)
            self.assertTrue(wait(lambda: "Arkadaşımın profili" in [x["name"] for x in sess.store.list()]))
            bad = os.path.join(self.tmp, "bad.json")
            open(bad, "w").write("{bozuk")
            pg.set_input_files("#f-import", bad)
            pg.wait_for_selector("#toasts .toast.err")

            # ── arama + kategori ──
            pg.fill("#p-search", "rock")
            ids = pg.eval_on_selector_all("#pgrid .pcard", "els => els.map(e => e.dataset.p)")
            self.assertIn("rock", ids)
            self.assertNotIn("zengin_bas", ids)
            pg.fill("#p-search", "zzzz")
            pg.wait_for_selector("#pgrid .empty")
            pg.fill("#p-search", "")
            pg.click('#cats button[data-c="Bas"]')
            groups = {console.PRESETS[i]["group"] for i in pg.eval_on_selector_all("#pgrid .pcard", "els => els.map(e => e.dataset.p)")}
            self.assertEqual(groups, {"Bas"})

            # ── sekmeler (ok tuşu) + uzay tarzı EQ'yu korur + geri al ──
            bands_before = json.dumps(sess.state["bands"])
            pg.locator("#tab-prof").focus()
            pg.keyboard.press("ArrowRight")
            self.assertEqual(pg.get_attribute("#tab-space", "aria-selected"), "true")
            pg.click('#space-presets .pcard[data-p="studyo"]')
            self.assertTrue(wait(lambda: sess.state["crossfeed"]["feed"] == 9.5))
            self.assertEqual(json.dumps(sess.state["bands"]), bands_before)
            pg.wait_for_selector("#graph .cross")
            pg.keyboard.press("Control+z")
            self.assertTrue(wait(lambda: sess.state["crossfeed"]["feed"] != 9.5 or not sess.state["crossfeed"]["enabled"]))

            # ── A/B basılı tut ──
            pg.hover("#b-ab"); pg.mouse.down()
            self.assertTrue(wait(lambda: sess.bypass))
            pg.mouse.up()
            self.assertTrue(wait(lambda: not sess.bypass))

            # ── açılışta kullan ──
            pg.click("#b-commit")
            self.assertTrue(wait(lambda: len(self.commits) == 1))
            pg.wait_for_function("document.getElementById('b-commit').disabled")

            # ── canlı analizör (sahte kaynak: 1 kHz, −6 dBFS) ──
            pg.wait_for_function("document.getElementById('sig').classList.contains('on')", timeout=8000)
            self.assertIn("Müzik algılandı", pg.inner_text("#sig"))
            lit = pg.evaluate("""() => { const c = document.getElementById('spec'); const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
                                          let n = 0; for (let i = 3; i < d.length; i += 4) if (d[i]) n++; return n; }""")
            self.assertGreater(lit, 500)
            self.assertIn("−6", pg.inner_text("#m-val"))
            self.assertTrue(self.an.running())
            pg.click("#tab-an")
            pg.click('#an-resp button[data-r="slow"]')
            self.assertTrue(wait(lambda: self.an.response == "slow"))
            pg.click("label:has(#an-en)")
            self.assertTrue(wait(lambda: not self.an.running(), 4))            # kapatınca yakalama DURUR

            # ── tema + yardım + ekran görüntüleri ──
            pg.keyboard.press("?")
            self.assertTrue(pg.locator("#help-dlg").evaluate("d => d.open"))
            pg.keyboard.press("Escape")
            pg.click("#b-theme"); pg.click("#b-theme")                         # otomatik → koyu → açık
            self.assertEqual(pg.evaluate("document.documentElement.dataset.theme"), "light")
            pg.click("label:has(#an-en)")
            pg.wait_for_function("document.getElementById('sig').classList.contains('on')", timeout=8000)
            pg.click("#tab-prof")
            pg.screenshot(path=os.path.join(UI, "console-v2-light-1440.png"), full_page=True)
            m = ctx.new_page()
            m.set_viewport_size({"width": 390, "height": 900})
            m.goto(self.url)
            m.wait_for_selector("#pgrid .pcard")
            self.assertLessEqual(m.evaluate("document.scrollingElement.scrollWidth"), 390)   # yatay taşma yok
            m.screenshot(path=os.path.join(UI, "console-v2-mobile-390-tr.png"), full_page=True)
            m.close()
            b.close()
        # tek beklenen kayıt: çakışma akışının BİLEREK tetiklediği 409 (Chrome ağ günlüğü). JS hatası yok.
        self.assertEqual(errors, ["Failed to load resource: the server responded with a status of 409 (Conflict)"])


if __name__ == "__main__":
    unittest.main()
