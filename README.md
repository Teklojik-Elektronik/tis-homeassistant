# TIS Smart Home Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/Teklojik-Elektronik/tis-homeassistant.svg)](https://github.com/Teklojik-Elektronik/tis-homeassistant/releases)

TIS akıllı ev cihazlarını Home Assistant'a entegre eden resmi entegrasyon. [TIS Addon](https://github.com/Teklojik-Elektronik/tis_addon) ile birlikte çalışır.

## 🚀 Özellikler

- ✅ TIS Addon ile senkronize cihaz yönetimi
- ✅ Otomatik cihaz tanıma (`/config/tis_devices.json`'dan okur)
- ✅ Gerçek zamanlı UDP listener (ağdan gelen feedback'leri dinler)
- ✅ Switch entity'leri (açma/kapama, parlaklık kontrolü)
- ✅ SMARTCLOUD gateway desteği
- ✅ 191+ TIS cihaz modeli desteği
- ✅ Canlı durum güncellemesi

## 📦 Kurulum

### HACS Üzerinden (Önerilen)

1. **HACS** → **Integrations** → **⋮ (sağ üst)** → **Custom repositories**
2. Repository ekleyin:
   ```
   https://github.com/Teklojik-Elektronik/tis-homeassistant
   ```
   Category: **Integration**
3. **TIS Smart Home Integration** ara ve **Download** tıkla
4. Home Assistant'ı yeniden başlat
5. **Settings → Devices & Services → Add Integration**
6. **"TIS"** ara ve entegrasyonu ekle

### Manuel Kurulum

1. `custom_components/tis` klasörünü Home Assistant `config/custom_components/` dizinine kopyalayın
2. Home Assistant'ı yeniden başlatın
3. **Settings → Devices & Services → Add Integration** → **TIS**

## ⚙️ Yapılandırma

Entegrasyonu kurarken gerekli bilgiler:

- **Gateway IP**: TIS gateway cihazınızın IP adresi (örn: `192.168.1.200`)
- **UDP Port**: UDP iletişim portu (varsayılan: `6000`)

> **Önemli:** Bu entegrasyon [TIS Addon](https://github.com/Teklojik-Elektronik/tis_addon) ile birlikte çalışır. 
> Önce addon'u kurup cihazlarınızı ekleyin, sonra bu entegrasyonu yükleyin.

## 🎯 Kullanım

### 1. TIS Addon Kurulumu (İlk Adım)

[TIS Addon](https://github.com/Teklojik-Elektronik/tis_addon)'u Home Assistant'a yükleyin ve cihazlarınızı ekleyin:
- Addon Web UI'dan cihazları keşfet ve ekle
- Cihazlar `/config/tis_devices.json` dosyasına kaydedilir

### 2. TIS Entegrasyonu Kurulumu (İkinci Adım)

Bu entegrasyonu HACS veya manuel olarak yükleyin:
- Settings → Integrations → Add → TIS
- Gateway IP ve Port girin
- Addon'dan eklenen cihazlar otomatik yüklenecek

### 3. Cihaz Kontrolü

- Her cihaz **switch** entity'si olarak görünür
- Çok kanallı cihazlar için her kanal ayrı switch oluşur
- Açma/kapama komutları UDP üzerinden gateway'e gönderilir
- Ağdan gelen feedback'ler otomatik olarak entity durumlarını günceller

### Yeni Cihaz Ekleme

Addon'dan yeni cihaz ekledikten sonra:
1. Settings → Integrations → **TIS** → **⋮ (üç nokta)** → **Reload**
2. Yeni cihazlar otomatik yüklenecek

## 🔧 Teknik Detaylar

- **Protokol**: TIS UDP (Port 6000, SMARTCLOUD header)
- **Cihaz Kaynağı**: `/config/tis_devices.json` (TIS Addon tarafından yönetilir)
- **OpCode Desteği**:
  - `0x0031`: Tek Kanal Işık Kontrolü (gönderim)
  - `0x0032`: Tek Kanal Işık Geri Bildirimi (alım)
  - `0x0034`: Multi Kanal Durum (alım)
- **UDP Listener**: Non-blocking async socket, gerçek zamanlı feedback
- **Brightness Scale**: TIS 0-248 → Home Assistant 0-100%

## 📱 Desteklenen Cihazlar

- 💡 Dimmer'lar ve LED kontrolörler
- 🔌 Röle modülleri (RCU-24R20Z, vb.)
- 🌈 RGB kontrolörler
- 🪟 Perde motorları
- 🌡️ Termostatlar
- Ve 191+ TIS cihaz modeli!

## 🐛 Sorun Giderme

### Switch açılmıyor/kapanmıyor
- Gateway IP adresinin doğru olduğundan emin olun
- Home Assistant loglarını kontrol edin: Settings → System → Logs
- TIS Addon'un debug tool'unu kullanarak ağ trafiğini izleyin

### Cihaz durumu güncellenmiyor
- UDP listener çalışıyor mu kontrol edin (loglarda "TIS UDP listener started" mesajı arayın)
- Firewall UDP port 6000'i engelliyor olabilir
- Cihazın feedback gönderdiğinden emin olun

### Yeni eklenen cihazlar görünmüyor
- TIS Addon'da cihazı "Ekle" butonuna bastınız mı?
- Entegrasyonu reload ettiniz mi? (Settings → Integrations → TIS → Reload)
- `/config/tis_devices.json` dosyasını kontrol edin

## 🔄 Güncelleme

### HACS ile:
- HACS otomatik olarak güncellemeleri bildirir
- Güncellemeleri tek tıkla yükleyebilirsiniz

### Manuel:
- Yeni sürümü indirip `custom_components/tis/` klasörüne kopyalayın
- Home Assistant'ı yeniden başlatın

## 📄 Lisans

MIT License

## 🤝 Katkıda Bulunma

Pull request'ler ve issue'lar memnuniyetle karşılanır!

## 📞 İletişim

- **TIS Addon**: [github.com/Teklojik-Elektronik/tis_addon](https://github.com/Teklojik-Elektronik/tis_addon)
- **TIS Integration**: [github.com/Teklojik-Elektronik/tis-homeassistant](https://github.com/Teklojik-Elektronik/tis-homeassistant)
- **Issues**: [Report a bug](https://github.com/Teklojik-Elektronik/tis-homeassistant/issues)

## 🙏 Teşekkürler

TIS akıllı ev sistemlerini tercih ettiğiniz için teşekkür ederiz!
