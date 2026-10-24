# `btaudio/procs.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [infrastructure](../layers/L5-bta-software.md#infrastructure) |
| rol | Alt süreç doğurma: ebeveynle ölen çocuklar (E23) |
| boyut | 62 satır |
| içe aktarır (iç) | — |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__`, `os`, `queue`, `shutil`, `subprocess`, `threading` |
| kullanan modüller | [`analyzer`](analyzer.md), [`analyzerverify`](analyzerverify.md), [`cli`](cli.md), [`consoleverify`](consoleverify.md), [`crossfade`](crossfade.md), [`eqverify`](eqverify.md), [`resample`](resample.md), [`tones`](tones.md), [`zipperverify`](zipperverify.md) |

## Amaç (modül docstring'i)

Alt süreç doğurma (infrastructure): hiçbir alt süreç ebeveyninden uzun YAŞAMAZ (E23, U64).

Neden: pw-cli 1.6.8 stdin EOF'unda çıkmaz, döner (ölçüldü: yetim pw-cli 1 saat %22 çekirdek). Ebeveyn ani ölürse
(SIGKILL, çökme) kapanış kodu çalışmaz → çekirdek düzeyinde bağ gerekir: PR_SET_PDEATHSIG.

TUZAK (U64 ayrıca test eder): PDEATHSIG ebeveyn SÜRECİ değil, fork eden İŞ PARÇACIĞI ölünce tetiklenir. Analizör ve
pw-cli kısa ömürlü HTTP istek iş parçacıklarından doğar → doğrudan orada Popen + PDEATHSIG = istek biter bitmez çocuk
ölür. Çözüm: tüm doğurmalar süreç ömrü boyunca yaşayan TEK bir "doğurucu" iş parçacığında yapılır.
PDEATHSIG `setpriv --pdeathsig` (util-linux) ile verilir → preexec_fn (iş parçacıklı süreçte güvensiz) gerekmez.

## Genel API

- `wrap(cmd: list) -> list` — Komutu `setpriv --pdeathsig TERM --` ile sarar (setpriv yoksa olduğu gibi).
- `spawn(cmd: list, **kw) -> subprocess.Popen` — subprocess.Popen ile aynı; fark: ebeveyn süreç ölünce çocuk SIGTERM alır (iş parçacığından bağımsız).
- `has_deathsig() -> bool` — Bu sistemde ebeveynle ölme bağı kurulabiliyor mu.

## Testler

- doğrudan test dosyası yok (dolaylı: kullanan modüllerin testleri) — **gri alan**
