"""Alt süreç doğurma (infrastructure): hiçbir alt süreç ebeveyninden uzun YAŞAMAZ (E23, U64).

Neden: pw-cli 1.6.8 stdin EOF'unda çıkmaz, döner (ölçüldü: yetim pw-cli 1 saat %22 çekirdek). Ebeveyn ani ölürse
(SIGKILL, çökme) kapanış kodu çalışmaz → çekirdek düzeyinde bağ gerekir: PR_SET_PDEATHSIG.

TUZAK (U64 ayrıca test eder): PDEATHSIG ebeveyn SÜRECİ değil, fork eden İŞ PARÇACIĞI ölünce tetiklenir. Analizör ve
pw-cli kısa ömürlü HTTP istek iş parçacıklarından doğar → doğrudan orada Popen + PDEATHSIG = istek biter bitmez çocuk
ölür. Çözüm: tüm doğurmalar süreç ömrü boyunca yaşayan TEK bir "doğurucu" iş parçacığında yapılır.
PDEATHSIG `setpriv --pdeathsig` (util-linux) ile verilir → preexec_fn (iş parçacıklı süreçte güvensiz) gerekmez."""
from __future__ import annotations

import os
import queue
import shutil
import subprocess
import threading

_SETPRIV = shutil.which("setpriv")
_q: "queue.Queue" = queue.Queue()
_lock = threading.Lock()
_thread = None


def _run():
    while True:
        cmd, kw, box, ev = _q.get()
        try:
            box["p"] = subprocess.Popen(cmd, **kw)
        except BaseException as e:                      # hata çağırana taşınır
            box["e"] = e
        ev.set()


def _ensure():
    global _thread
    with _lock:
        if _thread is None or not _thread.is_alive():
            _thread = threading.Thread(target=_run, name="bta-spawner", daemon=True)
            _thread.start()


def wrap(cmd: list) -> list:
    """Komutu `setpriv --pdeathsig TERM --` ile sarar (setpriv yoksa olduğu gibi)."""
    return [_SETPRIV, "--pdeathsig", "TERM", "--", *cmd] if _SETPRIV else list(cmd)


def spawn(cmd: list, **kw) -> subprocess.Popen:
    """subprocess.Popen ile aynı; fark: ebeveyn süreç ölünce çocuk SIGTERM alır (iş parçacığından bağımsız)."""
    if threading.current_thread() is _thread:           # doğurucunun içinden çağrı (olmamalı) → kilitlenme yok
        return subprocess.Popen(wrap(cmd), **kw)
    _ensure()
    box, ev = {}, threading.Event()
    _q.put((wrap(cmd), kw, box, ev))
    ev.wait()
    if "e" in box:
        raise box["e"]
    return box["p"]


def has_deathsig() -> bool:
    """Bu sistemde ebeveynle ölme bağı kurulabiliyor mu."""
    return bool(_SETPRIV) and os.name == "posix"
