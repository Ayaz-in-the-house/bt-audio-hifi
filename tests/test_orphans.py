"""U64: uzun ömürlü alt süreçler ebeveynlerinden uzun YAŞAMAZ (E23).

Ölçülen olay (2026-09-27 23:41): yeniden başlatılan konsol sunucusunun `pw-cli` alt süreci 1 saat boyunca yetim kaldı ve
%22 çekirdek yaktı. Kök neden (ölçüldü): pw-cli 1.6.8 stdin EOF'unda ÇIKMAZ, döner (durum R); `quit` komutuyla anında
çıkar. Sınıf: kapanışta açıkça kapatılmayan / ebeveyn ani ölümünde kalan alt süreçler.

1. PwCliSession.close() → pw-cli ≤ 1 sn'de çıkar (quit + stdin kapat + zaman aşımında terminate).
2. Ebeveyn ANİ ölürse (os._exit, SIGKILL benzeri; kapanış kodu çalışmaz) pw-cli ve analizörün pw-record'u ≤ 3 sn'de ölür.
PipeWire yoksa (CI) atlanır — bu makinede koşar."""
import os
import shutil
import subprocess
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from btaudio import crossfade  # noqa: E402

HAVE_PW = bool(shutil.which("pw-cli") and shutil.which("pw-record")) and \
    subprocess.run(["pw-cli", "info", "0"], capture_output=True, timeout=10).returncode == 0
REPO = os.path.join(os.path.dirname(__file__), "..")


def alive(pid):
    try:
        return open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()[0] != "Z"
    except OSError:
        return False


def wait_dead(pid, t=3.0):
    t0 = time.time()
    while time.time() - t0 < t:
        if not alive(pid):
            return True
        time.sleep(0.05)
    return False


@unittest.skipUnless(HAVE_PW, "PipeWire yok")
class TestOrphans(unittest.TestCase):
    def test_u64_pwcli_close_exits(self):
        s = crossfade.PwCliSession("effect_input.yok_bta_test")
        s._spawn()
        pid = s.proc.pid
        self.assertTrue(alive(pid))
        t0 = time.time()
        s.close()
        self.assertTrue(wait_dead(pid, 1.0), "pw-cli close() sonrası yaşıyor")
        self.assertLess(time.time() - t0, 0.5, "quit yolu değil zaman aşımı yedeği çalıştı")

    def test_u64_children_die_with_parent(self):
        code = (
            "import sys, time, os\n"
            f"sys.path.insert(0, {REPO!r})\n"
            "from btaudio import crossfade, analyzer\n"
            "import threading\n"
            "s = crossfade.PwCliSession('effect_input.yok_bta_test')\n"
            "t = threading.Thread(target=s._spawn); t.start(); t.join()\n"      # kısa ömürlü iş parçacığından doğsa da
            "time.sleep(0.5)\n"
            "print('CLI', s.proc.pid, flush=True)\n"
            "an = analyzer.Analyzer({'pre': {'ports': []}})\n"
            "th = threading.Thread(target=lambda: an.subscribe(kind='auto')); th.start(); th.join()\n"
            "time.sleep(1.0)\n"
            "print('REC', *an.pids(), flush=True)\n"
            "time.sleep(0.5)\n"
            "os._exit(0)\n")
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=30).stdout
        pids = {ln.split()[0]: [int(x) for x in ln.split()[1:]] for ln in out.splitlines() if ln[:3] in ("CLI", "REC")}
        self.assertEqual(len(pids.get("CLI", [])), 1, out)
        self.assertEqual(len(pids.get("REC", [])), 1, out)
        for kind, lst in pids.items():
            for pid in lst:
                if not wait_dead(pid, 3.0):
                    os.kill(pid, 15)                            # testin kendi artığı — temizle, sonra başarısız say
                    self.fail(f"{kind} {pid} ebeveyn öldükten sonra yaşıyor (yetim)")
        # kısa ömürlü iş parçacığı bittiğinde çocuk ÖLMEMİŞ olmalı (PDEATHSIG iş parçacığı tuzağı) — yukarıda
        # 'CLI'/'REC' satırları iş parçacığı bittikten SONRA basıldı ve süreçler o an yaşıyordu (aşağıda kontrol).


class TestThreadPitfall(unittest.TestCase):
    @unittest.skipUnless(HAVE_PW, "PipeWire yok")
    def test_u64_child_survives_spawning_thread_exit(self):
        """PR_SET_PDEATHSIG, ebeveyn SÜRECİ değil doğuran İŞ PARÇACIĞI ölünce tetiklenir. Analizör/pw-cli HTTP istek
        iş parçacıklarından doğar → o iş parçacığı bitince çocuk ÖLMEMELİ."""
        import threading
        s = crossfade.PwCliSession("effect_input.yok_bta_test")
        th = threading.Thread(target=s._spawn)
        th.start()
        th.join()
        time.sleep(0.5)
        try:
            self.assertTrue(alive(s.proc.pid), "doğuran iş parçacığı bitince pw-cli öldü")
        finally:
            s.close()


if __name__ == "__main__":
    unittest.main()
