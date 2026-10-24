"""U63: yönetim sayfası arka ucu (D6) — sürüm zaman çizelgesi, sürüm geri yükleme (yıkıcı DEĞİL), profil tablosu,
çöp kutusu listesi, toplu dışa/içe aktarma, /admin sayfası güvenlik başlıkları."""
import json
import os
import sys
import tempfile
import unittest
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import console, consoleserver, history  # noqa: E402


class Rec:
    def apply_payload(self, p):
        pass


def st_gain(g):
    s = console.default_state()
    s["bands"][0].update(type="bell", freq=1000.0, gain=float(g), q=1.0, enabled=True)
    return console.sanitize(s)


def session(tmp):
    t = [100.0]
    sess = consoleserver.Session(Rec(), lambda st: None, profiles_dir=os.path.join(tmp, "p"), clock=lambda: t[0])
    return sess, t


class TestTimeline(unittest.TestCase):
    def test_u63_timeline_follows_replay_semantics(self):
        lines = [json.dumps(x).encode() for x in (
            {"v": 0, "t": 1.0, "state": {"a": 0}, "reset": True},
            {"v": 1, "t": 2.0, "state": {"a": 1}},
            {"v": 2, "t": 3.0, "state": {"a": 2}},
            {"ptr": 1, "t": 4.0},                      # geri al
            {"v": 2, "t": 5.0, "state": {"a": 9}},     # yeni dal → eski v2 düşer
            {"v": 3, "t": 6.0, "state": {"a": 10}})] + [b'{"v": 4, "t": 7']   # yarım satır (çökme)
        tl = history.timeline(lines)
        self.assertEqual([(x["v"], x["t"]) for x in tl["versions"]], [(0, 1.0), (1, 2.0), (2, 5.0), (3, 6.0)])
        self.assertEqual(tl["versions"][2]["state"], {"a": 9})
        self.assertEqual(tl["ptr"], 3)
        self.assertEqual(history.replay(lines).current(), tl["versions"][tl["ptr"]]["state"])


class TestAdmin(unittest.TestCase):
    def test_u63_versions_restore_is_non_destructive(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, t = session(tmp)
            sess.preset("zengin_bas")
            for g in (2, 4, 6):
                t[0] += 5
                sess.set_state(st_gain(g), seal=True)
            pid = sess.active["id"]
            tl = sess.admin_timeline(pid)
            self.assertEqual(len(tl["versions"]), 4)                    # v0 (dokunuş öncesi) + 3 düzenleme
            self.assertEqual(tl["ptr"], 3)
            self.assertIn("summary", tl["versions"][1])
            self.assertTrue(tl["versions"][2]["diff"])                  # önceki sürüme göre ne değişti
            t[0] += 5
            sess.admin_restore(pid, 1)
            self.assertEqual(sess.state, st_gain(2))
            tl2 = sess.admin_timeline(pid)
            self.assertEqual(len(tl2["versions"]), 5)                   # geri yükleme YENİ sürüm (geçmiş silinmez)
            self.assertEqual(tl2["versions"][3]["state"], st_gain(6))
            self.assertEqual(sess.store.get(pid)["state"], st_gain(2))
            self.assertTrue(sess.undo()["history"]["can_redo"])         # geri yükleme de geri alınabilir

    def test_u63_profile_table_trash_and_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, t = session(tmp)
            locked = sess.store.save("Ana bas", st_gain(3))
            sess.set_state(st_gain(1), seal=True)
            wc = sess.active["id"]
            rows = {r["id"]: r for r in sess.admin_profiles()}
            self.assertEqual(rows[locked]["versions"], 1)
            self.assertGreaterEqual(rows[wc]["versions"], 2)
            self.assertGreater(rows[locked]["bytes"], 100)
            with self.assertRaises(ValueError):
                sess.admin_restore(locked, 0)                          # kilitli profilin sürüm geçmişi yok
            token = sess.delete_profile(locked)["trash"]
            tr = sess.store.trash_list()
            self.assertEqual([(x["token"], x["name"]) for x in tr], [(token, "Ana bas")])
            bundle = sess.admin_export_all()
            self.assertEqual(bundle["schema"], "bta-bundle/1")
            self.assertEqual([p["name"] for p in bundle["profiles"]], [sess.store.get(wc)["name"]])
            sess2, _ = session(tempfile.mkdtemp(dir=tmp))
            res = sess2.admin_import_bundle(bundle)
            self.assertEqual(len(res["imported"]), 1)
            self.assertEqual(sess2.store.list()[0]["name"], sess.store.get(wc)["name"])
            with self.assertRaises(ValueError):
                sess2.admin_import_bundle({"schema": "x", "profiles": []})

    def test_u63_admin_http(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, t = session(tmp)
            sess.set_state(st_gain(1), seal=True)
            httpd, url, stop = consoleserver.serve(sess)
            try:
                r = urllib.request.urlopen(url + "admin", timeout=5)
                self.assertIn("default-src 'self'", r.headers["Content-Security-Policy"])
                self.assertIn(b"<title>", r.read())
                rows = json.load(urllib.request.urlopen(url + "api/admin/profiles", timeout=5))
                self.assertEqual(len(rows["profiles"]), 1)
                pid = rows["profiles"][0]["id"]
                from urllib.parse import quote
                tl = json.load(urllib.request.urlopen(url + "api/admin/timeline?id=" + quote(pid), timeout=5))
                self.assertGreaterEqual(len(tl["versions"]), 2)
                b = urllib.request.urlopen(url + "api/admin/export-all", timeout=5)
                self.assertIn("attachment", b.headers["Content-Disposition"])
                self.assertEqual(json.load(b)["schema"], "bta-bundle/1")
            finally:
                stop.set()


if __name__ == "__main__":
    unittest.main()
