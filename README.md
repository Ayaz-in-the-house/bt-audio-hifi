<p align="center"><img src="assets/icon.svg" width="96" alt="bt-audio-hifi"></p>

# bt-audio-hifi

**English** · [Türkçe](README.tr.md)

Tools that make a **Bluetooth headphone** on Linux (Fedora 44 · PipeWire 1.6.8 · WirePlumber 0.5.14) sound its best —
measurably and reversibly: stay on the high-quality profile, measure codecs, a **professional EQ console** (10 bands you
drag on the graph, spatial controls, 31 presets, live analyzer), **working copies saved the moment you touch a control**
(undo/redo), an **auto mode that recognises the music and picks the setting itself**, and an admin page.

Reference device: Solix Nexus ANC (TWS, AAC/SBC). It works with other Bluetooth headphones too; speaker/HDMI/USB outputs
are intentionally left untouched ([why](docs/USER-DECISIONS.md#0-önce-kısa-cevap-bu-proje-tüm-çıkış-aygıtlarını-yönetir-mi)).

**License: [MIT](LICENSE)** — anyone may use, modify and redistribute it. Third-party components: [NOTICE](NOTICE.md).

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

Requires: Python 3.11+, numpy, scipy · onnxruntime for auto mode · playwright for the tests.

## What it does

| | feature | where |
|---|---|---|
| 🎧 | Headphone always on A2DP (high quality); an app opening the microphone does not drop audio to mono 16 kHz | automatic |
| 📡 | Codec measurement (AAC / SBC), link health, blind ABX listening test | `bta bench` · `bta link-test` · `bta abx` |
| 🎛️ | 10-band parametric EQ (drag on the graph), crossfeed, width, balance, 31 sourced presets | console |
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

## Roadmap — layers not yet analysed

The software side (upper part of L2 and L3–L6) has been mapped with its classes and states. The inside of the headphone
(chip, DSP, DAC, ANC, TWS) and the lower layers of the radio/protocol stack have not. That is also where the question
"are we using the hardware's full potential?" is mostly answered — for example, we do not know whether the headphone
applies its own EQ or limiter internally.

| layer | what we know | what is missing |
|---|---|---|
| Acoustics / driver | — | Not analysed as its own layer. |
| Chip / microcontroller / DSP | Vendor identified (Bluetrum, from LMP) | Internal DSP chain, own volume limit, firmware version. Never written up as a separate layer — two lines inside L1. |
| TWS (transfer between the two earbuds) | — | Never studied: does audio go to the primary earbud, how is it relayed to the other one, latency and loss. |
| Bluetooth radio / protocol stack (radio layer, LMP, L2CAP, AVDTP) | AX210 adapter, BlueZ 5.87, profile and disconnect behaviour | No radio capture (btmon) taken yet — it needs sudo. Wi-Fi coexistence not measured. Protocol state machines not documented. |
| A2DP / codec | Strong: AAC and SBC decoded byte by byte, SBC-XQ measured and ruled out, quality compared | The AAC ↔ SBC decision is pending the blind ABX test. |
| Linux / PipeWire / bta / UI (L3–L6) | Detailed: processes, graph, resampler, API, state transitions | Small gray areas. |

Plan: split L1 and L2 into separate layers and fill each one with the same template — options, states, variables and
measurement method:

- [ ] **L1a** acoustics and driver
- [ ] **L1b** chip, firmware, DSP, DAC, amplifier and ANC — start here, the most unknowns are in this layer
- [ ] **L1c** TWS relay
- [ ] **L2a** radio and LMP
- [ ] **L2b** L2CAP and AVDTP
- [ ] **L2c** A2DP and codec

Sources: chip-vendor SDK documents and manuals, the Bluetooth Core Specification, and measurements on the device. The
radio capture needs one root command (`sudo bash tools/btmon-capture.sh 60`, then `bta btmon-report`).
