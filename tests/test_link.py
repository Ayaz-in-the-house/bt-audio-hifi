"""U15: bağlantı sağlığı günlük ayrıştırıcısı (media-sink.c:1090 reduce / :1164 increase)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import link  # noqa: E402

LINES = """Sep 27 19:30:01 fedora wireplumber[1]: spa.bluez5.sink.media: 0x1: increase bitpool: 0
Sep 27 19:30:02 fedora wireplumber[1]: spa.bluez5.sink.media: 0x1: reduce bitpool: 174762
Sep 27 19:30:03 fedora wireplumber[1]: spa.bluez5.sink.media: 0x1: increase bitpool: 233016
Sep 27 19:30:04 fedora wireplumber[1]: spa.bluez5.sink.media: 0x1: increase bitpool: 262144
Sep 27 19:30:05 fedora wireplumber[1]: spa.bluez5.sink.media: 0x1: increase bitpool: 0
Sep 27 19:30:06 fedora wireplumber[1]: something else""".splitlines()


class TestLinkParse(unittest.TestCase):
    def test_u15_summary(self):
        s = link.parse(LINES, seconds=6)
        self.assertEqual(s["reduce_events"], 1)       # her reduce = en az 1 atlanan paket (glitch)
        self.assertEqual(s["increase_events"], 4)
        self.assertEqual(s["min_bitrate_seen"], 174762)
        self.assertEqual(s["recoveries"], [233016, 262144])
        self.assertEqual(s["verdict"], "DEGRADED")

    def test_clean(self):
        s = link.parse([l for l in LINES if "reduce" not in l], seconds=6)
        self.assertEqual(s["verdict"], "CLEAN")
        self.assertIsNone(s["min_bitrate_seen"])

    def test_no_data(self):
        self.assertEqual(link.parse([], seconds=10)["verdict"], "NO_DATA")


if __name__ == "__main__":
    unittest.main()
