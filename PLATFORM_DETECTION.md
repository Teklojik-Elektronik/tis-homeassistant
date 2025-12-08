# TIS Home Assistant Integration - Sensör Tipleri

## Otomatik Platform Algılama

TIS entegrasyonu, cihaz model adlarını `device_appliance_mapping.py` ile eşleştirerek otomatik olarak doğru platform tipini algılar.

## Desteklenen Platform Tipleri

### 1. **Switch (Röle)** 🔌
Model örnekleri:
- `RCU-24R20Z` - 24 kanallı röle kontrolü
- `TIS-1CH-RY`, `TIS-2CH-RY`, `TIS-4CH-RY` - 1/2/4 kanallı röleler
- `RCU-12-10A`, `RCU-8-10A` - Yüksek akım röleleri

**Özellikler:**
- ON/OFF kontrolü
- Anlık durum geri bildirimi
- Çoklu kanal desteği

---

### 2. **Light (Dimmer/Işık)** 💡
Model örnekleri:
- `DIM-4CH` - 4 kanallı dimmer
- `DIM-8CH-ZN` - 8 kanallı zone dimmer
- `VLC-DALI-4CH` - DALI kontrol modülü

**Özellikler:**
- Parlaklık kontrolü (0-100%)
- Yumuşak açma/kapama
- TIS protokolü: 0-248 parlaklık aralığı

---

### 3. **Binary Sensor (Hareket Sensörü)** 🚶
Model örnekleri:
- `PIR-*` - PIR hareket sensörleri
- `OS-MMV2` - Doluluk sensörü

**Özellikler:**
- ON/OFF durum algılama
- Hareket tespiti
- Gerçek zamanlı geri bildirim

---

### 4. **Sensor (Sensörler)** 🌡️

#### 4.1 Health Sensor (Sağlık Sensörü)
Model örnekleri:
- `TIS-HEALTH-CM` - Çoklu ortam sensörü
- `TIS-HEALTH-CM-RADAR` - Radar + ortam sensörü

**Sağlanan metrikler:**
- 🌡️ **Temperature** - Sıcaklık (°C)
- 💧 **Humidity** - Nem (%)
- 🌫️ **CO2** - Karbondioksit seviyesi (ppm)
- 🧪 **VOC** - Uçucu Organik Bileşikler
- 🌫️ **PM2.5** - Partikül madde (µg/m³)
- ☀️ **Luminance** - Işık seviyesi (lux)
- 🔊 **Noise** - Gürültü seviyesi (dB)

#### 4.2 Energy Sensor (Enerji Sensörü)
Model örnekleri:
- `ES-10F-CM` - 10 kanal enerji ölçüm modülü
- `TIS-ENERGY-*` - Enerji monitörleri

**Sağlanan metrikler:**
- ⚡ Voltaj, Akım, Güç
- 📊 Enerji tüketimi
- 📈 Güç faktörü
- 🔌 Frekans

#### 4.3 Temperature Sensor (Sıcaklık Sensörü)
Model örnekleri:
- `4T-IN` - 4 kanal sıcaklık girişi
- `4CH-AIN` - Analog giriş modülü

---

### 5. **Climate (HVAC/Termostat)** ❄️🔥
Model örnekleri:
- `VRV-AC-*` - VRV klima kontrol modülleri
- `TIS-HVAC-*` - HVAC kontrol cihazları
- `TIS-VAV-*` - VAV (Variable Air Volume) kontrol

**Özellikler:**
- Mod seçimi (Cooling, Heating, Fan, Auto, Dry)
- Sıcaklık ayarı
- Fan hızı kontrolü
- ON/OFF kontrolü

---

### 6. **Cover (Perde/Motor)** 🪟
Model örnekleri:
- `TIS-M-*` - Motor kontrol modülleri
- `TIS-TM-*` - Tüp motor kontrol
- `LFT-*` - Lift/asansör kontrol

**Özellikler:**
- Açma/kapama
- Pozisyon kontrolü (0-100%)
- Durdurma komutu

---

## Platform Eşleştirme Sistemi

### Otomatik Algılama
Entegrasyon `device_appliance_mapping.py` dosyasını kullanarak:

```python
DEVICE_APPLIANCE_MAPPING = {
    "TIS-HEALTH-CM": {"health_sensor": 1},
    "RCU-24R20Z": {"switch": 24},
    "DIM-4CH": {"dimmer": 4},
    # ... 100+ cihaz tanımı
}
```

### Platform Kontrolü
Her platform setup fonksiyonu şunları kontrol eder:

