"""U41–U42: profil deposu (C1) + oturumun aktif profil / değişti (dirty) takibi."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import console, consoleserver, profiles  # noqa: E402


def st_with(gain):
    s = console.default_state()
    s["bands"][0].update(type="lowshelf", freq=105.0, gain=gain, q=0.7, enabled=True)
    return console.sanitize(s)


class TestStore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = profiles.ProfileStore(os.path.join(self.tmp.name, "p"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_u41_save_schema_and_turkish_name(self):
        pid = self.store.save("Akşam dinleme — güçlü bas", st_with(6), notes="kulak tıkacı L")
        doc = json.load(open(os.path.join(self.store.dir, pid + ".json")))
        self.assertEqual(doc["schema"], profiles.SCHEMA)
        self.assertEqual(doc["name"], "Akşam dinleme — güçlü bas")
        self.assertEqual(doc["notes"], "kulak tıkacı L")
        self.assertTrue(doc["created"] and doc["updated"])
        self.assertEqual(doc["state"], st_with(6))
        self.assertEqual([p["id"] for p in self.store.list()], [pid])

    def test_u41_conflict_requires_overwrite(self):
        pid = self.store.save("Benim", st_with(3))
        created = self.store.get(pid)["created"]
        with self.assertRaises(profiles.Conflict):
            self.store.save("benim", st_with(5))            # aynı kimlik (büyük/küçük harf)
        self.store.save("Benim", st_with(5), overwrite=True)
        doc = self.store.get(pid)
        self.assertEqual(doc["state"]["bands"][0]["gain"], 5.0)
        self.assertEqual(doc["created"], created)            # oluşturma zamanı korunur

    def test_u41_path_traversal_cannot_escape(self):
        for evil in ("../../etc/passwd", "..", "/tmp/x", "a/../../b"):
            pid = self.store.save(evil, st_with(1), overwrite=True)
            p = os.path.realpath(os.path.join(self.store.dir, pid + ".json"))
            self.assertTrue(p.startswith(os.path.realpath(self.store.dir) + os.sep), p)
        with self.assertRaises(ValueError):
            self.store.save("   ", st_with(1))
        with self.assertRaises(KeyError):
            self.store.get("../../etc/passwd")

    def test_u41_rename_duplicate(self):
        pid = self.store.save("A", st_with(2))
        nid = self.store.rename(pid, "B")
        self.assertEqual([p["name"] for p in self.store.list()], ["B"])
        self.store.save("C", st_with(1))
        with self.assertRaises(profiles.Conflict):
            self.store.rename(nid, "C")
        d1 = self.store.duplicate(nid)
        d2 = self.store.duplicate(nid)
        names = sorted(p["name"] for p in self.store.list())
        self.assertEqual(names, ["B", "B (kopya 2)", "B (kopya)", "C"])
        self.assertNotEqual(d1, d2)

    def test_u41_delete_to_trash_and_restore(self):
        pid = self.store.save("Sil beni", st_with(4))
        token = self.store.delete(pid)
        self.assertEqual(self.store.list(), [])
        self.store.restore(token)
        self.assertEqual(self.store.get(pid)["state"], st_with(4))

    def test_u41_export_import_roundtrip_and_validation(self):
        pid = self.store.save("Paylaş", st_with(7))
        doc = self.store.export(pid)
        other = profiles.ProfileStore(os.path.join(self.tmp.name, "q"))
        nid = other.import_doc(doc)
        self.assertEqual(other.get(nid)["state"], st_with(7))
        nid2 = other.import_doc(doc)                          # çakışma → yeni adla, veri kaybı yok
        self.assertNotEqual(nid, nid2)
        legacy = {"name": "eski", "saved_at": "2026-09-27 21:00:00", "state": st_with(2)}
        self.assertEqual(other.get(other.import_doc(legacy))["name"], "eski")
        bad = json.loads(json.dumps(doc))
        bad["state"]["bands"] = bad["state"]["bands"][:3]
        for b in (bad, {"schema": "x"}, [], {"name": "n"}):
            with self.assertRaises(ValueError):
                other.import_doc(b)
        clamped = json.loads(json.dumps(doc))
        clamped["state"]["bands"][0]["gain"] = 99
        self.assertEqual(other.get(other.import_doc(clamped))["state"]["bands"][0]["gain"], console.G_MAX)


class Fake:
    def apply_payload(self, p):
        self.last = p


class TestSessionDirty(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.sess = consoleserver.Session(Fake(), on_commit=lambda s: {}, profiles_dir=os.path.join(self.tmp.name, "p"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_u42_active_and_dirty(self):
        """D1 sözleşmesi (PRD-BTA04): kayıtlı (kilitli) profil düzenlenince 'değişti' OLMAZ — Özel N çalışma kopyası
        açılır ve her an kayıtlıdır; hazır tarz da aynı."""
        v = self.sess.view()
        self.assertIsNone(v["active"])
        v = self.sess.set_state(st_with(6))                   # kaydedilmemiş ayara dokunuş → Özel 1
        self.assertEqual((v["active"]["name"], v["dirty"]), ("Özel 1", False))
        v = self.sess.save_profile("Benim bas")               # çalışma kopyası adlandırılır → kilitli ana profil
        self.assertEqual((v["active"]["kind"], v["active"]["name"], v["active"]["locked"], v["dirty"]),
                         ("profile", "Benim bas", True, False))
        v = self.sess.set_state(st_with(8))
        self.assertEqual((v["active"]["name"], v["dirty"]), ("Özel 2", False))
        self.assertEqual(self.sess.store.get("benim-bas")["state"]["bands"][0]["gain"], 6.0)
        v = self.sess.preset("zengin_bas")
        self.assertEqual((v["active"]["kind"], v["active"]["id"], v["dirty"]), ("preset", "zengin_bas", False))
        v = self.sess.set_state({**v["state"], "width": 1.3})
        self.assertEqual(v["active"]["name"], "Özel 3")
        v = self.sess.load_profile("benim-bas")
        self.assertEqual((v["active"]["kind"], v["dirty"]), ("profile", False))

    def test_u42_overwrite_active_profile(self):
        self.sess.set_state(st_with(6))
        pid = self.sess.save_profile("X")["active"]["id"]
        self.sess.set_state(st_with(9))                       # → Özel 2
        with self.assertRaises(profiles.Conflict):
            self.sess.save_profile("X")                      # çalışma kopyasını "X" adına terfi → çakışma
        v = self.sess.save_profile("X", overwrite=True)
        self.assertFalse(v["dirty"])
        self.assertEqual(self.sess.store.get(pid)["state"]["bands"][0]["gain"], 9.0)

    def test_u42_is_default_tracks_commit(self):
        self.assertTrue(self.sess.view()["is_default"])            # başlangıç durumu = kurulu olan
        self.assertFalse(self.sess.set_state(st_with(5))["is_default"])
        self.assertTrue(self.sess.commit()["is_default"])
        self.assertFalse(self.sess.set_state(st_with(6))["is_default"])

    def test_u42_copy_preset_to_profiles(self):
        v = self.sess.preset("harman_bas")
        v = self.sess.save_profile("Harman bas (benim)")
        self.assertIn("Harman bas (benim)", [p["name"] for p in v["profiles"]])


if __name__ == "__main__":
    unittest.main()
