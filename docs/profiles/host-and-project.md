# Makine + proje profili

## Makine (workstation)
| alan | değer |
|---|---|
| OS | Fedora 44, kernel 7.1.10 |
| ses yığını | PipeWire 1.6.8 · WirePlumber 0.5.14 · BlueZ 5.87 · libfdk-aac (fdk-aac-free 2.0.3) · libsbc 2.1 |
| BT adaptör | Intel AX210 (USB 8087:0032), hci0 · Wi-Fi 5 GHz ch108 (2,4 GHz çakışması yok) |
| aynı radyoda | M96BT1 klavye, MX Master 3S fare |
| masaüstü | GNOME 50 (kopmada varsayılan çıkışı hoparlöre yazan istemci burada — E4) |
| tarayıcı | Zen (Firefox tabanlı) → sesi 48k F32 verir |
| kısıtlar | laptopta derleme YASAK (filo kuralı) · sudo kullanıcıda · session-safety (kill yok) |

## Proje (`~/projects/bt-audio-hifi`)
| katman | yer |
|---|---|
| CLI | `bin/bta` → `btaudio/cli.py` |
| kurulu config | `config/pipewire/{pipewire-pulse.conf.d,client.conf.d,filter-chain.conf.d}` → `~/.config/pipewire/` (`bta install`) |
| canlı araçlar | konsol `tools/console.html` + `btaudio/consoleserver.py` · bas `tools/bass-tune.html` · ölçüm `tools/loudness-match.html` (gelişmiş) |
| DSP | `btaudio/dsp.py` (RBJ) · `btaudio/console.py` (graf + bs2b + model) |
| ölçüm/doğrulama | `link.py` · `bench.py` + `sbclib.py` · `resample.py` · `eqverify.py` · `consoleverify.py` |
| testler | `tests/` (birim) · `tests/ui/` (başsız E2E) · `tests/live/` (headful, gerçek graf) → `tests/run.sh [--live]` |
| kanıt | `analysis/` (benchmark, link-health, resampler, ui ekran görüntüleri) · `state/snapshots/` |
| bilgi | `docs/` (PRD, PROCESS, lessons, research, profiles) · `.cartography/` (harita + ajan parçaları) |
| paylaşım | `skill/bt-audio-hifi/SKILL.md` (başka makineye kopyalanabilir) · `profiles/*.json` (kullanıcı EQ profilleri) |
