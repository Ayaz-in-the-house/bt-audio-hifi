"""U71: kurulu konsol filtresinin hedefi bağlı kulaklıkla eşleşmiyorsa bayattır → açılışta yeniden kurulur.
Olay 2026-10-15: smart filter eski MAC'e hedefliydi → akışlar filtreyi atladı → EQ yok, analizör sessiz, otomatik mod ölü.
U72 sonrası hedef MAC'siz kimliktir; eski node.name biçimli kurulum da bayat sayılır (kendiliğinden göç)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import console, identity  # noqa: E402

OLD = "bluez_output.02_00_00_00_00_02.1"
T = identity.target("Solix Nexus ANC")


class TestSmartTarget(unittest.TestCase):
    def test_renders_identity_target_without_mac(self):
        conf = console.render_graph_ab(T, console.default_state(), source="test")
        self.assertEqual(console.smart_target(conf), T)
        self.assertNotIn("01_5F", conf)

    def test_string_target_still_supported(self):           # doğrulama sondaları kendi null sink adını verir
        conf = console.render_graph_ab(OLD, console.default_state(), source="test")
        self.assertEqual(console.smart_target(conf), {"node.name": OLD})

    def test_missing_target_is_none(self):
        self.assertIsNone(console.smart_target("context.modules = []"))

    def test_legacy_mac_target_is_stale(self):
        conf = console.render_graph_ab(OLD, console.default_state(), source="test")
        self.assertTrue(console.target_stale(conf, T))

    def test_identity_target_not_stale(self):
        conf = console.render_graph_ab(T, console.default_state(), source="test")
        self.assertFalse(console.target_stale(conf, T))

    def test_renamed_headphone_is_stale(self):
        conf = console.render_graph_ab(T, console.default_state(), source="test")
        self.assertTrue(console.target_stale(conf, identity.target("Kulaklığım")))

    def test_not_stale_when_no_headphone(self):              # bağlı değilse yeniden kurma (son hedef korunur)
        conf = console.render_graph_ab(OLD, console.default_state(), source="test")
        self.assertFalse(console.target_stale(conf, None))


if __name__ == "__main__":
    unittest.main()
