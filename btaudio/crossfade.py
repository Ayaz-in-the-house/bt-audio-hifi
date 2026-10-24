"""D2 — Tıksız geçiş sıralayıcısı (infrastructure).

Kurallar (R33'ün sonuçları):
1. Yeni durum YALNIZ sessiz zincire yüklenir; çalan zincire asla dokunulmaz.
2. Bir geçiş bitmeden (fade süresi dolmadan) sessizleşmekte olan zincir yeniden yüklenmez — aksi hâlde hâlâ duyulan
   zincirin belleği sıfırlanır (tık). Bu yüzden istekler sıralanır; bekleyenlerden yalnız EN SONUNCUSU uygulanır.
3. `submit` çağıranı asla bloklamaz (istek yolu pw-cli beklemez) — iş parçacığı + koşul değişkeni."""
from __future__ import annotations

import threading
import time

from . import console

STEP_S = 0.012          # ≈ yarım PipeWire kuantumu (1024/48000 = 21 ms) → her blokta ≤ 1 kazanç adımı


class PwCliSession:
    """Tek kalıcı `pw-cli` süreci (stdin'den komut): her adım için süreç doğurmak ~20 ms sürer, geçişi bozardı."""

    def __init__(self, node_name: str):
        import json
        import subprocess
        self.node_name, self._json, self._sp = node_name, json, subprocess
        self.proc, self.id = None, None

    def _resolve(self):
        from .tunerserver import PwApplier
        return PwApplier(node_name=self.node_name)._resolve()

    def _spawn(self):
        from . import procs
        self.proc = procs.spawn(["pw-cli"], stdin=self._sp.PIPE, stdout=self._sp.DEVNULL, stderr=self._sp.DEVNULL,
                                text=True, bufsize=1)

    def apply_payload(self, payload: str):
        """Props yükünü kalıcı pw-cli oturumuna yazar; oturum yoksa düğümü çözüp başlatır."""
        if self.proc is None or self.proc.poll() is not None:
            self.id = self._resolve()
            self._spawn()
        self.proc.stdin.write(f"set-param {self.id} Props {payload}\n")
        self.proc.stdin.flush()

    def close(self):
        """pw-cli 1.6.8 stdin EOF'unda ÇIKMAZ, döner (E23, ölçüldü) → önce `quit`, sonra kapat, sonra zaman aşımı."""
        p, self.proc = self.proc, None
        if not (p and p.poll() is None):
            return
        try:
            p.stdin.write("quit\n")
            p.stdin.flush()
            p.stdin.close()
        except (BrokenPipeError, OSError, ValueError):
            pass
        try:
            p.wait(timeout=1)
        except self._sp.TimeoutExpired:
            p.terminate()                                 # yalnız KENDİ alt sürecimiz
            try:
                p.wait(timeout=2)
            except self._sp.TimeoutExpired:
                p.kill()
                p.wait(timeout=2)


def detect_active(node_name: str) -> str:
    """Çalan zinciri PipeWire'dan oku (sumL:Gain 2 > 0,5 → B). Sunucu yeniden başlarsa yanlış varsayım = duyulan
    zincire yükleme = tık."""
    import json
    import subprocess
    try:
        objs = json.loads(subprocess.run(["pw-dump"], capture_output=True, text=True, timeout=10).stdout)
        for o in objs:
            if o.get("type") == "PipeWire:Interface:Node" and o["info"]["props"].get("node.name") == node_name:
                for pr in o["info"]["params"].get("Props", []):
                    par = pr.get("params")
                    if par:
                        d = dict(zip(par[::2], par[1::2]))
                        if "sumL:Gain 2" in d:
                            return "B" if d["sumL:Gain 2"] > 0.5 else "A"
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    return "A"


