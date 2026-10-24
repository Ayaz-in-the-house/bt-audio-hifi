"""U07–U10: snapshot diff, WirePlumber state ayrıştırma, config manifest."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import state  # noqa: E402


class TestDiff(unittest.TestCase):
    def test_u07_categories(self):
        a = {"card": {"profile": "headset-head-unit", "x": 1}, "gone": True}
        b = {"card": {"profile": "a2dp-sink", "x": 1}, "new": 5}
        d = state.diff(a, b)
        self.assertEqual(d["changed"], {"card.profile": ["headset-head-unit", "a2dp-sink"]})
        self.assertEqual(d["added"], {"new": 5})
        self.assertEqual(d["removed"], {"gone": True})

    def test_u08_volatile_ignored(self):
        a = {"taken_at": "t1", "device": {"battery": 90, "name": "x"}, "label": "a"}
        b = {"taken_at": "t2", "device": {"battery": 80, "name": "x"}, "label": "b"}
        d = state.diff(a, b)
        self.assertEqual(d, {"changed": {}, "added": {}, "removed": {}})

    def test_lists_compared_as_values(self):
        d = state.diff({"p": [1, 2]}, {"p": [1, 3]})
        self.assertEqual(d["changed"], {"p": [[1, 2], [1, 3]]})


class TestWpState(unittest.TestCase):
    def test_u09_parse(self):
        text = (
            "[default-profile]\n"
            "bluez_card.02_00_00_00_00_02=a2dp-sink\n"
            'bluez_card.X:output:headset-output={"mute":false}\n'
            "\n"
        )
        kv = state.parse_wp_state(text)
        self.assertEqual(kv["bluez_card.02_00_00_00_00_02"], "a2dp-sink")
        self.assertEqual(kv["bluez_card.X:output:headset-output"], '{"mute":false}')
        self.assertNotIn("[default-profile]", kv)


class TestManifest(unittest.TestCase):
    def test_u10_manifest_drift(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as dst:
            os.makedirs(os.path.join(src, "pipewire/client.conf.d"))
            p = os.path.join(src, "pipewire/client.conf.d/60-a.conf")
            with open(p, "w") as f:
                f.write("a\n")
            m = state.config_manifest(src, dst)
            self.assertEqual(m["pipewire/client.conf.d/60-a.conf"]["status"], "missing")
            os.makedirs(os.path.join(dst, "pipewire/client.conf.d"))
            with open(os.path.join(dst, "pipewire/client.conf.d/60-a.conf"), "w") as f:
                f.write("a\n")
            self.assertEqual(state.config_manifest(src, dst)["pipewire/client.conf.d/60-a.conf"]["status"], "ok")
            with open(os.path.join(dst, "pipewire/client.conf.d/60-a.conf"), "w") as f:
                f.write("b\n")
            self.assertEqual(state.config_manifest(src, dst)["pipewire/client.conf.d/60-a.conf"]["status"], "drift")



class TestRestartPlan(unittest.TestCase):
    def test_u13_minimal_services(self):
        from btaudio import cli
        self.assertEqual(cli.services_for(["pipewire/pipewire-pulse.conf.d/60-x.conf"]), ["pipewire-pulse.service"])
        self.assertEqual(cli.services_for(["pipewire/client.conf.d/60-x.conf"]), [])
        self.assertEqual(cli.services_for(["wireplumber/wireplumber.conf.d/60-x.conf"]), ["wireplumber.service"])
        self.assertEqual(cli.services_for(["pipewire/pipewire.conf.d/60-x.conf", "pipewire/client.conf.d/a"]),
                         ["pipewire.service", "pipewire-pulse.service", "wireplumber.service"])
        self.assertEqual(cli.services_for(["pipewire/pipewire-pulse.conf.d/a", "wireplumber/b"]),
                         ["pipewire-pulse.service", "wireplumber.service"])
        # filter-chain.conf.d → yalnız ayrı filter-chain süreci (diğer sesler kesilmez)
        self.assertEqual(cli.services_for(["pipewire/filter-chain.conf.d/60-bta-bass-eq.conf"]),
                         ["filter-chain.service"])


class TestSpaJsonName(unittest.TestCase):
    def test_u14_lenient_name(self):
        # module-switch-on-connect.c:142 yazımı: iki nokta üst üste YOK (SPA JSON'da geçerli, JSON'da değil)
        self.assertEqual(state.spa_json_name('{ "name""bluez_output.02_00_00_00_00_02.1" }'),
                         "bluez_output.02_00_00_00_00_02.1")
        self.assertEqual(state.spa_json_name('{"name":"alsa_output.x"}'), "alsa_output.x")
        self.assertEqual(state.spa_json_name('{ "name": "a b" }'), "a b")
        self.assertIsNone(state.spa_json_name("garbage"))


class TestDeliveryChain(unittest.TestCase):
    def test_u20_pending_restart(self):
        from btaudio import cli
        mt = {"pipewire/pipewire-pulse.conf.d/a.conf": 200.0, "pipewire/client.conf.d/b.conf": 300.0,
              "wireplumber/wireplumber.conf.d/c.conf": 100.0}
        started = {"pipewire-pulse.service": 150.0, "wireplumber.service": 120.0, "pipewire.service": 50.0}
        # pulse drop-in servis başlangıcından YENİ → bekleyen; client.conf.d servissiz; wireplumber güncel
        self.assertEqual(cli.pending_restarts(mt, started),
                         [("pipewire/pipewire-pulse.conf.d/a.conf", "pipewire-pulse.service")])
        started["pipewire-pulse.service"] = 250.0
        self.assertEqual(cli.pending_restarts(mt, started), [])


class TestSystemdTs(unittest.TestCase):
    def test_u21_parse_us_utc(self):
        from btaudio import cli
        # saniye hassasiyeti aynı-saniye kurulum+yeniden başlatmada yanlış pozitif üretti (E10)
        self.assertAlmostEqual(cli.parse_systemd_us("Sun 2026-09-27 17:19:29.800699 UTC"), 1790529569.800699, places=5)  # gerçek gözlem: @1790529569
        self.assertEqual(cli.parse_systemd_us(""), 0.0)
        self.assertEqual(cli.parse_systemd_us("n/a"), 0.0)


if __name__ == "__main__":
    unittest.main()
