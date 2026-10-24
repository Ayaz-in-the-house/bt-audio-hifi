"""U51–U53: Özel çalışma profilleri (D1). Ana profiller (hazır tarzlar + kilitli profiller) hiç değişmez; ilk elle
dokunuşta "Özel N" doğar; her değişiklik arka planda kalıcı olur (istek yolu diske dokunmaz); geri/ileri al yeniden
başlatmadan sonra da çalışır."""
import builtins
import hashlib
import json
import os
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import console, consoleserver, history, journal  # noqa: E402


class Fake:
    def apply_payload(self, p):
        pass


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def gain(st, g):
    s = json.loads(json.dumps(st))
    s["bands"][0].update(type="lowshelf", freq=105.0, gain=float(g), q=0.7, enabled=True)
    return s


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.pdir = os.path.join(self.tmp, "p")
        self.jdir = os.path.join(self.tmp, "j")
        self.sess = self.new_session()

    def new_session(self):
        w = journal.Writer(self.jdir, delay_s=0.05)
        return consoleserver.Session(Fake(), on_commit=lambda s: {}, profiles_dir=self.pdir, writer=w)

    def tearDown(self):
        self.sess.writer.close()


class TestFork(Base):
    def test_u51_first_touch_on_preset_forks_ozel_1(self):
        v = self.sess.preset("zengin_bas")
        before = json.dumps(console.PRESETS["zengin_bas"], sort_keys=True)
        v = self.sess.set_state(gain(v["state"], 5))
        self.assertEqual(v["active"]["kind"], "profile")
        self.assertEqual(v["active"]["name"], "Özel 1")
        doc = self.sess.store.get(v["active"]["id"])
        self.assertTrue(doc["auto"])
        self.assertFalse(doc["locked"])
        self.assertEqual(doc["derived_from"], {"kind": "preset", "id": "zengin_bas", "name": "Zengin bas"})
        self.assertEqual(json.dumps(console.PRESETS["zengin_bas"], sort_keys=True), before)   # hazır tarz dokunulmadı
        v2 = self.sess.set_state(gain(v["state"], 6))                                        # ikinci dokunuş: çatal YOK
        self.assertEqual(v2["active"]["id"], v["active"]["id"])
        self.assertEqual(len(v2["profiles"]), 1)
        self.assertFalse(v2["dirty"])

    def test_u51_locked_profile_never_changes(self):
        self.sess.set_state(gain(console.default_state(), 3))
        v = self.sess.save_profile("Benim ana ayarım")                   # adıyla kayıt = kilitli
        pid = v["active"]["id"]
        self.sess.writer.flush()                                          # önce diske insin, sonra sha
        path = os.path.join(self.pdir, pid + ".json")
        h0 = sha(path)
        v = self.sess.set_state(gain(v["state"], 9))
        self.assertTrue(v["active"]["name"].startswith("Özel"))
        self.sess.writer.flush()
        self.assertEqual(sha(path), h0)                                   # ana profil DEĞİŞMEDİ
        self.assertEqual(self.sess.store.get(v["active"]["id"])["derived_from"]["id"], pid)

    def test_u51_numbering_never_reuses(self):
        a = self.sess.set_state(gain(console.default_state(), 1))["active"]  # varsayılan → Özel 1
        self.sess.preset("rock")
        b = self.sess.set_state(gain(self.sess.state, 2))["active"]
        self.assertEqual((a["name"], b["name"]), ("Özel 1", "Özel 2"))
        self.sess.delete_profile(a["id"])
        self.sess.preset("pop")
        c = self.sess.set_state(gain(self.sess.state, 4))["active"]
        self.assertEqual(c["name"], "Özel 3")                             # silinen numara yeniden kullanılmaz

    def test_u51_apply_to_parent_and_promote(self):
        self.sess.set_state(gain(console.default_state(), 3))
        parent = self.sess.save_profile("Ana")["active"]["id"]
        v = self.sess.set_state(gain(self.sess.state, 7))
        work = v["active"]["id"]
        v = self.sess.apply_to_parent()                                  # açık eylem: ana profile yaz
        self.assertEqual(self.sess.store.get(parent)["state"]["bands"][0]["gain"], 7.0)
        self.assertEqual(v["active"]["id"], parent)
        v = self.sess.load_profile(work)
        v = self.sess.promote(work, "Gece bası")                         # çalışma kopyasını adlandır → kilitli ana profil
        doc = self.sess.store.get(v["active"]["id"])
        self.assertEqual((doc["name"], doc["locked"], doc["auto"]), ("Gece bası", True, False))


class TestLatency(Base):
    def test_u52_request_path_never_touches_disk(self):
        main = threading.get_ident()
        writes = []
        real_open = builtins.open

        def spy(file, mode="r", *a, **k):
            if any(c in mode for c in "wax+") and threading.get_ident() == main:
                writes.append(file)
            return real_open(file, mode, *a, **k)
        self.sess.preset("zengin_bas")
        self.sess.set_state(gain(self.sess.state, 1))                    # çatal (bir kerelik, profil oluşturma)
        builtins.open = spy
        try:
            t = []
            for i in range(300):
                t0 = time.perf_counter()
                self.sess.set_state(gain(self.sess.state, (i % 20) * 0.5))
                t.append(time.perf_counter() - t0)
        finally:
            builtins.open = real_open
        self.assertEqual(writes, [])                                     # istek iş parçacığında dosya yazımı YOK
        self.sess.writer.flush()
        pid = self.sess.active["id"]
        self.assertEqual(self.sess.store.get(pid)["state"], self.sess.state)   # son durum diskte
        t.sort()
        self.assertLess(t[int(len(t) * 0.95)], 0.02)                     # p95 < 20 ms (model hesabı dahil)

    def test_u52_overhead_vs_no_writer_under_1ms(self):
        def p95(sess):
            sess.preset("zengin_bas")
            sess.set_state(gain(sess.state, 1))
            t = []
            for i in range(200):
                t0 = time.perf_counter()
                sess.set_state(gain(sess.state, (i % 20) * 0.5))
                t.append(time.perf_counter() - t0)
            return sorted(t)[int(len(t) * 0.95)]
        off = consoleserver.Session(Fake(), on_commit=lambda s: {}, profiles_dir=os.path.join(self.tmp, "q"),
                                    writer=journal.NullWriter())
        a, b = p95(self.sess), p95(off)
        self.assertLess(a - b, 0.001, (a, b))


