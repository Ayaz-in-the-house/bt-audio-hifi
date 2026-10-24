# Skill testi (writing-skills TDD, 2026-09-27)

Senaryo (RED ve GREEN aynı): "Fedora 44 PipeWire 1.6, ucuz TWS; ses kötü, bas yok, kopunca hoparlörde kalıyor; en iyi
codec + bas EQ istiyorum" — ajan komut ÇALIŞTIRMADAN 12 adımlık plan yazar.

| kriter | RED (skill yok) | GREEN (skill var) |
|---|---|---|
| profil HFP + WP kalıcı kaydı + autoswitch kapat | kısmi (autoswitch'i kapatmıyor) | ✅ |
| transport baytlarından gerçek codec | ❌ | ✅ |
| yüksek bitrate codec'i link-test ile karar | ❌ ("LDAC>aptX>AAC>SBC-XQ", `enable-sbc-xq`) | ✅ |
| kopunca hoparlör → switch-on-connect | ❌ ("eski tarif, uygulama" — YANLIŞ) | ✅ (+ pw-metadata ölçümü) |
| önce tıkaç sızdırmazlığı | ❌ | ✅ |
| EQ yalnız kulaklığa (smart filter, ayrı servis) | ❌ (yeni sink + tüm PipeWire restart) | ✅ |
| preamp/kırpılma | ✅ | ✅ |
| ürün katmanında doğrulama | ❌ (yalnız dinleme) | ✅ (null sink + bağ listesi) |
| REFACTOR bulgusu | — | `filter.smart` yanlış yere (`node.properties`) → iskelet + tablo satırı eklendi |

## Tur 2 (2026-09-28) — canlı parametre değişimi / otomasyon bölümü

Senaryo (RED ve GREEN aynı): "PipeWire 1.6.8, smart filter + 10 bant `bq_raw` EQ kurulu; müzik çalarken türe göre EQ'yu
CANLI değiştiren Python otomatik modu ekle" — 5 soru (uygulama, profil ilişkisi, yardımcı süreç, tık ölçümü, CPU).
RED: taze alt ajan, dosya okuma yasak. GREEN: yalnız `SKILL.md` okuma izni.

| kriter | RED (skill yok) | GREEN (skill var) |
|---|---|---|
| canlı `set-param` her güncellemede belleği sıfırlar → A/B çift zincir ZORUNLU | ❌ "5–10 adımda interpolasyon" (1.6.8'de her adım tık), A/B yalnız "yedek" | ✅ A/B + mixer adımları, "küçük adım da tık" |
| `ramp` düğümü kullanılamaz | ❌ değinmedi | ✅ |
| otomatik düzeltme üst katman, profile yazılmaz | ✅ | ✅ |
| pw-cli `quit` ile kapanır (EOF'ta döner) | ❌ "stdin kapat, EOF ile kapanır" (YANLIŞ) | ✅ |
| PDEATHSIG iş parçacığı tuzağı | ❌ `preexec_fn` ile, tuzaktan habersiz | ✅ tek uzun ömürlü iş parçacığı |
| ölçümde smart filter monitör tuzağı + süzgeç başlangıç artefaktı | ❌ `pw-record --target <filter-output>` | ✅ elle `pw-link`, ilk pencere dışla |
| CPU: önce ölç, darboğaz FFT/true-peak | ❌ `nice`/`CPUQuota` | ✅ |
| REFACTOR bulgusu | — | "süreç yarı geçişte ölürse iki zincir de duyulur" → **açılışta karışımı etkin zincire sabitle** satırı + kod `Crossfader.settle` + U68 |

