# Türkiye yüzey sıcaklığı analiz ve tahmin sistemi

**Başlangıç:** ZIP dosyasını klasöre çıkarıp **Atlas.html** dosyasını açın. Kurulum veya Google hesabı gerektirmez. İstanbul, Erzurum ve Antalya’yı seçerek ölçülen LST’yi, tahminin hedef dönemini ve görülmemiş veri üzerindeki hataları inceleyebilirsiniz. Diğer illerin sınırları ve veri durumları gösterilir. Projedeki çalıştırılmış deneylerin kapsamı ve sonuçları **DENEY_RAPORU.md** içindedir.

## Uygulamayı veritabanıyla çalıştırma

Windows 11 / Docker Desktop için PowerShell komutları. Terminali bu dosyanın olduğu klasörde açın.

```powershell
$env:LST_DB_PASSWORD = [guid]::NewGuid().ToString("N")
docker compose up --build -d
docker compose ps
Start-Process http://localhost:5274
```

İlk kurulumda konteyner imajları indirilir. Parolanızı geri kullanmak için saklayın. Aynı veritabanı birimi varken sonraki açılışlarda aynı parolayı kullanın. Kapatmak için `docker compose down`. Seed görevi tek işlemde sonuçları ve 81 il geometrisini yazar. Tekrar çalışması il kaydını günceller. Web arayüzü aynı sunucunun API’sinden seçili ilin sonuçlarını alır.

| Adres | Yanıt |
|---|---|
| /api/iller | Kapsamdaki iller |
| /api/iller/Antalya | Pilot hücreler, geçmiş seri, tahminler, metrikler |
| /api/konum?lon=30.70&lat=36.89 | PostGIS nokta–poligon sorgusunda Antalya |

## Araştırma ortamı