```python
platforms = get_device_platforms(model_name)
health_channels = get_platform_channel_count(model_name, "health_sensor")

if health_channels > 0:
    # Health sensor entity'leri oluştur
    for sensor_key, sensor_name in HEALTH_SENSOR_TYPES.items():
        # 7 farklı sensör (temperature, humidity, co2, voc, pm25, luminance, noise)
```

---

## Log Mesajları

Entegrasyon kurulurken log'larda şunları göreceksiniz:

```
INFO:custom_components.tis.__init__:Loaded 2 TIS devices from addon
INFO:custom_components.tis.sensor:Setting up TIS sensor entities from 2 devices
INFO:custom_components.tis.sensor:Device TIS-HEALTH-CM (1.103) - Sensors: health=1, energy=0, temp=0, lux=0, analog=0
INFO:custom_components.tis.sensor:Added 7 TIS sensor entities
INFO:custom_components.tis.switch:Setting up TIS switch entities from 2 devices
INFO:custom_components.tis.switch:Device RCU-24R20Z (1.1) - Switches: 24 channels
INFO:custom_components.tis.switch:Added 24 TIS switch entities
```

---

## Addon ve Entegrasyon Senkronizasyonu

### Addon (tis_addon)
1. Cihazı keşfeder ve model adını tespit eder
2. `_detect_entity_type()` ile platform tipini belirler
3. `/config/tis_devices.json` dosyasına kaydeder:
   ```json
   {
     "tis_1_103": {
       "model_name": "TIS-HEALTH-CM",
       "entity_type": "sensor",  // Addon'un tespiti
       "channels": 1,
       ...
     }
   }
   ```

### Entegrasyon (tis_homeassistant)
1. `tis_devices.json` dosyasını okur
2. Her cihaz için `device_appliance_mapping.py`'den platform bilgilerini kontrol eder
3. Desteklenen her platform için entity'ler oluşturur:
   - Health sensor → 7 sensor entity (temperature, humidity, co2, voc, pm25, luminance, noise)
   - Switch → N kanal switch entity
   - Dimmer → N kanal light entity
   - vb.

---

## Yeni Cihaz Ekleme

### 1. device_appliance_mapping.py'ye Ekle
```python
DEVICE_APPLIANCE_MAPPING = {
    "YENİ-CİHAZ-MODEL": {
        "switch": 8,           # 8 kanal röle
        "dimmer": 4,           # 4 kanal dimmer
        "health_sensor": 1,    # 1 sağlık sensörü
    }
}
```

### 2. Addon'da Entity Type Tespitini Güncelle (web_ui.py)
```python
def _detect_entity_type(self, model_name: str) -> str:
    if 'YENİ-CİHAZ' in model:
        return 'switch'  # veya uygun platform
```

### 3. Test Et
1. Addon'u rebuild et
2. Cihazı addon UI'den ekle
3. TIS entegrasyonunu reload et
4. Log'ları kontrol et

---

## Sorun Giderme

### Cihaz görünmüyor?
1. **Log kontrolü:**
   ```
   Settings → System → Logs → custom_components.tis
   ```

2. **Device mapping kontrolü:**
   - Model adı `device_appliance_mapping.py`'de var mı?
   - Platform bilgisi doğru mu?

3. **JSON kontrolü:**
   - `/config/tis_devices.json` dosyasında cihaz var mı?
   - `entity_type` doğru mu?

### Entity type yanlış?
1. Addon Web UI → "🔧 Fix Entity Types" butonuna tıklayın
2. Veya entegrasyonu reload edin

### Kanal sayısı yanlış?
- `device_appliance_mapping.py`'deki kanal sayısını kontrol edin
- Cihazı addon'dan kaldırıp tekrar ekleyin

---

## Commit Geçmişi

- **Tarih:** 8 Aralık 2024
- **Commit 1:** Platform logging iyileştirmeleri
- **Commit 2:** TIS-HEALTH-CM entity_type düzeltmesi
- **Commit 3:** Fix Entity Types API endpoint eklendi

---

## Özet

✅ **100+ cihaz modeli** tanımlı  
✅ **6 platform** destekleniyor (switch, light, binary_sensor, sensor, climate, cover)  
✅ **Otomatik platform algılama** - Model adından platform tespiti  
✅ **Detaylı logging** - Her adım log'lanıyor  
✅ **Addon senkronizasyonu** - JSON tabanlı cihaz yönetimi  
✅ **Kolay sorun giderme** - Fix Entity Types butonu ile tek tıkla düzeltme
