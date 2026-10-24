"""C4 — Canlı analizör ("müzik algılama"): EQ öncesi + sonrası spektrum, seviye metresi, parça ortalaması.

Ölçüm tasarımı (docs/research/findings.md R31–R36):
- Hann penceresi, N=16384 @48 kHz (2,93 Hz/bin), hop 2400 (20 kare/sn).
- 1/6 oktav BANT GÜCÜ (RTA biçimi): bant içindeki bin güçleri toplanır (kesirli kenar, kümülatif). Parseval gereği
  bir sinüsün tüm ana-lob enerjisi banda düşer → pencere taraklanması (scalloping) yok; tam ölçek sinüs = 0 dBFS
  (C = N·Σw²/4, tek taraflı). Pembe gürültü bu gösterimde DÜZ görünür → 4,5 dB/okt eğim gerekmez (FFT-bin
  görünümlerinin — SPAN/Pro-Q — eğimi bunu telafi etmek içindir).
- Zaman: güç alanında üstel IIR (Friture `spectrum.py:212`), τ hızlı 125 ms / orta 300 ms / yavaş 1 s.
- Tepe tutma: 1,5 sn tut, 12 dB/sn düş (tasarım; kaynaklı varsayılan bulunamadı).
- Metre: örnek tepe, RMS (300 ms, VU geleneği — Friture `levels.py:56`), true-peak ≈ 4× aşırı örnekleme
  (ITU-R BS.1770 Ek 2 yöntemi), kırpılma = |x| ≥ 0,999.

Yakalama (C4.3): `pw-record` + `node.autoconnect=false` + ELLE `pw-link`. Otomatik bağlantı KULLANILMAZ: WirePlumber
smart filter, hedefi monitörleyen akışı filtrenin girişine yönlendirir (R17). `node.passive=true` → analizör, ses
yokken kulaklığı uyanık TUTMAZ. Abone yokken süreç YOK (kimse bakmıyorken bedel ödenmez)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time

import numpy as np
from scipy import signal as _sig

FS = 48000
N_FFT = 16384
HOP = 2400
FLOOR_DB = -120.0
SIGNAL_DB = -80.0     # kısık uygulama sesi −60…−70 dBFS olabilir; gerçek sessizlik dijital sıfır (K14)
RESPONSE = {"fast": 0.125, "medium": 0.3, "slow": 1.0}
BANDS_PER_OCT = 6
RING_S = 3.0          # sınıflayıcı girdisi (D3): son 3 sn mono ses, float32 → 576 KB/dokunuş


def _centers():
    k = np.arange(round(BANDS_PER_OCT * np.log2(20 / 1000)), round(BANDS_PER_OCT * np.log2(20000 / 1000)) + 1)
    return 1000.0 * 2.0 ** (k / BANDS_PER_OCT)


def _db(p):
    return np.maximum(10 * np.log10(np.maximum(p, 1e-30)), FLOOR_DB)


class Spectrum:
    """1/6 oktav bant gücü (Hann N=16384, hop 2400), güç alanı EMA, tepe tutma, parça ortalaması (LTAS)."""
    def __init__(self, fs=FS, n=N_FFT, hop=HOP, response="medium", hold_s=1.5, fall_db_s=12.0):
        self.fs, self.n, self.hop = fs, n, hop
        self.w = _sig.windows.hann(n, sym=False)
        self.cal = n * float(np.sum(self.w ** 2)) / 4.0
        self.centers = _centers()
        half = 2 ** (1 / (2 * BANDS_PER_OCT))
        # kesirli bin kenarları: bin k [k−½, k+½] aralığını kaplar → kümülatif güç fonksiyonunun argümanı
        self.lo = self.centers / half * n / fs + 0.5
        self.hi = self.centers * half * n / fs + 0.5
        self.buf = np.zeros((n, 2))
        self.pending = np.zeros((0, 2))
        self.set_response(response)
        self.hold_s, self.fall = hold_s, fall_db_s
        self.y = np.zeros(len(self.centers))
        self.hold_db = np.full(len(self.centers), FLOOR_DB)
        self.hold_t = np.zeros(len(self.centers))
        self.ltas_sum, self.ltas_n = np.zeros(len(self.centers)), 0

    def set_response(self, response):
        """Tepki hızı: fast 125 ms · medium 300 ms · slow 1 s."""
        self.response = response if response in RESPONSE else "medium"
        self.a = float(np.exp(-self.hop / (self.fs * RESPONSE[self.response])))

    def band_power(self, x):
        """Bir pencerenin bant güçleri (kalibre: tam ölçek sinüs = 0 dBFS, kanalların güç ortalaması)."""
        p = np.zeros(len(self.centers))
        for c in range(x.shape[1]):
            X = np.fft.rfft(x[:, c] * self.w)
            cp = np.concatenate([[0.0], np.cumsum(np.abs(X) ** 2)])
            idx = np.arange(len(cp), dtype=float)
            p += np.interp(self.hi, idx, cp) - np.interp(self.lo, idx, cp)
        return p / x.shape[1] / self.cal                   # kanalların güç ortalaması (faz iptali yok)

    def push(self, block):
        """Blok ekler, her hop için kare üretir: {bands, hold} (dBFS)."""
        block = np.asarray(block, dtype=np.float64).reshape(-1, 2)
        self.pending = np.concatenate([self.pending, block])
        frames = []
        dt = self.hop / self.fs
        while len(self.pending) >= self.hop:
            new, self.pending = self.pending[:self.hop], self.pending[self.hop:]
            self.buf = np.concatenate([self.buf[self.hop:], new])
            x = self.band_power(self.buf)
            self.y = self.a * self.y + (1 - self.a) * x
            ydb = _db(self.y)
            if 10 * np.log10(max(float(np.mean(new ** 2)), 1e-30)) > SIGNAL_DB:
                self.ltas_sum += x
                self.ltas_n += 1
            up = ydb >= self.hold_db
            self.hold_db[up], self.hold_t[up] = ydb[up], 0.0
            self.hold_t[~up] += dt
            fall = (~up) & (self.hold_t > self.hold_s)
            self.hold_db[fall] -= self.fall * dt
            self.hold_db = np.maximum(self.hold_db, ydb)
            frames.append({"bands": np.round(ydb, 1).tolist(), "hold": np.round(self.hold_db, 1).tolist()})
        return frames

    def ltas(self):
        """Sinyal varken biriken uzun süreli ortalama spektrum (dBFS)."""
        return (np.round(_db(self.ltas_sum / self.ltas_n), 1) if self.ltas_n else np.full(len(self.centers), FLOOR_DB)).tolist()

    def reset_ltas(self):
        """Parça ortalamasını sıfırlar."""
        self.ltas_sum[:], self.ltas_n = 0.0, 0


class LevelMeter:
    """Kanal başına örnek tepe, RMS (300 ms), true-peak (4× aşırı örnekleme), kırpılma sayısı, sinyal var/yok."""
    def __init__(self, fs=FS, rms_tau=0.3):
        self.fs, self.tau = fs, rms_tau
        self.ms = np.zeros(2)

    def push(self, block, light=False):
        """light=True (yalnız otomasyon dinliyor): true-peak aşırı örneklemesi atlanır (blok başına ~1,4 ms, T-L40) →
        true_peak = örnek tepe. Arayüz metresi her zaman tam modda çalışır."""
        x = np.asarray(block, dtype=np.float64).reshape(-1, 2)
        a = float(np.exp(-len(x) / (self.fs * self.tau)))
        inst = np.mean(x ** 2, axis=0)
        self.ms = a * self.ms + (1 - a) * inst
        pk = np.max(np.abs(x), axis=0)
        tp = pk if (light or len(x) < 8) else np.max(np.abs(_sig.resample_poly(x, 4, 1, axis=0)), axis=0)
        out = {ch: {"peak": round(float(_db(pk[i] ** 2)), 2), "rms": round(float(_db(self.ms[i])), 2),
                    "true_peak": round(float(_db(tp[i] ** 2)), 2)} for i, ch in enumerate(("L", "R"))}
        out["clips"] = int(np.sum(np.abs(x) >= 0.999))
        out["signal"] = bool(10 * np.log10(max(float(np.max(inst)), 1e-30)) > SIGNAL_DB)
        return out


def pw_record_cmd(node_name: str) -> list:
    """Ham f32 stereo 48 kHz pw-record komutu (autoconnect kapalı, passive — kulaklığı uyanık tutmaz)."""
    props = f'{{ node.name = "{node_name}" node.description = "bta analizör" node.autoconnect = false node.passive = true }}'
    return ["pw-record", "--raw", "--format", "f32", "--rate", str(FS), "--channels", "2", "-P", props, "-"]


def _link(src_ports, node_name, timeout=5.0):
    """Kayıt düğümünün giriş portları görünene dek bekle, sonra kaynak portlara ELLE bağla (R17)."""
    t0 = time.time()
    while time.time() - t0 < timeout:
        out = subprocess.run(["pw-link", "-i"], capture_output=True, text=True, timeout=5).stdout
        if f"{node_name}:input_FL" in out and f"{node_name}:input_FR" in out:
            for src, ch in zip(src_ports, ("FL", "FR")):
                subprocess.run(["pw-link", src, f"{node_name}:input_{ch}"], capture_output=True, timeout=5)
            return True
        time.sleep(0.1)
    return False


_SEQ = [0]


def _unique(name: str) -> str:
    """Düğüm adı süreç + örnek başına benzersiz: aynı adlı iki kayıt düğümü olursa `pw-link port adı` İLK eşleşene
    bağlanır → ikinci analizör sessizce veri almaz (E19, ölçüldü: konsol sunucusu açıkken teşhis örneği 0 kare)."""
    _SEQ[0] += 1
    return f"bta_analyzer_{name}_{os.getpid()}_{_SEQ[0]}"


class _Tap:
    def __init__(self, name, spec, response):
        self.name, self.spec = name, spec
        self.node = _unique(name)
        self.sp = Spectrum(response=response)
        self.lv = LevelMeter()
        self.proc, self.thread = None, None
        self.last, self.levels, self.clips = None, None, 0
        self.light = False                                 # yalnız otomasyon: kare başına FFT/true-peak YOK
        self.ring = np.zeros(int(RING_S * FS), np.float32)
        self.ring_w = 0                                    # toplam yazılan örnek (halka konumu = ring_w % len)
        self.ring_lock = threading.Lock()

    def _ring_push(self, mono):
        n, N = len(mono), len(self.ring)
        if n >= N:
            mono, n = mono[-N:], N
        with self.ring_lock:
            i = self.ring_w % N
            k = min(n, N - i)
            self.ring[i:i + k] = mono[:k]
            if k < n:
                self.ring[:n - k] = mono[k:]
            self.ring_w += n

    def recent(self, seconds):
        """Son `seconds` sn mono ses (kopya) — yeterli örnek birikmediyse None."""
        N = len(self.ring)
        n = min(int(seconds * FS), N)
        with self.ring_lock:
            if self.ring_w < n:
                return None
            i = self.ring_w % N
            return np.concatenate([self.ring[i:], self.ring[:i]])[-n:].copy() if n else None

    def start(self, on_frame):
        cmd = self.spec.get("cmd") or pw_record_cmd(self.node)
        from . import procs
        self.proc = procs.spawn(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)   # ebeveynle ölür (E23)
        if "ports" in self.spec:
            threading.Thread(target=_link, args=(self.spec["ports"], self.node), daemon=True).start()
        self.thread = threading.Thread(target=self._read, args=(on_frame,), daemon=True)
        self.thread.start()

    def _read(self, on_frame):
        nbytes = HOP * 2 * 4
        buf = b""
        while self.proc and self.proc.poll() is None:
            try:
                chunk = self.proc.stdout.read(nbytes - len(buf))
            except (ValueError, OSError):
                break
            if not chunk:
                break
            buf += chunk
            if len(buf) < nbytes:
                continue
            x = np.frombuffer(buf, dtype="<f4").reshape(-1, 2).astype(np.float64)
            buf = b""
            self._ring_push(x.mean(axis=1).astype(np.float32))
            light = self.light
            lv = self.lv.push(x, light=light)
            self.clips += lv["clips"]
            self.levels = lv
            if light:
                self.last = None                           # bayat kare arayüze sızmasın
                continue
            for fr in self.sp.push(x):
                self.last = fr
            on_frame(self.name)

    def bands_now(self, windows=4, hop=8192):
        """Halka tampondan istek anında 1/6 okt bant gücü (hafif mod): son ~0,9 sn'de `windows` Hann penceresinin güç
        ortalaması. Kalibrasyon tam analizörle aynı (Spectrum.band_power). Yeterli ses yoksa None."""
        need = self.sp.n + (windows - 1) * hop
        x = self.recent(need / FS)
        if x is None:
            return None
        p = np.zeros(len(self.sp.centers))
        for k in range(windows):
            seg = x[k * hop:k * hop + self.sp.n].astype(np.float64).reshape(-1, 1)
            p += self.sp.band_power(seg)
        return np.round(_db(p / windows), 1).tolist()

    def stop(self):
        p, self.proc = self.proc, None
        if p and p.poll() is None:
            p.terminate()                                  # yalnız KENDİ alt sürecimiz (session-safety kapsamı dışı)
            try:
                p.wait(timeout=3)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait(timeout=3)
        if p and p.stdout:
            p.stdout.close()

    def alive(self):
        return self.proc is not None and self.proc.poll() is None


class Analyzer:
    """Abone sayımlı yakalama yöneticisi. İlk abone → başlat; son abone gidince `linger_s` sonra DURDUR."""

    def __init__(self, taps: dict, linger_s: float = 2.0, response: str = "medium", on_activity=None):
        self.spec, self.linger, self.response = taps, linger_s, response
        self.taps: dict[str, _Tap] = {}
        self.subs: dict[int, int] = {}
        self.seq, self.frame = 0, None
        self.cond = threading.Condition()
        self.lock = threading.Lock()
        self._next_id, self._stop_timer = 1, None
        self.kinds: dict[int, str] = {}
        self.on_activity = on_activity

    # ── yaşam döngüsü ──
    def running(self):
        """Herhangi bir yakalama süreci yaşıyor mu."""
        return any(t.alive() for t in self.taps.values())

    def pids(self):
        """Yaşayan yakalama süreçlerinin pid'leri."""
        return [t.proc.pid for t in self.taps.values() if t.alive()]

    def _want(self) -> dict:
        """İstenen dokunuşlar → hafif mi? Arayüz abonesi varsa hepsi tam; yalnız otomasyon varsa yalnız 'pre', hafif."""
        kinds = set(self.kinds.values())
        if "ui" in kinds:
            return {n: False for n in self.spec}
        if "auto" in kinds and "pre" in self.spec:
            return {"pre": True}
        return {}

    def _reconcile(self, allow_stop):
        want = self._want()
        for n, light in want.items():
            t = self.taps.get(n)
            if t is None or not t.alive():
                t = _Tap(n, self.spec[n], self.response)
                t.light = light
                self.taps[n] = t
                t.start(self._on_frame)
            else:
                if t.light and not light:
                    t.sp = Spectrum(response=self.response)   # tam moda dönüş: eski yarım pencere yok
                t.light = light
        if allow_stop:
            for n, t in list(self.taps.items()):
                if n not in want:
                    t.stop()

    def _start(self):
        self._reconcile(allow_stop=False)

    def _stop(self):
        with self.lock:
            self._reconcile(allow_stop=True)

    def subscribe(self, kind: str = "ui") -> int:
        """kind="ui": arayüz (tam analiz, kareler) · kind="auto": otomasyon motoru (hafif, yalnız snapshot)."""
        with self.lock:
            sid = self._next_id
            self._next_id += 1
            self.subs[sid] = self.seq
            self.kinds[sid] = kind
            if self._stop_timer:
                self._stop_timer.cancel()
                self._stop_timer = None
            self._start()
        return sid

    def unsubscribe(self, sid):
        """Aboneliği bırakır; bekleme süresi (linger) sonunda istenmeyen dokunuşlar durur."""
        with self.lock:
            self.subs.pop(sid, None)
            self.kinds.pop(sid, None)
            if self._stop_timer:
                self._stop_timer.cancel()
            # bekleme: sekme yenileme gibi kısa kopuşlarda süreç öldürülüp yeniden doğmasın
            self._stop_timer = threading.Timer(self.linger, self._stop)
            self._stop_timer.daemon = True
            self._stop_timer.start()

    def close(self):
        """Tüm abonelikleri siler, süreçleri durdurur."""
        with self.lock:
            self.subs.clear()
            self.kinds.clear()
            if self._stop_timer:
                self._stop_timer.cancel()
        self._stop()

    # ── kareler ──
    def _on_frame(self, name):
        if name != ("post" if "post" in self.taps else name):
            return                                         # kareyi EQ sonrası dokunuş sürer; öncesi en son değerle eşlenir
        pre, post = self.taps.get("pre"), self.taps.get("post")
        fr = {"t": round(time.time(), 3), "f": [round(float(f), 1) for f in post.sp.centers],
              "post": post.last["bands"], "hold": post.last["hold"],
              "pre": pre.last["bands"] if pre and pre.last else None,
              "ltas": post.sp.ltas(),
              "levels": {"post": post.levels, "pre": pre.levels if pre else None},
              "clips": post.clips, "signal": bool((post.levels or {}).get("signal") or (pre and (pre.levels or {}).get("signal"))),
              "response": self.response}
        with self.cond:
            self.seq += 1
            self.frame = fr
            self.cond.notify_all()
        if self.on_activity:
            self.on_activity()

    def snapshot(self, tap="pre", seconds=2.0):
        """Otomasyon girdisi (D3): {centers, bands (dBFS, 1/6 okt), level_db (L/R RMS ort.), signal, audio}.
        Yakalama çalışmıyorsa / henüz kare yoksa None. Canlı veri, istek yolunu bloklamaz (kopya)."""
        t = self.taps.get(tap)
        if not (t and t.alive() and t.levels):
            return None
        bands = t.bands_now() if (t.light or t.last is None) else list(t.last["bands"])
        if bands is None:
            return None
        lv = t.levels
        rms = 10 * np.log10((10 ** (lv["L"]["rms"] / 10) + 10 ** (lv["R"]["rms"] / 10)) / 2)
        return {"centers": t.sp.centers.tolist(), "bands": bands, "level_db": round(float(rms), 2),
                "signal": bool(lv.get("signal")), "audio": t.recent(seconds)}

    def wait_frame(self, sid, timeout=1.0):
        """Abonenin görmediği yeni kareyi bekler (timeout → None)."""
        with self.cond:
            seen = self.subs.get(sid, self.seq)
            if not self.cond.wait_for(lambda: self.seq > seen, timeout=timeout):
                return None
            if sid in self.subs:
                self.subs[sid] = self.seq
            return self.frame

    # ── yapılandırma ──
    def info(self):
        """Kullanılabilirlik, çalışma durumu, dokunuşlar, tepki hızı."""
        return {"available": bool(self.spec) and all("cmd" in s or shutil.which("pw-record") for s in self.spec.values()),
                "running": self.running(), "taps": sorted(self.spec), "response": self.response,
                "responses": list(RESPONSE)}

    def configure(self, body: dict):
        """Tepki hızı / LTAS sıfırlama / kırpılma sayacı sıfırlama."""
        if body.get("response") in RESPONSE:
            self.response = body["response"]
            for t in self.taps.values():
                t.sp.set_response(self.response)
        if body.get("reset_ltas"):
            for t in self.taps.values():
                t.sp.reset_ltas()
        if body.get("reset_clips"):
            for t in self.taps.values():
                t.clips = 0
        return self.info()

    # ── SSE ──
    def serve_sse(self, h):
        """SSE akışı: her yeni kare JSON; kopunca abonelik bırakılır."""
        h.send_response(200)
        h.send_header("Content-Type", "text/event-stream")
        h.send_header("Cache-Control", "no-store")
        h.send_header("Connection", "close")
        h.send_header("X-Content-Type-Options", "nosniff")
        h.end_headers()
        h.close_connection = True
        sid = self.subscribe()
        try:
            h.wfile.write(b"retry: 2000\n\n")
            h.wfile.flush()
            while True:
                fr = self.wait_frame(sid, timeout=1.0)
                payload = fr if fr is not None else {"idle": True, "t": round(time.time(), 3)}
                h.wfile.write(b"data: " + json.dumps(payload, separators=(",", ":")).encode() + b"\n\n")
                h.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            self.unsubscribe(sid)


def console_taps() -> dict:
    """Gerçek konsol grafı: EQ öncesi = filtre girişinin monitörü, sonrası = filtre çıkışı (BT sink'e giden sinyal)."""
    return {"pre": {"ports": ["effect_input.bta_console:monitor_FL", "effect_input.bta_console:monitor_FR"]},
            "post": {"ports": ["effect_output.bta_console:output_FL", "effect_output.bta_console:output_FR"]}}
