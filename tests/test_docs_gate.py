"""U67: belge güncelliği KAPISI — "belgeleri güncellemeyi unutma" bir hatırlatma değil, kırmızı bir testtir.

Neden (kullanıcı, 2026-09-27): "docs güncelliği çok kritik bir disiplin süreci". Ölçülen olay: TEST-PLAN'da aynı
kimlik iki ayrı teste verilmişti (T-L30…34/T-L40: terk edilen EasyEffects yolu ↔ bugünkü konsol testleri; T-U05:
plan ↔ kod), 20+ test kimliği planda hiç yoktu, ARCHITECTURE.md kaldırılan ramp×mult grafını anlatıyordu.

1. btaudio/ altındaki HER modül `tools/gen-docs.py` katman haritasında (yeni modül = belge zorunlu).
2. docs/modules/*.md kaynaktan üretilir; kaynak değişip belge üretilmediyse kırmızı.
3. Testlerde geçen her test kimliği TEST-PLAN'de tanımlı; bir kimlik planda iki kez TANIMLANMAZ.
4. Katman belgeleri zorunlu bölümleri taşır (durum · değişkenler · gri alanlar · testler · nasıl ölçülür).
5. FEATURES.md'deki test kimlikleri gerçek; belge hub'ındaki göreli bağlantılar kırık değil."""
import glob
import importlib.util
import os
import re
import sys
import unittest

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
ID = r"(?:U\d{2,3}|T-U\d{2}|T-L\d{2}|T-H\d{2})"


def gen():
    spec = importlib.util.spec_from_file_location("gen_docs", os.path.join(REPO, "tools", "gen-docs.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def expand(text):
    """'U31–U35' / 'U31-U35' aralıklarını açar."""
    out = set()
    for a, b in re.findall(r"\bU(\d{2,3})\s*[–-]\s*U(\d{2,3})\b", text):
        out |= {f"U{i:02d}" for i in range(int(a), int(b) + 1)}
    return out | set(re.findall(r"\b" + ID + r"\b", text))


def plan_rows():
    rows = []
    for ln in open(os.path.join(REPO, "docs", "TEST-PLAN.md")):
        m = re.match(r"^\|\s*(" + ID + r"(?:\s*[–-]\s*" + ID + r")?)\s*\|", ln)
        if m:
            rows.append(m.group(1))
    return rows


class TestDocsGate(unittest.TestCase):
    def test_u67_every_module_has_a_layer(self):
        mods = sorted(os.path.basename(p)[:-3] for p in glob.glob(os.path.join(REPO, "btaudio", "*.py"))
                      if not p.endswith("__init__.py"))
        missing = [m for m in mods if m not in gen().LAYERS]
        self.assertEqual(missing, [], "katman haritasında olmayan modül (tools/gen-docs.py LAYERS)")

    def test_u67_module_docs_are_generated_from_current_source(self):
        stale = gen().check()
        self.assertEqual(stale, [], "bayat modül belgesi → `python3 tools/gen-docs.py` çalıştır")

    def test_u67_every_test_id_is_planned_exactly_once(self):
        used = set()
        for p in glob.glob(os.path.join(REPO, "tests", "**", "test_*.py"), recursive=True):
            if os.path.basename(p) == "test_docs_gate.py":
                continue
            used |= expand(open(p).read())
        rows = plan_rows()
        planned = set()
        for r in rows:
            planned |= expand(r)
        self.assertEqual(sorted(used - planned), [], "testte var, TEST-PLAN'de yok")
        single = [r for r in rows if not re.search(r"[–-]\s*U", r)]
        dup = sorted({r for r in single if single.count(r) > 1})
        self.assertEqual(dup, [], "aynı kimlik TEST-PLAN'de birden çok kez tanımlı")

    def test_u67_layer_docs_have_required_sections(self):
        docs = sorted(glob.glob(os.path.join(REPO, "docs", "layers", "L*.md")))
        self.assertGreaterEqual(len(docs), 6)
        for p in docs:
            t = open(p).read()
            for sec in ("## Durum", "## Değişkenler", "## Gri alanlar", "## Testler", "## Nasıl ölçülür"):
                self.assertIn(sec, t, f"{os.path.basename(p)}: '{sec}' bölümü yok")
            self.assertRegex(t, r"Son doğrulama: \d{4}-\d{2}-\d{2}", os.path.basename(p))

    def test_u79_append_only_ledgers_are_not_truncated(self):
        """U79: kayıt defterleri yalnız EKLENİR. Ölçülen olay (14af43c): üç defter tek satırla ezildi
        (findings 78→2, errors 38→1, STATE-LOG 39→2) ve on gün fark edilmedi — kimlik dizisi kopuksa kırmızı."""
        for rel, prefix in (("docs/lessons/errors.md", "E"), ("docs/research/findings.md", "R")):
            ids = [int(n) for n in re.findall(r"^\|\s*" + prefix + r"(\d+)\s*\|", open(os.path.join(REPO, rel)).read(), re.M)]
            self.assertTrue(ids, f"{rel}: kayıt yok")
            missing = sorted(set(range(1, max(ids) + 1)) - set(ids))
            self.assertEqual(missing, [], f"{rel}: kayıp kimlikler (defter ezilmiş olabilir)")
        log = open(os.path.join(REPO, "docs", "STATE-LOG.md")).read()
        self.assertTrue(log.startswith("# Durum günlüğü"), "STATE-LOG.md başlığı yok (defter ezilmiş olabilir)")

    def test_u67_feature_catalog_ids_exist_and_links_resolve(self):
        planned = set()
        for r in plan_rows():
            planned |= expand(r)
        feats = open(os.path.join(REPO, "docs", "FEATURES.md")).read()
        self.assertEqual(sorted(expand(feats) - planned), [], "FEATURES.md'de olmayan test kimliği")
        for doc in [os.path.join(REPO, "README.md")] + glob.glob(os.path.join(REPO, "docs", "**", "*.md"), recursive=True):
            if "/research/upstream/" in doc:
                continue
            for link in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", open(doc).read()):
                if re.match(r"^[a-z]+:", link):
                    continue
                self.assertTrue(os.path.exists(os.path.normpath(os.path.join(os.path.dirname(doc), link))),
                                f"{os.path.relpath(doc, REPO)} → kırık bağlantı {link}")


if __name__ == "__main__":
    unittest.main()