class TestNav(Base):
    def test_u53_accidental_preset_click_is_undoable(self):
        self.sess.preset("rock")
        work = self.sess.set_state(gain(self.sess.state, 4))["active"]["id"]   # Özel 1, saatlerce uğraş
        self.sess.preset("klasik")                                         # yanlış tıklama
        v = self.sess.undo()
        self.assertEqual((v["active"]["id"], v["state"]["bands"][0]["gain"]), (work, 4.0))
        v = self.sess.redo()
        self.assertEqual(v["active"]["id"], "klasik")

    def test_u53_space_preset_edits_working_copy(self):
        self.sess.preset("rock")
        self.sess.set_state(gain(self.sess.state, 4))
        v = self.sess.preset("studyo")
        self.assertEqual((v["active"]["name"], v["state"]["bands"][0]["gain"], v["state"]["crossfeed"]["feed"]), ("Özel 1", 4.0, 9.5))
        v = self.sess.undo()
        self.assertFalse(v["state"]["crossfeed"]["enabled"])


class TestHistory(Base):
    def test_u53_undo_redo_survives_restart(self):
        self.sess.preset("zengin_bas")
        for g in (1, 2, 3, 4, 5):
            self.sess.set_state(gain(self.sess.state, g))
            self.sess.history_seal()                                     # her biri ayrı geri-al adımı
        pid = self.sess.active["id"]
        self.sess.writer.close()
        self.sess = self.new_session()                                   # yeniden başlatma benzetimi
        v = self.sess.load_profile(pid)
        self.assertEqual(v["state"]["bands"][0]["gain"], 5.0)
        for _ in range(3):
            v = self.sess.undo()
        self.assertEqual(v["state"]["bands"][0]["gain"], 2.0)
        v = self.sess.redo()
        self.assertEqual(v["state"]["bands"][0]["gain"], 3.0)
        v = self.sess.set_state(gain(v["state"], 9))                     # yeni değişiklik ileri dalı keser
        self.assertFalse(v["history"]["can_redo"])
        self.sess.writer.close()
        self.sess = self.new_session()
        v = self.sess.load_profile(pid)
        self.assertEqual(v["state"]["bands"][0]["gain"], 9.0)
        v = self.sess.undo()
        self.assertEqual(v["state"]["bands"][0]["gain"], 3.0)
        v = self.sess.undo()
        v = self.sess.undo()
        self.assertEqual(v["state"]["bands"][0]["gain"], 1.0)
        v = self.sess.undo()                                             # v0 = çatal öncesi tarzın kendisi
        self.assertEqual(v["state"]["bands"], console.PRESETS["zengin_bas"]["bands"])

    def test_u53_stale_journal_with_same_name_is_ignored(self):
        """E21: aynı kimlikte eski günlük (silinmiş profil / test artığı) yeni çalışma kopyasına karışmaz."""
        os.makedirs(self.jdir, exist_ok=True)
        with open(os.path.join(self.jdir, "özel-1.jsonl"), "w") as f:
            f.write(json.dumps({"v": 0, "state": gain(console.default_state(), -9)}) + "\n")
            f.write(json.dumps({"v": 1, "state": gain(console.default_state(), -7)}) + "\n")
        self.sess.preset("rock")
        self.sess.set_state(gain(self.sess.state, 2))
        pid = self.sess.active["id"]
        self.sess.writer.close()
        self.sess = self.new_session()
        self.sess.load_profile(pid)
        v = self.sess.undo()
        self.assertEqual(v["state"]["bands"], console.PRESETS["rock"]["bands"])
        self.assertEqual(v["history"]["versions"], 2)                    # eski -9/-7 sürümleri YOK (v0 tarz + v1)
        self.assertFalse(self.sess.hist.info()["can_undo"])

    def test_u53_rapid_changes_coalesce_into_one_step(self):
        self.sess.preset("rock")
        for i in range(30):                                              # sürükleme: 30 ara değer
            self.sess.set_state(gain(self.sess.state, i * 0.2))
        v = self.sess.undo()
        self.assertEqual(v["state"]["bands"], console.PRESETS["rock"]["bands"])   # tek adımda sürükleme öncesi

    def test_u53_journal_lines_small_and_crash_tolerant(self):
        self.sess.preset("rock")
        for g in (1, 2, 3):
            self.sess.set_state(gain(self.sess.state, g))
            self.sess.history_seal()
        self.sess.writer.flush()
        pid = self.sess.active["id"]
        path = os.path.join(self.jdir, pid + ".jsonl")
        lines = open(path, "rb").read().splitlines()
        self.assertTrue(all(len(l) <= 4096 for l in lines), [len(l) for l in lines])
        with open(path, "ab") as f:
            f.write(b'{"v": 99, "state": {"ban')                          # çökmede yarım satır
        h = history.load(path)
        self.assertEqual(h.current()["bands"][0]["gain"], 3.0)


if __name__ == "__main__":
    unittest.main()
