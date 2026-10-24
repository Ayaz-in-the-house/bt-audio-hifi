#!/usr/bin/env python3
"""Modül belgelerini KAYNAKTAN üretir: docs/modules/<modül>.md + docs/modules/README.md (katman dizini).

Neden üretim, neden el yazısı değil: el yazısı modül belgesi koddan ayrı yaşar ve sessizce bayatlar. Burada tek doğruluk
kaynağı kodun kendisi (docstring + imzalar + içe aktarımlar + testler); U67 (tests/test_docs_gate.py) üretilmiş belge
ile kaynak uyuşmazsa KIRMIZI olur. Açıklamayı değiştirmek için modülün docstring'ini düzenle, bu betiği çalıştır.

Kullanım:  python3 tools/gen-docs.py          # yaz
           python3 tools/gen-docs.py --check  # yalnız bayat olanları listele (çıkış 1)
Çıktı deterministiktir (zaman damgası yok, sıralı) → git diff yalnız gerçek değişikliği gösterir."""
from __future__ import annotations

import ast
import glob
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "btaudio")
OUT = os.path.join(REPO, "docs", "modules")

# Tek doğruluk kaynağı: modül → (katman, bir satırlık rol). Yeni modül eklenince BURAYA eklenmeden U67 geçmez.
# Katmanlar docs/ARCHITECTURE.md ile aynı: domain · application · infrastructure · presentation · ölçüm · cli.
LAYERS = {
    # domain — saf mantık, G/Ç yok
    "dsp": ("domain", "RBJ biquad katsayıları + frekans yanıtı (numpy)"),
    "console": ("domain", "Konsol durumu, sanitize, stereo model, hazır tarzlar, A/B graf üretimi, koruma uyarıları"),
    "profiles": ("domain", "Profil deposu mantığı: kaydet/kilit/çalışma kopyası/çöp/içe-dışa aktar"),
    "history": ("domain", "Sürüm yığını (geri/ileri al) + günlük yeniden oynatma + zaman çizelgesi"),
    "features": ("domain", "Müzik karakteri öznitelikleri (bölge fazlası, karakter etiketleri)"),
    "autoctl": ("domain", "APC (otomatik profil) + ADL (canlı uyarlama) karar mantığı"),
    "presetfit": ("domain", "Grafik EQ presetlerini parametrik EQ'ya uydurma"),
    "state": ("domain", "Snapshot diff, WirePlumber durum ayrıştırma, config manifesti"),
    "codecs": ("domain", "A2DP codec bayt çözücüleri (AAC/SBC)"),
    "tuner": ("domain", "Eski canlı bas ayarlayıcı mantığı (PRD-BTA01 F8 v2)"),
    "bass": ("domain", "Bas analizi: eşleştirme → kulakta yanıt → EQ tasarımı (F8)"),
    "loudness": ("domain", "Eşit-yükseklik (ISO 226) ile kulakta bas yanıtı (F8)"),
    "eqconf": ("domain", "EQ tasarımı → filter-chain config metni"),
    "analysis": ("domain", "Encoder/resampler kalite metrikleri"),
    # application — durum sahibi, zamanlama
    "consoleserver": ("application", "Session (tek durum sahibi) + yerel HTTP API + güvenlik kapıları"),
    "autoengine": ("application", "Otomasyon motoru: analizör → öznitelik/sınıflayıcı → APC/ADL → Session"),
    "abxsession": ("application", "Konsoldaki kör ABX testi: klip (kendi müziğinden), 12 deneme, sonuç, tercih, uygula/iptal"),
    "tunerserver": ("application", "Eski bas ayarlayıcı sunucusu + PwApplier (pw-cli ile canlı yazım)"),
    # infrastructure — yan etkiler (PipeWire, disk, süreç, model)
    "crossfade": ("infrastructure", "Tıksız A/B geçiş sıralayıcı + kalıcı pw-cli oturumu"),
    "analyzer": ("infrastructure", "Canlı analizör: pw-record dokunuşları, 1/6 okt spektrum, metre, SSE, hafif mod"),
    "journal": ("infrastructure", "Arka plan disk yazıcı (ekle-yalnız günlük + atomik profil yazımı)"),
    "classifier": ("infrastructure", "YAMNet ONNX tür/enstrüman sınıflayıcı (sha256 kilitli, yerel)"),
    "paths": ("infrastructure", "XDG kullanıcı verisi yerleşimi + göç"),
    "procs": ("infrastructure", "Alt süreç doğurma: ebeveynle ölen çocuklar (E23)"),
    "tones": ("infrastructure", "Oturma testi tonları (pw-play)"),
    "collect": ("infrastructure", "Canlı sistem durumu toplayıcı (salt-okuma: pactl, bluez, systemd)"),
    "identity": ("infrastructure", "Cihaz kimliği: ad + bilinen MAC kümesi önbelleği, kulaklık seçici, MAC'siz filtre hedefi (U72)"),
    "sbclib": ("infrastructure", "libsbc ctypes sarmalayıcı (SBC-XQ ölçümü)"),
    "resample": ("infrastructure", "Resampler ölçümü + geçici null sink yardımcıları"),
    "link": ("infrastructure", "Bağlantı sağlığı (bitrate düşürme olayları)"),
    "btmon": ("infrastructure", "btmon/RSSI kaydı ayrıştırma (root kaydı kullanıcıdan)"),
    "bench": ("infrastructure", "Encoder benchmark (fdk-aac / libsbc)"),
    # ölçüm — ürün katmanında kanıt üreten doğrulayıcılar (kullanıcının kulaklığına dokunmaz)
    "eqverify": ("ölçüm", "T-L30: smart filter EQ'sunun ürün katmanında doğrulanması"),
    "consoleverify": ("ölçüm", "T-L32: tam stereo konsol grafı null sink'te model ±0,05 dB"),
    "analyzerverify": ("ölçüm", "T-L34: analizörün ürün katmanında doğrulaması"),
    "zipperverify": ("ölçüm", "D0/T-L39/T-L41: canlı güncelleme tık ölçümü (null sink)"),
    "abx": ("ölçüm", "Kör ABX dinleme testi (kullanıcı kararı için)"),
    # cli — giriş noktası
    "cli": ("cli", "`bta` komutları (durum, kurulum, konsol, ölçümler, model)"),
}
ORDER = ["domain", "application", "infrastructure", "ölçüm", "cli"]
LAYER_DOC = {"domain": "../layers/L5-bta-software.md#domain", "application": "../layers/L5-bta-software.md#application",
             "infrastructure": "../layers/L5-bta-software.md#infrastructure", "ölçüm": "../layers/L5-bta-software.md#olcum",
             "cli": "../layers/L5-bta-software.md#cli"}
