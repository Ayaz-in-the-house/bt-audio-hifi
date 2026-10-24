# `btaudio/crossfade.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [infrastructure](../layers/L5-bta-software.md#infrastructure) |
| rol | Tıksız A/B geçiş sıralayıcı + kalıcı pw-cli oturumu |
| boyut | 174 satır |
| içe aktarır (iç) | [`console`](console.md), [`procs`](procs.md), [`tunerserver`](tunerserver.md) |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__`, `json`, `subprocess`, `threading`, `time` |
| kullanan modüller | [`cli`](cli.md), [`zipperverify`](zipperverify.md) |

## Amaç (modül docstring'i)

D2 — Tıksız geçiş sıralayıcısı (infrastructure).

Kurallar (R33'ün sonuçları):
1. Yeni durum YALNIZ sessiz zincire yüklenir; çalan zincire asla dokunulmaz.
2. Bir geçiş bitmeden (fade süresi dolmadan) sessizleşmekte olan zincir yeniden yüklenmez — aksi hâlde hâlâ duyulan
   zincirin belleği sıfırlanır (tık). Bu yüzden istekler sıralanır; bekleyenlerden yalnız EN SONUNCUSU uygulanır.
3. `submit` çağıranı asla bloklamaz (istek yolu pw-cli beklemez) — iş parçacığı + koşul değişkeni.

## Sabitler

| ad | değer |
|---|---|
| `STEP_S` | `0.012` |

## Genel API

### `class PwCliSession`

Tek kalıcı `pw-cli` süreci (stdin'den komut): her adım için süreç doğurmak ~20 ms sürer, geçişi bozardı.

- `__init__(self, node_name: str)`
- `apply_payload(self, payload: str)` — Props yükünü kalıcı pw-cli oturumuna yazar; oturum yoksa düğümü çözüp başlatır.
- `close(self)` — pw-cli 1.6.8 stdin EOF'unda ÇIKMAZ, döner (E23, ölçüldü) → önce `quit`, sonra kapat, sonra zaman aşımı.

### `class Crossfader`

A/B zincirli tıksız geçiş sıralayıcısı: yeni durum sessiz zincire yüklenir, toplama kazançları 12 ms adımlarla kaydırılır; istekler birleşir, en sonuncusu kazanır.

- `__init__(self, applier, fade_s: float=0.04, clock=time.monotonic, active: str='A')`
- `settle(self)` — Karışımı etkin zincire SABİTLE (açılışta, ilk yüklemeden önce). Önceki süreç yarı geçişte öldüyse iki zincir de duyuluyordur; sabitlemeden yüklemek duyulan zincirin belleğini sıfırlar → tık (U68).
- `apply_payload(self, payload: str)` — Zincirden bağımsız tek kazanç (U78 sınırlayıcı): geçişle aynı oturumdan, sıraya girmeden yazar.
- `submit(self, state: dict, bypass: bool=False, fade_s: float | None=None)` — Geçiş isteği kuyruğa (çağıranı bloklamaz); bekleyen önceki istek ezilir.
- `apply_state(self, state, bypass=False, fade_s=None)` — Session uyumluluğu: submit ile aynı.
- `wait_idle(self, timeout: float=5.0) -> bool` — Kuyruk boşalıp son geçiş bitene dek bekler (en çok timeout sn); boşaldıysa True.
- `close(self)` — İş parçacığını durdurur ve uygulayıcının pw-cli oturumunu kapatır (E23).

- `detect_active(node_name: str) -> str` — Çalan zinciri PipeWire'dan oku (sumL:Gain 2 > 0,5 → B). Sunucu yeniden başlarsa yanlış varsayım = duyulan zincire yükleme = tık.

## Testler

- [`tests/test_crossfade.py`](../../tests/test_crossfade.py) — U57, U68, U77
- [`tests/test_orphans.py`](../../tests/test_orphans.py) — U64
