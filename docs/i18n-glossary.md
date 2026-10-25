# i18n glossary — Turkish UI term → English UI term

English strings in `tools/i18n/en.json`, `btaudio/console.py` (`PRESETS_EN`, warning `text_en`) and
`btaudio/consoleserver.py` (`ERRORS_EN`, `diff_en`) are **written as native audio-product copy, not translated**.
Turkish strings are unchanged (U83 checks this byte for byte). Decision: [ARCHITECTURE.md → Arayüz dili](ARCHITECTURE.md#arayüz-dili-adr-i18n-2026-10-25).

Style rules: sentence case for labels; buttons are imperative ("Set as default", "Restore"); helper text is plain
language; units in standard form (dB, Hz, kHz, dBFS, ms, s) with a decimal point; percentages as `12%` (Turkish `%12`).

## Terms

| Turkish | Literal reading (rejected) | English used | Why / where |
|---|---|---|---|
| Ses Konsolu | Sound Console | **Audio Console** | product-style name; page title, header |
| Yönetim | Administration | **Manage** | link/page for versions, trash, export; short verb used by audio apps |
| Hazır tarz(lar) | Ready style(s) | **Preset(s)** | universal EQ term; preset tab, cards, toasts |
| Profil / Profillerim | Profile / My profiles | **Profile / My profiles** | same concept in English |
| Ana profil (kilitli) | Main profile | **Saved profile** | it is the named, locked profile; "main" means nothing to a new user |
| Çalışma kopyası / Özel N | Work copy / Special N | **Working copy / Custom N** | DAW/editor term; the `Özel N` name is shown as `Custom N` in EN only (display, not data) |
| ÖZEL (rozet) | SPECIAL | **CUSTOM** | badge on the working copy |
| ANA (rozet) | MAIN | **SAVED** | admin table badge for locked profiles |
| Açılışta kullan | Use at opening | **Set as default** | installs the current sound into the boot-time config |
| Açılışta: bu ses ✓ | At opening: this sound ✓ | **Default ✓** | done state of the same button |
| EQ'suz dinle | Listen without EQ | **Hold to bypass** | "bypass" is the standard term; the button is press-and-hold |
| Geri al / İleri al | Take back / Take forward | **Undo / Redo** | standard |
| Uzay (sekme, grup) | Space | **Spatial** | tab and preset group for crossfeed/width; "space" reads as whitespace |
| Sahne | Stage / Scene | **Soundstage** | headphone-review term for perceived width/depth |
| Uzay tarzları | Space styles | **Spatial presets** | — |
| Crossfeed (bs2b) · Kesim · Miktar | Cut · Amount | **Crossfeed · Cutoff · Level** | bs2b's own parameter names are cut frequency and feed level |
| Stereo genişlik | Stereo width | **Stereo width** | same |
| Denge (sol ↔ sağ) | Balance (left ↔ right) | **Balance (L ↔ R)** | standard short form |
| Güç (dB) | Power (dB) | **Gain (dB)** | EQ band parameter |
| Genişlik (Q) | Width (Q) | **Q (bandwidth)** | "width" collides with stereo width |
| Tepe / Bas rafı / Tiz rafı | Peak / Bass shelf / Treble shelf | **Bell / Low shelf / High shelf** | standard parametric-EQ filter names |
| Alçak / Yüksek geçiren · Çentik | Low passing / High passing · Notch | **Low-pass / High-pass · Notch** | standard |
| preamp · kırpılma | — · clipping | **Preamp · Clips** | chip text; tooltip mentions headroom |
| Ses yükseltme · Ses +N dB | Sound raising | **Loudness boost · Boost +N dB** | the limiter-backed output gain (U77/U78) |
| sınırlayıcı | limiter | **limiter** | — |
| Canlı analiz | Live analysis | **Spectrum analyzer** | what the panel is |
| Tepki hızı | Reaction speed | **Response** (Fast/Medium/Slow) | analyzer ballistics |
| Tepe tutma · Parça ortalaması | Top holding · Piece average | **Peak hold · Track average** | standard meter/analyzer terms |
| EQ öncesi / sonrası | Before/after EQ | **Pre-EQ / post-EQ** | standard |
| tepe · RMS · TP | top | **Peak · RMS · TP** | meter labels |
| Kör dinleme testi | Blind listening test | **Blind ABX test** | the method's standard name |
| Deneme 3/12 | Attempt 3/12 | **Trial 3 of 12** | ABX vocabulary |
| X, A mı B mi? | — | **Is X the same as A or B?** | — |
| Fark kanıtlanmadı | Difference not proven | **No audible difference proven** | ABX result wording |
| kalıcı olsun | let it be permanent | **Keep {codec}** | button after ABX |
| Kulak tıkacı oturma testi | Ear plug sitting test | **Ear-tip fit test** | in-ear headphone term ("seal") |
| tıkacın kulağı kapatması | — | **seal** | — |
| Bas tonu · Karşılaştırma | Bass tone · Comparison | **Bass tone · Reference** | test-tone buttons |
| Otomatik mod / Oto | Automatic mode | **Auto mode / Auto** | genre detection + adaptation |
| Otomatik profil | Automatic profile | **Auto profile** | mode that switches profile by detected genre |
| Canlı uyarlama | Live adaptation | **Live adaptation** | ADL; kept — it describes the behaviour well |
| İkisi birden | Both of them | **Both** | — |
| Tür / Tür etiketleri | Kind / Kind labels | **Genre / Genre tags** | auto-profile mapping |
| Tür tanıma | Kind recognition | **Genre detection** | YAMNet classifier |
| askıda | suspended | **paused** | automation on hold (e.g. during a blind test) |
| elle dokundun | you touched by hand | **manual change** | automation waits after a manual change |
| Karakter etiketleri (bas ağırlıklı, bas az, tiz az, vokal öne…) | bass weighted, bass little, treble little, vocal front | **bass-heavy, bass-light, dark, vocal-forward, bright, balanced, deep sub** | headphone-review adjectives |
| Varlık / Hava / Alt-orta | Existence / Weather / Lower-middle | **Presence / Air / Low mids** | standard EQ region names (iZotope) |
| DİKKAT / BİLGİ | ATTENTION / INFORMATION | **CAUTION / INFO** | warning badges |
| Araştırma verisi · Kaynaktan · Tasarım | Research data · From source · Design | **Research target · Published preset · Design choice** | preset provenance badges (`kind`) |
| Referans · Kullanım | Reference · Usage | **Reference · Use case** | preset groups |

## Preset names (ids unchanged — `console.PRESETS_EN`)

| id | Turkish | Literal (rejected) | English |
|---|---|---|---|
| `notr` | Nötr | Neutral | **Flat** — EQ convention for "no processing" |
| `hifi_uzay` | Hi-fi dengeli + uzay | Hi-fi balanced + space | **Balanced hi-fi + soundstage** |
| `harman_bas` / `harman_oe` | Harman bas (kulakiçi 2019 / kulaküstü 2018) | Harman bass (in-ear 2019 / over-ear 2018) | **Harman bass (in-ear 2019 / over-ear 2018)** — the target's own names |
| `hafif_bas` · `zengin_bas` · `derin_sub` | Hafif bas · Zengin bas · Derin sub-bas | Light bass · Rich bass · Deep sub-bass | same |
| `vurucu_bas` | Vurucu bas (punch) | Hitting bass (punch) | **Punchy bass** |
| `guclu_bas` | Güçlü bas | Powerful bass | **Heavy bass** |
| `ee_bass_boosted` / `ee_boosted` | Bas takviyeli / Canlı (EasyEffects …) | Bass reinforced / Live | **Bass Boosted / Lively (EasyEffects …)** — original EasyEffects preset names |
| `v_sekli` · `sicak` · `parlak` · `vokal` | V-şekli · Sıcak · Parlak · Vokal netliği | V-shape · Hot · Shiny · Vocal clearness | **V-shaped · Warm · Bright · Vocal clarity** |
| `konser` · `film` · `oyun` · `gece` | Canlı konser · Film / dizi · Oyun (ayak sesi) · Gece / düşük ses | Live concert · Film / series · Game (foot sound) · Night / low sound | **Live concert · Movies / TV · Gaming (footsteps) · Night / low volume** |
| `sahne` · `studyo` · `dogal_crossfeed` | Geniş sahne · Stüdyo monitör · Doğal crossfeed | Wide stage · Studio monitor · Natural crossfeed | **Wide soundstage · Studio monitors · Natural crossfeed** |

Descriptions are rewritten for an English reader and keep the factual source attribution (AutoEq targets, VLC
`equalizer_presets.h`, EasyEffects presets, bs2b constants, ISO 226:2003, iZotope/TeachMeAudio ranges).

## Not translated (data, not UI)

User profile names and notes, device names, other apps' names (ABX "other audio"), AudioSet instrument names outside
the mapped list, codec names (AAC/SBC), file paths. Legacy pages `tools/bass-tune.html` and `tools/loudness-match.html`
are Turkish only (FEATURES G8).
