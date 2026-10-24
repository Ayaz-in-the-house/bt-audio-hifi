"""U01–U06: A2DP codec byte çözücüleri (PipeWire 1.6.8 a2dp-codec-caps.h, little-endian bitfield düzeni)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import codecs  # noqa: E402


class TestAAC(unittest.TestCase):
    def test_u01_live_config(self):
        # Canlı transport'ta 2026-09-27 ölçülen bayt dizisi
        c = codecs.decode_aac(bytes([0x80, 0x00, 0x84, 0x84, 0x00, 0x00]))
        self.assertEqual(c["object_types"], ["MPEG-2 AAC LC"])
        self.assertEqual(c["rates"], [48000])
        self.assertEqual(c["channels"], [2])
        self.assertTrue(c["vbr"])
        self.assertEqual(c["bitrate"], 262144)

    def test_u02_remote_caps(self):
        c = codecs.decode_aac(bytes([0x80, 0xFF, 0x8C, 0x80, 0x00, 0x00]))
        self.assertEqual(c["rates"], [8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000])
        self.assertEqual(c["channels"], [1, 2])
        self.assertTrue(c["vbr"])
        self.assertEqual(c["bitrate"], 0)
        # PipeWire get_valid_aac_bitrate(): <64000 → 320000 varsayılan
        self.assertEqual(codecs.pipewire_effective_aac_bitrate(c["bitrate"]), 320000)
        self.assertEqual(codecs.pipewire_effective_aac_bitrate(262144), 262144)
        self.assertEqual(codecs.pipewire_effective_aac_bitrate(400000), 320000)

    def test_u03_bitrate_roundtrip(self):
        self.assertEqual(codecs.encode_aac_bitrate(320000, vbr=True), bytes([0x84, 0xE2, 0x00]))
        raw = bytes([0x80, 0x00, 0x84]) + codecs.encode_aac_bitrate(320000, vbr=True)
        self.assertEqual(codecs.decode_aac(raw)["bitrate"], 320000)

    def test_aac_bandwidth_branch(self):
        # a2dp-codec-aac.c:400 — yalnız vbr=0 ve cur_bitrate>110000 iken 19293 Hz bant genişliği zorlanır
        self.assertIsNone(codecs.pipewire_aac_forced_bandwidth(vbr=True, cur_bitrate=262144))
        self.assertEqual(codecs.pipewire_aac_forced_bandwidth(vbr=False, cur_bitrate=262144), 19293)
        self.assertIsNone(codecs.pipewire_aac_forced_bandwidth(vbr=False, cur_bitrate=96000))

    def test_aac_mtu_cap(self):
        # max_bitrate = (mtu - 12) * 8 * rate / 1024
        self.assertEqual(codecs.pipewire_aac_max_bitrate(mtu=895, rate=48000), (883 * 8 * 48000) // 1024)


class TestSBC(unittest.TestCase):
    def test_u04_remote_caps(self):
        c = codecs.decode_sbc(bytes([0xFF, 0xFF, 0x02, 0x35]))
        self.assertEqual(c["rates"], [16000, 32000, 44100, 48000])
        self.assertEqual(c["channel_modes"], ["mono", "dual", "stereo", "joint"])
        self.assertEqual(c["block_lengths"], [4, 8, 12, 16])
        self.assertEqual(c["subbands"], [4, 8])
        self.assertEqual(c["allocation"], ["snr", "loudness"])
        self.assertEqual((c["min_bitpool"], c["max_bitpool"]), (2, 53))

    def test_u05_xq_config_bitrate(self):
        # 44.1k (0x2<<4) | dual (0x4) ; blk16 (0x1<<4) | sb8 (0x1<<2) | loudness (0x1)
        raw = bytes([0x24, 0x15, 2, 43])
        c = codecs.decode_sbc(raw)
        self.assertEqual(c["rates"], [44100])
        self.assertEqual(c["channel_modes"], ["dual"])
        self.assertEqual(codecs.sbc_frame_length("dual", subbands=8, blocks=16, bitpool=43), 184)
        self.assertEqual(codecs.sbc_bitrate("dual", 44100, subbands=8, blocks=16, bitpool=43), 507150)

    def test_sbc_joint_formula(self):
        # joint: 4 + 4*8*2/8 + ceil((8 + 16*53)/8) = 4 + 8 + 107 = 119
        self.assertEqual(codecs.sbc_frame_length("joint", subbands=8, blocks=16, bitpool=53), 119)


class TestErrors(unittest.TestCase):
    def test_u06_bad_length(self):
        with self.assertRaises(ValueError):
            codecs.decode_aac(bytes([0x80, 0x00, 0x84]))
        with self.assertRaises(ValueError):
            codecs.decode_sbc(bytes([0xFF, 0xFF]))

    def test_decode_dispatch(self):
        self.assertEqual(codecs.decode(2, bytes([0x80, 0x00, 0x84, 0x84, 0, 0]))["codec"], "AAC")
        self.assertEqual(codecs.decode(0, bytes([0xFF, 0xFF, 2, 53]))["codec"], "SBC")
        self.assertEqual(codecs.decode(0xFF, b"\x00" * 6)["codec"], "vendor")


if __name__ == "__main__":
    unittest.main()
