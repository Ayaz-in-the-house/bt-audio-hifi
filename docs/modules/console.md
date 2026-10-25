# `btaudio/console.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [domain](../layers/L5-bta-software.md#domain) |
| rol | Konsol durumu, sanitize, stereo model, hazır tarzlar, A/B graf üretimi, koruma uyarıları |
| boyut | 778 satır |
| içe aktarır (iç) | [`dsp`](dsp.md), [`paths`](paths.md) |
| içe aktarır (dış) | `numpy` |
| standart kitaplık | `__future__`, `copy`, `json`, `math`, `os`, `re` |
| kullanan modüller | [`analyzerverify`](analyzerverify.md), [`autoengine`](autoengine.md), [`cli`](cli.md), [`consoleserver`](consoleserver.md), [`consoleverify`](consoleverify.md), [`crossfade`](crossfade.md), [`eqconf`](eqconf.md), [`profiles`](profiles.md), [`zipperverify`](zipperverify.md) |

## Amaç (modül docstring'i)

F9 — Profesyonel ses konsolu modeli: 10 bant stereo PEQ + bs2b crossfeed + stereo genişlik + denge + otomatik
preamp. Her şey PipeWire filter-chain'de CANLI değişir (bq_raw katsayıları + mixer kazançları + linear çarpan).

Graf (kanal başına):
    preX(linear) → eqX_1 … eqX_N (bq_raw) ─┬→ hiX (bq_raw, bs2b yüksek raf) ─┐
                                           └→ loX (bq_raw, bs2b alçak geçiren)┤→ mixL / mixR (mixer)
    mixL = g·[a·hiL + b·hiR + a·loR + b·loL]   mixR = g·[a·hiR + b·hiL + a·loL + b·loR]
    a=(1+w)/2, b=(1−w)/2 (w=genişlik; L=R içerikte a+b=1 → mono uyumlu), g = bs2b kazancı.
bs2b: docs/research/upstream/bs2b.c:131-214 (birinci derece filtreler → bq_raw ile BİREBİR).

## Sabitler

| ad | değer |
|---|---|
| `N_BANDS` | `10` |
| `FS` | `48000` |
| `RATES` | `(44100, 48000)` |
| `BS2B_FCUT` | `(300, 2000)` |
| `BS2B_FEED` | `(1.0, 15.0)` |
| `BS2B_PRESETS` | `{'default': {'fcut': 700, 'feed': 4.5, 'label': 'Varsayılan (bs2b)'…` |
| `DEFAULT_FREQS` | `[32, 64, 125, 250, 500, 1000, 2000, 4000, 8000, 16000]` |
| `ZERO` | `{'b0': 0.0, 'b1': 0.0, 'b2': 0.0, 'a0': 1.0, 'a1': 0.0, 'a2': 0.0}` |
| `RECOMMENDED_PRESET` | `'hifi_uzay'` |
| `RECOMMENDED_LOUD_DB` | `6.0` |
| `GRID` | `np.geomspace(20, 20000, 240).tolist()` |
| `CATEGORIES` | `['Referans', 'Bas', 'Tür', 'Karakter', 'Kullanım', 'Uzay']` |
| `KINDS` | `{'hedef': 'Araştırma hedef eğrisinden (ölçülmüş veri)', 'kaynak': '…` |
| `DESIGN` | `'Tasarım (yetkili tek-değer kaynağı yok). Bölge sınırları: TeachMeA…` |
| `VLC_SRC` | `"VLC equalizer_presets.h (LGPL-2.1+) '{n}' 10 bant → 1 kHz'e göre, …` |
| `EE_SRC` | `"JackHack96/EasyEffects-Presets '{n}.json' (MIT) — 10 bell bant bir…` |
| `PRESETS` | `{'notr': {'label': 'Nötr', 'group': 'Referans', 'kind': 'standart',…` |
| `DESIGN_EN` | `'Design choice (no single authoritative source). Range boundaries: …` |
| `VLC_SRC_EN` | `"VLC equalizer_presets.h (LGPL-2.1+) '{n}': 10 bands normalised to …` |
| `EE_SRC_EN` | `"JackHack96/EasyEffects-Presets '{n}.json' (MIT): 10 bell bands, va…` |
| `NO_OPEN_PRESET_EN` | `' (no published open preset exists for this genre)'` |
| `PRESETS_EN` | `{'notr': ('Flat', 'No processing. Use it as the reference to compar…` |
| `PREVIEW_F` | `[round(f, 1) for f in np.geomspace(20, 20000, 48)]` |
| `LOUD_MAX_DB` | `15.0` |
| `LIMIT_CEIL_DB` | `-1.0` |
| `LSP_LADSPA` | `'/usr/lib64/ladspa/lsp-plugins-ladspa.so'` |
| `BASS_WARN_DB` | `12.0` |
| `INFRA_WARN_DB` | `10.0` |
| `HF_AAC_DB` | `3.0` |

