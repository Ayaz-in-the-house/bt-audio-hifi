"""Canlı / headful kabul testleri — gerçek PipeWire grafı + gerçek kulaklık + gerçek ses çalma.

Kulaklık bağlı değilse testler FAIL eder (SKIP değil): kabul testinin konusu tam olarak bu cihazdır.
T-L10 kulaklığı kısa süre ayırıp yeniden bağlar; T-L12 düşük seviyede (-30 dBFS) 1 kHz ton çalar.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from btaudio import cli, collect  # noqa: E402

DEC = json.load(open(os.path.join(collect.REPO, "decision.json")))


def sh(*cmd, timeout=20):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def wait_for(pred, timeout=25, step=1.0):
    t0 = time.time()
    while time.time() - t0 < timeout:
        v = pred()
        if v:
            return v, time.time() - t0
        time.sleep(step)
    return None, timeout


def bt_sink_errors():
    """pw-top batch çıktısında BT sink satırının ERR sütunu (xrun/hata sayacı)."""
    out = sh("pw-top", "-b", "-n", "2", timeout=10).stdout
    vals = [int(line.split()[8]) for line in out.splitlines()
            if f"bluez_output.{collect.DEV_ID}" in line and len(line.split()) > 8 and line.split()[8].isdigit()]
    return vals[-1] if vals else None


class T01_State(unittest.TestCase):
    def test_static_checks(self):
        """T-L01..05, T-L20 — bta check ile aynı kimlikler."""
        res = cli.checks()
        failed = [(i, d) for i, ok, d in res if not ok]
        self.assertEqual(failed, [], f"başarısız: {failed}")

    def test_l06_transport_active_when_playing(self):
        tone = _tone(seconds=4)
        p = subprocess.Popen(["pw-play", "--volume", "0.5", "--target", _sink_name(), tone])
        try:
            got, _ = wait_for(lambda: any(t.get("state") == "active"
                                          for t in collect.bluez_endpoints()["transports"].values()), timeout=6)
            self.assertTrue(got, "çalarken transport active olmadı")
        finally:
            p.wait(timeout=10)


def _sink_name():
    return collect.sink()["name"]


def _tone(seconds=3, rate=48000, freq=1000, db=-30):
    path = os.path.join(tempfile.gettempdir(), f"bta-tone-{freq}-{rate}-{seconds}.wav")
    if not os.path.exists(path):
        amp = 10 ** (db / 20)
        sh("ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "lavfi",
           "-i", f"sine=frequency={freq}:sample_rate={rate}:duration={seconds}",
           "-af", f"volume={amp},aformat=channel_layouts=stereo", path)
    return path


class T10_Reconnect(unittest.TestCase):
    """Test hijyeni: kopma sırasında GNOME varsayılan çıkışı değiştirebilir (ölçüldü) — test öncesi değer
    her durumda geri yüklenir, böylece test kullanıcının ses yönlendirmesini kalıcı değiştirmez."""

    def setUp(self):
        self._saved_default = collect.default_nodes().get("default.configured.audio.sink")

    def tearDown(self):
        if self._saved_default:
            collect.set_configured_default_sink(self._saved_default)

    def test_l10_reconnect_restores_a2dp_codec(self):
        """HEADFUL: disconnect → connect sonrası A2DP + karar codec'i + stereo geri gelmeli;
        T-L13: varsayılan çıkış tekrar kulaklık olmalı (switch-on-connect)."""
        before = collect.snapshot("pre-reconnect")
        r = sh("bluetoothctl", "disconnect", collect.DEVICE_MAC)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        gone, _ = wait_for(lambda: not collect.card().get("present"), timeout=10)
        self.assertTrue(gone, "kart disconnect sonrası kaybolmadı")
        time.sleep(2)
        t_connect = time.time()
        # bluetoothctl connect, A2DP transport kurulana dek bloklar → süre connect başlangıcından ölçülür.
        # TWS kulaklık art arda kopar-bağlan sonrası ~40 sn sayfalamaya yanıt vermeyebilir
        # (ölçüldü 19:17:54–19:18:26, br-connection-page-timeout ×3) → 90 sn'ye kadar geri çekilmeli dene.
        attempts = []
        while time.time() - t_connect < 90:
            r = sh("bluetoothctl", "connect", collect.DEVICE_MAC, timeout=30)
            attempts.append((r.stdout + r.stderr).strip().splitlines()[-1:])
            if "Connection successful" in r.stdout + r.stderr:
                break
            time.sleep(5)
        self.assertIn("Connection successful", str(attempts[-1]), f"bağlanamadı: {attempts}")

        def ready():
            s = collect._safe(collect.sink)
            return s if s.get("present") and s.get("codec") == DEC["codec"] and s.get("channels") == 2 else None

        s, _ = wait_for(ready, timeout=20)
        secs = time.time() - t_connect
        self.assertIsNotNone(s, f"20 sn içinde {DEC['codec']} stereo geri gelmedi: {collect._safe(collect.sink)}")
        self.assertTrue(collect.card()["active_profile"].startswith("a2dp-sink"))
        print(f"\n    T-L10: connect başlangıcından {secs:.1f} sn sonra hazır → {s['codec']} {s['channels']}ch "
              f"{s['rate']}Hz (önce: {before['sink'].get('codec')})", file=sys.stderr)
        # T-L13
        d, _ = wait_for(lambda: collect.default_nodes().get("default.audio.sink") == s["name"], timeout=5, step=0.5)
        self.assertTrue(d, f"T-L13: yeniden bağlanınca varsayılan çıkış kulaklık olmadı: {collect.default_nodes()}")


class T11_NoAutoswitch(unittest.TestCase):
    def test_l11a_no_virtual_bt_source(self):
        """autoswitch=false iken sanal bluez_input kaynağı olmamalı (HFP tetikleyicisi yok)."""
        out = sh("pw-dump", timeout=15).stdout
        names = [o.get("info", {}).get("props", {}).get("node.name", "") for o in json.loads(out)]
        self.assertFalse([n for n in names if n.startswith("bluez_input.")], names)

    def test_l11b_mic_capture_keeps_a2dp(self):
        """HEADFUL: bir uygulama mikrofon açınca (varsayılan kaynak) profil A2DP'de kalmalı."""
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            p = subprocess.Popen(["pw-record", f.name])
            time.sleep(4)
            prof = collect.card()["active_profile"]
            p.terminate()
            p.wait(timeout=5)
        self.assertTrue(prof.startswith("a2dp-sink"), f"kayıt sırasında profil {prof} oldu")


