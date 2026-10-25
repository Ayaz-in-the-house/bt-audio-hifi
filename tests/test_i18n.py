"""U82–U86: arayüz dili (EN/TR) — devir App-i18n-02 test noktaları I1, I2, I4 (durağan), I6, I7 + sözlük yolu güvenliği.

Neden: kullanıcı "application dillerini de ingilizce de yapsak" dedi; GitHub'dan kuran yabancı kullanıcı arayüzü İngilizce
görmeli, Türkçe hiçbir yerde bozulmamalı. Eksik çeviri sessizce anahtar adı gösterir (I1); çevrilmeyen kalıntı gözden
kaçar (I2); sunucu metinleri çevrilmezse uyarılar Türkçe kalır (I7); hazır tarz kimlikleri API sözleşmesidir (I6)."""
import ast
import http.client
import json
import os
import re
import sys
import tempfile
import unittest
from html.parser import HTMLParser

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from btaudio import console, consoleserver  # noqa: E402

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
PAGES = [os.path.join(REPO, "tools", n) for n in ("console.html", "admin.html")]
TR_CH = "çğıöşüÇĞİÖŞÜâÂ"
TR_RE = re.compile(f"[{TR_CH}]")
ATTRS = ("title", "aria-label", "placeholder", "alt")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr", "use",
        "path", "circle", "rect"}
# dile bağlı olmayan görünür belirteçler (kanal adı, codec, düğme harfleri, birim)
NEUTRAL = {"L", "R", "AAC", "SBC", "X = A", "X = B", "▶ A", "▶ B", "▶ X", "TR", "EN", "—", "RMS —", "TP —",
           "Dil / Language", "Türkçe", "English"}   # dil düğmesi: her dil kendi adıyla
# betikte Türkçe harfli ama GÖRÜNMEYEN makine değerleri (API alanları/kimlikler, yerel ayar adları)
MACHINE = {"eşit", "varlık", "konuşma", "Tümü", "tasarım", "dinliyor", "sessizlik", "askıda", "kapalı",
           "Özel"}


def load(lang):
    with open(os.path.join(REPO, "tools", "i18n", f"{lang}.json"), encoding="utf-8") as f:
        return json.load(f)


