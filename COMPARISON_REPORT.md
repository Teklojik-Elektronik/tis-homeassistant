# 🔍 TIS Entegrasyon Karşılaştırma Raporu

## 📊 Orjinal vs Bizim Entegrasyon

### ✅ Mevcut Platformlar (Bizde VAR)

| Platform | Orjinal | Bizim | Durum |
|----------|---------|-------|-------|
| Switch | ✅ | ✅ | **TAM** |
| Light | ✅ | ✅ | **TAM** (RGB, RGBW, Dimmer) |
| Binary Sensor | ✅ | ✅ | **TAM** |
| Sensor | ✅ | ✅ | **TAM** (Health, Energy, Analog, Luna Temp) |
| Climate | ✅ | ✅ | **TAM** (AC + Floor Heating) |
| Cover | ✅ | ✅ | **TAM** (Position + No Position) |
| Fan | ✅ | ✅ | **TAM** |

---

### ❌ EKSİK PLATFORMLAR (Bizde YOK)

#### 1. **BUTTON Platform** 
**Dosya**: `button.py`
- **Amaç**: Universal Switch (Buton) kontrolü
- **OpCode**: `0xE01C` (OPERATION_UNIVERSAL_SWITCH)
- **Özellikler**:
  - Tek tuşa basma aksiyonu
  - `universal_type` parametresi (0-255 arası değer)
  - Button entity (basıldığında aksiyon tetiklenir)
- **Kullanım Alanı**: Scene/Sahne tetikleme, makro komutlar

#### 2. **LOCK Platform**
**Dosya**: `lock.py`
- **Amaç**: Güvenlik kilidi (Admin Lock) kontrolü
- **Özellikler**:
  - Password korumalı kilit/aç
  - Auto-lock timer (60 saniye)
  - Event bus: `admin_lock` (locked: true/false)
  - Tüm güvenlik modüllerini koruma
- **Kullanım Alanı**: Güvenlik modüllerini koruma, çocuk kilidi

#### 3. **SELECT Platform**
**Dosya**: `select.py`
- **Amaç**: Güvenlik modu seçimi (Security Module)
- **OpCode**: 
  - `0x0104` - Control Security
  - `0x011E` - Update Security
  - `0x011F` - Security Feedback
- **Modlar**:
  - `vacation` (1) - Tatil modu
  - `away` (2) - Evden uzakta
  - `night` (3) - Gece modu
  - `disarm` (6) - Silahsızlandır
- **Özellikler**:
  - Lock ile entegre (kilitlendiyse read-only)
  - ACK tabanlı güvenilir iletişim
- **Kullanım Alanı**: Alarm sistemi, güvenlik senaryoları

#### 4. **WEATHER Platform**
**Dosya**: `weather.py`
- **Amaç**: TIS Hava İstasyonu desteği
- **OpCode**: 
  - `0x2020` - Weather Update Query
  - `0x2021` - Weather Feedback
- **Özellikler**:
  - UV Index
  - Temperature
  - Humidity
  - Wind speed
  - Wind bearing
  - Condition (sunny, cloudy, etc.)
- **Kullanım Alanı**: Hava durumu istasyonu entegrasyonu

---

### 🔧 EKSİK FONKSİYONLAR ve ÖZELLİKLER

#### 1. **Coordinator Pattern** (DataUpdateCoordinator)
**Dosya**: `coordinator.py`
- Orjinalde var, bizde yok
- Periyodik sensör güncellemeleri için koordinatör
- **Bizde**: Her platform kendi async_update yapıyor
- **Orjinalde**: Merkezi coordinator ile yönetiliyor

#### 2. **Base Entity Sınıfı**
**Dosya**: `entities.py`
- Orjinalde `BaseSensorEntity` var
- CoordinatorEntity'den türüyor
- Tüm sensörler bu base class'ı kullanıyor
- **Bizde**: Her sensör kendi state management yapıyor

#### 3. **Dashboard Otomatik Oluşturma**
**Dosyalar**: 
- `security_dashboard.py` - Güvenlik lock ayarları dashboard
- `tis_configuration_dashboard.py` - TIS yapılandırma dashboard
- **Özellikler**:
  - `configuration.yaml` otomatik düzenleme
  - Lovelace dashboard otomatik oluşturma
  - Sidebar'da otomatik gösterim
  - Butonlar:
    - Change Lock Password
    - Tier Price (Elektrik faturası)

#### 4. **HTTP Configuration Otomatik Setup**
**Dosya**: `__init__.py`
- Orjinalde Home Assistant `configuration.yaml` dosyasına otomatik HTTP ayarları ekleniyor:
```yaml
http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 172.30.33.0/24
```
- **Amaç**: Add-on ile entegrasyon için güvenli proxy ayarları

#### 5. **CPU Fan Control**
**Dosya**: `fan.py`
- Orjinalde `TISCPUFan` entity var
- Raspberry Pi CPU fan kontrolü
- **Bizde**: Sadece TIS cihaz fanları var

#### 6. **CPU Temperature Sensor**
**Dosya**: `sensor.py`
- Orjinalde `CPUTemperatureSensor` var
- Raspberry Pi CPU sıcaklığı
- **Bizde**: Yok

#### 7. **Version Display**
**Dosya**: `__init__.py`
- Orjinalde `manifest.json`'dan version okuyup TISApi'ye gönderiyor
- Dashboard'da version bilgisi gösteriliyor
- **Bizde**: Version bilgisi kullanılmıyor

