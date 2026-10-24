"""D1.3 — Arka plan disk yazıcısı (infrastructure).

Sözleşme: istek iş parçacığı yalnız `enqueue_*` çağırır (O(1), kilit + deque, disk YOK). Yazıcı iş parçacığı `delay_s`
boyunca birleştirir: aynı profil dosyası için yalnız EN SON belge yazılır (atomik: geçici dosya + os.replace), aynı
(profil, sürüm) günlük satırı için yalnız en sonuncusu eklenir. Çökmede kayıp üst sınırı ≈ `delay_s`.
`flush()` yazım bitene dek bekler (testler / kapanış); `close()` = flush + dur."""
from __future__ import annotations

import collections
import json
import os
import threading
import time


class Writer:
    """Arka plan yazıcı iş parçacığı: istek yolu yalnız kuyruğa ekler; `delay_s` birleştirme ile profil belgeleri atomik yazılır, günlük satırları eklenir."""
    def __init__(self, journal_dir: str, delay_s: float = 0.3):
        self.dir, self.delay = journal_dir, delay_s
        os.makedirs(journal_dir, exist_ok=True)
        self._lock = threading.Condition()
        self._docs = {}                                   # yol → belge (en sonuncu kazanır)
        self._lines = collections.OrderedDict()           # (pid, anahtar) → satır
        self._busy = False
        self._stop = False
        self.errors = collections.deque(maxlen=20)
        self.writes = 0
        self.last_write = None
        self._t = threading.Thread(target=self._run, name="bta-journal", daemon=True)
        self._t.start()

    # ── istek yolu (disk YOK) ──
    def enqueue_doc(self, path: str, doc: dict):
        """Profil belgesini yazım kuyruğuna koyar (aynı yol için en sonuncusu kazanır)."""
        with self._lock:
            self._docs[path] = doc
            self._lock.notify()

    def enqueue_raw(self, path: str, text: str):
        """Ham metni (ör. .seq sayacı) yazım kuyruğuna koyar."""
        with self._lock:
            self._docs[path] = text
            self._lock.notify()

    def enqueue_lines(self, pid: str, events: list):
        """Günlük olaylarını kuyruğa ekler; güncellenen (aynı sürüm) satır sona taşınır."""
        with self._lock:
            for ev in events:
                key = (pid, ("v", ev["v"]) if "v" in ev else ("p", ev.get("t")))
                self._lines.pop(key, None)                # güncellenen satır SONA taşınır → yeniden oynatma sırası doğru
                self._lines[key] = ev
            if events:
                self._lock.notify()

    def pending(self) -> int:
        """Diske inmemiş öğe sayısı (arayüzdeki 'kaydediliyor…')."""
        with self._lock:
            return len(self._docs) + len(self._lines) + (1 if self._busy else 0)

    def journal_path(self, pid: str) -> str:
        """Profilin günlük dosyası yolu (<dizin>/<id>.jsonl)."""
        return os.path.join(self.dir, pid + ".jsonl")

    # ── yazıcı iş parçacığı ──
    def _run(self):
        while True:
            with self._lock:
                while not (self._docs or self._lines or self._stop):
                    self._lock.wait()
                if self._stop and not (self._docs or self._lines):
                    return
            time.sleep(self.delay)                        # birleştirme penceresi
            with self._lock:
                docs, lines = self._docs, self._lines
                self._docs, self._lines = {}, collections.OrderedDict()
                self._busy = True
            try:
                by_pid = collections.defaultdict(list)
                for (pid, _), ev in lines.items():
                    by_pid[pid].append(ev)
                for pid, evs in by_pid.items():
                    with open(self.journal_path(pid), "a", encoding="utf-8") as f:
                        for ev in evs:
                            f.write(json.dumps(ev, ensure_ascii=False, separators=(",", ":")) + "\n")
                for path, doc in docs.items():
                    tmp = path + ".tmp"
                    with open(tmp, "w", encoding="utf-8") as f:
                        if isinstance(doc, str):
                            f.write(doc)
                        else:
                            json.dump(doc, f, indent=2, ensure_ascii=False)
                    os.replace(tmp, path)
                self.writes += 1
                self.last_write = time.time()
            except OSError as e:                          # disk dolu vb. → görünür hata, veri bellekte kalır
                self.errors.append(f"{time.strftime('%T')} {e}")
                with self._lock:
                    for k, v in docs.items():
                        self._docs.setdefault(k, v)
                    for k, v in lines.items():
                        self._lines.setdefault(k, v)
                time.sleep(1.0)
            finally:
                with self._lock:
                    self._busy = False
                    self._lock.notify_all()

    def flush(self, timeout: float = 10.0) -> bool:
        """Bekleyen tüm yazımlar diske inene dek bekler (en çok timeout sn)."""
        t0 = time.time()
        while self.pending():
            if time.time() - t0 > timeout:
                return False
            time.sleep(0.01)
        return True

    def close(self):
        """flush + iş parçacığını durdur."""
        self.flush()
        with self._lock:
            self._stop = True
            self._lock.notify_all()
        self._t.join(timeout=5)


class NullWriter:
    """Kalıcılık kapalı karşılaştırma (U52: yazıcının istek yoluna eklediği süre ölçülür)."""
    dir = None
    errors = ()
    writes = 0
    last_write = None

    def enqueue_doc(self, path, doc):
        """No-op (testler / yazıcısız mod)."""
        pass

    def enqueue_lines(self, pid, events):
        """No-op."""
        pass

    def enqueue_raw(self, path, text):
        """No-op."""
        pass

    def pending(self):
        """Her zaman 0."""
        return 0

    def journal_path(self, pid):
        """os.devnull."""
        return os.devnull

    def flush(self, timeout=0):
        """Hemen True."""
        return True

    def close(self):
        """No-op."""
        pass
