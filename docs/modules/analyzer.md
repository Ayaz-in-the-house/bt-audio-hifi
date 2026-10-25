# `btaudio/analyzer.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [infrastructure](../layers/L5-bta-software.md#infrastructure) |
| rol | Canlı analizör: pw-record dokunuşları, 1/6 okt spektrum, metre, SSE, hafif mod |
| boyut | 477 satır |
| içe aktarır (iç) | [`procs`](procs.md) |
| içe aktarır (dış) | `numpy`, `scipy` |
| standart kitaplık | `__future__`, `json`, `os`, `shutil`, `subprocess`, `threading`, `time` |
| kullanan modüller | [`analyzerverify`](analyzerverify.md), [`cli`](cli.md) |

## Amaç (modül docstring'i)

C4 — Canlı analizör ("müzik algılama"): EQ öncesi + sonrası spektrum, seviye metresi, parça ortalaması.

Ölçüm tasarımı (docs/research/findings.md R31–R36):
- Hann penceresi, N=16384 @48 kHz (2,93 Hz/bin), hop 2400 (20 kare/sn).
- 1/6 oktav BANT GÜCÜ (RTA biçimi): bant içindeki bin güçleri toplanır (kesirli kenar, kümülatif). Parseval gereği
  bir sinüsün tüm ana-lob enerjisi banda düşer → pencere taraklanması (scalloping) yok; tam ölçek sinüs = 0 dBFS
  (C = N·Σw²/4, tek taraflı). Pembe gürültü bu gösterimde DÜZ görünür → 4,5 dB/okt eğim gerekmez (FFT-bin
  görünümlerinin — SPAN/Pro-Q — eğimi bunu telafi etmek içindir).
- Zaman: güç alanında üstel IIR (Friture `spectrum.py:212`), τ hızlı 125 ms / orta 300 ms / yavaş 1 s.
- Tepe tutma: 1,5 sn tut, 12 dB/sn düş (tasarım; kaynaklı varsayılan bulunamadı).
- Metre: örnek tepe, RMS (300 ms, VU geleneği — Friture `levels.py:56`), true-peak ≈ 4× aşırı örnekleme
  (ITU-R BS.1770 Ek 2 yöntemi), kırpılma = |x| ≥ 0,999.

Yakalama (C4.3): `pw-record` + `node.autoconnect=false` + ELLE `pw-link`. Otomatik bağlantı KULLANILMAZ: WirePlumber
smart filter, hedefi monitörleyen akışı filtrenin girişine yönlendirir (R17). `node.passive=true` → analizör, ses
yokken kulaklığı uyanık TUTMAZ. Abone yokken süreç YOK (kimse bakmıyorken bedel ödenmez).

## Sabitler

| ad | değer |
|---|---|
| `FS` | `48000` |
| `N_FFT` | `16384` |
| `HOP` | `2400` |
| `FLOOR_DB` | `-120.0` |
| `SIGNAL_DB` | `-80.0` |
| `RESPONSE` | `{'fast': 0.125, 'medium': 0.3, 'slow': 1.0}` |
| `BANDS_PER_OCT` | `6` |
| `RING_S` | `3.0` |

## Genel API

### `class Spectrum`

1/6 oktav bant gücü (Hann N=16384, hop 2400), güç alanı EMA, tepe tutma, parça ortalaması (LTAS).

- `__init__(self, fs=FS, n=N_FFT, hop=HOP, response='medium', hold_s=1.5, fall_db_s=12.0)`
- `set_response(self, response)` — Tepki hızı: fast 125 ms · medium 300 ms · slow 1 s.
- `band_power(self, x)` — Bir pencerenin bant güçleri (kalibre: tam ölçek sinüs = 0 dBFS, kanalların güç ortalaması).
- `push(self, block)` — Blok ekler, her hop için kare üretir: {bands, hold} (dBFS).
- `ltas(self)` — Sinyal varken biriken uzun süreli ortalama spektrum (dBFS).
- `reset_ltas(self)` — Parça ortalamasını sıfırlar.

### `class LevelMeter`

Kanal başına örnek tepe, RMS (300 ms), true-peak (4× aşırı örnekleme), kırpılma sayısı, sinyal var/yok.

- `__init__(self, fs=FS, rms_tau=0.3)`
- `push(self, block, light=False)` — light=True (yalnız otomasyon dinliyor): true-peak aşırı örneklemesi atlanır (blok başına ~1,4 ms, T-L40) → true_peak = örnek tepe. Arayüz metresi her zaman tam modda çalışır.

### `class Analyzer`

Abone sayımlı yakalama yöneticisi. İlk abone → başlat; son abone gidince `linger_s` sonra DURDUR.

- `__init__(self, taps: dict, linger_s: float=2.0, response: str='medium', on_activity=None)`
- `running(self)` — Herhangi bir yakalama süreci yaşıyor mu.
- `pids(self)` — Yaşayan yakalama süreçlerinin pid'leri.
- `subscribe(self, kind: str='ui') -> int` — kind="ui": arayüz (tam analiz, kareler) · kind="auto": otomasyon motoru (hafif, yalnız snapshot).
- `unsubscribe(self, sid)` — Aboneliği bırakır; bekleme süresi (linger) sonunda istenmeyen dokunuşlar durur.
- `close(self)` — Tüm abonelikleri siler, süreçleri durdurur.
- `snapshot(self, tap='pre', seconds=2.0)` — Otomasyon girdisi (D3): {centers, bands (dBFS, 1/6 okt), level_db (L/R RMS ort.), signal, audio}. Yakalama çalışmıyorsa / henüz kare yoksa None. Canlı veri, istek yolunu bloklamaz (kopya).
- `wait_frame(self, sid, timeout=1.0)` — Abonenin görmediği yeni kareyi bekler (timeout → None).
- `info(self)` — Kullanılabilirlik, çalışma durumu, dokunuşlar, tepki hızı.
- `configure(self, body: dict)` — Tepki hızı / LTAS sıfırlama / kırpılma sayacı sıfırlama.
- `serve_sse(self, h)` — SSE akışı: her yeni kare JSON; kopunca abonelik bırakılır.

- `pw_record_cmd(node_name: str) -> list` — Ham f32 stereo 48 kHz pw-record komutu (autoconnect kapalı, passive — kulaklığı uyanık tutmaz).
- `console_taps() -> dict` — Gerçek konsol grafı: EQ öncesi = filtre girişinin monitörü, sonrası = filtre çıkışı (BT sink'e giden sinyal).

## Testler

- [`tests/live/test_live.py`](../../tests/live/test_live.py) — T-L01, T-L10, T-L12, T-L13, T-L14, T-L20
- [`tests/live/test_live_auto.py`](../../tests/live/test_live_auto.py) — T-L39, T-L40, T-L41, T-L42, U62
- [`tests/test_analyzer.py`](../../tests/test_analyzer.py) — T-L40, U44, U46, U81
- [`tests/test_autoctl.py`](../../tests/test_autoctl.py) — T-L42, U54, U56
- [`tests/test_autoengine.py`](../../tests/test_autoengine.py) — U58, U59, U60, U73
- [`tests/ui/test_console_page.py`](../../tests/ui/test_console_page.py) — T-U04
- [`tests/ui/test_i18n_page.py`](../../tests/ui/test_i18n_page.py) — T-U04, T-U06, T-U08, T-U09
