"""U44–U46: canlı analizör (C4). Ölçü aletinin kendisi test edilir: dBFS kalibrasyonu, 1/6 oktav bant gücü,
seviye metresi, balistik, abone yaşam döngüsü (kimse bakmıyorken yakalama süreci YOK)."""
import json
import os
import socket
import sys
import tempfile
import threading
import time
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import analyzer  # noqa: E402

FS = 48000


def sine(f, db, seconds=1.0, ch=2):
    t = np.arange(int(FS * seconds)) / FS
    x = 10 ** (db / 20) * np.sin(2 * np.pi * f * t)
    return np.stack([x] * ch, 1)


def wait_for(cond, t=6.0):
    t0 = time.time()
    while time.time() - t0 < t:
        if cond():
            return True
        time.sleep(0.1)
    return False


def band_at(sp, f):
    return int(np.argmin(np.abs(np.log(sp.centers / f))))


class TestCalibration(unittest.TestCase):
    def run_spec(self, x, response="fast"):
        sp = analyzer.Spectrum(response=response)
        out = None
        for i in range(0, len(x), 1200):
            for fr in sp.push(x[i:i + 1200]):
                out = fr
        return sp, out

    def test_u44_full_scale_sine_is_0_dbfs(self):
        for f, db, tol in ((1000, 0.0, 0.2), (1000, -20.0, 0.2), (997, -6.0, 0.2), (100, -10.0, 0.5), (5000, -3.0, 0.2)):
            with self.subTest(f=f, db=db):
                sp, fr = self.run_spec(sine(f, db, 2.0))
                self.assertAlmostEqual(fr["bands"][band_at(sp, f)], db, delta=tol)

    def test_u44_neighbouring_bands_much_lower(self):
        sp, fr = self.run_spec(sine(1000, 0.0, 2.0))
        i = band_at(sp, 1000)
        self.assertLess(fr["bands"][i + 3], -40)          # yarım oktav uzak: sızıntı küçük
        self.assertLess(fr["bands"][i - 3], -40)

    def test_u44_level_meter(self):
        lv = analyzer.LevelMeter()
        for i in range(0, FS * 2, 2400):
            m = lv.push(sine(1000, 0.0, 2.0)[i:i + 2400])
        self.assertAlmostEqual(m["L"]["rms"], -3.01, delta=0.05)
        self.assertAlmostEqual(m["L"]["peak"], 0.0, delta=0.05)
        self.assertGreaterEqual(m["L"]["true_peak"], m["L"]["peak"] - 0.01)
        x = np.zeros((2400, 2))
        x[100:110, 0] = 1.0
        x[200, 1] = -0.9995
        self.assertEqual(analyzer.LevelMeter().push(x)["clips"], 11)

    def test_u44_silence_is_floor_and_no_signal(self):
        sp, fr = self.run_spec(np.zeros((FS, 2)))
        self.assertTrue(all(v <= analyzer.FLOOR_DB for v in fr["bands"]))
        self.assertFalse(analyzer.LevelMeter().push(np.zeros((2400, 2)))["signal"])
        self.assertTrue(analyzer.LevelMeter().push(sine(1000, -40, 0.05))["signal"])


