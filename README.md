<p align="center"><img src="assets/icon.svg" width="96" alt="bt-audio-hifi"></p>

# bt-audio-hifi

**English** · [Türkçe](README.tr.md)

Tools that make a **Bluetooth headphone** on Linux (Fedora 44 · PipeWire 1.6.8 · WirePlumber 0.5.14) sound its best —
measurably and reversibly: stay on the high-quality profile, measure codecs, a **professional EQ console** (10 bands you
drag on the graph, spatial controls, 32 presets, live analyzer), **working copies saved the moment you touch a control**
(undo/redo), an **auto mode that recognises the music and picks the setting itself**, and an admin page.

Reference device: Solix Nexus ANC (TWS, AAC/SBC). It works with other Bluetooth headphones too; speaker/HDMI/USB outputs
are intentionally left untouched ([why](docs/USER-DECISIONS.md#0-önce-kısa-cevap-bu-proje-tüm-çıkış-aygıtlarını-yönetir-mi)).

**License: [MIT](LICENSE)** — anyone may use, modify and redistribute it. Third-party components: [NOTICE](NOTICE.md).

## Roadmap — what doing it unlocks

The software side (upper part of L2 and L3–L6) has been mapped with its classes and states. The inside of the headphone (chip, DSP, DAC, ANC, TWS) and the lower layers of the radio/protocol stack have not — that is where the question "are we using the hardware's full potential?" is mostly answered. Gains in the table are **expectations, not measured results**.

| layer | known today (done) | not done · untested · unknown | when done, it unlocks | method / source |
|---|---|---|---|---|
| **L1a** acoustics and driver | Bass brought toward the Harman target (105 Hz shelf) | The headphone's frequency response is not measured; no measurement of this model exists. Mids and treble are untouched | **Biggest potential gain:** every frequency pulled to the target — hearing all frequencies evenly | Cheap measurement mic + simple rig; measurement → parametric EQ |
| **L1b** chip, firmware, DSP, DAC, amp, ANC | Chip vendor identified (Bluetrum, from LMP); service channel (SPP) found, 0 bytes when listening | Internal DSP chain, own volume limit, firmware version, whether it applies its own EQ/bass boost/limiter — unknown. Never written up as its own layer | If it processes internally, our EQ stops stacking on it and both layers are tuned together; possibly ANC mode / internal EQ changed from Linux | Bluetrum SDK documents and manuals; **read-only first** — sending commands can brick the device |
| **L1c** TWS (relay between the earbuds) | — | Never studied: does audio go to the primary earbud, how is it relayed, latency and loss | Reliability rather than quality: the ~40 s reconnect wait, inter-earbud latency, stutters | Bluetooth Core Specification + on-device measurement |
| **L2a** radio and LMP | AX210 adapter, BlueZ 5.87, profile and disconnect behaviour | No radio capture (btmon) yet (needs sudo); Wi-Fi coexistence not measured | Shows why SBC-XQ dropped packets (signal or Wi-Fi); if fixable, SBC-XQ is a candidate again | `sudo bash tools/btmon-capture.sh 60` → `bta btmon-report` |
| **L2b** L2CAP and AVDTP | Connection establishes, streaming works | Protocol state machines not documented; MTU / packet size / latency not measured | Separates the causes of stutter and latency | Bluetooth Core Specification + btmon capture |
| **L2c** A2DP and codec | **Strong:** AAC and SBC decoded byte by byte, SBC-XQ measured and ruled out, quality compared; AAC cuts off around 17 kHz | AAC ↔ SBC decision pending the blind ABX test; forcing AAC to a higher bitrate not tried | Codec chosen by ear; possibly AAC's high-frequency cutoff lifted | `bta abx` (blind test, in the console) |
| **L3–L6** Linux, PipeWire, bta, UI | **Detailed:** processes, graph, resampler, API, state transitions | Small gray areas ([FEATURES](docs/FEATURES.md)) | — | `docs/layers/` |

**The ceiling you cannot pass.** The headphone supports only SBC and AAC; LDAC/aptX will never come from software. Transport tops out at AirPods level (AirPods use AAC too); beyond that it is driver physics. Realistic target: AirPods-class transport + a correction measured for this headphone — it can get close to expensive headphones by ear, it cannot change physics.

**Open-source angle.** Most budget TWS earbuds use Bluetrum chips. With the measurement method and tools documented layer by layer, this stops being "one headphone's tuning" and becomes a method other owners of the same class of earbuds can use.

**Plan:** split L1 and L2 into separate layers and fill each with the same template (options · states · variables · measurement method). Suggested order: L1a (measurement) → L1b (read-only) → L2a (radio capture).

- [ ] **L1a** acoustics and driver
- [ ] **L1b** chip, firmware, DSP, DAC, amplifier and ANC — the most unknowns are here
- [ ] **L1c** TWS relay
- [ ] **L2a** radio and LMP
- [ ] **L2b** L2CAP and AVDTP
- [ ] **L2c** A2DP and codec

## Screenshots

![Audio console: drag-on-graph EQ, live analyzer, presets](analysis/ui/console-v2-dark-1440.png)

| Blind listening test (AAC ↔ SBC) | Admin: profiles, version history, automation |
|---|---|
| ![Blind listening test](analysis/ui/abx-trial-dark.png) | ![Admin page](analysis/ui/admin-dark-1440.png) |

<img src="analysis/ui/console-v2-mobile-390.png" width="260" alt="Console on a phone">

## Quick start

```bash
git clone <repo> bt-audio-hifi && cd bt-audio-hifi
ln -s "$PWD/bin/bta" ~/.local/bin/bta   # run `bta` from any directory (below, `bin/bta` = `bta`)
bin/bta status                 # headphone, profile, codec, streams
bin/bta check                  # acceptance checks
bin/bta install                # config drop-ins (backed up; only for the connected Bluetooth headphone)
bin/bta console                # ⭐ console — opens in the browser (127.0.0.1 only)
bin/bta model fetch            # (optional) local genre classifier for auto mode (YAMNet, sha256-pinned)
```

A fresh install starts with the **Hi-fi balanced + space** preset (second after *Neutral*): a measured, moderate bass shelf
(+6 dB below 105 Hz, Harman over-ear amount), gentle bs2b crossfeed and 10 % extra width, loudness +6 dB to offset the
preamp. Pick *Neutral* for no processing at all.

Requires: Python 3.11+, numpy, scipy · onnxruntime for auto mode · playwright for the tests.

## What it does

| | feature | where |
|---|---|---|
| 🎧 | Headphone always on A2DP (high quality); an app opening the microphone does not drop audio to mono 16 kHz | automatic |
| 📡 | Codec measurement (AAC / SBC), link health, blind ABX listening test | `bta bench` · `bta link-test` · `bta abx` |
| 🎛️ | 10-band parametric EQ (drag on the graph), crossfeed, width, balance, 32 sourced presets | console |
| 📈 | Live analyzer: 1/6-octave spectrum before/after EQ, meters, track average | Analysis tab |
| 💾 | First touch creates a "Custom N" working copy — the base profiles never change; every change is saved instantly (< 1 ms), with undo/redo | automatic |
| 🔇 | Click-free parameter changes (A/B chain crossfade) | automatic |
| 🤖 | Auto mode: recognises the genre (electronic, rock, speech…) → loads the profile bound to it; bounded live bass/treble adaptation on thin recordings; leaves speech untouched | Auto tab |
| 🗂️ | Admin: version timeline with diffs, restore a version, trash, bulk export/import | `/admin` |
| 🛡️ | Driver-protection and codec-awareness warnings, ear-tip fit test | under the graph · Analysis |

Full catalogue (gray areas included): [docs/FEATURES.md](docs/FEATURES.md).

## Documentation

The in-depth docs and the UI are currently in Turkish ([README in Turkish](README.tr.md)); an English UI is a planned gray area.

- **Start here:** [docs/README.md](docs/README.md) (documentation hub, for agents and developers)
- Layers: [headphone](docs/layers/L1-headphone.md) · [Bluetooth](docs/layers/L2-bluetooth.md) · [Linux](docs/layers/L3-linux-os.md) ·
  [PipeWire](docs/layers/L4-pipewire.md) · [software](docs/layers/L5-bta-software.md) · [UI](docs/layers/L6-browser-ui.md)
- Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · modules: [docs/modules/](docs/modules/README.md)
- Decisions (plain language): [docs/USER-DECISIONS.md](docs/USER-DECISIONS.md) · requirements: [docs/PRD.md](docs/PRD.md) ·
  tests: [docs/TEST-PLAN.md](docs/TEST-PLAN.md) · lessons: [docs/lessons/](docs/lessons/errors.md)

## Installed changes (`~/.config/pipewire/`)

| file | what it does |
|---|---|
| `pipewire-pulse.conf.d/60-bta-switch-on-connect.conf` | default output switches back to the headphone when it connects |
| `{client,pipewire-pulse}.conf.d/60-bta-resample.conf` | resampler quality 4 → 10 |
| `filter-chain.conf.d/60-bta-console.conf` | console graph (Bluetooth headphone only, smart filter) |

Persistent settings outside the session: card profile `a2dp-sink` · `bluetooth.autoswitch-to-headset-profile=false`.
User data lives outside the repo: `~/.config/bt-audio-hifi/` · `~/.local/state/bt-audio-hifi/` · `~/.local/share/bt-audio-hifi/`.

## Undo

```bash
bin/bta uninstall                                                   # drop-ins (those whose sha matches) + restart
wpctl settings --save bluetooth.autoswitch-to-headset-profile true
```

## Tests

```bash
tests/run.sh            # unit + browser (headless, no sound)
tests/run.sh --live     # + live/headful (real PipeWire; measurements on a null sink, no tones mixed into the headphone)
```
