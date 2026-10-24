# Kanıtlanmış yollar

## GP1 — BT ses durumunu tek komutta gör
```bash
~/projects/bt-audio-hifi/bin/bta status      # profil, codec, transport baytları çözülmüş, akışlar, varsayılanlar
~/projects/bt-audio-hifi/bin/bta check       # kabul kontrolleri (exit 0 = hepsi geçti)
```

## GP2 — Codec'in GERÇEK konfigürasyonunu oku (tahmin etme)
```bash
busctl --json=short get-property org.bluez /org/bluez/hci0/dev_<MAC_>/sepN/fdM org.bluez.MediaTransport1 Configuration
```
Baytları `btaudio.codecs.decode(codec_id, bytes)` ile çöz. Bitfield düzeni: PipeWire `a2dp-codec-caps.h` LE bölümü.

## GP3 — "Varsayılan çıkışı kim değiştirdi?" sorusunu ölç
```bash
pw-metadata -n default -m 0 | while read -r l; do echo "$(date +%T.%3N) $l"; done
```
`default.audio.sink` = WirePlumber'ın etkin seçimi · `default.configured.audio.sink` = bir istemcinin açık isteği.
Aynı ms'lerde ikisi farklı değer alıyorsa: WP önceliğe göre seçti, ardından bir istemci üzerine yazdı.

## GP4 — Durum geçişini kaydet ve karşılaştır
```bash
bta snapshot <etiket>   # önce
# … değişiklik …
bta snapshot <etiket>   # sonra
bta diff                # son iki snapshot; uçucu alanlar (pil, zaman) yok sayılır
```

## GP5 — Config değişikliği → en küçük yeniden başlatma
`bta install` değişen yola göre: `pipewire-pulse.conf.d` → yalnız `pipewire-pulse` · `client.conf.d` → hiçbiri ·
`wireplumber/` → `wireplumber` · `pipewire.conf.d` → üçü birden.

## GP6 — Bas ayarı (kullanıcı dostu yol)
```bash
bin/bta bass-tune        # sayfa Zen'de açılır; müziğini çal → hazır ayar → kaydırıcı → "EQ'suz dinle" → Kaydet
bin/bta bass-off         # geri al
```
Filtre kontrolleri çalışırken değişir (`pw-cli set-param <effect_input id> Props '{ params = [ "eq_band_1:Gain" 6.0 ] }'`),
servis yeniden başlatılmaz. Geri okuma: düğümün `eq_band_1:Gain` içeren Props nesnesi.

## GP7 — Kullanıcıya ölçüm yaptırma dersi
Laik kullanıcıya psikoakustik eşleştirme görevi verme; **kendi müziğiyle anında duyulan tercih ayarı** ver.
Her kullanıcı-girdili ölçüme inandırıcılık kapısı koy (yanlış EQ, EQ'suzdan kötüdür).
## GP8 — Canlı ölçü aleti ekleme (analizör)
1) Ölçü aletini önce SAYISAL test et (tam ölçek sinüs = 0 dBFS, pembe gürültü eğimi, mutasyonla testin yakaladığını gör).
2) Ürün katmanında null sink'te kopya grafla doğrula (post−pre = model; T-L34 0,042 dB).
3) Gerçek yolda salt-okuma kanıtı (bağ listesi: yalnız monitör/çıkış portları; kullanıcı dinliyorsa ton çalma).
4) Yaşam döngüsü: abone yokken süreç YOK (U46) + düğüm adları örnek başına benzersiz (E19).
## GP9 — Commit kapısı
Test çıktısını boruya verip `&& git commit` YAPMA; `rc=$?` yakala, `[ $rc -eq 0 ] && git commit`. (E18)
## GP10 — Otomasyonu kullanıcının ayarına KARIŞTIRMADAN eklemek
Otomatik düzeltmeyi durumun kendisine yazma: **üst katman** olarak tut (`Session.auto_offsets`), sese giden durum =
kullanıcı durumu + katman (`_effective`). Kullanıcı dokununca katman kaydedilen profile sızmaz (U58); kapatınca/kapanışta
katman kalkar; elle dokunuş otomasyonu askıya alır; otomatik yükleme geri alınabilir (nav geçmişi).
## GP11 — Arka plan özelliği eklemeden önce maliyetini ÖLÇ
Canlı akışta kararları sahte uygulayıcıya yönlendir (kullanıcının sesi değişmez), 30 sn süreç + çocuk CPU zamanını ölç
(T-L40). İlk ölçüm %15 → darboğaz blok başına FFT (1,6 ms) + true-peak (1,4 ms) → "yalnız otomasyon" aboneliği için hafif
mod (tek dokunuş, istek anında FFT) → %2,3. Tahmin değil profil: `time.perf_counter` ile blok başına maliyet.
## GP12 — Belge güncelliğini test yap
Modül belgeleri kaynaktan üretilir (`tools/gen-docs.py`: docstring + imza + içe aktarım + testler), U67 bayatlığı,
kimlik tekliğini, katman belgelerinin bölümlerini ve bağlantıları denetler. Açıklamayı değiştirmek = docstring'i değiştirmek.
## GP13 — Canlı konsolu sesi bozmadan yeniden başlatmak
`GET /api/state` → `state` JSON'a · aktif profil kimliğini not et · `POST /api/quit` · eski sürecin çıktığını PID ile doğrula ·
(E23 öncesi koddan geliyorsa) yetim `pw-cli`'yi PID ile sonlandır · `setsid nohup bin/bta console --port N --no-open
--initial <json> --profile <id>` · `/api/state` ile durumun birebir aynı olduğunu karşılaştır ·
sayfayı kullanıcının Zen'inde AJAN açar: `zen --new-tab http://127.0.0.1:<port>/` (E28).