class TestBallistics(unittest.TestCase):
    def test_u45_release_and_peak_hold(self):
        """Tepe tutma hold_s boyunca sabit, sonra fall_db_s ile iner, ama hiçbir zaman anlık seviyenin altına inmez;
        anlık seviye τ ile güç alanında düşer (Friture ile aynı: üstel IIR, güç)."""
        sp = analyzer.Spectrum(response="medium", hold_s=0.5, fall_db_s=20.0)
        feed = lambda x: [fr for k in range(0, len(x), 2400) for fr in sp.push(x[k:k + 2400])]
        last = feed(sine(1000, -6, 2.0))[-1]
        i = band_at(sp, 1000)
        self.assertAlmostEqual(last["hold"][i], -6, delta=0.3)
        mid = feed(np.zeros((int(FS * 0.3), 2)))[-1]
        self.assertGreaterEqual(mid["hold"][i], -6.5)                       # tutma süresi içinde
        end = feed(np.zeros((int(FS * 1.7), 2)))[-1]
        self.assertLess(end["bands"][i], -26)                               # ≥20 dB düştü
        self.assertLessEqual(end["hold"][i], -6 - 20.0 * (2.0 - 0.5 - 0.4) + 2)
        self.assertGreaterEqual(end["hold"][i], end["bands"][i] - 0.05)      # tutma anlığın altına inmez

    def test_u45_ltas_average_only_while_signal(self):
        sp = analyzer.Spectrum(response="fast")
        for x in (sine(200, -12, 1.5), np.zeros((FS, 2))):
            for k in range(0, len(x), 2400):
                sp.push(x[k:k + 2400])
        i = band_at(sp, 200)
        self.assertAlmostEqual(sp.ltas()[i], -12, delta=1.0)     # sessizlik ortalamayı bozmaz
        sp.reset_ltas()
        self.assertLessEqual(max(sp.ltas()), analyzer.FLOOR_DB)


class FakeSource:
    """pw-record yerine: test sinüsü üreten alt süreç (gerçek süreç yaşam döngüsü test edilir)."""
    CMD = [sys.executable, "-c",
           "import sys,numpy as n,time\nt=n.arange(2400)/48000\nb=(0.5*n.sin(2*n.pi*1000*t)).astype('<f4')\n"
           "b=n.repeat(b,2).tobytes()\nwhile True:\n sys.stdout.buffer.write(b); sys.stdout.buffer.flush(); time.sleep(0.05)"]


