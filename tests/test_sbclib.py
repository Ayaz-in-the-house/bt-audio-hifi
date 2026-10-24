"""U17: gerçek libsbc ↔ codecs.sbc_frame_length formülü çapraz doğrulama + gidiş-dönüş."""
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import codecs, sbclib  # noqa: E402


class TestLibSbc(unittest.TestCase):
    def test_u17_frame_length_matches_formula(self):
        for rate, mode, bp in ((48000, "joint", 53), (48000, "dual", 39), (44100, "dual", 43), (48000, "stereo", 53)):
            c = sbclib.Codec(rate=rate, mode=mode, bitpool=bp)
            self.assertEqual(c.frame_length, codecs.sbc_frame_length(mode, 8, 16, bp), (rate, mode, bp))
            c.close()

    def test_roundtrip_sine(self):
        t = np.arange(48000) / 48000
        x = (np.sin(2 * np.pi * 1000 * t) * 8000).astype(np.int16)
        pcm = np.stack([x, x], 1)
        enc = sbclib.Codec(48000, "joint", 53)
        data = enc.encode(pcm)
        enc.close()
        dec = sbclib.Codec(48000, "joint", 53)
        y = dec.decode(data)
        dec.close()
        self.assertEqual(y.shape[1], 2)
        self.assertGreater(len(y), 47000)
        self.assertAlmostEqual(np.sqrt(np.mean(y[2000:40000, 0].astype(float) ** 2)), 8000 / np.sqrt(2), delta=300)

    def test_msbc(self):
        c = sbclib.Codec(msbc=True)
        self.assertEqual(c.channels, 1)
        self.assertEqual(c.frame_length, 57)          # mSBC: 57 bayt/çerçeve (HFP spec)
        c.close()


if __name__ == "__main__":
    unittest.main()