#### 8. **DEVICES_DICT Kullanımı**
**Dosya**: `const.py`
- Orjinalde `DEVICES_DICT` var ve TISApi'ye gönderiliyor
- Cihaz bilgileri merkezi dictionary'de tutuluyor
- **Bizde**: `device_appliance_mapping.py` kullanılıyor (benzer ama farklı format)

---

### 📦 ADD-ON Özellikleri (Device Manager)

#### Laravel Web Interface
**Port**: 8000
**Özellikler**:
- Cihaz yönetimi web arayüzü
- SQLite database (`/data/database.sqlite`)
- Home Assistant Ingress desteği
- API endpoints:
  - `/api/change-password` - Lock password değiştirme
  - `/api/electricity-bill` - Elektrik faturası hesaplama (Tier Price)
- Database seeders:
  - `DefaultApplianceChannelsSeeder.php` - Varsayılan cihaz kanalları
  - `ApplianceTypeSeeder.php` - Cihaz tipleri

#### Ingress Configuration
- Otomatik URL yapılandırması
- HTTPS/HTTP otomatik algılama
- Secure cookie desteği
- Database migration ve seed

---

### 🔑 MANIFEST.JSON Farkları

#### Orjinal Dependencies:
```json
"requirements": [
  "TISControlProtocol==1.0.5",
  "aiofiles==24.1.0",
  "RPi.GPIO==0.7.1",
  "spidev==3.6",
  "st7789==0.0.4",
  "gpiozero==1.6.2",
  "python-dotenv==1.0.1",
  "cryptography",
  "psutil==7.0.0",
  "ruamel.yaml==0.18.10"
]
```

#### Bizim Dependencies:
```json
"requirements": [
  "ruamel.yaml"
]
```

**Eksik Kütüphaneler**:
- `TISControlProtocol==1.0.5` - Ana protokol kütüphanesi
- `aiofiles==24.1.0` - Async file operations
- `RPi.GPIO==0.7.1` - Raspberry Pi GPIO
- `spidev==3.6` - SPI interface
- `st7789==0.0.4` - LCD display driver
- `gpiozero==1.6.2` - GPIO zero interface
- `python-dotenv==1.0.1` - Environment variables
- `cryptography` - Şifreleme
- `psutil==7.0.0` - System monitoring

---

### 📋 ÖNCELİKLENDİRİLMİŞ EKSİKLİKLER

#### 🔴 KRİTİK (Hemen Eklenmeli)

1. **SELECT Platform** - Güvenlik modu seçimi
   - Security system için gerekli
   - Alarm entegrasyonu için kritik

2. **LOCK Platform** - Admin Lock
   - Güvenlik modüllerini koruma
   - Select platform ile birlikte çalışır

3. **BUTTON Platform** - Universal Switch
   - Scene tetikleme için gerekli
   - Kullanıcı tarafından sık kullanılır

#### 🟡 ORTA ÖNCELİK (Sonra Eklenebilir)

4. **WEATHER Platform** - Hava istasyonu
   - Sadece hava istasyonu olan kullanıcılar için
   - Opsiyonel özellik

5. **Dashboard Auto-Creation** - Otomatik dashboard
   - Kullanıcı deneyimi için iyi
   - Elle de yapılabilir

6. **Coordinator Pattern** - DataUpdateCoordinator
   - Kod kalitesi iyileştirmesi
   - Mevcut yapı da çalışıyor

#### 🟢 DÜŞÜK ÖNCELİK (İsteğe Bağlı)

7. **CPU Fan/Temperature** - RPi sensörleri
   - Sadece Raspberry Pi kullanıcıları için
   - TIS cihazlarıyla ilgisi yok

8. **HTTP Auto-Config** - configuration.yaml düzenleme
   - Add-on kullanıcıları için
   - Manuel de yapılabilir

---

### 🎯 ÖNERİLER

#### Hemen Yapılması Gerekenler:
1. ✅ **BUTTON Platform ekle** - Universal Switch desteği
2. ✅ **LOCK Platform ekle** - Admin Lock desteği
3. ✅ **SELECT Platform ekle** - Security mode seçimi
4. ⚠️ **OpCode 0xE01C** handler ekle (__init__.py)
5. ⚠️ **OpCode 0x0104** handler ekle (__init__.py)
6. ⚠️ **TISPacket.create_universal_switch_packet** ekle (tis_protocol.py)

#### Sonra Yapılabilecekler:
7. 🔄 **WEATHER Platform ekle** - Hava istasyonu desteği
8. 🔄 **Dashboard otomatik oluşturma** - UX iyileştirmesi
9. 🔄 **Coordinator pattern** - Kod kalitesi iyileştirmesi

#### İsteğe Bağlı:
10. 💡 **CPU sensörleri** - Raspberry Pi kullanıcıları için
11. 💡 **HTTP auto-config** - Add-on kullanıcıları için

---

### 📝 SONUÇ

**Toplam Eksik Platform**: 4 adet
- Button ❌
- Lock ❌
- Select ❌
- Weather ❌

**Toplam Eksik OpCode**: 3 adet
- 0xE01C - Universal Switch ❌
- 0x0104 - Control Security ❌
- 0x2020 - Weather Update ❌

**Mevcut Platform Kalitesi**: ⭐⭐⭐⭐⭐ (Çok İyi)
**Genel Tamamlanma Oranı**: %70 (7/10 platform mevcut)

**Kritik Eksiklikler Tamamlanma Süresi**: ~4-6 saat
**Tüm Eksiklikler Tamamlanma Süresi**: ~8-12 saat
