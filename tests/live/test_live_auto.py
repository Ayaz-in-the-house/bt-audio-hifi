"""T-L40 / T-L42: otomasyon motoru GERÇEK ses akışında (kulaklığa giden, EQ öncesi dokunuş) — ama kararları SAHTE
uygulayıcıya gider: kullanıcının duyduğu ses DEĞİŞMEZ (K10: dinlerken sesine karışma).

T-L40  Kaynak maliyeti: motor + 2 yakalama süreci + sınıflayıcı, 30 sn, tek çekirdeğin yüzdesi olarak.
       Beklenen: motorun kendi payı (Python süreci: tick + YAMNet + halka tampon) ≤ %3, pw-record çocuğu ≤ %2.
       İlk ölçüm (tam analizör, 2 dokunuş, kare başına FFT + true-peak) %15 idi → hafif mod (U62) ile düzeltildi.
       Sebep: kulaklık 7/24 açık bir arka plan hizmeti; "kimse bakmıyorken bedel ödenmez" (analizör C4 ilkesi) otomatik
       modda bilerek esnetiliyor → bedel ölçülmeli ve sınırlı olmalı. Sınıflama medyanı ≤ 50 ms / 2 sn ses.
T-L42  Ürün katmanı: ses çalıyorsa (K11: dijital sessizlik değilse) motor en az bir tür tahmini üretir, tonal denge
       (bölge fazlası) hesaplanır ve ADL/APC kararları uygulayıcıya ulaşır; ses yoksa durum "sessizlik" olur.
       Hangi türün çıktığı RAPORLANIR (kullanıcının o an ne dinlediğini testi yazan bilemez) — doğruluk iddiası değil."""
import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from btaudio import analyzer, autoengine, classifier, consoleserver  # noqa: E402

TCK = os.sysconf("SC_CLK_TCK")


def cpu_s(pid):
    try:
        f = open(f"/proc/{pid}/stat").read().rsplit(")", 1)[1].split()
        return (int(f[11]) + int(f[12])) / TCK
    except OSError:
        return None


class Rec:
    def __init__(self):
        self.n = 0

    def apply_payload(self, p):
        self.n += 1


class T40_AutoLive(unittest.TestCase):
    def test_l40_l42_engine_on_real_stream(self):
        tmp = tempfile.mkdtemp(prefix="bta-auto-live-")
        rec = Rec()
        sess = consoleserver.Session(rec, lambda st: None, profiles_dir=os.path.join(tmp, "p"))
        an = analyzer.Analyzer(analyzer.console_taps())
        clf = classifier.YamnetClassifier()
        self.assertTrue(clf.available, clf.reason)
        eng = autoengine.AutoEngine(sess, an, classifier=clf, state_path=os.path.join(tmp, "auto.json"))
        try:
            eng.set_mode("both")
            t0 = time.time()
            while time.time() - t0 < 6 and not an.pids():
                time.sleep(0.2)
            pids = an.pids()
            self.assertEqual(len(pids), 1, "otomasyon yalnız EQ-öncesi dokunuşu hafif modda açmalı (U62)")
            time.sleep(4)                                      # ısınma (model, ilk FFT penceresi)
            c0 = {p: cpu_s(p) for p in pids}
            s0, w0 = os.times(), time.time()
            states = []
            while time.time() - w0 < 30:
                time.sleep(1)
                states.append(eng.state)
            s1, w1 = os.times(), time.time()
            c1 = {p: cpu_s(p) for p in pids}
            wall = w1 - w0
            own = ((s1.user - s0.user) + (s1.system - s0.system)) / wall * 100
            kids = sum((c1[p] - c0[p]) for p in pids if c0[p] is not None and c1[p] is not None) / wall * 100
            st = eng.status()
            med = st["classifier"]["ms"]
            report = {"own_cpu_pct": round(own, 2), "capture_cpu_pct": round(kids, 2), "classify_median_ms": med,
                      "states": {k: states.count(k) for k in set(states)}, "genre": st["genre"],
                      "scores": st["scores"], "instruments": st["instruments"], "character": st["character"],
                      "excess": st["excess"], "level_db": st["level_db"], "offsets": st["offsets"],
                      "apc_log": st["log"], "applied_payloads": rec.n, "errors": st["errors"]}
            os.makedirs(os.path.join(os.path.dirname(__file__), "..", "..", "analysis", "auto"), exist_ok=True)
            with open(os.path.join(os.path.dirname(__file__), "..", "..", "analysis", "auto",
                                   time.strftime("live-%Y%m%d-%H%M%S.json")), "w") as f:
                json.dump(report, f, indent=1, ensure_ascii=False)
            print("\nT-L40/42:", json.dumps(report, ensure_ascii=False))
            self.assertEqual(st["errors"], [])
            # T-L40
            self.assertLessEqual(own, 3.0, report)
            self.assertLessEqual(kids, 2.0, report)
            # T-L42
            if states.count("dinliyor") >= 10:
                self.assertIsNotNone(med)
                self.assertLessEqual(med, 50.0, report)
                self.assertTrue(st["scores"], "ses varken tür tahmini yok")
                self.assertIsNotNone(st["excess"])
                self.assertGreater(rec.n, 0, "ses varken hiçbir karar uygulanmadı")
            else:
                self.assertIn("sessizlik", states)             # K11: ses yok → karar yok
                self.assertEqual(rec.n, 0)
        finally:
            eng.close()
            an.close()
        time.sleep(0.5)
        self.assertFalse(any(os.path.exists(f"/proc/{p}") and open(f"/proc/{p}/stat").read().split()[2] != "Z"
                             for p in pids), "yakalama süreci kapanmadı")


class T41_AutoNoClicks(unittest.TestCase):
    def test_l41_adl_update_pattern_is_click_free(self):
        """T-L41: otomasyonun GERÇEK güncelleme deseni (0,5 dB kuantalı adımlar, 1,5 sn A/B geçiş — autoengine) null
        sink'te. Beklenen: doğrudan güncellemenin −46 dBFS tıkı YOK → başlangıç artefaktı dışında en büyük artık
        ≤ −70 dBFS (duyulmaz; R43 artığı −68…−88) ve olay sayısı ≤ güncelleme/3; son seviye model ±0,05 dB.
        Not (2026-09-28): ilk sürüm T-L39'un "≤1 olay" ölçütünü kopyalamıştı (5 güncelleme için); 6 güncellemede 2 olay
        (−84/−88 dBFS, ikisi de B yüklemesinde) ölçütü düşürdü. −38,3 dBFS tepe = kırpılmış kaydın İLK penceresi
        (süzgeç başlangıç tepkisi, max_time_s ile kanıtlı) → tık değil."""
        from btaudio import zipperverify
        ab = zipperverify.run_ab(1.5, seconds=11.0, updates="adl")
        print("\nT-L41:", {k: ab[k] for k in ("event_times_s", "top6", "max_time_s", "residual_after_start_dbfs",
                                               "final_level_db", "model_db") if k in ab})
        ev = [t for t in ab["event_times_s"] if t > (ab["play_start_s"] or 0) + 0.3]
        self.assertLessEqual(ab["max_time_s"], (ab["play_start_s"] or 0) + 0.3, "en büyük artık başlangıç artefaktı değil")
        self.assertLessEqual(ab["residual_after_start_dbfs"], -70.0, ab)
        self.assertLessEqual(len(ev), max(1, ab["updates"] // 3), ab)
        self.assertAlmostEqual(ab["final_level_db"], ab["model_db"], delta=0.05)
        self.assertEqual(ab["errors"], [])


if __name__ == "__main__":
    unittest.main()
