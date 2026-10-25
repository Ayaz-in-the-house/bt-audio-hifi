/* bt-audio-hifi arayüz dili (EN/TR) — bağımlılıksız. Karar: docs/ARCHITECTURE.md → Arayüz dili.
   Dil: ?lang=en|tr (geçici, kaydedilmez) > localStorage "bta.lang" > navigator.language (tr* → tr) > en.
   Sözlük: /i18n/<dil>.json. Durağan metin: data-i18n (metin) · data-i18n-html (biçimli) · data-i18n-title /
   -aria-label / -placeholder (öznitelik). TR görünümünde durağan metne dokunulmaz (sayfadaki Türkçe = tr.json, U83). */
"use strict";
(function () {
  const LANGS = ["en", "tr"];
  function detect() {
    const q = new URLSearchParams(location.search).get("lang");
    if (LANGS.includes(q)) return q;
    try { const v = JSON.parse(localStorage.getItem("bta.lang")); if (LANGS.includes(v)) return v; } catch (e) { /* yok */ }
    const n = String((navigator.languages && navigator.languages[0]) || navigator.language || "");
    return /^tr/i.test(n) ? "tr" : "en";
  }
  const lang = detect();
  let dict = {};
  document.documentElement.lang = lang;
  if (lang !== "tr") {
    document.documentElement.classList.add("i18n-wait");   // Türkçe metin bir an bile görünmesin
    setTimeout(() => document.documentElement.classList.remove("i18n-wait"), 3000);   // sigorta: sayfa asla gizli kalmaz
  }

  const has = k => Object.prototype.hasOwnProperty.call(dict, k);
  function t(key, vars) {
    const s = has(key) ? dict[key] : key;
    return vars ? s.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m)) : s;
  }
  function apply(root) {
    root = root || document;
    for (const el of root.querySelectorAll("[data-i18n]")) el.textContent = t(el.dataset.i18n);
    for (const el of root.querySelectorAll("[data-i18n-html]")) el.innerHTML = t(el.dataset.i18nHtml);   // sözlük depodan gelir (güvenilir)
    for (const [attr, ds] of [["title", "i18nTitle"], ["aria-label", "i18nAriaLabel"], ["placeholder", "i18nPlaceholder"]])
      for (const el of root.querySelectorAll(`[data-i18n-${attr}]`)) el.setAttribute(attr, t(el.dataset[ds]));
  }
  function set(l) {
    if (!LANGS.includes(l)) return;
    try { localStorage.setItem("bta.lang", JSON.stringify(l)); } catch (e) { /* özel kip */ }
    const u = new URL(location.href); u.searchParams.delete("lang"); location.href = u.toString();
  }
  function wireToggle() {
    for (const b of document.querySelectorAll("[data-lang]")) {
      b.setAttribute("aria-pressed", String(b.dataset.lang === lang));
      b.onclick = () => { if (b.dataset.lang !== lang) set(b.dataset.lang); };
    }
  }
  async function load() {
    try { const r = await fetch(`/i18n/${lang}.json`); if (r.ok) dict = await r.json(); } catch (e) { /* anahtar adı görünür */ }
    if (lang !== "tr") apply();
    wireToggle();
    document.documentElement.classList.remove("i18n-wait");
  }
  window.I18N = {lang, locale: lang === "tr" ? "tr-TR" : "en-US", t, has, apply, load, set};
})();
