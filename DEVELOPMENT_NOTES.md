# TIS Home Assistant Entegrasyon - Geliştirme Notu

## Son Güncellemeler

### 2025-12-08 Update 2 - Device Appliance Mapping Sistemi

Laravel Addon'daki **seeder dosyaları** analiz edildi ve her cihaz modelinin hangi platformları desteklediği detaylı olarak çıkarıldı.

#### Yeni Eklenen Dosya

**device_appliance_mapping.py** - Kapsamlı Cihaz-Platform Haritası
- 100+ cihaz modeli için detaylı platform desteği
- Her cihaz için kanal sayıları (switch, dimmer, binary_sensor, vb.)
- `DEVICE_APPLIANCE_MAPPING`: Model → Platformlar sözlüğü
- `PLATFORM_TO_DEVICES`: Platform → Cihazlar ters eşleştirme
- Helper fonksiyonlar:
  - `get_device_platforms(model)`: Cihazın tüm platformlarını döndürür
  - `supports_platform(model, platform)`: Platform desteği kontrolü
  - `get_platform_channel_count(model, platform)`: Kanal sayısı

**Kaynak**: `Orjinal/tis-addon-main/laravel/database/seeders/`
- `ApplianceTypeSeeder.php`: 17 appliance tipi
- `DefaultApplianceSeeder.php`: 191 cihaz için platform mapping'i
- `DeviceTypeSeeder.php`: Cihaz model numaraları ve açıklamaları

#### Platform Güncellemeleri

Tüm platformlar artık `device_appliance_mapping` kullanıyor:

**switch.py**
```python
platforms = get_device_platforms(model_name)
switch_channels = get_platform_channel_count(model_name, "switch")
if switch_channels > 0:
    # Create switch entities
```

**light.py**
```python
dimmer_channels = get_platform_channel_count(model_name, "dimmer")
rgb_channels = get_platform_channel_count(model_name, "rgb")
rgbw_channels = get_platform_channel_count(model_name, "rgbw")
```

**binary_sensor.py**
```python
binary_sensor_channels = get_platform_channel_count(model_name, "binary_sensor")
security_channels = get_platform_channel_count(model_name, "security")
```

**sensor.py**
```python
health_channels = get_platform_channel_count(model_name, "health_sensor")
energy_channels = get_platform_channel_count(model_name, "energy_sensor")
temp_channels = get_platform_channel_count(model_name, "temperature_sensor")
```

### 2025-12-08 - Sensör Tipleri ve Platform Genişletmeleri

Orijinal `Orjinal/tis_integration-main/` klasöründeki detaylı entegrasyon kodu analiz edildi ve eksik özellikler mevcut `tis_homeassistant` entegrasyonuna eklendi.

#### Eklenen Dosyalar

1. **entities.py** - Base entity sınıfları
   - `BaseSensorEntity`: Koordinatör tabanlı sensör entity'leri için temel sınıf
   
2. **coordinator.py güncellemeleri**
   - `SensorUpdateCoordinator`: Sensör verilerini periyodik güncellemek için

3. **binary_sensor.py** - Yeni Platform
   - PIR, Motion, Occupancy sensörleri
   - Digital input desteği
   - OpCode 0x0032 ve 0x0034 paket desteği

4. **light.py** - Yeni Platform
   - Dimmer cihazları için destek
   - Parlaklık kontrolü (0-255 HA ↔ 0-248 TIS)
   - OpCode 0x0031 (Control), 0x0032, 0x0034 paket desteği
   - Optimistic state updates

5. **sensor.py** - Yeni Platform
   - Temperature sensörleri (TIS-4T-IN, vb.)
   - Health sensörleri (HEALTH-CM):
     - Temperature, Humidity, CO2, VOC, Noise, Lux
   - Energy sensörleri (MET-EN):
     - Voltage, Current, Power, Energy, Power Factor, Frequency
     - 3-phase desteği (Phase 1, 2, 3)

#### const.py Genişletmeleri

- **191 Cihaz Tipi Eklendi**: TIS_DEVICE_TYPES sözlüğü
  - Relays, Dimmers, DALI, Panels, Sensors, vb.
  - Tüm Luna, Venera, Mars, Terre, Tariq, Click serileri
  
- **Yeni Sabitler**:
  - `TEMPERATURE_RANGES`: Climate/HVAC mod sıcaklık aralıkları
  - `FAN_MODES`: Fan hızı mapping'i
  - `ENERGY_SENSOR_TYPES`: 30+ enerji sensör tipi
  - `HEALTH_SENSOR_TYPES`: 7 sağlık/çevre sensör tipi
  - `HEALTH_STATES`: CO2/VOC durum açıklamaları

#### __init__.py Güncellemeleri

