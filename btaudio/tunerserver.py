"""F8 v2 — Canlı bas ayarlayıcının yerel HTTP sunucusu (yalnız 127.0.0.1). Uygulayıcı enjekte edilir:
gerçek kullanımda `PwApplier` (pw-cli set-param), testte sahte uygulayıcı."""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import loudness, tuner

PAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "bass-tune.html")
NODE = "effect_input.bta_bass_eq"


class PwApplier:
    """Çalışan filter-chain düğümüne kontrol değerlerini yazar (servis yeniden başlatılmaz)."""

    def __init__(self, node_name=NODE):
        self.node_name, self._id = node_name, None

    def _resolve(self, wait_s: float = 10.0):
        """systemd 'active' dediğinde düğüm henüz yaratılmamış olabilir (ölçüldü: ilk sorguda yok, ~1 sn sonra
        running) → kısa süre yokla."""
        t0 = time.time()
        while True:
            objs = json.loads(subprocess.run(["pw-dump"], capture_output=True, text=True, timeout=15).stdout)
            for o in objs:
                if o.get("type") == "PipeWire:Interface:Node" and o["info"]["props"].get("node.name") == self.node_name:
                    return o["id"]
            if time.time() - t0 > wait_s:
                raise RuntimeError(f"{self.node_name} düğümü {wait_s:.0f} sn'de oluşmadı — filter-chain.service?")
            time.sleep(0.5)

    def apply(self, st, bypass=False):
        return self.apply_payload(tuner.pw_params(st, bypass=bypass))

    def apply_payload(self, payload):
        for attempt in range(2):
            if self._id is None:
                self._id = self._resolve()
            r = subprocess.run(["pw-cli", "set-param", str(self._id), "Props", payload],
                               capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and "error" not in (r.stderr + r.stdout).lower():
                return payload
            self._id = None                               # düğüm yeniden doğmuş olabilir → yeniden çöz
        raise RuntimeError(f"pw-cli set-param başarısız: {r.stderr.strip()[:200]}")


class Session:
    def __init__(self, applier, on_save, initial=None, idle_timeout_s=3600):
        self.applier, self.on_save = applier, on_save
        self.gains = dict(initial or tuner.PRESETS["notr"])
        self.bypass = False
        self.last = time.time()
        self.idle_timeout_s = idle_timeout_s
        self.saved = None
        self.lock = threading.Lock()

    def snapshot(self):
        st = tuner.state(self.gains)
        return {"bands": [{**b, "desc": next(x[4] for x in tuner.BANDS if x[0] == b["id"])} for b in st["bands"]],
                "preamp_db": st["preamp_db"], "bypass": self.bypass, "presets": tuner.PRESETS,
                "min": tuner.MIN_GAIN, "max": tuner.MAX_GAIN, "saved": self.saved,
                "curve": {"f": [round(f, 1) for f in tuner.GRID],
                          "db": [round(v, 2) for v in loudness.eq_response_db(st["bands"], tuner.GRID)]}}

    def set_gains(self, gains):
        with self.lock:
            self.gains.update({k: float(v) for k, v in gains.items() if k in {b[0] for b in tuner.BANDS}})
            self.applier.apply(tuner.state(self.gains), bypass=self.bypass)
            self.last = time.time()
        return self.snapshot()

    def set_bypass(self, on):
        with self.lock:
            self.bypass = bool(on)
            self.applier.apply(tuner.state(self.gains), bypass=self.bypass)
            self.last = time.time()
        return self.snapshot()

    def save(self):
        with self.lock:
            self.saved = self.on_save(tuner.state(self.gains))
            self.last = time.time()
        return self.snapshot()


def make_handler(sess: Session, stop_event: threading.Event):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, body, ctype="application/json"):
            data = body if isinstance(body, bytes) else json.dumps(body, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)


        def _guard(self, post=False):
            """DNS rebinding: yalnız 127.0.0.1/localhost Host · CSRF: POST yalnız application/json (basit istek değil →
            tarayıcı CORS ön-uçuşu yapar, izin başlığı vermediğimiz için başka site gönderemez)."""
            host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
            if host not in ("127.0.0.1", "localhost"):
                self._send(403, {"error": "yasak host"})
                return False
            if post and not (self.headers.get("Content-Type") or "").startswith("application/json"):
                self._send(415, {"error": "application/json gerekli"})
                return False
            return True

        def do_GET(self):
            if not self._guard():
                return
            if self.path in ("/", "/index.html"):
                return self._send(200, open(PAGE, "rb").read(), "text/html; charset=utf-8")
            if self.path == "/api/state":
                return self._send(200, sess.snapshot())
            self._send(404, {"error": "yok"})

        def do_POST(self):
            if not self._guard(post=True):
                return
            n = int(self.headers.get("Content-Length", 0) or 0)
            body = json.loads(self.rfile.read(n) or b"{}")
            try:
                if self.path == "/api/set":
                    return self._send(200, sess.set_gains(body.get("gains", {})))
                if self.path == "/api/bypass":
                    return self._send(200, sess.set_bypass(body.get("on")))
                if self.path == "/api/save":
                    return self._send(200, sess.save())
                if self.path == "/api/quit":
                    self._send(200, {"ok": True})
                    stop_event.set()
                    return
            except Exception as e:                        # hata sayfada görünsün, sessizce yutulmasın
                return self._send(500, {"error": str(e)[:300]})
            self._send(404, {"error": "yok"})
    return H


def serve(sess: Session, port: int = 0):
    """Sunucuyu başlatır; (httpd, url, stop_event, thread) döner. Boşta kalma süresi dolunca kendini kapatır."""
    stop = threading.Event()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(sess, stop))
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()

    def watchdog():
        while not stop.is_set():
            if time.time() - sess.last > sess.idle_timeout_s:
                stop.set()
            time.sleep(1)
        httpd.shutdown()
    threading.Thread(target=watchdog, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/", stop, t
