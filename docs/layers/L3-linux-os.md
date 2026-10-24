# L3 — Linux işletim sistemi (Fedora, systemd kullanıcı servisleri, dosya yerleşimi)

> Katman haritası: [00-overview](00-overview.md) · altı: [L2 Bluetooth](L2-bluetooth.md) · üstü: [L4 PipeWire](L4-pipewire.md)
>
> Son doğrulama: 2026-09-28 (`systemctl --user is-active …` hepsi active; `bta check` T-L20 config sapması yok)

## Rol

Ses yığınını çalıştıran servisler, kalıcı ayar dosyaları ve bizim süreçlerimizin yaşam döngüsü. Kullanıcı verisi ile ürün
kodunu ayıran çizgi bu katmandadır (XDG).

## Durum

| öğe | değer |
|---|---|
| dağıtım / çekirdek | Fedora 44 · Linux 7.1.10-200.fc44.x86_64 |
| kullanıcı servisleri | `pipewire` · `wireplumber` · `pipewire-pulse` · `filter-chain` (hepsi `systemctl --user`, active) |
| Python | 3.14.7 · numpy 2.4.3 · scipy 1.17.1 · onnxruntime 1.24.3 (yalnız sınıflayıcı) · playwright 1.61.0 (yalnız test) |
| alt süreç koruması | `setpriv --pdeathsig TERM` (util-linux) — `procs.spawn` (E23) |
| donanım (bu makine) | 16 çekirdek, 15 GB RAM — ağır bellek baskısı ölçüldü (yük 20–50): tarayıcı testleri tek tek koşulabilir (K15) |

## Dosya yerleşimi (tek doğruluk kaynağı: [`btaudio/paths.py`](../modules/paths.md))

| ne | yol | kim yazar | paylaşılır mı |
|---|---|---|---|
| ürün (kod, şablon config, belge) | depo (`~/projects/bt-audio-hifi`) | geliştirici | evet (MIT) |
| kullanıcı profilleri | `$XDG_CONFIG_HOME/bt-audio-hifi/profiles/*.json` (+ `.trash/`, `.seq`) | konsol (arka plan yazıcı) | dışa aktar ile |
| çalışma kopyası günlükleri | `$XDG_STATE_HOME/bt-audio-hifi/journal/*.jsonl` (sürüm başına ≈2 KB satır) | `journal.Writer` | hayır |
| "açılışta kullan" geçmişi | `$XDG_STATE_HOME/bt-audio-hifi/console/*-committed.json` | `commit_console_state` | hayır |
| otomasyon ayarı + öğrenilen tercih | `$XDG_STATE_HOME/bt-audio-hifi/auto.json` | `AutoEngine.flush` | hayır |
| üretilmiş PipeWire config | `$XDG_STATE_HOME/bt-audio-hifi/generated/…` → kurulum → `~/.config/pipewire/*.conf.d/60-bta-*.conf` | `bta install` / konsol | hayır |
| yedekler | `$XDG_STATE_HOME/bt-audio-hifi/backups/` | install/uninstall/bass-off | hayır |
| sınıflayıcı modeli | `$XDG_DATA_HOME/bt-audio-hifi/models/` (sha256 kilitli) | `bta model fetch` | hayır (ayrı lisans: Apache-2.0) |
| cihaz hafızası | `$XDG_CONFIG_HOME/bt-audio-hifi/device` (son görülen MAC) | `collect._detect_mac` | hayır (kişisel) |

`$BTA_HOME` verilirse hepsi onun altına gider (testler gerçek kullanıcı verisine dokunmaz — U40).

## Değişkenler

| değişken | etkisi |
|---|---|
| `BTA_HOME` | tüm kullanıcı verisini tek köke taşır (test izolasyonu) |
| `BTA_DEVICE` | hedef kulaklık MAC'i (algılamayı ezer) |
| `BTA_CONFIG_DST` / `BTA_NO_RESTART` | kurulum hedefi / servis yeniden başlatmama (test) |
| `BTA_BROWSER` | konsolun açılacağı tarayıcı komutu |
| `XDG_*_HOME` | standart XDG kökleri |

## Süreç yaşam döngüsü (bizim süreçlerimiz)

| süreç | doğuran | ne zaman ölür |
|---|---|---|
| `bta console` (Python) | kullanıcı | `/api/quit`, 1 saat etkinliksizlik (otomasyon açıkken etkinlik sayılır), sinyal |
| `pw-cli` (kalıcı, geçiş yazıcısı) | `Crossfader` | kapanışta `quit`; ebeveyn ölürse SIGTERM (E23) |
| `pw-record` × 1–2 (analizör) | `Analyzer` | son abone gidince 2 sn sonra; ebeveyn ölürse SIGTERM |
| `pw-play` (oturma tonu) | `tones.player` | süre dolunca / Durdur |

⛔ Kullanıcının uygulamalarına (tarayıcı, terminal) hiçbir yol kill göndermez — yalnız kendi alt süreçlerimiz.

## Gri alanlar

| alan | durum |
|---|---|
| diğer dağıtımlar (Ubuntu, Arch, Debian) | denenmedi; PipeWire ≥ 1.6 + WirePlumber ≥ 0.5 smart filter gerekir |
| askıya alma / uyanma sonrası graf | test edilmedi |
| çok kullanıcılı makine | tasarım tek kullanıcı (127.0.0.1, kullanıcı servisleri) |
| systemd servisi olarak konsol (her açılışta otomasyon) | yok — konsol elle açılır; "açılışta kullan" yalnız EQ'yu kalıcı yapar |

## Testler

U40 (XDG izolasyonu + göç) · U49 (açılışta kullan repoyu kirletmez) · U10/T-L20 (config manifesti) · U64 (yetim süreç) ·
T-L37 (canlı kalıcılık) · T-H40 (kaldırma — gri, yazılmadı).

## Nasıl ölçülür

```bash
systemctl --user is-active pipewire wireplumber pipewire-pulse filter-chain
bin/bta check                                      # T-L20 config sapması, T-L24 kurulu-ama-etkin-değil
ls ~/.config/pipewire/*.conf.d/60-bta-*            # kurulu drop-in'ler
pgrep -a pw-cli; pgrep -af 'pw-record.*bta_analyzer'   # bizim alt süreçlerimiz
```