```python
PLATFORMS = [
    Platform.SWITCH,       # ✅ Mevcut
    Platform.LIGHT,        # ✅ Yeni eklendi
    Platform.BINARY_SENSOR,# ✅ Yeni eklendi
    Platform.SENSOR,       # ✅ Yeni eklendi
    # Platform.CLIMATE,    # 🔜 Gelecek
    # Platform.COVER,      # 🔜 Gelecek
    # Platform.FAN,        # 🔜 Gelecek
]
```

## Protokol Desteği

### OpCode'lar

| OpCode | Yön | Açıklama | Kullanıldığı Yer |
|--------|-----|----------|------------------|
| 0x0031 | → | Kanal kontrol komutu | switch, light |
| 0x0032 | ← | Kanal geri bildirimi | switch, light, binary_sensor |
| 0x0033 | → | Çok kanallı durum sorgusu | Initial state query |
| 0x0034 | ← | Çok kanallı durum yanıtı | Tüm platformlar |
| 0xF00E | → | Kanal adı sorgusu | Addon tarafından |
| 0xF00F | ← | Kanal adı yanıtı | Addon tarafından |

### Parlaklık Dönüşümü

```python
# TIS → Home Assistant
ha_brightness = int((tis_value / 248.0) * 255)

# Home Assistant → TIS
tis_brightness = int((ha_value / 255.0) * 248)
```

## Cihaz Tipi Algılama

Entegrasyon, model adına göre otomatik platform ataması yapar:

- **Light**: "DIM", "DIMMER", "DALI" içeren modeller
- **Binary Sensor**: "PIR", "MOTION", "4DI-IN" içeren modeller
- **Temperature Sensor**: "TEMP", "4T-IN" içeren modeller
- **Health Sensor**: "HEALTH" içeren modeller
- **Energy Sensor**: "MET-EN", "ENERGY" içeren modeller
- **Switch**: Diğer tüm cihazlar (varsayılan)

## Kullanım

### TIS Addon ile Çalışma

1. TIS Addon `/config/tis_devices.json` dosyasına cihazları ekler
2. Entegrasyon bu dosyayı okur ve entity'leri oluşturur
3. UDP listener (port 6000) paketleri dinler ve entity durumlarını günceller

### Entity İsimlendirme

```python
# Kanal adı varsa
"{device_name} {channel_name}"
# Örnek: "Salon RCU Mutfak Işık"

# Kanal adı yoksa
"{device_name} CH{channel}"
# Örnek: "Salon RCU CH5"
```

## Eksik Özellikler (Gelecek Güncellemeler)

- [ ] Climate platform (HVAC/AC kontrolü)
- [ ] Cover platform (Motor/Perde kontrolü)
- [ ] Fan platform
- [ ] Lock platform
- [ ] Button platform
- [ ] Select platform
- [ ] Weather platform
- [ ] RGB/RGBW light desteği
- [ ] Scene desteği

## Orijinal Entegrasyondaki Özellikler

Orijinal entegrasyon `TISControlProtocol` proprietry kütüphanesini kullanıyor ve şu özelliklere sahip:

- Obfuscated kod (alpha__, beta__ fonksiyonları)
- TISApi ve TISProtocolHandler sınıfları
- Gelişmiş RGB/RGBW light kontrolü
- Climate full HVAC kontrolü (cool, heat, auto, fan modes)
- Cover position kontrolü
- Security dashboard
- Configuration dashboard
- Real-time feedback sistemi

Bu özelliklerin çoğu şu anda mevcut entegrasyonda açık kaynak olarak implement edilmedi çünkü TISControlProtocol kütüphanesi mevcut değil.

## Test Edilmesi Gerekenler

1. ✅ Switch entity'leri (mevcut, çalışıyor)
2. 🔄 Light entity'leri (dimmer cihazlarla test edilmeli)
3. 🔄 Binary sensor entity'leri (PIR sensörlerle test edilmeli)
4. 🔄 Temperature sensor entity'leri
5. 🔄 Health sensor entity'leri
6. 🔄 Energy sensor entity'leri

## Notlar

- Lint hataları normal (Home Assistant runtime ortamında çözülür)
- UDP listener zaten mevcut __init__.py'de çalışıyor
- Paket parse işlemleri geliştirilmeli (şu an temel seviyede)
- Orijinal entegrasyondaki tüm özellikleri eklemek için TIS protokolünün daha detaylı analizi gerekli

## Referanslar

- TIS Database Analysis: `tis_addon/TIS_DATABASE_ANALYSIS.json`
- TIS Protocol Documentation: `tis_addon/TIS_PROTOCOL_DOCUMENTATION.md`
- Orijinal Entegrasyon: `Orjinal/tis_integration-main/`
