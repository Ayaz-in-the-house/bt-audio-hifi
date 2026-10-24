"""U40: ürün / kullanıcı verisi ayrımı (C0). Testler $BTA_HOME ile izole — gerçek kullanıcı verisine dokunmaz."""
import hashlib
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import paths, state  # noqa: E402


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


class TestPaths(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old = os.environ.get("BTA_HOME")
        os.environ["BTA_HOME"] = os.path.join(self.tmp.name, "home")

    def tearDown(self):
        if self.old is None:
            os.environ.pop("BTA_HOME", None)
        else:
            os.environ["BTA_HOME"] = self.old
        self.tmp.cleanup()

    def test_u40_isolated_under_bta_home(self):
        root = os.environ["BTA_HOME"]
        for p in (paths.profiles_dir(), paths.console_states_dir(), paths.generated_dir(), paths.trash_dir()):
            self.assertTrue(p.startswith(root + os.sep), p)
            self.assertTrue(os.path.isdir(p))

    def test_u40_xdg_default_when_no_override(self):
        os.environ.pop("BTA_HOME")
        os.environ["XDG_CONFIG_HOME"] = os.path.join(self.tmp.name, "xc")
        os.environ["XDG_STATE_HOME"] = os.path.join(self.tmp.name, "xs")
        try:
            self.assertEqual(paths.profiles_dir(), os.path.join(self.tmp.name, "xc", "bt-audio-hifi", "profiles"))
            self.assertEqual(paths.console_states_dir(), os.path.join(self.tmp.name, "xs", "bt-audio-hifi", "console"))
        finally:
            os.environ.pop("XDG_CONFIG_HOME")
            os.environ.pop("XDG_STATE_HOME")

    def _fake_repo(self):
        repo = os.path.join(self.tmp.name, "repo")
        os.makedirs(os.path.join(repo, "analysis", "console"))
        os.makedirs(os.path.join(repo, "config", "pipewire", "filter-chain.conf.d"))
        with open(os.path.join(repo, "analysis", "console", "20260927-211452-committed.json"), "w") as f:
            json.dump({"x": 1}, f)
        with open(os.path.join(repo, "config", "pipewire", "filter-chain.conf.d", "60-bta-console.conf"), "w") as f:
            f.write("# user state\n")
        return repo

    def test_u40_migrate_copies_never_moves_and_is_idempotent(self):
        repo = self._fake_repo()
        src_json = os.path.join(repo, "analysis", "console", "20260927-211452-committed.json")
        src_conf = os.path.join(repo, "config", "pipewire", "filter-chain.conf.d", "60-bta-console.conf")
        before = (sha(src_json), sha(src_conf))
        r1 = paths.migrate(repo)
        self.assertEqual(len(r1["copied"]), 2)
        self.assertEqual((sha(src_json), sha(src_conf)), before)          # kaynak yerinde, aynı
        dst_conf = os.path.join(paths.generated_dir(), "pipewire", "filter-chain.conf.d", "60-bta-console.conf")
        self.assertEqual(sha(dst_conf), before[1])
        self.assertTrue(os.path.exists(os.path.join(paths.console_states_dir(), "20260927-211452-committed.json")))
        r2 = paths.migrate(repo)
        self.assertEqual(r2["copied"], [])                                  # ikinci koşu no-op

    def test_u40_migrate_never_overwrites_newer_generated(self):
        repo = self._fake_repo()
        dst_conf = os.path.join(paths.generated_dir(), "pipewire", "filter-chain.conf.d", "60-bta-console.conf")
        os.makedirs(os.path.dirname(dst_conf), exist_ok=True)
        with open(dst_conf, "w") as f:
            f.write("# newer\n")
        paths.migrate(repo)
        self.assertEqual(open(dst_conf).read(), "# newer\n")

    def test_u40_manifest_spans_repo_and_generated_roots(self):
        repo = self._fake_repo()
        os.remove(os.path.join(repo, "config", "pipewire", "filter-chain.conf.d", "60-bta-console.conf"))
        os.makedirs(os.path.join(repo, "config", "pipewire", "client.conf.d"))
        with open(os.path.join(repo, "config", "pipewire", "client.conf.d", "a.conf"), "w") as f:
            f.write("a")
        gen = os.path.join(paths.generated_dir(), "pipewire", "filter-chain.conf.d")
        os.makedirs(gen, exist_ok=True)
        with open(os.path.join(gen, "g.conf"), "w") as f:
            f.write("g")
        dst = os.path.join(self.tmp.name, "dotconfig")
        man = state.config_manifest([os.path.join(repo, "config"), paths.generated_dir()], dst)
        self.assertEqual(set(man), {"pipewire/client.conf.d/a.conf", "pipewire/filter-chain.conf.d/g.conf"})
        self.assertTrue(all(v["status"] == "missing" for v in man.values()))
        self.assertTrue(man["pipewire/filter-chain.conf.d/g.conf"]["src"].startswith(paths.generated_dir()))


if __name__ == "__main__":
    unittest.main()