def src(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


class Page(HTMLParser):
    """Durağan HTML: data-i18n dışındaki görünür metin, çevrilmemiş öznitelikler, ve data-i18n öğelerinin ham içeriği."""

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.text, self.lines = text, text.split("\n")
        self.stack, self.loose, self.bad_attrs, self.items = [], [], [], []
        self.feed(text)

    def _off(self):
        ln, col = self.getpos()
        return sum(len(x) + 1 for x in self.lines[:ln - 1]) + col

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for at in ATTRS:
            v = a.get(at)
            if v and re.search(r"[A-Za-z" + TR_CH + "]", v) and v not in NEUTRAL:
                key = a.get("data-i18n-" + at)
                if not key:
                    self.bad_attrs.append((tag, at, v))
                else:
                    self.items.append(("attr", key, v))
        if tag in VOID:
            return
        start = self._off() + len(self.get_starttag_text())
        self.stack.append({"tag": tag, "key": a.get("data-i18n"), "html": a.get("data-i18n-html"), "start": start})

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        while self.stack:
            e = self.stack.pop()
            if e["tag"] == tag:
                break
        else:
            return
        inner = self.text[e["start"]:self._off()]
        if e["key"]:
            self.items.append(("text", e["key"], inner))
        if e["html"]:
            self.items.append(("html", e["html"], inner))

    def handle_data(self, data):
        s = data.strip()
        if not s or not re.search(r"[A-Za-z" + TR_CH + "]", s):
            return
        tags = [e["tag"] for e in self.stack]
        if {"script", "style"} & set(tags) or "kbd" in tags[-1:] or s in NEUTRAL:
            return
        if any(e["key"] or e["html"] for e in self.stack):
            return
        self.loose.append(s)


def scripts(text):
    """Satır içi betikler, yorumlar çıkarılmış (// satır sonu ve /* */)."""
    out = []
    for body in re.findall(r"<script[^>]*>(.*?)</script>", text, re.S):
        body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
        body = re.sub(r"(?m)(^|[\s;{}),])//[^\n]*", r"\1", body)
        out.append(body)
    return "\n".join(out)


class TestU82Dictionaries(unittest.TestCase):
    """U82 (I1): iki sözlük aynı anahtar kümesi; boş değer yok; yer tutucular eş; EN'de Türkçe harf yok; kullanılan her anahtar var."""

    def test_u82_same_keys_and_placeholders(self):
        en, tr = load("en"), load("tr")
        self.assertEqual(sorted(set(en) ^ set(tr)), [], "yalnız bir dilde olan anahtar")
        for k in en:
            self.assertTrue(en[k].strip() and tr[k].strip(), k)
            self.assertEqual(sorted(set(re.findall(r"\{(\w+)\}", en[k]))), sorted(set(re.findall(r"\{(\w+)\}", tr[k]))), k)
            self.assertIsNone(TR_RE.search(en[k]), f"EN değerinde Türkçe harf: {k} = {en[k]!r}")

    def test_u82_every_used_key_exists(self):
        en = load("en")
        for p in PAGES:
            text = src(p)
            used = set(re.findall(r'data-i18n(?:-html|-title|-aria-label|-placeholder|-alt)?="([^"]+)"', text))
            used |= set(re.findall(r'\btx\("([^"]+)"\s*[,)]', scripts(text)))   # "önek." + değişken anahtarlar hariç
            self.assertEqual(sorted(used - set(en)), [], os.path.basename(p))

    def test_u82_negative_control(self):
        """Sözlük karşılaştırıcısı gerçekten fark yakalar (kendi kendine yeşil olmasın)."""
        en, tr = load("en"), dict(load("tr"))
        tr.pop(next(iter(tr)))
        self.assertNotEqual(set(en), set(tr))


class TestU83Pages(unittest.TestCase):
    """U83 (I2 + I4 durağan): HTML'de data-i18n dışında görünür metin yok; betikte görünür Türkçe dize yok; TR sözlüğü
    sayfanın bugünkü Türkçe metniyle BAYT BAYT aynı (TR görünümü değişmez)."""

    def test_u83_no_loose_visible_text(self):
        for p in PAGES:
            pg = Page(src(p))
            self.assertEqual(pg.loose, [], f"{os.path.basename(p)}: data-i18n dışında görünür metin")
            self.assertEqual(pg.bad_attrs, [], f"{os.path.basename(p)}: çevrilmemiş öznitelik")

    def test_u83_no_turkish_literals_in_script(self):
        for p in PAGES:
            words = set(re.findall(rf"[\w{TR_CH}]*[{TR_CH}][\w{TR_CH}]*", scripts(src(p))))
            self.assertEqual(sorted(words - MACHINE), [], f"{os.path.basename(p)}: betikte çevrilmemiş Türkçe")

    def test_u83_tr_dictionary_matches_inline_turkish(self):
        tr = load("tr")
        for p in PAGES:
            items = Page(src(p)).items
            self.assertGreater(len(items), 20, p)
            for kind, key, inner in items:
                self.assertIn(key, tr, key)
                if kind == "text":
                    self.assertNotIn("<", inner, f"data-i18n öğesinde biçimleme var (data-i18n-html olmalı): {key}")
                import html as _h
                want = _h.unescape(inner) if kind != "html" else inner
                self.assertEqual(tr[key], want, f"{os.path.basename(p)}: TR metni değişmiş → {key}")

    def test_u83_negative_control(self):
        pg = Page('<div><span>Kaydet</span><b data-i18n="x">Tamam</b><i title="Sil"></i></div>')
        self.assertEqual(pg.loose, ["Kaydet"])
        self.assertEqual(len(pg.bad_attrs), 1)
        self.assertEqual(set(re.findall(rf"[\w{TR_CH}]*[{TR_CH}][\w{TR_CH}]*", scripts('<script>x("Güç") // açıklama\n</script>'))), {"Güç"})


IDS = ["notr", "hifi_uzay", "harman_bas", "harman_oe", "hafif_bas", "zengin_bas", "derin_sub", "vurucu_bas", "guclu_bas",
       "ee_bass_boosted", "elektronik", "dans", "rock", "pop", "hiphop", "klasik", "akustik_caz", "konser", "parti",
       "v_sekli", "bas_tiz", "sicak", "parlak", "vokal", "ee_boosted", "konusma", "gece", "film", "oyun", "sahne", "studyo",
       "dogal_crossfeed"]


class TestU84Presets(unittest.TestCase):
    """U84 (I6): her hazır tarzın EN adı/açıklaması/kaynağı var; kimlik, grup, tür ve TR alanları DEĞİŞMEZ."""

    def test_u84_ids_and_turkish_fields_unchanged(self):
        self.assertEqual(list(console.PRESETS), IDS)
        self.assertEqual(console.PRESETS["notr"]["label"], "Nötr")
        self.assertEqual(console.PRESETS["hifi_uzay"]["label"], "Hi-fi dengeli + uzay")
        self.assertEqual(console.CATEGORIES, ["Referans", "Bas", "Tür", "Karakter", "Kullanım", "Uzay"])
        self.assertEqual(sorted(console.KINDS), ["hedef", "kaynak", "standart", "tasarım"])

    def test_u84_every_preset_has_english(self):
        cat = console.preset_catalog()
        for pid in IDS:
            for f in ("label", "desc", "source"):
                v = cat[pid].get(f + "_en")
                self.assertTrue(v and v.strip(), f"{pid}.{f}_en yok")
                self.assertIsNone(TR_RE.search(v), f"{pid}.{f}_en Türkçe harf: {v!r}")
            self.assertNotEqual(cat[pid]["label_en"], "", pid)
            for f in ("label", "desc", "source", "group", "kind"):
                self.assertEqual(cat[pid][f], console.PRESETS[pid][f], f"{pid}.{f} değişmiş")
        for k, p in console.BS2B_PRESETS.items():
            self.assertTrue(p.get("label_en"), k)
            self.assertIsNone(TR_RE.search(p["label_en"]), k)

    def test_u84_groups_kinds_have_dictionary_labels(self):
        en, tr = load("en"), load("tr")
        for g in console.CATEGORIES:
            self.assertIn("group." + g, en, g)
            self.assertEqual(tr["group." + g], g, "TR grup adı görünür metindir, değişmemeli")
        for k in console.KINDS:
            self.assertIn("kind." + k, en, k)

    def test_u84_negative_control(self):
        cat = dict(console.preset_catalog()["rock"])
        cat.pop("label_en")
        self.assertIsNone(cat.get("label_en"))


def _states():
    st = console.default_state()

    def mk(*bands):
        s = console.default_state()
        for i, (t, f, g, q) in enumerate(bands):
            s["bands"][i] = {"enabled": True, "type": t, "freq": f, "gain": g, "q": q}
        return console.sanitize(s)
    return st, mk


def raise_literals():
    """Sunucuya ulaşan modüllerde raise edilen sabit/f-string iletiler (yer tutucu → '7')."""
    out = []
    for mod in ("consoleserver", "profiles", "abxsession", "autoengine", "console", "classifier", "loudness", "abx"):
        tree = ast.parse(src(os.path.join(REPO, "btaudio", mod + ".py")))
        for n in ast.walk(tree):
            if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call) and n.exc.args:
                a = n.exc.args[0]
                if isinstance(a, ast.Constant) and isinstance(a.value, str):
                    out.append((mod, a.value, n.exc))
                elif isinstance(a, ast.JoinedStr):
                    out.append((mod, "".join(v.value if isinstance(v, ast.Constant) else "7" for v in a.values), n.exc))
    return out


