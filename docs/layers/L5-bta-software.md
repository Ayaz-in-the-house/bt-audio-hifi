# L5 — bta yazılımı (Python paket `btaudio`: domain · application · infrastructure · ölçüm · cli)

> Katman haritası: [00-overview](00-overview.md) · altı: [L4 PipeWire](L4-pipewire.md) · üstü: [L6 tarayıcı](L6-browser-ui.md) ·
> bağlayıcı sözleşme: [ARCHITECTURE](../ARCHITECTURE.md) · modül modül: [modules/](../modules/README.md) (kaynaktan üretilir)
>
> Son doğrulama: 2026-09-28 (birim 178, tarayıcı 6, canlı T-L40–T-L43 yeşil; `tools/gen-docs.py --check` güncel)

## Rol

Durumun TEK sahibi. Kullanıcının ve otomasyonun isteklerini güvenli, geri alınabilir, tıksız parametre yazımlarına
çevirir; kullanıcı verisini (profiller, sürümler) kaybetmeden saklar; her iddiayı ürün katmanında ölçen araçları taşır.

## Durum

Desen: **modüler monolit, portlar ve adaptörler** — tek süreç, tek kullanıcı, yalnız 127.0.0.1. Bağımlılık yönü İÇE.
37 modül, hepsi bir katmana atanmış (U67 zorlar). Tam liste + satır sayıları: [modules/README](../modules/README.md).

<a id="domain"></a>
### domain — saf mantık (G/Ç yok, saat parametre)
`dsp` · `console` · `profiles` · `history` · `features` · `autoctl` · `presetfit` · `state` · `codecs` · `bass` ·
`loudness` · `eqconf` · `analysis` · `tuner` — deterministik birim testlerle sınanır.

<a id="application"></a>
### application — durum sahibi, zamanlama
`consoleserver.Session` (tek durum sahibi, kilit) · `autoengine.AutoEngine` (1 Hz otomasyon) · `tunerserver` (eski).

<a id="infrastructure"></a>
### infrastructure — yan etkiler (hepsi sahte ile değiştirilebilir)
`crossfade` (pw-cli, A/B) · `analyzer` (pw-record) · `journal` (disk) · `classifier` (onnxruntime) · `paths` (XDG) ·
`procs` (alt süreç) · `tones` (pw-play) · `collect` (salt-okuma sistem durumu) · `sbclib` · `resample` · `link` · `btmon` · `bench`.

<a id="olcum"></a>
### ölçüm — ürün katmanında kanıt (kullanıcının kulaklığına dokunmaz, null sink)
`eqverify` (T-L30) · `consoleverify` (T-L32) · `analyzerverify` (T-L34) · `zipperverify` (T-L39/T-L41) · `abx` (kullanıcı kararı).

<a id="cli"></a>
### cli
`bta` komutları: `status` `check` `snapshot` `diff` `install` `uninstall` `codec` `link-test` `bench` `abx` `console`
`model` `apply-pending` `btmon-report` + eski bas araçları. Yardım: `bin/bta`.

## İş parçacıkları ve süreçler (`bta console` çalışırken)

| iş parçacığı / süreç | görevi | dokunduğu |
|---|---|---|
| HTTP istek iş parçacıkları | JSON API, sayfalar | yalnız Session (kilit) — **diske YAZMAZ** |
| `bta-crossfade` | geçiş sıralayıcı (en sonuncu kazanır) | kalıcı `pw-cli` |
| `bta-journal` | 300 ms birleştir → günlük satırı + atomik profil yazımı | disk |
| `bta-auto` | 1 Hz otomasyon tick'i | analizör anlık görüntüsü → Session |
| `bta-spawner` | tüm alt süreçleri doğurur (PDEATHSIG iş parçacığı tuzağına karşı, E23) | — |
| analizör okuyucuları | `pw-record` → spektrum / halka tampon | bellek |
| boşta bekçisi | 1 saat etkinliksizlikte kapat | — |

## API (yalnız 127.0.0.1; Host kontrolü; POST yalnız `application/json`; ≤ 256 KB; CSP)

| yöntem | yol | ne |
|---|---|---|
| GET | `/` · `/admin` | konsol · yönetim sayfası |
| GET | `/api/state` | tam görünüm (durum, eğriler, tarzlar, profiller, geçmiş, kayıt, otomasyon, uyarılar, ton) |
| GET | `/api/auto` · `/api/saved` | hafif yoklamalar (1 sn / kayıt göstergesi) |
| GET | `/api/analyzer/stream` | SSE spektrum/metre |
| GET | `/api/profile/export?id=` · `/api/admin/profiles` · `/api/admin/timeline?id=` · `/api/admin/export-all` | paylaşım / yönetim |
| POST | `/api/state` `{state, seal?}` | elle düzenleme (Özel N çatalı) |
| POST | `/api/preset` · `/api/bypass` · `/api/commit` · `/api/quit` | tarz · EQ'suz · açılışta kullan · kapat |
| POST | `/api/profile/{save,load,rename,duplicate,delete,restore,import,promote,apply-parent,genres}` | profiller |
| POST | `/api/history/{undo,redo,seal}` | geçmiş |
| POST | `/api/auto` `{mode?, nudge?, reset_learning?}` | otomasyon |
| POST | `/api/tone` `{kind: bass\|ref, seconds}` · `/api/tone/stop` | oturma testi |
| POST | `/api/admin/restore` `{id, v}` · `/api/admin/import-bundle` `{bundle}` | sürüme dön · paket içe aktar |
| POST | `/api/analyzer/config` | tepki hızı, sıfırlamalar |

