# Pilot deney raporu

## Araştırma sorusu

Aynı dönemdeki mekânsal sıcaklık dağılımı ile gelecek MODIS döneminin sıcaklığı ayrı deneylerde değerlendirildi. Aşağıdaki sayılar paketteki gözlemler ve bağımsız test tahminlerinden hesaplandı.

## Örnekleme ve kalite

| İl | Landsat | Sentinel-2 | Aday | Geçerli |
|---|---|---|---|---|
| Antalya | 2023-08-29 | 2023-08-29 | 400 | 255 |
| Erzurum | 2023-08-27 | 2023-08-27 | 400 | 393 |
| İstanbul | 2023-08-03 | 2023-08-02 | 400 | 389 |

Her mekânsal örnekleme alanı 6 × 6 km’dir. 300 m hücrede geçerli Landsat piksel oranı ve geçerli optik indis piksel oranı ayrı ayrı en az %70 olmalıdır. Landsat QA_PIXEL bit 0–5 ve doygunluk, Sentinel-2 SCL sınıfları ile filtreleme uygulandı. Sentinel verisi aynı güne veya ±3 gün içindeki en yakın uygun sahneye aittir. NDVI ve NDBI 20 m örnekleme ızgarasında hesaplanıp hücreye ortalandı. Skadi yükseklik örnekleri ve eğimler yaklaşık hücre ayak izi üzerinden toplandı.

| İl | Enlem | Boylam | Kaynak dönemi | Kaliteyi geçen |
|---|---|---|---|---|
| Antalya | 36,89 | 30,70 | 1057 | 1027 |
| Erzurum | 39,90 | 41,27 | 1057 | 812 |
| İstanbul | 41,05 | 28,86 | 1057 | 719 |

2003–2025 aralığındaki 1.058 beklenen kompozit tarihinden 16 Ekim 2022 kaynak yanıtında bulunmadı. Model dizisi yıl başına 46 takvim yuvası içerir. Sıcaklık için pozitif geçerli ham ölçüm, üretilmiş LST (zorunlu QA 0 veya 1), iyi veri kalitesi ve hata sınıfı ≤2 K kullanıldı. İlk denemede İstanbul (41,02; 28,97) koordinatında tüm ölçümler dolgu değeriydi. Zaman serisi noktası Esenler yönünde karaya taşındı. Mekânsal ve zamansal koordinatlar bu nedenle farklıdır. Bu tek piksel serilerinden il ortalaması çıkarılamaz.

## Mekânsal sonuçlar

Diğer iki pilotta eğitim, mekânsal bloklarla iç doğrulama ve dışarıda tutulan ilde bağımsız test yapıldı. Her pilot için yalnızca bir yaz sahne çifti olduğundan bölge etkisi ile tarih etkisi birlikte değişebilir. A grubu indisleri, B grubu ayrıca rakım ve eğimi içerir.

### Grup A

| İl | Model | n | MAE °C | RMSE °C | R² |
|---|---|---|---|---|---|
| Antalya | LinearRegression | 255 | 11,34 | 17,94 | -12,38 |
| Antalya | RandomForest | 255 | 3,82 | 4,34 | 0,22 |
| Antalya | XGBoost | 255 | 3,55 | 3,97 | 0,34 |
| Erzurum | LinearRegression | 393 | 6,44 | 7,49 | -12,40 |
| Erzurum | RandomForest | 393 | 7,52 | 7,86 | -13,73 |
| Erzurum | XGBoost | 393 | 7,40 | 7,71 | -13,21 |
| İstanbul | LinearRegression | 389 | 10,11 | 10,88 | 0,05 |
| İstanbul | RandomForest | 389 | 8,20 | 8,92 | 0,36 |
| İstanbul | XGBoost | 389 | 8,57 | 9,31 | 0,30 |

### Grup B

| İl | Model | n | MAE °C | RMSE °C | R² |
|---|---|---|---|---|---|
| Antalya | LinearRegression | 255 | 9,94 | 16,98 | -10,99 |
| Antalya | RandomForest | 255 | 4,61 | 5,18 | -0,12 |
| Antalya | XGBoost | 255 | 3,48 | 4,03 | 0,33 |
| Erzurum | LinearRegression | 393 | 271,84 | 272,08 | -17673,55 |
| Erzurum | RandomForest | 393 | 7,85 | 8,12 | -14,73 |
| Erzurum | XGBoost | 393 | 7,85 | 8,12 | -14,74 |
| İstanbul | LinearRegression | 389 | 9,50 | 10,51 | 0,11 |
| İstanbul | RandomForest | 389 | 6,23 | 6,99 | 0,61 |
| İstanbul | XGBoost | 389 | 6,55 | 7,28 | 0,57 |

Erzurum dışarıda tutulduğunda B grubundaki doğrusal regresyonun RMSE değeri 272 °C’yi geçti. Eğitimdeki iki kıyı alanı 100 m’nin altında kalırken Erzurum test hücrelerinin rakımı yaklaşık 1.800–2.190 m’dir. Bu sonuç doğrusal modelin eğitim aralığı dışına taşındığında yaptığı hatayı gösterir. Bu model bölgesel tahmin hizmetinde kullanılmamalıdır.

## Zamansal sonuçlar

Takvimde bir önceki yılın aynı kompoziti Seasonal Naive referansıdır. XGBoost ve LSTM tek bir modelde üç pilotu birlikte öğrenir. Girdide ufuk bilgisi vardır. Ölçekleme eğitim gözlemlerinden öğrenildi. En çok üç dönemlik ileri taşıma ve gözlem maskeleri kullanıldı, kalan eksikler ölçeklenmiş uzayda sıfırlandı. Gerçek test hedefleri doldurulmadı. Tüm yöntemler mevsimsel referansın da mevcut olduğu aynı test satırlarında karşılaştırıldı. n geçerli eşleşme sayısıdır.

