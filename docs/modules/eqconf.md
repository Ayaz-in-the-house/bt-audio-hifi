# `btaudio/eqconf.py`

> ÜRETİLMİŞ belge (`tools/gen-docs.py`) — elle düzenleme; açıklama için modül docstring'ini değiştir, betiği çalıştır.

| alan | değer |
|---|---|
| katman | [domain](../layers/L5-bta-software.md#domain) |
| rol | EQ tasarımı → filter-chain config metni |
| boyut | 89 satır |
| içe aktarır (iç) | [`console`](console.md) |
| içe aktarır (dış) | — |
| standart kitaplık | `__future__` |
| kullanan modüller | [`cli`](cli.md), [`eqverify`](eqverify.md) |

## Amaç (modül docstring'i)

F5/F8 — EQ tasarımını çalışır config'e çevirir.

1) BİRİNCİL: PipeWire filter-chain + WirePlumber 0.5 "smart filter". Yalnız hedef sink'e (bu kulaklık) giden
   akışlara uygulanır; hoparlör/Dock etkilenmez. Ek süreç: PipeWire'ın kendi filter-chain.service'i.
   bq_peaking = RBJ cookbook (PipeWire audioconvert/biquad.c:223) → btaudio.loudness.eq_response_db ile birebir.
2) İSTEĞE BAĞLI: EasyEffects 8 preset'i (aynı bantlar) — GUI ile deneme yapmak için; otomatik başlatılmaz.

## Sabitler

| ad | değer |
|---|---|
| `HEADER` | `'# bt-audio-hifi (PRD-BTA01 F8) — ÜRETİLMİŞ DOSYA, elle düzenleme: …` |

## Genel API

- `render_filter_chain(design: dict, target_sink: str, source: str='-') -> str`
- `render_ee_preset(design: dict) -> dict`

## Testler

- [`tests/test_eqconf.py`](../../tests/test_eqconf.py) — U25