ID = r"(?:U\d{2,3}|T-U\d{2}|T-L\d{2})"


def _first_para(doc):
    if not doc:
        return ""
    return " ".join(doc.strip().split("\n\n")[0].split())


def _sig(fn):
    a = ast.unparse(fn.args)
    ret = f" -> {ast.unparse(fn.returns)}" if fn.returns is not None else ""
    return f"{fn.name}({a}){ret}"


def _imports(tree):
    internal, external = set(), set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            if n.level == 1:
                if n.module:
                    internal.add(n.module.split(".")[0])
                else:
                    internal |= {a.name for a in n.names}
            elif n.module:
                external.add(n.module.split(".")[0])
        elif isinstance(n, ast.Import):
            external |= {a.name.split(".")[0] for a in n.names}
    return internal, external


STDLIB = set(sys.stdlib_module_names)


def _tests_for(mod):
    hits = []
    for p in sorted(glob.glob(os.path.join(REPO, "tests", "**", "test_*.py"), recursive=True)):
        t = open(p).read()
        imp = re.search(r"^from btaudio import [^\n]*\b" + re.escape(mod) + r"\b|^from btaudio\." + re.escape(mod)
                        + r"\b|^\s*from btaudio import [^\n]*\b" + re.escape(mod) + r"\b", t, re.M)
        if not imp:
            continue
        ids = sorted(set(re.findall(r"\b" + ID + r"\b", t)), key=lambda s: (s[0], len(s), s))
        hits.append((os.path.relpath(p, REPO), ids))
    return hits