class TestU85ServerTexts(unittest.TestCase):
    """U85 (I7): sunucunun görünen metinleri iki dilde — uyarılar `text_en`, hatalar `error_en`, sürüm farkı `diff_en`,
    sınıflayıcı nedeni `reason_en`. Makine alanları (`code`, `level`, `error`) değişmez."""

    def test_u85_warnings_have_english(self):
        _, mk = _states()
        cases = [mk(("lowshelf", 60, 12, 0.7), ("bell", 45, 6, 1.0)), mk(("lowshelf", 15, 12, 0.7)),
                 mk(("highshelf", 15000, 8, 0.7))]
        seen = set()
        for s in cases:
            for w in console.protection_warnings(s, codec="aac"):
                seen.add(w["code"])
                self.assertTrue(TR_RE.search(w["text"]), "TR metni kalmalı")
                self.assertTrue(w.get("text_en"), w["code"])
                self.assertIsNone(TR_RE.search(w["text_en"]), w["text_en"])
                self.assertRegex(w["text_en"], r"[+-]\d+\.\d dB", "EN ondalık nokta")
        self.assertEqual(seen, {"bass_high", "sub_infra", "hf_aac"})

    def test_u85_every_raised_message_translates(self):
        lits = raise_literals()
        self.assertGreater(len(lits), 30)
        for mod, msg, call in lits:
            en = consoleserver.error_en(msg)
            self.assertNotEqual(en, msg, f"{mod}: çevirisi yok → {msg!r}")
            self.assertIsNone(TR_RE.search(en), f"{mod}: {msg!r} → {en!r}")
        for msg in ("yasak host", "application/json gerekli", "istek çok büyük (> 256 KB)", "profil yok", "yok",
                    "geçersiz JSON: JSON nesnesi bekleniyor", "bulunamadı / eksik alan: 'sürüm 3'", "sınıflayıcı yok",
                    "model yok/doğrulanamadı: {'a': 'missing'} — `bta model fetch`"):
            en = consoleserver.error_en(msg)
            self.assertNotEqual(en, msg, msg)
            self.assertIsNone(TR_RE.search(en), en)

    def test_u85_negative_control(self):
        self.assertEqual(consoleserver.error_en("tamamen bilinmeyen ileti ğ"), "tamamen bilinmeyen ileti ğ")

    def test_u85_http_errors_and_timeline_carry_english(self):
        class Fake:
            def apply_payload(self, p):
                pass
        sess = consoleserver.Session(Fake(), on_commit=lambda s: {}, profiles_dir=tempfile.mkdtemp())
        httpd, url, stop = consoleserver.serve(sess)
        try:
            port = httpd.server_address[1]

            def req(method, path, body=None, headers=None):
                c = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
                c.request(method, path, body=body, headers=headers or {})
                r = c.getresponse()
                out = r.status, json.loads(r.read() or b"{}")
                c.close()
                return out
            st, b = req("GET", "/api/nope")
            self.assertEqual((st, b["error"], b["error_en"]), (404, "yok", "Not found"))
            st, b = req("GET", "/api/state", headers={"Host": "evil.example"})
            self.assertEqual(st, 403)
            self.assertIsNone(TR_RE.search(b["error_en"]))
            st, b = req("POST", "/api/profile/save", body=json.dumps({"name": "  "}), headers={"Content-Type": "application/json"})
            self.assertEqual(st, 400)
            self.assertTrue(TR_RE.search(b["error"]) or b["error"] != b["error_en"])
            self.assertIsNone(TR_RE.search(b["error_en"]), b)
            # sürüm farkı satırları
            st, v = req("POST", "/api/state", body=json.dumps({"state": console.apply_preset(console.default_state(), "rock"), "seal": True}),
                        headers={"Content-Type": "application/json"})
            self.assertEqual(st, 200)
            st, v = req("POST", "/api/state", body=json.dumps({"state": console.apply_preset(console.default_state(), "pop"), "seal": True}),
                        headers={"Content-Type": "application/json"})
            tl = sess.admin_timeline(sess.active["id"])
            for x in tl["versions"]:
                self.assertEqual(len(x["diff"]), len(x["diff_en"]))
                for line in x["diff_en"]:
                    self.assertIsNone(TR_RE.search(line), line)
            self.assertTrue(any("band" in ln for x in tl["versions"] for ln in x["diff_en"]))
        finally:
            stop.set()


