"""U58–U60: otomasyon motorunun canlı bağlantısı (D3–D5) — sahte analizör/sınıflayıcı/saat, gerçek Session.

U58  ADL düzeltmesi bir ÜST KATMAN: uygulanan sese eklenir, kullanıcının durumuna / çalışma kopyasına / geçmişine YAZILMAZ.
U59  Motor kararları: konuşma → Konuşma tarzı · etiketli profil öncelikli · elle dokunuş askı · sessizlik no-op ·
     konuşmada ADL bas eklemez · kapatınca katman kalkar + analizör aboneliği bırakılır · ayarlar kalıcı.
U60  /api/auto uç noktası: mod, geçersiz mod 400, yoklama (daha çok/az bas) öğrenmeye yazılır."""
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import analyzer, autoctl, autoengine, console, consoleserver, features  # noqa: E402

C = analyzer._centers()


class Rec:
    def __init__(self):
        self.payloads = []

    def apply_payload(self, p):
        self.payloads.append(p)


def bands(boost=None, base=-30.0):
    b = np.full(len(C), base)
    for (lo, hi), g in (boost or {}).items():
        b[(C >= lo) & (C < hi)] += g
    return b.tolist()


class FakeAnalyzer:
    def __init__(self):
        self.subs, self.snap = set(), None
        self._n = 0

    def subscribe(self, kind="ui"):
        self._n += 1
        self.subs.add(self._n)
        return self._n

    def unsubscribe(self, sid):
        self.subs.discard(sid)

    def snapshot(self, tap="pre", seconds=2.0):
        return self.snap

    def info(self):
        return {"available": True, "running": bool(self.subs)}


class FakeClassifier:
    available, reason = True, None

    def __init__(self):
        self.macro = None

    def predict(self, audio):
        return None if self.macro is None else {"macro": dict(self.macro), "music": 0.5,
                                                "instruments": [["Bass guitar", 0.4]]}


def snap(b, level=-20.0, signal=True):
    return {"centers": C.tolist(), "bands": b, "level_db": level, "signal": signal,
            "audio": np.zeros(96000, np.float32)}


def make(tmp, mode="off", **kw):
    rec = Rec()
    sess = consoleserver.Session(rec, lambda st: None, profiles_dir=os.path.join(tmp, "p"), clock=lambda: 0.0)
    an, clf = FakeAnalyzer(), FakeClassifier()
    t = [0.0]
    eng = autoengine.AutoEngine(sess, an, classifier=clf, clock=lambda: t[0], state_path=os.path.join(tmp, "auto.json"),
                                autostart=False, **kw)
    eng.set_mode(mode)
    return sess, rec, an, clf, eng, t


def run(eng, t, n):
    for _ in range(n):
        t[0] += 1.0
        eng.tick()


class TestOverlay(unittest.TestCase):
    def test_u58_offsets_reach_output_not_user_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, rec, *_ = make(tmp)
            sess.preset("zengin_bas")
            user = json.loads(json.dumps(sess.state))
            sess.set_auto_offsets({"bas": 3.0, "alt_orta": 0.0, "varlık": -2.0, "hava": 0.0})
            eff = autoctl.apply_offsets(user, sess.auto_offsets)
            self.assertEqual(rec.payloads[-1], console.pw_params(eff))          # sese ULAŞTI
            self.assertEqual(sess.state, user)                                   # kullanıcının durumu aynı
            v = sess.view()
            self.assertEqual(v["auto_offsets"]["bas"], 3.0)
            self.assertIn("curve_auto", v)
            # kullanıcı dokunur → çalışma kopyası açılır; kaydedilen durumda ADL bantları YOK
            st = json.loads(json.dumps(sess.state))
            st["width"] = 1.1
            sess.set_state(st)
            saved = sess.store.get(sess.active["id"])["state"]
            self.assertEqual(saved, console.sanitize(st))
            self.assertEqual(rec.payloads[-1], console.pw_params(autoctl.apply_offsets(sess.state, sess.auto_offsets)))
            sess.set_auto_offsets(None)                                          # katman kalkar
            self.assertEqual(rec.payloads[-1], console.pw_params(sess.state))
            self.assertIsNone(sess.view()["auto_offsets"])