## Genel API

- `default_state() -> dict` — Şeffaf başlangıç durumu: 10 kapalı bant, crossfeed kapalı, genişlik 1, denge 0.
- `recommended_state() -> dict` — U80: ilk kurulum varsayılanı = `hifi_uzay` hazır tarzı (ölçülü Harman bas rafı + hafif uzay). 'Nötr' (default_state) şeffaf referans olarak kalır; bu yalnız hiç durumu olmayan kuruluma verilir.
- `sanitize(st: dict) -> dict` — Dış girdiyi sözleşmeye zorlar: tip listesi, sınır kırpma, eksik alan tamamlama (her yazımdan önce).
- `bs2b_coeffs(fcut: float, feed_db: float, fs: int=FS) -> dict` — bs2b.c init(): level=feed dB, GB_lo=level·(−5/6)−3, GB_hi=level/6−3 …
- `stereo_model(st: dict, freqs, include_preamp=False, fs=FS) -> dict` — Karmaşık transfer fonksiyonları: LL (L giriş→L çıkış), LR (L→R), RL, RR, mono (L=R→L).
- `preamp_db(st: dict) -> float` — En kötü durum sınırı: |L çıkışı| ≤ |LL|+|RL| (tam ölçek, aynı fazlı L ve R). Tepe >0 dB ise o kadar kıs.
- `pw_params(st: dict, bypass: bool=False) -> str` — Tek zincirli graf için PipeWire Props yükü (bq_raw katsayıları, preamp, uzay kazançları).
- `render_graph(target_sink: str, st: dict | None=None, source: str='-') -> str` — Kalıcı config: mevcut durumun katsayıları GÖMÜLÜ (yeniden başlatmada aynı ses).
- `preset_catalog() -> dict` — Arayüz için: meta (TR + `*_en` İngilizce, U84) + küçük önizleme eğrisi (EQ, preamp hariç). Hazır tarzlar koddadır → bir kez hesaplanır.
- `apply_preset(st: dict, pid: str) -> dict` — EQ profilleri yalnız bantları, 'Uzay' profilleri yalnız uzay ayarını değiştirir (biri diğerini silmesin); 'film'/'konser' gibi ikisini birden tanımlayanlar ikisini; 'Nötr' her şeyi sıfırlar (açıklamasındaki vaat).
- `pw_params_ab(st: dict, chain: str, bypass: bool=False) -> str` — Tek zincirin (A|B) tüm denetim değerleri — `pw_params` ile aynı katsayılar, düğüm adları zincir önekli.
- `mix_gains(gain_a: float, gain_b: float) -> str` — Toplama düğümü kazançları (A = Gain 1, B = Gain 2). R42: PipeWire 1.6.8 `ramp` denetim portları aralıksız (min=max=0) → kullanılamaz; geçiş bu kazançların KÜÇÜK adımlarla değiştirilmesiyle yapılır (mixer blok başına sabit).
- `crossfade_steps(to_chain: str, n: int) -> list` — Doğrusal (ilişkili sinyalde sabit genlik) n adımlı geçiş kazanç yükleri.
- `loud_path() -> str`
- `load_loud_db(path: str | None=None) -> float`
- `save_loud_db(db: float, path: str | None=None) -> float` — Ayarı sınırlayıp atomik yazar (yarım dosya = bozuk ayar = 0 dB); yazılan değeri döndürür.
- `loud_payload(db: float) -> str` — Canlı sınırlayıcı giriş kazancı (Props yükü): müzik kesilmeden ses yükseltme.
- `render_graph_ab(target_sink: str, st: dict | None=None, source: str='-', node_suffix: str='bta_console', loud_db: float | None=None) -> str` — A/B zincirli smart filter-chain config metni (kopya → iki tam zincir → toplama → sınırlayıcı; hedef = BT sink).
- `protection_warnings(state: dict, codec: str | None=None) -> list` — Uyarılar: [{code, level: warn|info, text, text_en}] (U85: TR + İngilizce). Girdi = SESE GİDEN durum (ADL katmanı dahil).
- `target_spa(target) -> str` — Smart filter hedefi SPA-JSON nesnesi. str → {node.name} (doğrulama sondaları), dict → kimlik eşleşmesi (U72).
- `smart_target(conf_text: str) -> dict | None` — Kurulu graf config'inin smart filter hedefi (özellik sözlüğü) — yoksa None.
- `target_stale(conf_text: str, current) -> bool` — U71/U72: kurulu hedef, bağlı kulaklığın kimlik hedefiyle aynı değilse bayattır (eski MAC biçimi, ad değişimi). Kulaklık bağlı değilse (current boş) bayat SAYILMAZ: son bilinen hedef korunur, boşuna yeniden kurulum yok.