class Crossfader:
    """A/B zincirli tıksız geçiş sıralayıcısı: yeni durum sessiz zincire yüklenir, toplama kazançları 12 ms adımlarla kaydırılır; istekler birleşir, en sonuncusu kazanır."""
    def __init__(self, applier, fade_s: float = 0.04, clock=time.monotonic, active: str = "A"):
        self.applier, self.fade_s, self.clock = applier, fade_s, clock
        self.active = active
        self._cv = threading.Condition()
        self._pending = None                     # (state, bypass, fade_s)
        self._busy = False
        self._ready_at = 0.0                     # önceki geçiş bitiş zamanı
        self._stop = False
        self.errors = []
        self.applied = 0
        self._t = threading.Thread(target=self._run, name="bta-crossfade", daemon=True)
        self._t.start()

    def settle(self):
        """Karışımı etkin zincire SABİTLE (açılışta, ilk yüklemeden önce). Önceki süreç yarı geçişte öldüyse iki zincir de
        duyuluyordur; sabitlemeden yüklemek duyulan zincirin belleğini sıfırlar → tık (U68)."""
        with self._cv:
            self.applier.apply_payload(console.mix_gains(1.0, 0.0) if self.active == "A" else console.mix_gains(0.0, 1.0))

    def apply_payload(self, payload: str):
        """Zincirden bağımsız tek kazanç (U78 sınırlayıcı): geçişle aynı oturumdan, sıraya girmeden yazar."""
        with self._cv:
            self.applier.apply_payload(payload)

    def submit(self, state: dict, bypass: bool = False, fade_s: float | None = None):
        """Geçiş isteği kuyruğa (çağıranı bloklamaz); bekleyen önceki istek ezilir."""
        with self._cv:
            self._pending = (state, bypass, self.fade_s if fade_s is None else fade_s)
            self._cv.notify()

    # uyumluluk: Session.applier arayüzü (apply_payload) yerine durum alır
    def apply_state(self, state, bypass=False, fade_s=None):
        """Session uyumluluğu: submit ile aynı."""
        self.submit(state, bypass, fade_s)

    def _run(self):
        while True:
            with self._cv:
                while self._pending is None and not self._stop:
                    self._cv.wait()
                if self._stop:
                    return
                wait = self._ready_at - self.clock()
            if wait > 0:
                time.sleep(wait)                  # önceki geçiş bitsin (kural 2); bu arada gelenler birleşir
            with self._cv:
                job, self._pending = self._pending, None
                self._busy = True
            try:
                st, bypass, fade = job
                to = "B" if self.active == "A" else "A"
                self.applier.apply_payload(console.pw_params_ab(st, to, bypass=bypass))   # sessiz zincire yükle
                steps = console.crossfade_steps(to, max(3, round(fade / STEP_S)))
                for i, p in enumerate(steps):                                            # küçük kazanç adımları
                    self.applier.apply_payload(p)
                    if i < len(steps) - 1:
                        time.sleep(fade / len(steps))
                self.active = to
                self._ready_at = self.clock()
                self.applied += 1
            except Exception as e:                # uygulanamadı → zincir DEĞİŞMEDİ sayılır, hata görünür
                self.errors.append(str(e)[:200])
            finally:
                with self._cv:
                    self._busy = False
                    self._cv.notify_all()

    def wait_idle(self, timeout: float = 5.0) -> bool:
        """Kuyruk boşalıp son geçiş bitene dek bekler (en çok timeout sn); boşaldıysa True."""
        t0 = time.time()
        while True:
            with self._cv:
                idle = self._pending is None and not self._busy and self.clock() >= self._ready_at
            if idle:
                return True
            if time.time() - t0 > timeout:
                return False
            time.sleep(0.01)

    def close(self):
        """İş parçacığını durdurur ve uygulayıcının pw-cli oturumunu kapatır (E23)."""
        with self._cv:
            self._stop = True
            self._cv.notify_all()
        self._t.join(timeout=3)
        if hasattr(self.applier, "close"):
            self.applier.close()                          # kalıcı pw-cli oturumunu da kapat (E23)
