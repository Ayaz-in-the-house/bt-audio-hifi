"""U16: benchmark hattının kendi hatası — kayıpsız kontrol adayı ≫100 dB, HFP-mSBC ≤ 20 kHz'de çöker."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import bench  # noqa: E402


class TestBenchPlumbing(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="bta-bench-")
        cls.sig = bench.make_signals(cls.tmp, seconds=3)

    def test_u16_pcm_control_is_transparent(self):
        r = bench.run({"pembe": self.sig["pembe-gurultu"]}, self.tmp, ["PCM-kontrol"])["pembe"]["PCM-kontrol"]
        self.assertGreater(r["snr_20_20k"], 80, r)          # s16 nicemleme tabanı ~ -98 dBFS, sinyal -20 dBFS
        self.assertGreater(r["cutoff_hz"], 23000, r)

    def test_hfp_is_band_limited(self):
        r = bench.run({"pembe": self.sig["pembe-gurultu"]}, self.tmp, ["HFP-mSBC(baslangic)"])["pembe"]
        self.assertLess(r["HFP-mSBC(baslangic)"]["cutoff_hz"], 8200)   # 16 kHz örnekleme → Nyquist 8 kHz


if __name__ == "__main__":
    unittest.main()
