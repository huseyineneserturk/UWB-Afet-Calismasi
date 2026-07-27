[← Kategori](README.md) · [Güvenli kullanım](sinirlamalar.md)

# Kaynakça

Çalışırken yararlandığım veri seti, makale ve belge bağlantılarını bu sayfada topladım.

## Veri setleri

### Rescuer 2023 — bu projede kullanılan sürüm

**Uzunidis, D.; Kasnesis, P.; Margaritis, E.; Patrikakis, C. Z.; Mitilineos, S.**

*Signs of life detection behind obstacles using an UWB radar sensor.* Zenodo, 2023.

- [Resmî Zenodo kaydı](https://doi.org/10.5281/zenodo.7679165)
- Lisans: [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/)
- Projedeki kullanımı: Veri sözlüğü, ilk model, hata analizi ve karar eşiği çalışması

Resmî kayıt; dokuz katılımcı, X4M200 radar, 0,5–5 m mesafe, yaklaşık 17 örnek/sn ve duvarlı/duvarsız ölçümleri açıklar.

### Rescuer veri setini tanıtan yayın

**Uzunidis, D.; Margaritis, E.; Chatzigeorgiou, C.; Patrikakis, C. Z.; Mitilineos, S. A.**

*A Dataset for Aftermath Victim Detection Behind Walls or Obstacles Using an UWB Radar Sensor.* MOCAST, 2023.

- [DOI: 10.1109/MOCAST57943.2023.10176448](https://doi.org/10.1109/MOCAST57943.2023.10176448)
- Projedeki kullanımı: Rescuer deney düzeni ve veri toplama açıklaması

### Rescuer 2024 — devam veri seti

**Uzunidis, D.; Kasnesis, P.; Patrikakis, C. Z.; Mitilineos, S. A.**

*Machine Learning-based Human Life Detection Behind Walls Exploiting a UWB Radar Sensor.* Zenodo, 2024.

- [Resmî Zenodo kaydı](https://doi.org/10.5281/zenodo.10779256)
- Projedeki kullanımı: Yalnızca gelecek çalışma notu

Bu sürüm başlangıç modeliyle birleştirilmemiştir. Farklı duvar kalınlıkları, oturumlar ve solunum referansları içerir.

### MobiVital

**Wang, Z.; Hua, D.; Jiang, W.; Xing, T.; Chen, X.; Srivastava, M.**

*MobiVital: Self-supervised Time-series Quality Estimation for Contactless Respiration Monitoring Using UWB Radar.* 2025.

- [Teknik rapor / arXiv](https://arxiv.org/abs/2503.11064)
- [ACM DOI](https://doi.org/10.1145/3722570.3726878)
- [Veri DOI’si](https://doi.org/10.5281/zenodo.15022885)
- [Kod deposu](https://github.com/nesl/mobivital-public)
- Lisans: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- Projedeki kullanımı: Henüz modellenmeyen UWB solunum kalitesi veri setinin tanıtımı

### OMuSense-23

**Lage Cañellas, M. ve diğerleri.**

*OMuSense-23: A Multimodal Dataset for Contactless Breathing Pattern Recognition and Biometric Analysis.* 2024.

- [Makale / arXiv](https://arxiv.org/abs/2407.06137)
- [Güncel Zenodo v3 kaydı](https://doi.org/10.5281/zenodo.12705176)
- [TI IWR1443 ürün sayfası](https://www.ti.com/product/IWR1443)
- Lisans: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)
- Projedeki kullanımı: Henüz modellenmeyen poz ve nefes etkinliği veri setinin tanıtımı

## Afet ve radar bağlamı

### RESCUER projesi

Avrupa Komisyonu, Horizon 2020 — Grant Agreement `101021836`.

- [CORDIS proje sayfası](https://cordis.europa.eu/project/id/101021836)
- Projedeki kullanımı: Rescuer veri setinin araştırma bağlamı

### INACHUS projesi

Avrupa Komisyonu, FP7 — Grant Agreement `607522`.

- [CORDIS sonuç ve raporlama sayfası](https://cordis.europa.eu/project/id/607522/reporting)
- Projedeki kullanımı: Gerçek arama-kurtarma bağlamı, çoklu sensör yaklaşımı, saha testi ve etik gereksinimler

### Radar teknolojileri incelemesi

**Uzunidis ve diğerleri.**

*Detection of trapped victims behind large obstacles using radar sensors: a review on available technologies and candidate solutions.*

- [DOI: 10.1109/CAMA57522.2023.10352910](https://doi.org/10.1109/CAMA57522.2023.10352910)
- [Zenodo kopyası](https://zenodo.org/records/12741116)
- Projedeki kullanımı: Enkaz senaryosu ve radar teknolojilerinin genel sınırları

## Makine öğrenmesi

### Karar eşiği

- [scikit-learn — Tuning the decision threshold for class prediction](https://scikit-learn.org/stable/modules/classification_threshold.html)
- Projedeki kullanımı: Eğitim, doğrulama ve test ayrımının korunması; eşik seçiminin ayrı doğrulama verisiyle yapılması

### Değerlendirme ölçümleri

- [scikit-learn — Metrics and scoring](https://scikit-learn.org/stable/modules/model_evaluation.html)
- Projedeki kullanımı: Dengeli doğruluk, kesinlik, insan yakalama ve F1 ölçümleri

## Yazılım ortamı

### Python sanal ortamı

- [Python belgeleri — Virtual Environments and Packages](https://docs.python.org/3/tutorial/venv.html)
- Projedeki kullanımı: Projeyi çalıştırma rehberindeki izole Python ortamı

## Atıf notu

Veri seti başka bir rapor veya sunumda kullanılırsa Zenodo sayfasındaki atıf ve lisans bilgilerine bakılmalıdır. Bağlantıları son olarak **26 Temmuz 2026** tarihinde kontrol ettim.

---

[← Güvenli kullanım](sinirlamalar.md) · [Ana sayfa](../../README.md)