class TestLifecycle(unittest.TestCase):
    def test_u46_capture_starts_on_first_subscriber_and_stops_after_last(self):
        an = analyzer.Analyzer(taps={"pre": {"cmd": FakeSource.CMD}, "post": {"cmd": FakeSource.CMD}}, linger_s=0.5)
        self.assertFalse(an.running())
        a = an.subscribe()
        b = an.subscribe()
        time.sleep(1.0)
        self.assertTrue(an.running())
        pids = an.pids()
        self.assertEqual(len(pids), 2)
        # kararlı duruma ulaşmayı BEKLE (pencere 0,34 s + τ 0,3 s): ilk kareyi okumak zamanlama yarışıydı (E18)
        vals, t0 = [], time.time()
        while time.time() - t0 < 6 and not (len(vals) >= 5 and all(abs(v + 6.02) <= 0.5 for v in vals[-5:])):
            fr = an.wait_frame(a, timeout=3)
            self.assertIsNotNone(fr)
            self.assertIn("post", fr)
            vals.append(fr["post"][int(np.argmin(np.abs(np.log(np.array(fr["f"]) / 1000))))])
        self.assertTrue(all(abs(v + 6.02) <= 0.5 for v in vals[-5:]), vals[-8:])
        an.unsubscribe(a)
        time.sleep(1.0)
        self.assertTrue(an.running())                    # hâlâ bir abone var
        an.unsubscribe(b)
        time.sleep(2.0)
        self.assertFalse(an.running())
        for pid in pids:                                  # alt süreç gerçekten gitti (zombi dahil değil)
            self.assertFalse(os.path.exists(f"/proc/{pid}") and open(f"/proc/{pid}/stat").read().split()[2] != "Z")

    def test_u61_snapshot_ring_buffer_for_classifier(self):
        """D3: otomasyon anlık görüntüsü — son N sn mono ses (sınıflayıcı girdisi) + bantlar + seviye. Yakalama yokken
        None (motor sessizlik sanıp karar vermez), halka tampon taşmada en yeni sesi tutar."""
        an = analyzer.Analyzer(taps={"pre": {"cmd": FakeSource.CMD}, "post": {"cmd": FakeSource.CMD}}, linger_s=0.3)
        self.assertIsNone(an.snapshot("pre"))
        sid = an.subscribe()
        try:
            t0 = time.time()
            s = None
            while time.time() - t0 < 8:
                s = an.snapshot("pre", 2.0)
                if s and s["audio"] is not None and s["level_db"] > -12:
                    break
                time.sleep(0.2)
            self.assertIsNotNone(s)
            self.assertEqual(len(s["audio"]), 96000)
            self.assertEqual(s["audio"].dtype, np.float32)
            self.assertAlmostEqual(float(np.max(np.abs(s["audio"]))), 0.5, places=2)   # mono = (L+R)/2, aynı sinüs
            self.assertAlmostEqual(s["level_db"], -9.03, delta=0.3)                    # 0,5 genlik sinüs RMS
            self.assertTrue(s["signal"])
            self.assertEqual(len(s["bands"]), len(s["centers"]))
            time.sleep(3.2)                                                            # halka (3 sn) en az bir kez döndü
            s2 = an.snapshot("pre", 3.0)
            self.assertEqual(len(s2["audio"]), 3 * FS)
            self.assertAlmostEqual(float(np.max(np.abs(s2["audio"]))), 0.5, places=2)
        finally:
            an.unsubscribe(sid)
            an.close()

    def test_u62_auto_only_subscriber_runs_light_single_tap(self):
        """D3 kaynak disiplini (T-L40 ölçümü: tam analizör %15 çekirdek): yalnız otomasyon dinlerken YALNIZ EQ-öncesi
        dokunuş çalışır, kare başına FFT/true-peak yapılmaz (hafif); spektrum istek anında halka tampondan hesaplanır ve
        kalibrasyonu tam analizörle aynıdır (0,5 genlik 1 kHz sinüs = −6,02 dBFS). Arayüz abonesi gelince tam moda geçer,
        gidince (bekleme sonrası) hafife döner; son abone gidince hiçbir süreç kalmaz."""
        an = analyzer.Analyzer(taps={"pre": {"cmd": FakeSource.CMD}, "post": {"cmd": FakeSource.CMD}}, linger_s=0.3)
        a = an.subscribe(kind="auto")
        try:
            self.assertTrue(wait_for(lambda: len(an.pids()) == 1))
            self.assertEqual(sorted(t for t, x in an.taps.items() if x.alive()), ["pre"])
            self.assertTrue(an.taps["pre"].light)
            s = None
            t0 = time.time()
            while time.time() - t0 < 6:
                s = an.snapshot("pre", 2.0)
                if s and s["audio"] is not None and s["level_db"] > -12:
                    break
                time.sleep(0.2)
            self.assertIsNotNone(s)
            i1k = int(np.argmin(np.abs(np.log(np.array(s["centers"]) / 1000))))
            self.assertAlmostEqual(s["bands"][i1k], -6.02, delta=0.3)
            self.assertLess(max(s["bands"][:i1k - 6]), -40)                         # sızıntı yok (Hann)
            self.assertIsNone(an.taps["pre"].last)                                  # kare başına spektrum YOK
            u = an.subscribe()                                                      # arayüz açıldı
            self.assertTrue(wait_for(lambda: len(an.pids()) == 2))
            self.assertFalse(an.taps["pre"].light)
            self.assertIsNotNone(an.wait_frame(u, timeout=3))
            an.unsubscribe(u)
            self.assertTrue(wait_for(lambda: len(an.pids()) == 1, 4))
            self.assertTrue(an.taps["pre"].light)
        finally:
            an.unsubscribe(a)
        self.assertTrue(wait_for(lambda: not an.running(), 4))
        an.close()

    def test_u46_sse_stream_frames_and_disconnect_cleanup(self):
        from btaudio import consoleserver

        class Fake:
            def apply_payload(self, p):
                pass
        an = analyzer.Analyzer(taps={"pre": {"cmd": FakeSource.CMD}, "post": {"cmd": FakeSource.CMD}}, linger_s=0.3)
        sess = consoleserver.Session(Fake(), on_commit=lambda s: {}, profiles_dir=tempfile.mkdtemp(), analyzer=an)
        httpd, url, stop = consoleserver.serve(sess)
        try:
            port = httpd.server_address[1]
            s = socket.create_connection(("127.0.0.1", port), timeout=5)
            s.sendall(b"GET /api/analyzer/stream HTTP/1.1\r\nHost: 127.0.0.1\r\n\r\n")
            buf = b""
            t0 = time.time()
            while buf.count(b"\n\ndata:") < 3 and time.time() - t0 < 6:
                buf += s.recv(65536)
            head, _, rest = buf.partition(b"\r\n\r\n")
            self.assertIn(b"text/event-stream", head)
            ev = [l for l in rest.split(b"\n") if l.startswith(b"data:")]
            fr = json.loads(ev[1][5:])
            self.assertEqual(len(fr["pre"]), len(fr["f"]))
            self.assertIn("levels", fr)
            self.assertTrue(an.running())
            s.close()
            time.sleep(2.5)
            self.assertFalse(an.running())                # istemci gitti → yakalama durdu
            s2 = socket.create_connection(("127.0.0.1", port), timeout=5)
            s2.sendall(b"GET /api/analyzer/stream HTTP/1.1\r\nHost: evil.example\r\n\r\n")
            self.assertIn(b"403", s2.recv(200))
            s2.close()
        finally:
            stop.set()
            an.close()


