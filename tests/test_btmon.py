"""U27: btmon metin çıktısı + btmgmt conn-info ayrıştırıcısı (format: BlueZ monitor/packet.c başlık satırı)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import btmon  # noqa: E402

TRACE = """< ACL Data TX: Handle 3 flags 0x00 dlen 895                                  #10 [hci0] 1.000000
> HCI Event: Number of Completed Packets (0x13) plen 5                        #11 [hci0] 1.010000
< ACL Data TX: Handle 3 flags 0x00 dlen 895                                  #12 [hci0] 1.021000
< ACL Data TX: Handle 3 flags 0x00 dlen 895                                  #13 [hci0] 1.150000
> HCI Event: Mode Change (0x14) plen 6                                        #14 [hci0] 1.160000
> HCI Event: Role Change (0x12) plen 8                                        #15 [hci0] 1.170000
< ACL Data TX: Handle 9 flags 0x00 dlen 12                                   #16 [hci0] 1.180000
> HCI Event: Disconnect Complete (0x05) plen 4                                #17 [hci0] 2.000000
""".splitlines()

RSSI = """20:01:00 Connection Information for 02:00:00:00:00:02 	RSSI -58	TX power 4	maximum TX power 12
20:01:02 Connection Information for 02:00:00:00:00:02 	RSSI -61	TX power 4	maximum TX power 12
20:01:04 Get Conn Info failed, status 0x02 (Not Connected)""".splitlines()


class TestBtmon(unittest.TestCase):
    def test_u27_trace(self):
        r = btmon.parse_trace(TRACE, audio_handle=3)
        self.assertEqual(r["acl_tx_packets"], 3)
        self.assertEqual(r["acl_tx_bytes"], 3 * 895)
        self.assertAlmostEqual(r["max_gap_ms"], 129.0, delta=0.5)      # 1.021 → 1.150
        self.assertEqual(r["events"]["Mode Change"], 1)
        self.assertEqual(r["events"]["Role Change"], 1)
        self.assertEqual(r["events"]["Disconnect Complete"], 1)
        self.assertEqual(r["other_handles"], {9: 1})

    def test_rssi(self):
        r = btmon.parse_rssi(RSSI)
        self.assertEqual(r["samples"], 2)
        self.assertEqual(r["rssi_min"], -61)
        self.assertEqual(r["rssi_mean"], -59.5)
        self.assertEqual(r["failures"], 1)


if __name__ == "__main__":
    unittest.main()