## Testler

- [`tests/live/test_live.py`](../../tests/live/test_live.py) — T-L01, T-L10, T-L12, T-L13, T-L14, T-L20
- [`tests/test_admin.py`](../../tests/test_admin.py) — U63
- [`tests/test_autoctl.py`](../../tests/test_autoctl.py) — T-L42, U54, U56
- [`tests/test_autoengine.py`](../../tests/test_autoengine.py) — U58, U59, U60, U73
- [`tests/test_commit_isolation.py`](../../tests/test_commit_isolation.py) — T-L37, U49, U72
- [`tests/test_console.py`](../../tests/test_console.py) — U31, U35
- [`tests/test_crossfade.py`](../../tests/test_crossfade.py) — U57, U68, U77
- [`tests/test_first_run.py`](../../tests/test_first_run.py) — U80
- [`tests/test_i18n.py`](../../tests/test_i18n.py) — U82, U83, U84, U85, U86
- [`tests/test_identity.py`](../../tests/test_identity.py) — U72
- [`tests/test_loud_limiter.py`](../../tests/test_loud_limiter.py) — U77, U78
- [`tests/test_presets.py`](../../tests/test_presets.py) — U43
- [`tests/test_profiles.py`](../../tests/test_profiles.py) — U41, U42
- [`tests/test_protection.py`](../../tests/test_protection.py) — U65
- [`tests/test_retarget.py`](../../tests/test_retarget.py) — U71, U72
- [`tests/test_workcopy.py`](../../tests/test_workcopy.py) — U51, U53
- [`tests/ui/test_admin_page.py`](../../tests/ui/test_admin_page.py) — T-U06
- [`tests/ui/test_auto_page.py`](../../tests/ui/test_auto_page.py) — T-U05
- [`tests/ui/test_console_page.py`](../../tests/ui/test_console_page.py) — T-U04
- [`tests/ui/test_i18n_page.py`](../../tests/ui/test_i18n_page.py) — T-U04, T-U06, T-U08, T-U09
- [`tests/ui/test_protection_page.py`](../../tests/ui/test_protection_page.py) — T-U07, U65
