"""U48: arayüz token'larının WCAG 2.x kontrast oranları, iki temada (docs/DESIGN.md §4, §8).
Token'lar console.html'den okunur (tek doğruluk kaynağı); OKLCH → OKLab → doğrusal sRGB → göreli parlaklık."""
import math
import os
import re
import unittest

PAGE = os.path.join(os.path.dirname(__file__), "..", "tools", "console.html")


def oklch_to_rgb(L, C, h):
    a, b = C * math.cos(math.radians(h)), C * math.sin(math.radians(h))
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return [min(1.0, max(0.0, x)) for x in (r, g, bb)]          # doğrusal sRGB (gamut dışı kırpılır)


def lum(rgb_lin):
    r, g, b = rgb_lin
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(c1, c2):
    a, b = sorted((lum(c1), lum(c2)), reverse=True)
    return (a + 0.05) / (b + 0.05)


def parse(block):
    out = {}
    for name, L, C, h in re.findall(r"--([\w-]+):\s*oklch\(([\d.]+) ([\d.]+) ([\d.]+)\)", block):
        out[name] = oklch_to_rgb(float(L), float(C), float(h))
    return out


def themes():
    css = open(PAGE).read()
    light = parse(css[css.index(":root {"):css.index("@media (prefers-color-scheme: dark)")])
    dark_block = css[css.index(':root[data-theme="dark"] {'):]
    dark = parse(dark_block[:dark_block.index("}")])
    return {"açık": light, "koyu": dark}


TEXT = [("text", s) for s in ("bg", "s1", "s2", "s3")] + [("text-2", s) for s in ("bg", "s1", "s2", "s3")] + \
       [("text-3", "s1"), ("text-3", "bg"), ("acc-ink", "acc"), ("warn", "s2"), ("bad", "s3")]
UI = [("acc", "s1"), ("acc", "s2"), ("spec-post", "s1"), ("ok", "s2"), ("warn", "s2"), ("bad", "s2"), ("line", "s1")]


class TestContrast(unittest.TestCase):
    def test_u48_text_pairs_aa(self):
        for tname, t in themes().items():
            for fg, bg in TEXT:
                with self.subTest(tema=tname, fg=fg, bg=bg):
                    self.assertGreaterEqual(ratio(t[fg], t[bg]), 4.5)

    def test_u48_ui_pairs_3to1(self):
        for tname, t in themes().items():
            for fg, bg in UI:
                if fg == "line":
                    continue                                   # ayraç çizgisi dekoratif (WCAG 1.4.11 kapsamı dışı)
                with self.subTest(tema=tname, fg=fg, bg=bg):
                    self.assertGreaterEqual(ratio(t[fg], t[bg]), 3.0)

    def test_u48_both_themes_define_same_tokens(self):
        t = themes()
        self.assertGreaterEqual(len(t["açık"]), 18)
        self.assertEqual(set(t["açık"]) - {"acc-soft", "spec-pre"}, set(t["koyu"]) - {"acc-soft", "spec-pre"})


if __name__ == "__main__":
    unittest.main()
