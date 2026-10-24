"""T-L43: oturma testi tonu GERÇEK PipeWire'da doğru frekans + seviyede çalar — geçici sanal sink'e (kullanıcının
kulaklığına DEĞİL; K10). Monitör portları elle bağlanır (R17 smart-filter tuzağı)."""
import os
import subprocess
import sys
import tempfile
import time
import unittest

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from btaudio import eqverify, resample, tones  # noqa: E402


class T43_Tone(unittest.TestCase):
    def test_l43_seal_tone_on_null_sink(self):
        sink = "bta_tone_probe"
        mid = resample.null_sink(sink)
        tmp = tempfile.mkdtemp(prefix="bta-tone-")
        rec = os.path.join(tmp, "rec.wav")
        try:
            r = eqverify._record_monitor_start(sink, rec, name="bta_tone_rec")
            time.sleep(0.3)
            h = tones.player(sink)(50.0, 1.5, -24.0)
            h.proc.wait(timeout=10)
            time.sleep(0.4)
            r.terminate()
            r.wait(timeout=5)
            h.stop()
            fs, y = wavfile.read(rec)
            x = y[:, 0].astype(np.float64)
            x = x[np.abs(x) > 1e-6]
            self.assertGreater(len(x), fs)                                  # ≥ 1 sn ses yakalandı
            pk = 20 * np.log10(np.max(np.abs(x)))
            f = np.fft.rfftfreq(len(x), 1 / fs)[np.argmax(np.abs(np.fft.rfft(x * np.hanning(len(x)))))]
            print(f"\nT-L43: tepe {pk:.2f} dBFS, baskın {f:.1f} Hz, {len(x) / fs:.2f} sn")
            self.assertAlmostEqual(pk, -24.0, delta=0.5)
            self.assertAlmostEqual(f, 50.0, delta=1.5)
            self.assertFalse(os.path.exists(h.path))                        # geçici wav temizlendi
        finally:
            resample.unload(mid)


if __name__ == "__main__":
    unittest.main()


class T44_AbxCodecRoundTrip(unittest.TestCase):
    def test_l44_codec_round_trip_keeps_console_path(self):
        """T-L44 (PRD-BTA05): kör testin codec geçişi gerçek kulaklıkta aac→sbc→aac ≤ 15 sn/adım, sink geri gelir,
        konsol filtresi yolda kalır. Codec geçişi sesi 1–2 sn keser → YALNIZ kulaklıkta başka akış çalmıyorken (K10)."""
        from btaudio import abx, collect
        busy = [s.get("app") for s in collect.streams_to_sink() if s.get("state") == "running"]
        if busy:
            self.skipTest(f"kulaklıkta çalan ses var {busy} — kullanıcı dinlerken codec değiştirilmez (K10)")
        orig = collect.sink().get("codec")
        other = "sbc" if orig == "aac" else "aac"
        try:
            for c in (other, orig):
                t0 = time.time()
                self.assertTrue(abx._set_codec(c), f"{c} etkinleşmedi")
                self.assertLess(time.time() - t0, 15.0)
                self.assertEqual(collect.sink().get("codec"), c)
            nodes = subprocess.run(["pw-cli", "ls", "Node"], capture_output=True, text=True, timeout=10).stdout
            self.assertIn("effect_input.bta_console", nodes)
        finally:
            abx._set_codec(orig)