if __name__ == "__main__":
    unittest.main()


class FakePw:
    """pw-link yerine: port listeleri zamanla belirir; bağlantılar kaydedilir (gerçek grafa dokunulmaz)."""
    def __init__(self, src_after=0, dst_after=0, drop=False):
        self.calls, self.links, self.src_after, self.dst_after, self.drop = 0, set(), src_after, dst_after, drop

    def __call__(self, args):
        self.calls += 1
        if args[1:] == ["-o"]:
            return "\n".join(["eff:monitor_FL", "eff:monitor_FR"] if self.calls > self.src_after else []) + "\n"
        if args[1:] == ["-i"]:
            return "\n".join(["tap:input_FL", "tap:input_FR"] if self.calls > self.dst_after else []) + "\n"
        if args[1:] == ["-l"]:
            return "\n".join(f"{s}\n  |-> {d}" for s, d in sorted(self.links)) + "\n"
        if not self.drop:
            self.links.add((args[1], args[2]))
        return ""


class TestLinkHeal(unittest.TestCase):
    """U81: analizör dokunuşu kaynak portlar GEÇ belirse de bağlanır, bağlantı DOĞRULANIR, kopuk bağlantı abonede onarılır.
    Ölçülen olay (10-25): konsol yeniden başlatıldıktan sonra kayıt düğümleri vardı ama hiçbir bağlantı yoktu →
    panel 'idle', müzik çalarken spektrum boş; elle pw-link ile kare geldi."""
    SRC = ["eff:monitor_FL", "eff:monitor_FR"]

    def test_u81_links_when_ports_appear_late_and_verifies(self):
        pw = FakePw(src_after=40)                          # eski 5 sn sınırını aşan gecikme (0,1 sn adımla ~4 sn+)
        self.assertTrue(analyzer._link(self.SRC, "tap", timeout=5.0, run=pw, sleep=lambda s: None))
        self.assertEqual(pw.links, {("eff:monitor_FL", "tap:input_FL"), ("eff:monitor_FR", "tap:input_FR")})

    def test_u81_unverified_link_is_reported_as_failure(self):
        pw = FakePw(drop=True)                             # pw-link sessizce başarısız: bağlantı oluşmadı
        self.assertFalse(analyzer._link(self.SRC, "tap", timeout=0.5, run=pw, sleep=lambda s: None, clock=iter(range(10**6)).__next__))

    def test_u81_linked_check(self):
        pw = FakePw()
        self.assertFalse(analyzer._linked(self.SRC, "tap", run=pw))
        pw.links |= {("eff:monitor_FL", "tap:input_FL"), ("eff:monitor_FR", "tap:input_FR")}
        self.assertTrue(analyzer._linked(self.SRC, "tap", run=pw))
