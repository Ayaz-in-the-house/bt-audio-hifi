# `btaudio/cli.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [cli](../layers/L5-bta-software.md#cli) |
| rol | `bta` komutları (durum, kurulum, konsol, ölçümler, model) |
| boyut | 857 satır |
| içe aktarır (iç) | [`abx`](abx.md), [`abxsession`](abxsession.md), [`analyzer`](analyzer.md), [`autoengine`](autoengine.md), [`bass`](bass.md), [`bench`](bench.md), [`btmon`](btmon.md), [`classifier`](classifier.md), [`collect`](collect.md), [`console`](console.md), [`consoleserver`](consoleserver.md), [`crossfade`](crossfade.md), [`eqconf`](eqconf.md), [`link`](link.md), [`paths`](paths.md), [`procs`](procs.md), [`state`](state.md), [`tones`](tones.md), [`tuner`](tuner.md), [`tunerserver`](tunerserver.md) |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__`, `datetime`, `glob`, `json`, `os`, `shlex`, `shutil`, `subprocess`, `sys`, `time`, `urllib`, `webbrowser` |
| kullanan modüller | — |

## Amaç (modül docstring'i)

bta — Bluetooth audio hi-fi durum aracı.

bta snapshot [label]        durum JSON'u state/snapshots/'a yaz
bta diff [A] [B]            iki snapshot farkı (varsayılan: son iki); 'latest', '-2', dosya yolu
bta status                  insan-okur özet
bta check [--json]          kabul kontrolleri (exit 0 = hepsi geçti)
bta install | uninstall     config drop-in'lerini kur/kaldır (yedekli) + PipeWire yeniden başlat
bta codec <profil>          kart profilini değiştir (a2dp-sink | a2dp-sink-sbc_xq | a2dp-sink-sbc)
bta link-test [sn] [--passive] [--label x]  paket/bitrate düşürme ölçümü → analysis/link-health/
bta bench                   encoder benchmark (AAC/SBC/SBC-XQ/HFP) → analysis/encoder-benchmark-*.md
bta bass-analyze [dosya…] [--target harman-ie-bass|flat] [--max-boost 12]  eşleştirme JSON → yanıt+EQ
bta bass-apply [analiz.json]   EQ'yu smart filter-chain olarak kur (yalnız kulaklık) + EE preset'i üret
bta bass-tune [--no-open]      CANLI bas ayarı: yerel sayfa (Zen'de açılır), müziğini dinlerken kaydırıcılar, Kaydet
bta console [--no-open]        PROFESYONEL KONSOL: 10 bant EQ (grafikten sürükle) + ses uzayı + profiller
                [--idle-timeout SN]   boşta kapanma (varsayılan 3600, 0 = hiç; servis 0 kullanır)
bta service install|uninstall|status   otomatik modu arka plan servisi yap (systemd kullanıcı birimi, girişte başlar)
                  [--port N] [--allow-host AD]   uzaktan (tailnet) erişim: `tailscale serve` adı Host kapısından geçer
bta model verify|fetch         yerel müzik türü sınıflayıcısı (YAMNet ONNX, sha256 kilitli; otomatik modlar için)
bta bass-off                   bas EQ'sunu kaldır (filter-chain durur, dosyalar yedeklenir)
bta btmon-report <x.btsnoop>   kullanıcının root ile aldığı radyo kaydını çözümle (+ yanındaki .rssi.txt)
bta apply-pending              kurulu ama etkin olmayan config'leri (T-L24) yalnız ilgili servisi yeniden başlatarak etkinleştir
bta abx [a] [b] [--clip f] [--start s] [--dur s] [--n 12] [--apply]   kör ABX dinleme testi (etkileşimli)

## Sabitler

| ad | değer |
|---|---|
| `SNAP_DIR` | `os.path.join(collect.REPO, 'state', 'snapshots')` |
| `BACKUP_DIR` | `paths.backups_root()` |
| `DECISION` | `os.path.join(collect.REPO, 'decision.json')` |
| `SERVICES` | `['pipewire.service', 'pipewire-pulse.service', 'wireplumber.service']` |
| `ALL_SERVICES` | `SERVICES + ['filter-chain.service']` |
| `BASS_REL` | `'pipewire/filter-chain.conf.d/60-bta-bass-eq.conf'` |
| `CONSOLE_REL` | `'pipewire/filter-chain.conf.d/60-bta-console.conf'` |
| `SERVICE_PORT` | `8766` |
| `SERVICE_UNIT` | `'bta-console.service'` |
| `COMMANDS` | `{'service': cmd_service, 'console': cmd_console, 'model': cmd_model…` |

## Genel API

- `cmd_snapshot(args)`
- `cmd_diff(args)`
- `checks(snap=None)` — (id, ok, detay) listesi — TEST-PLAN T-L01..T-L05, T-L20 ile aynı kimlikler.
- `cmd_check(args)`
- `cmd_status(args)`
- `services_for(paths)` — Değişen config yollarına göre yeniden başlatılması GEREKEN en küçük servis kümesi. client.conf.d → servis yok (yeni başlayan native istemciler okur).
- `pending_restarts(installed_mtimes: dict, service_started: dict) -> list` — Teslimat zinciri: kurulu drop-in, onu okuyan servisin son başlangıcından YENİYSE ayar henüz ETKİN DEĞİL.
- `parse_systemd_us(value: str) -> float` — 'Sun 2026-09-27 16:19:29.123456 UTC' → epoch (µs hassasiyet). Boş/n/a → 0.
- `service_start_times() -> dict`
- `cmd_install(args)`
- `cmd_uninstall(args)`
- `cmd_codec(args)`
- `cmd_link_test(args)`
- `cmd_bench(args)`
- `cmd_abx(args)`
- `cmd_bass_analyze(args)`
- `cmd_bass_apply(args)`
- `cmd_bass_tune(args)`
- `commit_console_state(st)` — 'Açılışta kullan': durum geçmişi (XDG) + üretilmiş config + kurulum. Repo'ya YAZMAZ (C0, T-L37/U49).
- `cmd_console(args)`
- `cmd_model(args)` — bta model verify|fetch — yerel sınıflayıcı (YAMNet ONNX, Apache-2.0). İndirilen dosya models.lock.json sha256'sıyla doğrulanmadan kabul edilmez; uymazsa silinir.
- `cmd_bass_off(args)`
- `cmd_btmon_report(args)`
- `cmd_apply_pending(args)`
- `render_service_unit(bta_path)` — U76: otomatik mod arka plan servisi (systemd kullanıcı birimi). Tarayıcı açmaz, boşta kapanmaz.
- `cmd_service(args)`
- `main(argv=None)`

## Testler

- [`tests/live/test_live.py`](../../tests/live/test_live.py) — T-L01, T-L10, T-L12, T-L13, T-L14, T-L20
- [`tests/test_commit_isolation.py`](../../tests/test_commit_isolation.py) — T-L37, U49, U72
- [`tests/test_first_run.py`](../../tests/test_first_run.py) — U80
- [`tests/test_service.py`](../../tests/test_service.py) — U74, U76
- [`tests/test_state.py`](../../tests/test_state.py) — U07, U10
