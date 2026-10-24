# `btaudio/paths.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [infrastructure](../layers/L5-bta-software.md#infrastructure) |
| rol | XDG kullanıcı verisi yerleşimi + göç |
| boyut | 92 satır |
| içe aktarır (iç) | — |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__`, `glob`, `os`, `shutil` |
| kullanan modüller | [`cli`](cli.md), [`collect`](collect.md), [`console`](console.md), [`consoleserver`](consoleserver.md), [`identity`](identity.md) |

## Amaç (modül docstring'i)

C0 — Ürün / kullanıcı verisi ayrımı (XDG Base Directory).

Repo = ürün (kod, şablon config, belge). Kullanıcının ayarları ve üretilmiş config'ler repo DIŞINDA yaşar:
  profiller          $XDG_CONFIG_HOME/bt-audio-hifi/profiles/        (paylaşılabilir: dışa/içe aktar)
  kalıcı durum geçm. $XDG_STATE_HOME/bt-audio-hifi/console/*.json
  üretilmiş config   $XDG_STATE_HOME/bt-audio-hifi/generated/<~/.config ile aynı düzen>
`$BTA_HOME` verilirse her şey onun altında (testler gerçek kullanıcı verisine dokunmaz).
Neden: "Kalıcı yap" izlenen repo dosyasını yazıyordu → git kirleniyor, açık kaynakta kişisel ayar sızıyordu (PRD-BTA03).

## Sabitler

| ad | değer |
|---|---|
| `APP` | `'bt-audio-hifi'` |
| `GENERATED_RELS` | `('pipewire/filter-chain.conf.d/60-bta-console.conf', 'pipewire/filt…` |

## Genel API

- `profiles_dir() -> str` — Kullanıcı profilleri: $XDG_CONFIG_HOME/bt-audio-hifi/profiles.
- `trash_dir() -> str` — Profil çöp kutusu (.trash).
- `console_states_dir() -> str` — 'Açılışta kullan' durum geçmişi: $XDG_STATE_HOME/bt-audio-hifi/console.
- `backups_root() -> str` — Yedek kök yolu (oluşturmaz — yedek alınırken makedirs yapılır).
- `journal_dir() -> str` — Çalışma kopyası günlükleri: $XDG_STATE_HOME/bt-audio-hifi/journal.
- `auto_state_path() -> str` — Otomasyon (D3–D5) kalıcı durumu: mod + öğrenilen kişisel tonal referans + bas tercihi yoklaması.
- `generated_dir() -> str` — Durumdan üretilen PipeWire config'leri (kurulumdan önce).
- `migrate(repo: str) -> dict` — Eski yerleşimden (repo içi) yeni yerleşime KOPYALA. Kaynak silinmez; hedef varsa ezilmez; tekrar koşu no-op.

## Testler

- [`tests/test_paths.py`](../../tests/test_paths.py) — U40