class T12_Playback(unittest.TestCase):
    def test_l12_end_to_end_play(self):
        """HEADFUL: 1 kHz -30 dBFS ton BT sink'e çalar; akış sink'e bağlı ve çalışıyor, xrun artmıyor."""
        e0 = bt_sink_errors()
        p = subprocess.Popen(["pw-play", "--target", _sink_name(), _tone(seconds=5)])
        try:
            def linked():
                return [s for s in collect.streams_to_sink() if s.get("app") == "pw-play" and s.get("state") == "running"]
            got, _ = wait_for(linked, timeout=5, step=0.5)
            self.assertTrue(got, f"pw-play akışı BT sink'e bağlanmadı: {collect.streams_to_sink()}")
        finally:
            p.wait(timeout=15)
        self.assertEqual(p.returncode, 0)
        e1 = bt_sink_errors()
        if e0 is not None and e1 is not None:
            self.assertLessEqual(e1 - e0, 0, f"çalma sırasında BT sink ERR {e0}→{e1}")


if __name__ == "__main__":
    unittest.main()


class T14_AbxSmoke(unittest.TestCase):
    def test_l14_abx_scripted_headful(self):
        """HEADFUL: ABX gerçek kulaklıkta codec değiştirip çalar; bitince özgün codec'e döner."""
        from btaudio import abx
        clip = os.path.join(collect.REPO, "analysis", "tmp", "brahms1-48k-45s.wav")
        before = collect.sink()["codec"]
        t0 = time.time()
        res = abx.run("aac", "sbc", clip=clip, n=2, start=2, dur=1.5, answers=["a", "b"], log=lambda *_: None)
        self.assertEqual(res["n"], 2)
        self.assertEqual(len(res["answers"]), 2)
        self.assertEqual(collect.sink()["codec"], before, "ABX sonrası özgün codec'e dönülmedi")
        print(f"\n    T-L14: 2 deneme × 3 çalma, {time.time() - t0:.1f} sn, geri dönüş={before}", file=sys.stderr)


