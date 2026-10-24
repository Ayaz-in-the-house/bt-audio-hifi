"""U49 (T-L37'nin izole karşılığı): 'Açılışta kullan' repo'yu kirletmez — durum XDG'ye, üretilmiş config XDG'ye,
kurulum hedefe; git çalışma ağacı değişmez. Gerçek ~/.config ve servisler etkilenmez (BTA_CONFIG_DST + BTA_NO_RESTART)."""
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

REPO = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, REPO)


def git_status():
    return subprocess.run(["git", "-C", REPO, "status", "--porcelain"], capture_output=True, text=True).stdout


class TestCommitIsolation(unittest.TestCase):
    def test_u49_commit_leaves_repo_clean(self):
        tmp = tempfile.mkdtemp()
        env = {"BTA_HOME": os.path.join(tmp, "home"), "BTA_CONFIG_DST": os.path.join(tmp, "dotconfig"), "BTA_NO_RESTART": "1",
               "BTA_DEVICE": "02:00:00:00:00:01"}   # U72: gerçek kartlar okunmaz, kimlik önbelleği boş kalır
        with mock.patch.dict(os.environ, env):
            import importlib
            from btaudio import collect, console
            importlib.reload(collect)
            from btaudio import cli
            importlib.reload(cli)
            before = git_status()
            with mock.patch.object(collect, "sink", return_value={"name": "bluez_output.TEST.1"}):
                st = console.apply_preset(console.default_state(), "zengin_bas")
                r = cli.commit_console_state(st)
            self.assertEqual(git_status(), before)
            self.assertTrue(r["file"].startswith(env["BTA_HOME"]))
            inst = os.path.join(env["BTA_CONFIG_DST"], "pipewire/filter-chain.conf.d/60-bta-console.conf")
            self.assertIn('node.name = "bluez_output.TEST.1"', open(inst).read())
            man = collect.configs()
            self.assertEqual(man["pipewire/filter-chain.conf.d/60-bta-console.conf"]["status"], "ok")
            self.assertTrue(man["pipewire/filter-chain.conf.d/60-bta-console.conf"]["src"].startswith(env["BTA_HOME"]))
        importlib.reload(collect)
        importlib.reload(cli)


if __name__ == "__main__":
    unittest.main()
