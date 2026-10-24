"""U74–U76 (PRD-BTA06 G1): otomatik mod arka plan servisi — boşta kapanmama, tek örnek, systemd kullanıcı birimi."""
import http.server
import os
import socket
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from btaudio import cli, consoleserver  # noqa: E402


class Fake:
    def apply_payload(self, p):
        pass


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class TestIdle(unittest.TestCase):
    def test_u74_idle_timeout_zero_never_stops(self):
        sess = consoleserver.Session(Fake(), on_commit=lambda s: {}, profiles_dir=tempfile.mkdtemp(),
                                     idle_timeout_s=0, clock=lambda: 0.0)
        sess.last = 0.0                                   # 1970'ten beri "boşta" — yine de kapanmamalı
        httpd, url, stop = consoleserver.serve(sess)
        try:
            time.sleep(1.5)
            self.assertFalse(stop.is_set())
        finally:
            stop.set()

    def test_u74_positive_timeout_still_stops(self):
        sess = consoleserver.Session(Fake(), on_commit=lambda s: {}, profiles_dir=tempfile.mkdtemp(), idle_timeout_s=1)
        sess.last = 0.0
        httpd, url, stop = consoleserver.serve(sess)
        self.assertTrue(stop.wait(3))


class TestSingleInstance(unittest.TestCase):
    def test_u75_detects_running_console(self):
        sess = consoleserver.Session(Fake(), on_commit=lambda s: {}, profiles_dir=tempfile.mkdtemp())
        httpd, url, stop = consoleserver.serve(sess)
        try:
            self.assertEqual(cli._existing_console(httpd.server_address[1], owner_ok=lambda port: True), url)
        finally:
            stop.set()

    def test_u75_other_server_is_not_a_console(self):
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), http.server.BaseHTTPRequestHandler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            self.assertIsNone(cli._existing_console(srv.server_address[1]))
        finally:
            srv.server_close()

    def test_u75_impostor_with_console_shape_is_rejected(self):   # güvenlik: port gaspı (başka süreç aynı JSON'u taklit eder)
        sess = consoleserver.Session(Fake(), on_commit=lambda s: {}, profiles_dir=tempfile.mkdtemp())
        httpd, url, stop = consoleserver.serve(sess)
        try:
            self.assertIsNone(cli._existing_console(httpd.server_address[1], owner_ok=lambda port: False))
        finally:
            stop.set()

    def test_u75_owner_check_accepts_own_bta_process(self):
        self.assertTrue(cli._owner_is_bta(1234, lookup=lambda port: {"pid": 4242, "uid": os.getuid(),
                                                                             "cmd": ["python3", "/x/bin/bta", "console"]}))
        self.assertFalse(cli._owner_is_bta(1234, lookup=lambda port: {"pid": 4242, "uid": os.getuid() + 1,
                                                                      "cmd": ["python3", "/x/bin/bta", "console"]}))
        self.assertFalse(cli._owner_is_bta(1234, lookup=lambda port: {"pid": 4242, "uid": os.getuid(),
                                                                      "cmd": ["python3", "-m", "http.server"]}))
        self.assertFalse(cli._owner_is_bta(1234, lookup=lambda port: None))   # sahibi görünmüyor (başka kullanıcı)

    def test_u75_closed_port_is_none(self):
        self.assertIsNone(cli._existing_console(free_port()))


class TestUnit(unittest.TestCase):
    def test_u76_unit_text(self):
        u = cli.render_service_unit("/opt/x/bin/bta")
        self.assertIn("ExecStart=/opt/x/bin/bta console --no-open --port 8766 --idle-timeout 0", u)
        for dep in ("pipewire.service", "wireplumber.service", "filter-chain.service"):
            self.assertIn(dep, u)
        self.assertIn("Restart=on-failure", u)
        self.assertIn("WantedBy=default.target", u)
        self.assertNotRegex(u.lower(), r"password|token|secret")


if __name__ == "__main__":
    unittest.main()