class T30_SmartFilterEq(unittest.TestCase):
    def test_l30_smart_filter_matches_model(self):
        """HEADFUL (null sink, kulaklık meşgul edilmez): WirePlumber smart filter akışı EQ'dan geçirir ve ölçülen
        yanıt tasarım modeliyle ≤0.1 dB örtüşür; varsayılan çıkış değişmez."""
        import warnings
        from btaudio import eqverify
        warnings.simplefilter("ignore")
        d0 = collect.default_nodes()["default.audio.sink"]
        design = {"target": "test", "preamp_db": -6.0,
                  "bands": [{"type": "Bell", "frequency": 90, "gain": 6.0, "q": 1.0},
                            {"type": "Bell", "frequency": 40, "gain": 4.0, "q": 1.4}]}
        res = eqverify.verify(design)
        self.assertTrue(res["stream_went_through_filter"], res["filter_links"])
        self.assertLessEqual(res["max_abs_error_db"], 0.1, res["rows"])
        self.assertEqual(collect.default_nodes()["default.audio.sink"], d0)


class T33_ConsoleInPath(unittest.TestCase):
    def test_l33_console_in_headphone_path(self):
        """HEADFUL: konsol kuruluysa kulaklığa giden akış effect_input.bta_console → effect_output → BT sink; eski bas
        filtresi aynı anda zincirde OLMAMALI (iki smart filter üst üste binmez)."""
        rel = "pipewire/filter-chain.conf.d/60-bta-console.conf"
        if not os.path.exists(os.path.join(collect.CONFIG_DST, rel)):
            self.skipTest("konsol kurulu değil (bta console)")
        from btaudio import eqverify
        p = subprocess.Popen(["pw-play", "--target", _sink_name(), _tone(seconds=3, db=-45)])
        time.sleep(1.5)
        links = eqverify._links_through_filter()
        p.wait(timeout=15)
        self.assertIn(("pw-play", "effect_input.bta_console"), links, links)
        self.assertIn(("effect_output.bta_console", _sink_name()), links, links)
        self.assertFalse([l for l in links if "bta_bass_eq" in str(l)], "eski bas filtresi hâlâ zincirde")


class T31_BassEqInPath(unittest.TestCase):
    def test_l31_bass_eq_in_headphone_path(self):
        """HEADFUL: bas EQ kuruluysa kulaklığa çalınan akış effect_input.bta_bass_eq → effect_output → BT sink yolundan
        geçmeli; hoparlöre giden akış geçmemeli (smart filter hedefi yalnız kulaklık)."""
        rel = "pipewire/filter-chain.conf.d/60-bta-bass-eq.conf"
        if not os.path.exists(os.path.join(collect.CONFIG_DST, rel)):
            self.skipTest("bas EQ henüz kurulmadı — kullanıcı ölçümü (tools/loudness-match.html) bekleniyor")
        from btaudio import eqverify
        p = subprocess.Popen(["pw-play", "--target", _sink_name(), _tone(seconds=4)])
        time.sleep(2)
        links = eqverify._links_through_filter()
        p.wait(timeout=15)
        self.assertIn(("pw-play", "effect_input.bta_bass_eq"), links, links)
        self.assertIn(("effect_output.bta_bass_eq", _sink_name()), links, links)


class T32_ConsoleGraph(unittest.TestCase):
    def test_l32_console_graph_matches_model(self):
        """HEADFUL (null sink): 10 bant EQ + bs2b + genişlik + denge + preamp — L/R her iki çıkış modelle ≤0.05 dB."""
        import warnings
        from btaudio import console, consoleverify
        warnings.simplefilter("ignore")
        st = console.apply_preset(console.default_state(), "v_sekli")
        st.update(crossfeed={"enabled": True, "fcut": 700, "feed": 4.5}, width=1.3, balance=0.2)
        r = consoleverify.verify(console.sanitize(st))
        self.assertLessEqual(r["max_abs_error_db"], 0.05, r["rows"])


class T34_AnalyzerNullSink(unittest.TestCase):
    def test_l34_analyzer_matches_model_on_null_sink(self):
        """Kulaklığa dokunmaz: kopya konsol grafı null sink'te; analizör post−pre = model (preamp dahil) ±0,5 dB,
        EQ öncesi mutlak seviye = çalınan seviye ±0,5 dB; abonelik bitince yakalama süreci kalmaz."""
        from btaudio import analyzerverify
        d0 = collect.default_nodes()["default.audio.sink"]
        r = analyzerverify.verify()
        self.assertGreater(r["frames"], 20, r)
        self.assertLessEqual(r["max_abs_error_db"], 0.5, r["rows"])
        self.assertTrue(r["stopped_after_unsubscribe"])
        for pid in r["capture_pids"]:
            self.assertFalse(os.path.exists(f"/proc/{pid}/exe"), pid)
        self.assertEqual(collect.default_nodes()["default.audio.sink"], d0)