## Veri akışları ve durum geçişleri

**Elle düzenleme (D1):** `POST /api/state` → `Session.set_state` → aktif tarz/kilitli profilse **Özel N çatalı**
(ana kaynak DEĞİŞMEZ) → `Crossfader.submit` (40 ms) → `History.push` (1 sn içinde birleşir) → `journal.enqueue` (O(1)).
Kanıt: istek yolunda `open()` 0 çağrı, p95 fark < 1 ms (U52).

**Otomasyon (D3–D5):** `AutoEngine.tick` (1 Hz) → `Analyzer.snapshot("pre")` (hafif mod: yalnız EQ öncesi dokunuş,
FFT istek anında) → LTAS τ 8 sn → `features.region_excess` + YAMNet (2 sn'de bir, ~13 ms) → APC: `Session.auto_load`
(tarz/profil, 1,5 sn geçiş, nav geçmişi → geri alınabilir) · ADL: `Session.set_auto_offsets` (**üst katman**: boş bant
yuvalarına, kullanıcının durumuna/geçmişine YAZILMAZ). Elle dokunuş → `AutoEngine.manual` → 10 sn askı.

**Sürüm geçişleri (hızlı fark analizi):** her çalışma kopyasının tam sürüm geçmişi günlükte; `/admin` her sürümün
bir öncekine göre farkını satır satır gösterir (`Session._diff`: "bant 1: +2,0→+4,0 dB", "crossfeed açık (700 Hz, 4,5 dB)").
"Bu sürüme dön" yıkıcı değildir: yeni sürüm olarak eklenir, geri alınabilir (U63). Kurulum durumu için `bta snapshot` + `bta diff`.

## Değişkenler (ayarlanabilir sabitler — değiştirmeden önce testini oku)

| sabit | değer | modül | gerekçe |
|---|---|---|---|
| `STEP_S` | 12 ms | crossfade | ≈ yarım kuantum; blok başına ≤ 1 kazanç adımı |
| elle / otomasyon geçişi | 40 ms / 1,5 sn | cli / autoengine | tık yok, gecikme hissedilmez / otomasyon fark edilmez |
| günlük birleştirme | 300 ms | journal | çökmede kayıp üst sınırı |
| geçmiş birleştirme | 1 sn | history | sürükleme = tek adım |
| APC | τ 10 sn, marj 0,15, süreklilik 8 sn, en az kalma 30 sn, güven 0,3, askı 10 sn | autoctl | salınım/pompalama yok (U55) |
| ADL | ölü bölge ±2 dB, güç 0,5, bas −3…+4, diğer ±3, ≤ 1 dB/sn, kuanta 0,5 dB | autoctl / autoengine | sınırlı, yavaş (U56, T-L41) |
| koruma eşikleri | bas +12 dB · 20 Hz altı +10 dB · AAC 17k+ +3 dB | console | hazır tarz ölçümü (U65) |
| sinyal eşiği | −80 dBFS | analyzer | kısık uygulama sesi (K14) |

## Gri alanlar

| alan | durum |
|---|---|
| çok aygıt / aygıt başına profil | tasarım notu [L4 §Aygıt kapsamı](L4-pipewire.md#aygıt-kapsamı) |
| yönetim sayfasında gelişmiş uzay (kanal başına trim, Haas gecikmesi) | yapılmadı (PRD D6 opsiyonel) |
| sınıflayıcısız "temel mod"da tür tahmini | yalnız tonal denge; tür/enstrüman yok |
| eski modüllerin API açıklamaları (`cli`, `collect`, `bench`, `btmon`, `tuner*`, `abx`) | üretilmiş belgede "—" (88 öğe) |
| R43 artığının kök nedeni | açık (duyulmaz seviye) |
| İngilizce arayüz metinleri | yok (arayüz Türkçe) |

## Testler

Tüm birim/tarayıcı/canlı testler: [TEST-PLAN](../TEST-PLAN.md). Koşum: `tests/run.sh` (birim + tarayıcı) ·
`tests/run.sh --live` (+ canlı). Belge kapısı: U67.

## Nasıl ölçülür

```bash
tests/run.sh                         # birim + tarayıcı, rc kapısı
python3 tools/gen-docs.py --check    # modül belgeleri güncel mi
curl -s 127.0.0.1:<port>/api/state | python3 -m json.tool | head    # canlı oturum durumu
```
