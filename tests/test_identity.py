"""U72: cihaz kimliği MAC'e bağlı değil. Kulaklık = ad (alias) + bilinen MAC kümesi (önbellek); seçimde hoparlör
(JBL vb.) asla kulaklık sanılmaz. Olay 2026-10-15: yeniden eşleşen kulaklık yeni MAC aldı → filtre eski MAC'te kaldı."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import identity  # noqa: E402

SOLIX_NEW = {"mac": "02:00:00:00:00:04", "alias": "Solix Nexus ANC", "form_factor": "headset"}
SOLIX_OLD = {"mac": "02:00:00:00:00:02", "alias": "Solix Nexus ANC", "form_factor": "headset"}
JBL = {"mac": "02:00:00:00:00:05", "alias": "JBL Charge 6", "form_factor": "speaker"}
TWS = {"mac": "02:00:00:00:00:06", "alias": "TWS", "form_factor": "headphone"}


class TestChoose(unittest.TestCase):
    def test_alias_match_beats_unknown_mac(self):          # yeni MAC, aynı ad → aynı kulaklık
        ident = {"alias": "Solix Nexus ANC", "macs": [SOLIX_OLD["mac"]]}
        self.assertEqual(identity.choose([JBL, SOLIX_NEW], ident)["mac"], SOLIX_NEW["mac"])

    def test_known_mac_beats_renamed_alias(self):          # kullanıcı adı değiştirdi, MAC biliniyor
        ident = {"alias": "Solix Nexus ANC", "macs": [SOLIX_NEW["mac"]]}
        renamed = dict(SOLIX_NEW, alias="Kulaklığım")
        self.assertEqual(identity.choose([JBL, renamed], ident)["mac"], SOLIX_NEW["mac"])

    def test_speaker_never_chosen(self):                   # çakışma yok: yalnız hoparlör bağlıysa kulaklık YOK
        self.assertIsNone(identity.choose([JBL], {"alias": "Solix Nexus ANC", "macs": []}))
        self.assertIsNone(identity.choose([JBL], None))

    def test_first_run_prefers_headset_form_factor(self):  # önbellek yok → kulaklık biçimli ilk cihaz
        self.assertEqual(identity.choose([JBL, SOLIX_NEW], None)["mac"], SOLIX_NEW["mac"])

    def test_known_beats_other_headphone(self):            # başka bir kulaklık (TWS) da bağlıysa bilinen kazanır
        ident = {"alias": "Solix Nexus ANC", "macs": []}
        self.assertEqual(identity.choose([TWS, SOLIX_NEW], ident)["mac"], SOLIX_NEW["mac"])


class TestCache(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.path = os.path.join(self.d, "device.json")

    def test_remember_accumulates_macs(self):
        identity.remember(SOLIX_OLD, self.path)
        identity.remember(SOLIX_NEW, self.path)
        ident = identity.load(self.path)
        self.assertEqual(ident["alias"], "Solix Nexus ANC")
        self.assertEqual(ident["macs"], [SOLIX_OLD["mac"], SOLIX_NEW["mac"]])
        self.assertEqual(ident["last_mac"], SOLIX_NEW["mac"])

    def test_legacy_mac_only_file_migrates(self):          # eski önbellek: düz MAC satırı (C5.1)
        legacy = os.path.join(self.d, "device")
        open(legacy, "w").write(SOLIX_OLD["mac"] + "\n")
        ident = identity.load(self.path, legacy=legacy)
        self.assertEqual(ident["macs"], [SOLIX_OLD["mac"]])
        self.assertIsNone(ident["alias"])

    def test_corrupt_cache_is_empty_not_crash(self):
        open(self.path, "w").write("{bozuk")
        self.assertEqual(identity.load(self.path)["macs"], [])

    def test_atomic_write_valid_json(self):
        identity.remember(SOLIX_NEW, self.path)
        json.load(open(self.path))
        self.assertFalse([f for f in os.listdir(self.d) if f.endswith(".tmp")])


class TestTarget(unittest.TestCase):
    def test_target_has_no_mac(self):
        t = identity.target("Solix Nexus ANC")
        self.assertEqual(t, {"media.class": "Audio/Sink", "device.api": "bluez5", "node.description": "Solix Nexus ANC"})
        self.assertNotIn("node.name", t)



class TestInjection(unittest.TestCase):
    """U72 güvenlik: cihaz adı uzaktaki cihazın kontrolündedir → config'e ham yazılamaz."""
    EVIL = 'x" } } ] context.modules = [ { name = libpipewire-module-evil } ] #'

    def test_spa_rejects_unsafe_values(self):
        from btaudio import console
        for bad in (self.EVIL, 'a\\b', "a\nb", "a{b", "a}b"):
            with self.assertRaises(ValueError):
                console.target_spa({"node.description": bad})

    def test_unsafe_alias_not_cached(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "device.json")
        identity.remember(dict(SOLIX_NEW, alias=self.EVIL), p)
        self.assertIsNone(identity.load(p)["alias"])
        self.assertEqual(identity.load(p)["macs"], [SOLIX_NEW["mac"]])

    def test_unsafe_alias_never_targeted(self):
        self.assertIsNone(identity.target(self.EVIL))

    def test_turkish_alias_ok(self):
        self.assertEqual(identity.target("Kulaklığım Çşğü")["node.description"], "Kulaklığım Çşğü")


if __name__ == "__main__":
    unittest.main()
