"""U50: açık kaynak sızıntı kapısı regresyonu — gönderilen kümede MAC / ev yolu / makine adı / e-posta / özel IP yok."""
import os
import subprocess
import unittest

REPO = os.path.join(os.path.dirname(__file__), "..")


class TestOssAudit(unittest.TestCase):
    def test_u50_ship_set_clean(self):
        r = subprocess.run(["bash", os.path.join(REPO, "tools", "oss-audit.sh")], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_u50_audit_actually_detects(self):
        """Kapının kendisi test edilir: geçici bir izlenen dosyaya MAC koyunca kapı düşmeli."""
        probe = os.path.join(REPO, "tools", "_oss_probe.txt")
        try:
            open(probe, "w").write("cihaz 02:00:00:00:00:03\n")
            subprocess.run(["git", "-C", REPO, "add", "-N", probe], check=True)
            r = subprocess.run(["bash", os.path.join(REPO, "tools", "oss-audit.sh")], capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("_oss_probe.txt", r.stdout)
        finally:
            subprocess.run(["git", "-C", REPO, "rm", "-q", "--cached", "-f", probe], capture_output=True)
            os.path.exists(probe) and os.remove(probe)


if __name__ == "__main__":
    unittest.main()