class TestU86I18nRoutes(unittest.TestCase):
    """U86: sözlük + çalışma zamanı YALNIZ tam yol izin listesinden sunulur (dosya sistemi yolu yok, yol geçişi yok)."""

    @classmethod
    def setUpClass(cls):
        class Fake:
            def apply_payload(self, p):
                pass
        cls.sess = consoleserver.Session(Fake(), on_commit=lambda s: {}, profiles_dir=tempfile.mkdtemp())
        cls.httpd, _, cls.stop = consoleserver.serve(cls.sess)
        cls.port = cls.httpd.server_address[1]

    @classmethod
    def tearDownClass(cls):
        cls.stop.set()

    def get(self, path, host=None):
        c = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        c.request("GET", path, headers={"Host": host} if host else {})
        r = c.getresponse()
        out = r.status, r.getheader("Content-Type") or "", r.getheader("X-Content-Type-Options"), r.read()
        c.close()
        return out

    def test_u86_allowlisted_files_served(self):
        for lang in ("en", "tr"):
            st, ct, nos, body = self.get(f"/i18n/{lang}.json")
            self.assertEqual((st, nos), (200, "nosniff"))
            self.assertTrue(ct.startswith("application/json"), ct)
            self.assertEqual(json.loads(body), load(lang))
        st, ct, nos, body = self.get("/i18n/i18n.js?v=1")
        self.assertEqual(st, 200)
        self.assertTrue(ct.startswith("text/javascript"), ct)
        self.assertIn(b"I18N", body)

    def test_u86_nothing_else_under_i18n(self):
        for p in ("/i18n/", "/i18n/de.json", "/i18n/../btaudio/console.py", "/i18n/%2e%2e/README.md", "/i18n//etc/passwd",
                  "/tools/i18n/en.json", "/i18n/en.json/", "/i18n/EN.json"):
            self.assertEqual(self.get(p)[0], 404, p)
        self.assertEqual(self.get("/i18n/en.json", host="evil.example")[0], 403)


if __name__ == "__main__":
    unittest.main()