### Yalnızca geçmiş LST

| Model | Seçilen pencere | Doğrulama RMSE °C |
|---|---|---|
| LSTM | 24 | 3,12 |
| XGBoost | 24 | 3,48 |

16 günlük nominal ufuk için bağımsız test:

| İl | Model | n | MAE °C | RMSE °C | R² | Referansa göre iyileşme % |
|---|---|---|---|---|---|---|
| Antalya | LSTM | 91 | 2,33 | 3,51 | 0,87 | 19,46 |
| Antalya | SeasonalNaive | 91 | 2,67 | 4,36 | 0,80 | 0,00 |
| Antalya | XGBoost | 91 | 2,34 | 3,87 | 0,84 | 11,30 |
| Erzurum | LSTM | 66 | 3,09 | 4,00 | 0,92 | 18,89 |
| Erzurum | SeasonalNaive | 66 | 3,76 | 4,93 | 0,88 | 0,00 |
| Erzurum | XGBoost | 66 | 2,84 | 3,66 | 0,93 | 25,80 |
| İstanbul | LSTM | 46 | 1,91 | 2,50 | 0,93 | 33,01 |
| İstanbul | SeasonalNaive | 46 | 3,10 | 3,74 | 0,83 | 0,00 |
| İstanbul | XGBoost | 46 | 2,17 | 2,98 | 0,89 | 20,22 |

### Geçmiş LST ve çevresel değişkenler

| Model | Seçilen pencere | Doğrulama RMSE °C |
|---|---|---|
| LSTM | 16 | 3,74 |
| XGBoost | 16 | 3,44 |

16 günlük nominal ufuk için bağımsız test:

| İl | Model | n | MAE °C | RMSE °C | R² | Referansa göre iyileşme % |
|---|---|---|---|---|---|---|
| Antalya | LSTM | 91 | 2,36 | 3,77 | 0,85 | 13,64 |
| Antalya | SeasonalNaive | 91 | 2,67 | 4,36 | 0,80 | 0,00 |
| Antalya | XGBoost | 91 | 2,22 | 3,39 | 0,88 | 22,32 |
| Erzurum | LSTM | 66 | 4,27 | 5,23 | 0,86 | -6,18 |
| Erzurum | SeasonalNaive | 66 | 3,76 | 4,93 | 0,88 | 0,00 |
| Erzurum | XGBoost | 66 | 3,15 | 4,27 | 0,91 | 13,29 |
| İstanbul | LSTM | 46 | 2,20 | 3,07 | 0,89 | 17,77 |
| İstanbul | SeasonalNaive | 46 | 3,10 | 3,74 | 0,83 | 0,00 |
| İstanbul | XGBoost | 46 | 2,39 | 3,30 | 0,87 | 11,60 |

Diğer üç ufuk için sonuçlar Atlas.html ve results/temporal-*.json içinde bulunur. Çok değişkenli pilotta 2018–2025 MOD09A1 yansıtımından NDVI/NDBI, ERA5-Land hava ve çiy noktası sıcaklığı ve Skadi kullanıldı. MOD09A1 indisleri ile MOD11A2 hücrelerinin mekânsal ayak izi farklıdır. Ek girdilerin bağımsız katkısını ölçmek için tek değişkenli deney aynı 2018–2022 eğitim kesitiyle ayrıca tekrarlanmalıdır.

## Belirsizlik

1.000 blok bootstrap tekrarıyla model RMSE’si eksi referans RMSE’si için yüzde 95 aralık hesaplandı. Mekânsal bloklar yaklaşık 1,5–2 km, zamansal bloklar 32 gündür. Negatif değer adayın daha düşük hataya sahip olduğunu gösterir. Geçmiş LST ile 16 günlük LSTM sonucunda Antalya ve Erzurum aralıkları sıfırı içerdi. İstanbul aralığı sıfırın altında kaldı. Aralıklar örneklenen pilotlara ve blok boyuna bağlıdır. Ayrıntılar results/intervals.csv içindedir.

## Veri mühendisliği ve yazılım doğrulaması

3.171 satırdan aynı 69 il-yıl ortalamasını üretmek bu koşuda pandas ile 0,030 saniye, yerel Spark 4.0.1 ile 18,340 saniye sürdü. En büyük sonuç farkı 1,8 × 10⁻¹⁴ °C düzeyindeydi. Tek çalıştırma, küçük veri ve Spark başlatma süresi ölçeklenebilirlik veya bellek karşılaştırması için yeterli değildir.

Python takvim/veri sızıntısı testleri, .NET 10 derlemesi, TypeScript ve üretim web derlemesi tamamlandı. PostgreSQL 17 ve PostGIS ile uygulama sorguları, nokta–il eşlemesi ve çevrimdışı/API arayüz seçimleri denendi. API ve veritabanı yerel süreçlerle sınandı. Docker Compose ile Airflow zamanlayıcısının bu ortamda uçtan uca çalıştırması yapılmadı.

## Genişleme durumu

81 il geometrisi hazırdır. Earth Engine dışa aktarım betiğinin işlem grafikleri yerelde oluşturulup kontrol edildi. Yetkili Cloud projesiyle gerçek GEE görevi başlatılmadı. SRTM ve Dynamic World verisini içeren C/D deneyleri, çok yıllı Landsat karşılaştırması ve 81 il için alan ortalamalı sıcaklık arşivi bu pilot sonuçlarının dışındadır. Yeni bölgede ölçüm, kalite ve bağımsız doğrulama tamamlanmadan panel tahmin göstermez. Kayıtlı modellerin gösterdiği son tarihler 2025 sonundaki arşiv kesitinden çıkan Ocak 2026 dönemleridir.
