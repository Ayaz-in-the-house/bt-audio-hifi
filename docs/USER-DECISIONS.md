# Senden bekleyen kararlar — sade Türkçe

> Bu dosya teknik bilgi GEREKTİRMEZ. Her karar için: **ne**, **neden sana kalıyor**, **tam olarak ne yapacaksın**,
> **neye dikkat edeceksin**, **sonucu nasıl okuyacaksın**. Uygulama bu kararları senin yerine veremez: ya kulağın
> gerekir, ya bilgisayarın yönetici (sudo) şifresi, ya da kişisel tercih.
>
> Son güncelleme: 2026-09-28

## 0. Önce kısa cevap: "Bu proje tüm çıkış aygıtlarını yönetir mi?"

**Hayır — bugün tek seferde tek bir Bluetooth kulaklığı yönetir.** Ayarlar (EQ, bas, uzay, otomatik mod) yalnız o an
bağlı Bluetooth kulaklığa uygulanır. Dizüstünün hoparlörü, HDMI ekran, USB dock ya da kablolu kulaklıktan gelen sese
**hiç dokunulmaz** — bilerek: kulaklık için yapılmış bir bas ayarı hoparlörde yanlış ve zararlı olur.

- Başka bir Bluetooth kulaklık bağlarsan: çalışır (kurulum bağlı olanı bulur), ama ölçümler ve güvenlik eşikleri bu
  kulaklığa göre yapıldı.
