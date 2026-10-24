"""U36 + U47: yerel sunucu güvenliği — vendor yol geçişi, CSRF (basit istek), DNS rebinding (Host), yeni profil
uçlarında durum kodları, boyut sınırı, kimlik geçişi, indirme başlığı, güvenlik başlıkları."""
import http.client
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from btaudio import consoleserver  # noqa: E402


class Fake:
    def apply_payload(self, p):
        pass


class TestSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sess = consoleserver.Session(Fake(), on_commit=lambda s: {}, profiles_dir=tempfile.mkdtemp())
        cls.httpd, url, cls.stop = consoleserver.serve(cls.sess)
        cls.port = cls.httpd.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.stop.set()

    def req(self, method, path, body=None, headers=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request(method, path, body=body, headers=headers or {})
        r = c.getresponse()
        return r.status, r.read()

    def test_u36_vendor_traversal_blocked(self):
        for p in ("/vendor//etc/passwd", "/vendor/../../btaudio/cli.py", "/vendor/sashimi-ui-2.1.0/../../../README.md"):
            st, body = self.req("GET", p)
            self.assertEqual(st, 404, p)
            self.assertNotIn(b"root:", body)
        # v0.3.0: sayfa tek dosya, dosya sunan yol YOK (sashimi-ui kaldırıldı) → hiçbir yol dosya sistemine inmez
        for p in ("/tools/console.html", "/btaudio/cli.py", "/%2e%2e/README.md"):
            self.assertEqual(self.req("GET", p)[0], 404, p)

    def test_csrf_simple_post_rejected(self):
        st, _ = self.req("POST", "/api/preset", body='{"id":"guclu_bas"}', headers={"Content-Type": "text/plain"})
        self.assertEqual(st, 415)
        st, _ = self.req("POST", "/api/preset", body='{"id":"guclu_bas"}', headers={"Content-Type": "application/json"})
        self.assertEqual(st, 200)

    def test_foreign_host_rejected(self):
        st, _ = self.req("GET", "/api/state", headers={"Host": "evil.example:80"})
        self.assertEqual(st, 403)



    def jpost(self, path, obj):
        import json
        st, body = self.req("POST", path, body=json.dumps(obj), headers={"Content-Type": "application/json"})
        return st, json.loads(body or b"{}")

    def test_u47_profile_conflict_409_and_overwrite(self):
        st, v = self.jpost("/api/profile/save", {"name": "Çakışma testi"})
        self.assertEqual(st, 200)
        st, v = self.jpost("/api/profile/save", {"name": "çakışma TESTİ"})
        self.assertEqual((st, v.get("conflict")), (409, "çakışma-testi"))
        st, v = self.jpost("/api/profile/save", {"name": "Çakışma testi", "overwrite": True})
        self.assertEqual(st, 200)

    def test_u47_body_too_large_413(self):
        big = '{"doc": "' + "x" * (300 * 1024) + '"}'
        st, _ = self.req("POST", "/api/profile/import", body=big, headers={"Content-Type": "application/json"})
        self.assertEqual(st, 413)

    def test_u47_bad_json_and_bad_doc_400(self):
        st, _ = self.req("POST", "/api/profile/import", body="{not json", headers={"Content-Type": "application/json"})
        self.assertEqual(st, 400)
        st, _ = self.jpost("/api/profile/import", {"doc": {"name": "x", "state": {"bands": []}}})
        self.assertEqual(st, 400)

    def test_u47_profile_id_traversal_404(self):
        for pid in ("../../etc/passwd", "..%2F..%2Fetc%2Fpasswd", ""):
            st, body = self.req("GET", "/api/profile/export?id=" + pid)
            self.assertEqual(st, 404, pid)
            self.assertNotIn(b"root:", body)
        st, _ = self.jpost("/api/profile/load", {"id": "../../etc/passwd"})
        self.assertEqual(st, 404)

    def test_u47_export_download_headers_utf8(self):
        self.jpost("/api/profile/save", {"name": "Güçlü şarkı"})
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        from urllib.parse import quote
        c.request("GET", "/api/profile/export?id=" + quote("güçlü-şarkı"))
        r = c.getresponse()
        r.read()
        self.assertEqual(r.status, 200)
        self.assertIn("filename*=UTF-8''bta-g%C3%BC%C3%A7l%C3%BC-%C5%9Fark%C4%B1.json", r.getheader("Content-Disposition"))

    def test_u47_security_headers_on_page(self):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("GET", "/")
        r = c.getresponse()
        r.read()
        self.assertIn("frame-ancestors 'none'", r.getheader("Content-Security-Policy"))
        self.assertEqual(r.getheader("X-Content-Type-Options"), "nosniff")

    def test_u47_export_foreign_host_403(self):
        st, _ = self.req("GET", "/api/profile/export?id=x", headers={"Host": "evil.example"})
        self.assertEqual(st, 403)


class TestAllowedHost(unittest.TestCase):
    """F16 genişlemesi: `--allow-host` ile açıkça adlandırılan ad (tailnet `tailscale serve` adı) kabul edilir;
    başka her ad DNS rebinding kapısında 403 kalır. Liste boşken davranış eskisiyle aynı."""
    @classmethod
    def setUpClass(cls):
        cls.sess = consoleserver.Session(Fake(), on_commit=lambda s: {}, profiles_dir=tempfile.mkdtemp())
        cls.httpd, url, cls.stop = consoleserver.serve(cls.sess, allow_hosts=("box.tailnet.ts.net",))
        cls.port = cls.httpd.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.stop.set()

    def req(self, host):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("GET", "/api/state", headers={"Host": host})
        r = c.getresponse()
        r.read()
        return r.status

    def test_named_host_allowed(self):
        self.assertEqual(self.req("box.tailnet.ts.net"), 200)
        self.assertEqual(self.req("box.tailnet.ts.net:8453"), 200)

    def test_other_hosts_still_rejected(self):
        for h in ("evil.example", "box.tailnet.ts.net.evil.example", "tailnet.ts.net"):
            self.assertEqual(self.req(h), 403, h)
        self.assertEqual(self.req("127.0.0.1"), 200)


if __name__ == "__main__":
    unittest.main()