def render(mod, all_internal):
    path = os.path.join(SRC, mod + ".py")
    src = open(path).read()
    tree = ast.parse(src)
    layer, role = LAYERS[mod]
    doc = ast.get_docstring(tree) or "(modül docstring'i yok — ekle)"
    internal, external = _imports(tree)
    internal.discard(mod)
    users = sorted(m for m, deps in all_internal.items() if mod in deps and m != mod)
    L = [f"# `btaudio/{mod}.py`", "",
         "> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.",
         "", "| alan | değer |", "|---|---|",
         f"| katman | [{layer}]({LAYER_DOC[layer]}) |", f"| rol | {role} |",
         f"| boyut | {len(src.splitlines())} satır |",
         f"| içe aktarır (iç) | {', '.join(f'[`{d}`]({d}.md)' for d in sorted(internal)) or '—'} |",
         f"| içe aktarır (dış) | {', '.join(f'`{d}`' for d in sorted(external - STDLIB)) or '—'} |",
         f"| standart kitaplık | {', '.join(f'`{d}`' for d in sorted(external & STDLIB)) or '—'} |",
         f"| kullanan modüller | {', '.join(f'[`{u}`]({u}.md)' for u in users) or '—'} |", "",
         "## Amaç (modül docstring'i)", "", doc.strip(), ""]
    consts = []
    for n in tree.body:
        if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) \
                and re.fullmatch(r"[A-Z][A-Z0-9_]+", n.targets[0].id):
            v = ast.unparse(n.value)
            consts.append((n.targets[0].id, v if len(v) <= 70 else v[:67] + "…"))
    if consts:
        L += ["## Sabitler", "", "| ad | değer |", "|---|---|"] + [f"| `{k}` | `{v.replace('|', '¦')}` |" for k, v in consts] + [""]
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and not n.name.startswith("_")]
    funcs = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and not n.name.startswith("_")]
    if classes or funcs:
        L += ["## Genel API", ""]
    for c in classes:
        bases = ", ".join(ast.unparse(b) for b in c.bases)
        L += [f"### `class {c.name}{'(' + bases + ')' if bases else ''}`", "", _first_para(ast.get_docstring(c)) or "—", ""]
        meths = [m for m in c.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and (not m.name.startswith("_") or m.name == "__init__")]
        for m in meths:
            d = _first_para(ast.get_docstring(m))
            L.append(f"- `{_sig(m)}`" + (f" — {d}" if d else ""))
        if meths:
            L.append("")
    for f in funcs:
        d = _first_para(ast.get_docstring(f))
        L.append(f"- `{_sig(f)}`" + (f" — {d}" if d else ""))
    if funcs:
        L.append("")
    tests = _tests_for(mod)
    L += ["## Testler", ""]
    if tests:
        L += [f"- [`{p}`](../../{p}) — {', '.join(ids) or 'kimliksiz'}" for p, ids in tests]
    else:
        L.append("- doğrudan test dosyası yok (dolaylı: kullanan modüllerin testleri) — **gri alan**")
    L.append("")
    return "\n".join(L)


def render_index():
    L = ["# Modül dizini (üretilmiş)", "",
         "> `tools/gen-docs.py` üretir; U67 bayatlığı yakalar. Katmanların anlamı: [ARCHITECTURE](../ARCHITECTURE.md) · "
         "[L5 yazılım katmanı](../layers/L5-bta-software.md).", ""]
    for layer in ORDER:
        mods = sorted(m for m, (ly, _) in LAYERS.items() if ly == layer)
        L += [f"## {layer}", "", "| modül | rol | satır |", "|---|---|---|"]
        for m in mods:
            n = len(open(os.path.join(SRC, m + ".py")).read().splitlines())
            L.append(f"| [`{m}`]({m}.md) | {LAYERS[m][1]} | {n} |")
        L.append("")
    return "\n".join(L)


def build() -> dict:
    mods = sorted(os.path.basename(p)[:-3] for p in glob.glob(os.path.join(SRC, "*.py")) if not p.endswith("__init__.py"))
    unknown = [m for m in mods if m not in LAYERS]
    if unknown:
        raise SystemExit(f"LAYERS haritasında olmayan modül: {unknown}")
    deps = {m: _imports(ast.parse(open(os.path.join(SRC, m + ".py")).read()))[0] for m in mods}
    out = {os.path.join(OUT, m + ".md"): render(m, deps) for m in mods}
    out[os.path.join(OUT, "README.md")] = render_index()
    return out


def check() -> list:
    stale = []
    for p, txt in build().items():
        if not os.path.exists(p) or open(p).read() != txt:
            stale.append(os.path.relpath(p, REPO))
    known = set(build())
    stale += [os.path.relpath(p, REPO) + " (artık modülü yok)" for p in glob.glob(os.path.join(OUT, "*.md")) if p not in known]
    return stale


def main(argv):
    if "--check" in argv:
        s = check()
        print("\n".join(s) or "güncel")
        return 1 if s else 0
    os.makedirs(OUT, exist_ok=True)
    known = build()
    for p, txt in known.items():
        with open(p, "w") as f:
            f.write(txt)
    for p in glob.glob(os.path.join(OUT, "*.md")):
        if p not in known:
            os.remove(p)                                   # silinen modülün belgesi (üretilmiş dosya, kullanıcı verisi değil)
    print(f"{len(known)} belge yazıldı → {os.path.relpath(OUT, REPO)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