class TestEngine(unittest.TestCase):
    def test_u59_speech_switches_to_speech_preset_and_manual_pauses(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, rec, an, clf, eng, t = make(tmp, mode="apc")
            an.snap = snap(bands())
            clf.macro = {"konuşma": 0.9, "elektronik": 0.05}
            run(eng, t, 40)
            self.assertEqual((sess.active["kind"], sess.active["id"]), ("preset", "konusma"))
            self.assertTrue(eng.status()["log"])
            # kullanıcı elle dokunur → askı; müzik başlasa da 10 sn içinde geçiş yok
            st = json.loads(json.dumps(sess.state))
            st["width"] = 0.9
            sess.set_state(st)
            clf.macro = {"konuşma": 0.0, "elektronik": 0.95}
            active = sess.active["id"]
            run(eng, t, 9)
            self.assertEqual(sess.active["id"], active)
            run(eng, t, 60)
            self.assertEqual((sess.active["kind"], sess.active["id"]), ("preset", "elektronik"))

    def test_u59_tagged_profile_wins_over_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, rec, an, clf, eng, t = make(tmp, mode="apc")
            pid = sess.store.save("Benim derin basım", console.apply_preset(console.default_state(), "derin_sub"))
            sess.set_genres(pid, ["elektronik"])
            an.snap = snap(bands())
            clf.macro = {"elektronik": 0.9}
            run(eng, t, 40)
            self.assertEqual((sess.active["kind"], sess.active["id"]), ("profile", pid))
            self.assertEqual(eng.status()["mapping"]["elektronik"], "profile:" + pid)

    def test_u59_auto_counts_as_activity_and_close_clears_layer(self):
        """Otomatik mod açıkken sayfa kapalı olsa da sunucu 'boşta' sayılıp kapanmaz (idle watchdog); kapanışta ADL katmanı
        sesten kaldırılır (motorsuz, donmuş bir düzeltme kalmaz)."""
        with tempfile.TemporaryDirectory() as tmp:
            sess, rec, an, clf, eng, t = make(tmp, mode="adl")
            sess.clock = lambda: 5000.0
            an.snap = snap(bands())
            run(eng, t, 1)
            self.assertEqual(sess.last, 5000.0)
            sess.set_auto_offsets({"bas": 2.0})
            eng.close(clear=True)
            self.assertIsNone(sess.auto_offsets)
            self.assertEqual(rec.payloads[-1], console.pw_params(sess.state))

    def test_u59_hold_suspends_automation_until_release(self):
        """PRD-BTA05 E1.4: kör test sırasında otomasyon ASKIDA (test sesi tür değiştirmesin, ADL kaymasın)."""
        with tempfile.TemporaryDirectory() as tmp:
            sess, rec, an, clf, eng, t = make(tmp, mode="apc")
            an.snap = snap(bands())
            clf.macro = {"konuşma": 0.9}
            eng.hold("kör test")
            run(eng, t, 40)
            self.assertIsNone(sess.active)                                    # askıdayken yükleme yok
            self.assertEqual(eng.status()["held"], "kör test")
            eng.release()
            run(eng, t, 40)
            self.assertEqual(sess.active["id"], "konusma")
            self.assertIsNone(eng.status()["held"])

    def test_u59_silence_is_noop(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, rec, an, clf, eng, t = make(tmp, mode="both")
            an.snap = snap(bands(base=-300), level=-120, signal=False)
            clf.macro = {"elektronik": 0.9}
            n0 = len(rec.payloads)
            run(eng, t, 30)
            self.assertEqual(len(rec.payloads), n0)
            self.assertIsNone(sess.active)
            self.assertEqual(eng.status()["state"], "sessizlik")

    def test_u59_adl_bass_on_thin_music_not_on_speech(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, rec, an, clf, eng, t = make(tmp, mode="adl")
            eng.dyn.ref = {k: 0.0 for k in features.REGIONS}
            eng.ref_n = 10 ** 6                               # referans sabit (öğrenme etkisini dışla)
            an.snap = snap(bands({(20, 60): -10}))
            clf.macro = {"pop": 0.9}
            run(eng, t, 15)
            self.assertGreater(sess.auto_offsets["bas"], 1.0)
            self.assertIsNone(sess.active)                    # ADL profil DEĞİŞTİRMEZ
            sess2, rec2, an2, clf2, eng2, t2 = make(tempfile.mkdtemp(dir=tmp), mode="adl")
            eng2.dyn.ref = {k: 0.0 for k in features.REGIONS}
            eng2.ref_n = 10 ** 6
            an2.snap = snap(bands({(20, 60): -10}))
            clf2.macro = {"konuşma": 0.9}
            run(eng2, t2, 15)
            self.assertTrue(all(abs(v) < 1e-9 for v in (sess2.auto_offsets or {"x": 0}).values()))

    def test_u59_off_removes_layer_releases_capture_and_persists(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, rec, an, clf, eng, t = make(tmp, mode="adl")
            self.assertEqual(len(an.subs), 1)                 # açıkken analizör aboneliği var
            sess.set_auto_offsets({"bas": 2.0})
            eng.configure({"nudge": {"band": "bas", "delta": 2.0}})
            eng.set_mode("off")
            self.assertEqual(len(an.subs), 0)                 # kapalıyken yakalama bedeli yok
            self.assertIsNone(sess.auto_offsets)
            eng.flush()
            with open(os.path.join(tmp, "auto.json")) as f:
                saved = json.load(f)
            self.assertEqual(saved["mode"], "off")
            self.assertAlmostEqual(saved["bias"]["bas"], 0.4)
            eng3 = autoengine.AutoEngine(sess, an, classifier=clf, clock=lambda: 0.0,
                                         state_path=os.path.join(tmp, "auto.json"), autostart=False)
            self.assertAlmostEqual(eng3.dyn.bias["bas"], 0.4)  # öğrenilen tercih yeniden başlatmada korunur


class TestAdlHysteresis(unittest.TestCase):
    """U73 (E31/R50): nicemleme sınırında salınım sürekli geçiş üretmesin; gerçek sürüklenme yine takip edilsin."""

    def _engine(self, tmp, seq):
        sess, rec, an, clf, eng, t = make(tmp, mode="adl")
        an.snap = snap(bands())
        clf.macro = {"pop": 0.9}
        it = iter(seq)
        eng.dyn.step = lambda ex, genre, level, now: {"bas": next(it), "alt_orta": 0.0, "varlık": 0.0, "hava": 0.0}
        calls = []
        orig = sess.set_auto_offsets
        sess.set_auto_offsets = lambda o, **kw: (calls.append(dict(o) if o else None), orig(o, **kw))[1]
        return sess, eng, t, calls

    def test_u73_boundary_dither_is_not_applied_repeatedly(self):
        with tempfile.TemporaryDirectory() as tmp:
            seq = [1.24 if i % 2 else 1.26 for i in range(30)]
            sess, eng, t, calls = self._engine(tmp, seq)
            run(eng, t, 30)
            self.assertLessEqual(len(calls), 1, calls)

    def test_u73_real_drift_is_followed_with_bounded_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            seq = [4.0 * i / 29 for i in range(30)] + [4.0] * 10
            sess, eng, t, calls = self._engine(tmp, seq)
            run(eng, t, 40)
            self.assertLessEqual(abs(sess.auto_offsets["bas"] - 4.0), 0.5)
            self.assertLessEqual(len(calls), 40 / autoengine.ADL_MIN_S + 1, calls)


class TestApi(unittest.TestCase):
    def test_u60_auto_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            sess, rec, an, clf, eng, t = make(tmp)
            httpd, url, stop = consoleserver.serve(sess)
            try:
                def post(body):
                    rq = urllib.request.Request(url + "api/auto", json.dumps(body).encode(),
                                                {"Content-Type": "application/json"})
                    return json.load(urllib.request.urlopen(rq, timeout=5))
                v = post({"mode": "both"})
                self.assertEqual(v["auto"]["mode"], "both")
                with self.assertRaises(urllib.error.HTTPError) as cm:
                    post({"mode": "uçan"})
                self.assertEqual(cm.exception.code, 400)
                v = post({"nudge": {"band": "bas", "delta": -1.0}})
                self.assertAlmostEqual(v["auto"]["bias"]["bas"], -0.2)
                g = json.load(urllib.request.urlopen(url + "api/state", timeout=5))
                self.assertEqual(g["auto"]["mode"], "both")
            finally:
                stop.set()
                eng.close()


if __name__ == "__main__":
    unittest.main()
