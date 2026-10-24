"""D3.2 — Yerel müzik türü + enstrüman sınıflayıcısı (infrastructure; YAMNet ONNX, Apache-2.0).

Model depoda DEĞİL: `~/.local/share/bt-audio-hifi/models/` (XDG data). Dosyalar `models.lock.json` sha256'sıyla
doğrulanmadan YÜKLENMEZ (tedarik zinciri). Ses verisi makineden çıkmaz. Model yoksa `available=False` → sistem
öznitelik katmanıyla (features.py) çalışır."""
from __future__ import annotations

import csv
import hashlib
import json
import os

import numpy as np
from scipy import signal as _sig

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK = os.path.join(REPO, "models.lock.json")

# AudioSet sınıf adı → makro tür (yamnet_class_map.csv adlarıyla birebir)
MACRO = {
    "elektronik": ["Electronic music", "House music", "Techno", "Dubstep", "Drum and bass", "Electronica",
                   "Electronic dance music", "Trance music", "Ambient music", "Disco"],
    "hiphop": ["Hip hop music", "Rhythm and blues"],
    "rock": ["Rock music", "Heavy metal", "Punk rock", "Grunge", "Progressive rock", "Rock and roll", "Psychedelic rock"],
    "pop": ["Pop music", "Dance music"],
    "klasik": ["Classical music", "Opera", "Orchestra"],
    "caz_akustik": ["Jazz", "Blues", "Folk music", "Country", "Bluegrass", "Swing music", "Soul music"],
    "konuşma": ["Speech", "Narration, monologue", "Conversation"],
}
INSTRUMENTS = ["Bass guitar", "Electric guitar", "Acoustic guitar", "Drum kit", "Drum", "Synthesizer", "Piano",
               "Violin, fiddle", "Orchestra", "Singing", "Rapping",
               "Brass instrument", "Saxophone", "Bass drum", "Electronic organ", "Choir"]


def model_dir() -> str:
    """Model dizini: $XDG_DATA_HOME/bt-audio-hifi/models (depoda DEĞİL)."""
    return os.path.join(os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share"), "bt-audio-hifi", "models")


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(directory: str | None = None) -> dict:
    """Model dosyalarını models.lock.json sha256'larıyla karşılaştırır: {dosya: ok|missing|sha-mismatch}."""
    d = directory or model_dir()
    lock = json.load(open(LOCK))["yamnet"]["files"]
    out = {}
    for fn, meta in lock.items():
        p = os.path.join(d, fn)
        out[fn] = "missing" if not os.path.exists(p) else ("ok" if _sha(p) == meta["sha256"] else "sha-mismatch")
    return out


def fetch(directory: str | None = None) -> dict:
    """Kullanıcı komutu (`bta model fetch`): indir → sha256 doğrula → yanlışsa SİL (zehirli dosya kalmaz)."""
    import urllib.request
    d = directory or model_dir()
    os.makedirs(d, exist_ok=True)
    lock = json.load(open(LOCK))["yamnet"]["files"]
    for fn, meta in lock.items():
        p = os.path.join(d, fn)
        if os.path.exists(p) and _sha(p) == meta["sha256"]:
            continue
        tmp = p + ".part"
        urllib.request.urlretrieve(meta["url"], tmp)
        if _sha(tmp) != meta["sha256"]:
            os.remove(tmp)
            raise RuntimeError(f"{fn}: sha256 uyuşmuyor — reddedildi")
        os.replace(tmp, p)
    return verify(d)


def macro_scores(scores: np.ndarray, names: list) -> dict:
    """521 AudioSet skoru → makro tür skorları + müzik skoru + ilk 5 enstrüman."""
    idx = {n: i for i, n in enumerate(names)}
    raw = {k: float(max((scores[idx[n]] for n in v if n in idx), default=0.0)) for k, v in MACRO.items()}
    music = float(scores[idx["Music"]]) if "Music" in idx else 0.0
    return {"macro": raw, "music": music,
            "instruments": sorted(((n, round(float(scores[idx[n]]), 3)) for n in INSTRUMENTS if n in idx),
                                  key=lambda x: -x[1])[:5]}


class YamnetClassifier:
    """YAMNet ONNX çalıştırıcı (tek iş parçacığı); model doğrulanamazsa available=False, reason dolu."""
    def __init__(self, directory: str | None = None):
        self.dir = directory or model_dir()
        self.session, self.names, self.reason = None, None, None
        st = verify(self.dir)
        if any(v != "ok" for v in st.values()):
            self.reason = f"model yok/doğrulanamadı: {st} — `bta model fetch`"
            return
        try:
            import onnxruntime as ort
            ort.set_default_logger_severity(3)
            so = ort.SessionOptions()
            so.intra_op_num_threads = 1                   # kaynak disiplini: tek çekirdek
            self.session = ort.InferenceSession(os.path.join(self.dir, "yamnet.onnx"), so, providers=["CPUExecutionProvider"])
            self.names = [r[2] for r in csv.reader(open(os.path.join(self.dir, "yamnet_class_map.csv")))][1:]
        except Exception as e:                            # onnxruntime yok vb. → öznitelik katmanı
            self.session, self.reason = None, f"onnxruntime: {e}"[:200]

    @property
    def available(self):
        """Oturum hazır mı (model doğrulandı + onnxruntime yüklendi)."""
        return self.session is not None

    def predict(self, audio48k_mono: np.ndarray) -> dict | None:
        """48 kHz mono ses (≥1 sn) → 16 kHz'e indir → çerçeve skorlarının ortalaması → macro_scores; yetersizse None."""
        if not self.available or len(audio48k_mono) < 48000:
            return None
        x = _sig.resample_poly(np.asarray(audio48k_mono, np.float64), 1, 3).astype(np.float32)   # 48k → 16k
        scores = self.session.run(None, {"waveform": x})[0].mean(axis=0)
        return macro_scores(scores, self.names)