class T35_AnalyzerRealPath(unittest.TestCase):
    def test_l35_analyzer_on_headphone_path_is_read_only(self):
        """HEADFUL: gerçek konsol yolunda analizör açıkken — yakalama yalnız filtre monitör/çıkış portlarına bağlı,
        uygulama → effect_input → effect_output → BT yolu DEĞİŞMEZ, EQ sonrası kare sinyal görür; kapanınca süreç yok."""
        rel = "pipewire/filter-chain.conf.d/60-bta-console.conf"
        if not os.path.exists(os.path.join(collect.CONFIG_DST, rel)):
            self.skipTest("konsol kurulu değil (bta console)")
        from btaudio import analyzer, eqverify
        an = analyzer.Analyzer(analyzer.console_taps(), linger_s=0.1, response="fast")
        sid = an.subscribe()
        try:
            time.sleep(1.0)
            # kullanıcı zaten dinliyorsa kulağına test tonu KARIŞTIRMA — mevcut müziği gözle (K10)
            busy = [s for s in collect.streams_to_sink() if s.get("state") == "running"]
            audible = False
            if busy:                                 # K11: "running" akış sessiz olabilir → önce sinyali ÖLÇ
                t1 = time.time()
                while time.time() - t1 < 1.5:
                    fr = an.wait_frame(sid, timeout=1.0)
                    audible = audible or bool(fr and fr.get("signal"))
            p = None if audible else subprocess.Popen(["pw-play", "--target", _sink_name(), _tone(seconds=3, db=-45)])
            seen, t0 = [], time.time()
            while time.time() - t0 < 2.5:
                fr = an.wait_frame(sid, timeout=1.0)
                if fr:
                    seen.append(fr)
            links = eqverify._links_through_filter()
            if p:
                p.wait(timeout=15)
            pids = an.pids()
        finally:
            an.unsubscribe(sid)
            time.sleep(0.6)
            an.close()
        app = "pw-play" if p else next(l[0] for l in links if l[1] == "effect_input.bta_console")
        self.assertIn((app, "effect_input.bta_console"), links, links)
        self.assertIn(("effect_output.bta_console", _sink_name()), links, links)
        nodes = {an.taps["pre"].node: "pre", an.taps["post"].node: "post"}
        ours = sorted((l[0], nodes[l[1]]) for l in links if l[1] in nodes)
        self.assertEqual(ours, [("effect_input.bta_console", "pre"), ("effect_output.bta_console", "post")], links)
        self.assertFalse([l for l in links if l[0] in nodes], "analizör çıkış üretmemeli")
        self.assertTrue(any(fr.get("signal") for fr in seen), "EQ sonrası kare sinyal görmedi")
        self.assertFalse(an.running())
        for pid in pids:
            self.assertFalse(os.path.exists(f"/proc/{pid}/exe"), pid)


class T39_CrossfadeNoClicks(unittest.TestCase):
    def test_l39_ab_crossfade_removes_update_clicks(self):
        """Null sink: doğrudan güncelleme (bq_raw bellek sıfırlama, R33) güncelleme başına ≈ −46 dBFS artık üretir;
        A/B adımlı geçişte artık ≤ −60 dBFS ve 5 güncellemede en çok 1 olay (R43 açık), son seviye = model ±0,05 dB."""
        from btaudio import zipperverify
        direct = zipperverify.run("jump")
        ab = zipperverify.run_ab(0.5)
        self.assertGreaterEqual(direct["windows_over_-60"], 3, direct)          # sorunun kendisi hâlâ ölçülebilir
        ev = [t for t in ab["event_times_s"] if t > (ab["play_start_s"] or 0) + 0.3]
        self.assertLessEqual(len(ev), 1, ab)
        self.assertLessEqual(sorted(ab["top6"])[-2], -60.0, ab)
        self.assertAlmostEqual(ab["final_level_db"], ab["model_db"], delta=0.05)
        self.assertEqual(ab["errors"], [])