- "Her aygıta kendi profili" (hoparlöre ayrı, kulaklığa ayrı) henüz yapılmadı — gri alan, tasarımı hazır
  ([L4 §Aygıt kapsamı](layers/L4-pipewire.md#aygıt-kapsamı)).

## 1. AAC mı SBC mi?

**Ne:** Bluetooth sesi kablosuz gönderebilmek için **sıkıştırır** (tıpkı MP3 gibi). Bu sıkıştırmanın yöntemine *codec*
denir. Senin kulaklığın iki yöntem biliyor:

| | AAC (şu an bu) | SBC |
|---|---|---|
| ne | Apple'ın da kullandığı, daha "akıllı" sıkıştırma | Bluetooth'un zorunlu, eski ama sağlam yöntemi |
| bu bağlantıda ölçülen | ~262 kbps, **17 kHz üstünü keser** (kesim 17 039 Hz) | ~357 kbps, **kesmez** (24 kHz'e kadar taşır) |
| ölçülen bant gürültü oranı (algısal DEĞİL) | 20 Hz–20 kHz 15,3 dB · 16–20 kHz 1,3 dB | 20 Hz–20 kHz 19,7 dB · 16–20 kHz 11,1 dB |
| bağlantı sağlığı | temiz | temiz |

**Neden sana kalıyor:** İki bağlantı da temiz (paket atlama yok). Sayılar SBC'yi öne koyuyor, ama bu ölçüm **algısal
değil**: AAC, kulağın zor duyduğu bilgiyi bilerek atar; ölçüm bunu "kayıp" sayar, kulak çoğu zaman saymaz. Üstelik
insanların çoğu 17 kHz üstünü zaten duymaz (yaşla azalır). Farkı **duyup duymadığın** yalnız kulağınla anlaşılır —
bu yüzden karar **kör testle** verilir. (Kaynak: `analysis/encoder-benchmark-20260927-193307.md`.)

**Ne test etmiyorsun:** bas, derinlik, "dolgunluk". Codec'ler bası neredeyse aynı taşır; bas farkı EQ'dan ve kulak
tıkacının oturmasından gelir. Bu testte bası dinleme.

**Neye dikkat et (farkın çıktığı yerler):**
- zillerin, hi-hat'in **"tss"** sesi: parlak ve temiz mi, yoksa hışırtılı, "metalik", "su altında" gibi mi?
- vokaldeki **"s" ve "ş"** sesleri, nefesler
- alkış, yağmur, kalabalık gibi gürültülü sesler (sıkıştırma en çok bunlarda zorlanır)
- yankının kuyruğu (şarkı biterken sönen reverb) doğal mı, "cızırtılı" mı?
- sessiz kısımlarda arka planda "fokurdama" var mı?

**Tam olarak ne yapacaksın (konsolda, terminal gerekmez — 2026-09-28'den beri):**
1. Tarayıcıda **ziller, vokal ve alkış içeren** sevdiğin bir parçayı çal.
2. Konsol → **Analiz** sekmesi → **Kör dinleme testi** → *Testi başlat…* → **Çalan müzikten 12 sn al**
   (müziğin sıkıştırılmadan önceki hâli alınır, bilgisayarından çıkmaz).
3. Müziği **durdur** (pencere başka ses çalıyorsa uyarır) → **Teste başla**.
4. Her denemede **▶ A** (AAC) ve **▶ B** (SBC) dinle, sonra **▶ X**: X hangisine benziyor? **X = A** ya da **X = B**.
   Her çalmadan önce 1–2 sn sessizlik normaldir (kulaklık yöntem değiştiriyor — sıra hep aynı, ipucu değildir).
   İstediğin kadar tekrar dinleyebilirsin; emin değilsen tahmin et.
5. 12 deneme sonunda sonuç sade dille gelir. Fark varsa hangisinin daha iyi olduğunu seç → **kalıcı olsun**.
   Vazgeçersen ya da iptal edersen kulaklık testten önceki codec'e döner. Test boyunca otomatik mod askıdadır.
(Terminal isteyenler için: `bta abx aac sbc` — her klasörden çalışır.)

**Sonucu nasıl oku:**
- **12'de 10 ya da daha fazla doğru** → gerçekten bir fark duyuyorsun (şansla olma ihtimali %2'nin altında; araç
  "ayırt edilebilir" der). Hangisini daha iyi bulduğunu söyle, o kalıcı yapılır.
- **12'de 9 ya da daha az** → fark kanıtlanmadı (9/12'yi şansla tutturma ihtimali %7). **AAC'de kal** — şu anki ayar,
  bağlantı temiz. İstersen 12 deneme daha yap; karar toplam sonuca göre verilir.

## 2. Radyo ölçümü (btmon) — sudo ister

**Ne:** Bluetooth'un radyo trafiğini (paketler, sinyal gücü = RSSI, yeniden gönderimler) kaydeden bir ölçüm. Sesin
**kesilmesi, cızırdaması, kısa kopmalar** varsa nedenini bu katmanda gösterir.

**Neden sana kalıyor:** Bu kaydı yalnız yönetici (root) alabilir. Daha önce sohbete yazdığın şifre **kullanılmadı**
(güvenlik gereği; o şifreyi değiştirmeni öneririz). Komutu sen çalıştırırsın, şifreyi sen girersin.

**Gerekli mi?** Yalnız kesilme/cızırtı duyuyorsan. Duymuyorsan bu kararı **atlayabilirsin** — ses yolu bugün temiz ölçülüyor.

**Tam olarak ne yapacaksın:** müzik çalarken
```bash
cd ~/projects/bt-audio-hifi
sudo bash tools/btmon-capture.sh 60          # 60 saniye kayıt (bu sırada normal dinlemeye devam et)
bta btmon-report <komutun-yazdırdığı>.btsnoop   # ilk komut iki dosya yolu yazdırır: .btsnoop ve .rssi.txt
```
Rapor, sinyal gücünü ve yeniden gönderim sayılarını gösterir. Bana ilet, yorumlayayım.

## 3. 3B / HRTF paketi

**Ne:** Kulaklıkla dinlerken ses "kafanın içinden" gelir. **HRTF** (baş ile ilgili aktarım fonksiyonu), insan kulağının
ve kafasının sesi nasıl değiştirdiğinin ölçülmüş bir modelidir. Bununla ses, **önünde duran iki hoparlörden** geliyormuş
gibi yapılabilir. AirPods'taki "uzamsal ses"in temeli budur — ama AirPods ayrıca **kafa takibi** yapar (kafanı
çevirince ses yerinde kalır); bizde kafa hareketini ölçen sensör olmadığı için **kafa takibi yok**.

**Bugün ne var:** "Uzay" sekmesindeki **crossfeed** (hafif, doğal "hoparlör hissi") ve **genişlik** — ek paket gerektirmez.

**HRTF için ne gerekir:** Fedora paketi `pipewire-module-filter-chain-sofa` + bir **SOFA** veri dosyası (ölçülmüş kulak
seti). Kurulum `sudo dnf install …` ister.

**Karar:** "Evet dene" dersen: paketi kurarsın (komutu veririm), ben grafa isteğe bağlı bir "3B sahne" düğümü eklerim,
kör A/B ile crossfeed'e karşı dinlersin. Dürüst not: HRTF bazı insanlara çok doğal, bazılarına **bulanık ve tiz-kayıplı**
gelir, çünkü veri seti senin kulağından ölçülmemiştir. Bu tamamen kişisel tercih.

## 4. Otomatik mod — açalım mı?

**Ne:** Konsol → **Otomatik** sekmesi. Varsayılan **Kapalı**. Açarsan:
- **Otomatik profil:** çalan sesin türünü (elektronik, rock, konuşma…) bilgisayarda (internet YOK) tanır ve o türe
  bağladığın profili yumuşak geçişle yükler. Senin derin bas profilini "Elektronik"e bağlarsan, rock çalınca rock ayarına,
  sonra geri seninkine döner. Bağlamak için: Profillerim → ⋯ → **Tür etiketleri…**
- **Canlı uyarlama:** profilin kalır; bas/tiz dengesi ince kayıtlarda küçük ve yavaş bir düzeltme eklenir (en çok bas
  +4 dB). **Konuşmada hiçbir şey eklemez** — şu an dinlediğin anlatım videosu gibi içerikte sesi bozmaz.

Ölçüldü: anlatım videon "konuşma" olarak %82–92 güvenle tanındı; otomasyonun işlemci maliyeti tek çekirdeğin %2,3'ü.

**Karar:** açıp denemek sende. Elle dokunduğun an otomasyon 10 sn durur — kontrol her zaman sende.

## 5. Kulak tıkacı oturması (öneri, karar değil)

Konsol → Analiz → **Kulak tıkacı oturma testi**. Müziği durdur, "Bas tonu"nu çal, tıkaç boyunu değiştirip tekrarla:
bas tonunun **en dolgun** duyulduğu boy doğru boydur. Kulak içi kulaklıkta bu, bas için EQ'dan daha etkilidir.

## Karar sonuçlarını nereye yazıyoruz

Karar verince bana söylemen yeterli; `docs/STATE-LOG.md` ve `decision.json`'a işlenir.


## 2026-10-15 — PRD-BTA06 onayı ve bekleyenler

- **Onaylandı** (kullanıcı: *"onerilerini onayliyourm"*): sıra G0 ADL düzeltmesi → G1 otomatik mod servisi → G2 panelden
  aygıt seçimi → G3 kulaklık kanalı (salt-okuma).
- **Sende bekleyen:** kör dinleme testi (AAC ↔ SBC, ~5 dk) · oturma testi + tıkaç denemesi · T-L04 için birkaç saniyelik
  profil değiştir-geri al (ses kesilir; dinlemediğin bir an) · G3 için `sudo dnf install bluez-deprecated` (sdptool).
- **Komut gönderen SPP denemeleri** (ANC/EQ yazma) her adımda ayrıca sorulur — yanlış komut kulaklığı fabrika/güncelleme
  kipine sokabilir.