Python 3.12 önerilir. Windows için sanal ortamı etkinleştirmeden:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python scripts/spatial_train.py
.\.venv\Scripts\python scripts/forecast.py
.\.venv\Scripts\python scripts/forecast.py --mode multi --data data/modis-multi.csv
.\.venv\Scripts\python scripts/confidence.py
```

Paketlenmiş CSV’ler bu komutlarla doğrudan kullanılabilir. `models/` içinde eğitilmiş modeller, `results/` içinde bağımsız test tahminleri, doğrulama sonuçları ve güven aralıkları vardır. Joblib modelleri için eğitim ortamındaki scikit-learn sürümü **1.8.0** kullanılmıştır. Keras 3 modeli JAX CPU arka ucunu kullanır.

Yeni gözlemleri aynı CSV şemasına ekledikten sonra yeniden eğitim gerektirmeyen çıkarım:

```powershell
.\.venv\Scripts\python scripts/predict.py data/modis.csv --output results/yeni-tahmin.csv
```

### Verileri kaynağından yeniden alma

Aşağıdaki betikler çalışma dizini olarak proje kökünü kullanır. Ağ erişimi gerekir. ORNL istekleri önbelleğe alınır.

| Sıra | Komut (Python ile çalıştırın) | Üretilen veri |
|---|---|---|
| 1 | scripts/spatial_data.py | Üç pilotta Ağustos 2023 Landsat–Sentinel eşleşmeleri, her aday hücre için iki geçerlilik oranı |
| 2 | scripts/topography.py | Hücrelerin yükseklik ve eğim özellikleri |
| 3 | scripts/modis.py | 2003–2025 MODIS gündüz LST, tarih, koordinat, QC ve ham değer |
| 4 | scripts/temporal_features.py | 2018–2025 LST, MOD09A1 indisleri, ERA5-Land hava ve çiy noktası sıcaklığı, topoğrafya |

Mekânsal deney her seferinde bir ili dışarıda tutar. Hiperparametre seçimi diğer illerin mekânsal bloklarında yapılır. `points-*.csv` dosyalarındaki her satır test hücresi, gerçek sıcaklık ve tahmin içerir. Modeller dışlanan ilin adını taşır.

Zamansal deney her hedefin tarihine göre bölünür. Tek değişkenli eğitim 2003–2021, doğrulama 2022–2023; çok değişkenli eğitim 2018–2022, doğrulama 2023; her ikisinde test 2024–2025’tir. Pencere seçimi 8, 16, 24 dönem arasından doğrulama RMSE’sine göre yapılır. Son girişten 1–4 kompozit sonrasına tahmin üretilir. Takvim yıl sonunda yeniden başladığı için nominal gün ufukları ile tarihler arasındaki gün sayısı bazen farklıdır. Panelde gerçek hedef başlangıç tarihi bulunur. Her test tahmininde yalnızca başlangıç döneminin sonuna dek bilinen girdiler kullanılır. Arşiv ürünlerinin yayın gecikmesi modellenmemiştir.

### Earth Engine ile altı kaynak ve il ölçeğinde genişleme

Earth Engine erişimi olan bir Google Cloud projesiyle bir kez `earthengine authenticate` çalıştırın. Aşağıdaki komutlardaki PROJE_KIMLIGI yerine kendi proje kimliğinizi girin.

```powershell
python scripts/earthengine_export.py --project PROJE_KIMLIGI --mode spatial --city Antalya --year 2023
python scripts/earthengine_export.py --project PROJE_KIMLIGI --mode temporal --city Antalya --year 2023
```

Mekânsal dışa aktarım yaz aylarında sekiz günlük kompozitler üretir. Landsat LST, Sentinel-2 indisleri, SRTM, Dynamic World yapılaşma olasılığı ve ERA5-Land değişkenleri 300 m hücrelerde örneklenir. Zamansal dışa aktarım MODIS’i kendi ızgarasında işler, ardından il ortalaması ve kapsam oranını kaydeder. 2018 sonrası çevresel özellikler eklenir. `--city ALL` seçilen yıl için 81 ayrı görevi başlatır. Earth Engine Tasks üzerinden durumunu izleyin. Tam araştırma için mekânsal ihracatı 2018–2025’te üç pilotta, zamansal ihracatı 2003–2025’te seçili illerde tekrarlayın. Drive/LST_Turkiye CSV’lerini bir klasöre indirin.

```powershell
python scripts/import_ee.py indirilen_csv deney_ee
cd deney_ee
python ../scripts/spatial_train.py
python ../scripts/forecast.py --data data/modis.csv
python ../scripts/forecast.py --data data/modis.csv --mode multi
```

A/B/C/D grupları veri sütunlarına göre çalışır. C grubunda arazi örtüsü göstergesi yapılaşma olasılığıdır. D grubuna hava ve çiy noktası sıcaklığı eklenir. İllerin model eğitimine yetecek sayıda ve farklı yıllardan kayıt içermesi gerekir. İl serileri ile paketteki tek piksel serileri ayrı deney dizinlerinde tutulur. Yeni bir il ortalaması modeli yayımlanırken arayüzdeki tek piksel açıklaması da güncellenmelidir.

### Web arayüzünü yeniden üretme

```powershell
python scripts/snapshot.py
cd web
npm ci
npm run build
Copy-Item dist/index.html ../Atlas.html -Force
```

### Airflow ve Spark

`airflow/lst_pipeline.py` Airflow 2.10 için elle tetiklenen pilot iş akışıdır. Linux/WSL'de Airflow'un kendi ortamında DAG dosyasını DAG dizinine yerleştirin. `LST_ROOT` mutlak proje yolu, `LST_PYTHON` ise araştırma ortamının Python çalıştırılabilir dosyasıdır. DAG mekânsal indirme/eğitim ile MODIS indirme/eğitimini paralel yürütür ve sonuçları panoya hazırlar.

`scripts/benchmark.py data/modis.csv pandas` ve aynı komutun `spark` seçeneği aynı il-yıl ortalamalarını üretir. Spark için Java 17+ ve PySpark gerekir. Küçük pilotta süreye Spark oturumunun başlatılması dahildir.

### Veri kaynakları

- Landsat 8/9 Collection 2 L2 — USGS / Microsoft Planetary Computer, ST_B10 ve QA bantları. https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2
- Copernicus Sentinel-2 L2A — Earth Search, yansıtım COG’ları ve SCL. https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a
- NASA LP DAAC Terra MOD11A2 ve MOD09A1 — ORNL DAAC TESViS REST. https://modis.ornl.gov/data/modis_webservice.html
- Terrain Tiles Skadi — Mapzen/AWS, birleştirilmiş sayısal yükseklik ürünü. Pilot topoğrafyası bu üründendir. https://registry.opendata.aws/terrain-tiles/
- Open-Meteo Historical Weather API / Copernicus ERA5-Land. https://open-meteo.com/en/docs/historical-weather-api
- İl geometrileri — Natural Earth 1:10m Admin 1, kamu malı, görselleştirme için sadeleştirildi. https://www.naturalearthdata.com/downloads/10m-cultural-vectors/
- GEE koleksiyonları — LANDSAT/LC08/C02/T1_L2, LANDSAT/LC09/C02/T1_L2, COPERNICUS/S2_SR_HARMONIZED, MODIS/061/MOD11A2, USGS/SRTMGL1_003, GOOGLE/DYNAMICWORLD/V1, ECMWF/ERA5_LAND/DAILY_AGGR. https://developers.google.com/earth-engine/datasets/catalog
