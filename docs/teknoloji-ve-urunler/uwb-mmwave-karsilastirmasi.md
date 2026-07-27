[← Teknoloji ve ürünler](README.md)

# UWB ve mmWave Karşılaştırması

![UWB ve mmWave görev karşılaştırması](../../assets/images/teknoloji/uwb-mmwave-karsilastirma.svg)

UWB ve mmWave birbirinin doğrudan yerine geçen iki teknoloji değildir. Hangisinin uygun olduğu ortama ve yapılacak işe bağlıdır.

## Önce küçük bir ayrım

**UWB**, sinyalin çok geniş bir bant kapladığını anlatır; tek başına belirli bir merkez frekans anlamına gelmez. Göçük aramasında incelenen UWB/GPR ürünleri çoğunlukla daha düşük merkez frekanslarını derinlik avantajı için kullanır.

**mmWave** ise genellikle 30–300 GHz arasındaki çok yüksek frekans bölgesini ifade eder. Endüstriyel sensörlerde 60 ve 77 GHz çevresi yaygındır.

## Göreve göre fark

| Başlık | UWB / GPR yaklaşımı | mmWave yaklaşımı |
|---|---|---|
| Öncelik | Engel arkasına ulaşmak | Yakın alanı ayrıntılı algılamak |
| Güçlü yön | Moloz ve duvar arkasında tarama | Küçük hareket, konum, hız ve açı |
| Zayıf yön | Daha sınırlı ayrıntı | Yoğun malzemede daha fazla zayıflama |
| Uygun örnek | Göçük altında yaşam belirtisi arama | Hasarlı yapı içi boşluk ve robot algısı |

## Frekans, derinlik ve çözünürlük dengesi

Genel olarak frekans yükseldikçe daha küçük ayrıntılar ayırt edilebilir; fakat malzeme içindeki zayıflama da artabilir. Daha düşük frekans daha derine ulaşabilir, ancak ayrıntı azalır.

Bu basit kural tek başına ürün seçmeye yetmez. Nem, metal, beton yapısı, anten, gönderim gücü ve sinyal işleme yöntemi de sonucu etkiler.

## Afet senaryosundaki görev paylaşımı

- **UWB/GPR:** Enkaz üzerinde ilk ve geniş alan taraması
- **mmWave:** Yakın mesafede hassas hareket ve konum incelemesi
- **Diğer sensörler:** Radar bulgusunu doğrulama

Benim çıkardığım sonuç, birinin diğerinden tamamen daha iyi olmadığıdır. İkisi farklı aşamalarda işe yarayabilir.

## Kaynaklar

- [47 CFR §15.503 — UWB tanımları](https://www.ecfr.gov/current/title-47/chapter-I/subchapter-A/part-15/subpart-F/section-15.503)
- [Sensors & Software — GPR frekans, derinlik ve çözünürlük ilişkisi](https://www.sensoft.ca/range-of-gpr/)
- [Texas Instruments — mmWave radar geliştirme kaynakları](https://www.ti.com/design-development/embedded-development/mmwave-radar.html)

---

[← Kategori](README.md) · [Sonraki: Radar ürünleri →](arama-kurtarma-urunleri.md)
