# TIS Protokol & Veritabanı Dokümantasyonu

**Oluşturulma:** 2025-12-05  
**Kaynak:** tis.db3 (TIS DevSearch Yapılandırma Veritabanı)  
**Amaç:** TIS Ev Otomasyon Protokolü implementasyonu için eksiksiz referans

---

## İçindekiler

1. [Protokol OpCode'ları](#protokol-opcodeları)
2. [Paket Yapısı](#paket-yapısı)
3. [Cihaz Tipleri](#cihaz-tipleri)
4. [Kanal Yapılandırmaları](#kanal-yapılandırmaları)
5. [Önemli Bulgular](#önemli-bulgular)

---

## Protokol OpCode'ları

### Keşfedilen OpCode'lar (TIS DevSearch paket analizinden)

| OpCode | Yön | Açıklama | Ek Veri |
|--------|-----|----------|---------|
| `0x0031` | → Cihaz | Kanal kontrol komutu | `[kanal, 0x00, parlaklık, ...]` |
| `0x0032` | ← Cihaz | Kanal geri bildirimi/durum | `[kanal, 0xF8, parlaklık, ...]` |
| `0x0033` | → Cihaz | Çok kanallı durum sorgusu | Boş (tüm kanalları ister) |
| `0x0034` | ← Cihaz | Çok kanallı durum yanıtı | 24 byte (kanal başına bir) |
| `0xF00E` | → Cihaz | Kanal adı sorgusu | `[kanal_numarası]` |
| `0xF00F` | ← Cihaz | Kanal adı yanıtı | `[kanal, ...UTF-8 ad byte'ları...]` |
| `0xEFFD` | → Cihaz | Cihaz bilgi sorgusu | Değişken |
| `0xEFFE` | ← Cihaz | Cihaz bilgi yanıtı | Değişken |
| `0xF00A` | → Cihaz | Bilinmeyen fonksiyon sorgusu | Değişken |
| `0xF00B` | ← Cihaz | Bilinmeyen fonksiyon yanıtı | Değişken |
| `0xF012` | → Cihaz | Bilinmeyen fonksiyon sorgusu | Değişken |
| `0xF013` | ← Cihaz | Bilinmeyen fonksiyon yanıtı | Değişken |

### Parlaklık Kodlaması

- **Aralık:** 0-248 (ham değer)
- **Dönüşüm:** `parlaklık_yüzde = (ham_değer / 248.0) * 100`
- **Durumlar:**
  - `0` = KAPALI
  - `1-248` = AÇIK parlaklık seviyesi ile (0.4% - 100%)

### OpCode 0x0032 (Geri Bildirim) Paket Yapısı

```
additional_data[0] = Kanal numarası (0-23)
additional_data[1] = 0xF8 (maks parlaklık sabiti, her zaman 248)
additional_data[2] = Gerçek parlaklık (0-248)
additional_data[3+] = Rezerve/kullanılmıyor
```

**Önemli:** İndeks 2 gerçek parlaklığı içerir, indeks 1 DEĞİL!

### OpCode 0x0034 (Çok Kanallı Durum) Paket Yapısı

```
additional_data[0]  = CH0 parlaklığı (0-248)
additional_data[1]  = CH1 parlaklığı (0-248)
...
additional_data[23] = CH23 parlaklığı (0-248)
```

Toplam: 24 byte, kanal başına bir

### OpCode 0xF00F (Kanal Adı) Paket Yapısı

```
additional_data[0] = Kanal numarası (0-23)
additional_data[1+] = UTF-8 kodlu kanal adı (maks 20 byte)
```

**Örnekler:**
- `[0, 0x42, 0x69, 0x6C, 0x69, 0x6E, 0x6D, 0x69, 0x79, 0x6F, 0x72]` = CH0: "Bilinmiyor"
- `[5, 0x4B, 0x4F, 0x52, 0x49, 0x44, 0x4F, 0x52]` = CH5: "KORIDOR"
- `[12, 0x4C, 0x41, 0x56, 0x41, 0x42, 0x4F]` = CH12: "LAVABO"

**Not:** UTF-8 kodlaması Türkçe karakterleri destekler (İ, Ğ, Ş, Ç, Ö, Ü)

---

## Paket Yapısı

### Tam UDP Paket Formatı

```
[PC IP (4 bytes)] + "SMARTCLOUD" (10 bytes) + [TIS Packet]
```

### TIS Paket Yapısı

| Alan | Boyut | Açıklama |
|------|-------|-------|
| `src_subnet` | 1 byte | Kaynak subnet ID (0-255) |
| `src_device` | 1 byte | Kaynak cihaz ID (0-255) |
| `src_type` | 2 byte | Kaynak cihaz tip kodu |
| `tgt_subnet` | 1 byte | Hedef subnet ID (0-255) |
| `tgt_device` | 1 byte | Hedef cihaz ID (0-255) |
| `op_code` | 2 byte | İşlem kodu (yukarıdaki tabloya bakın) |
| `additional_data_length` | 1 byte | Ek veri uzunluğu |
| `additional_data` | Değişken | Komut/yanıt verisi |

**Toplam Başlık Boyutu:** 9 byte (additional_data'dan önce)

### Örnek Paket (CH5'i %50 parlaklıkta AÇ)

```
Kaynak: Subnet 1, Cihaz 254 (Kontrolör)
Hedef: Subnet 1, Cihaz 10 (RCU-24R20Z)
OpCode: 0x0031 (Kontrol)
Ek Veri: [0x05, 0x00, 0x7C] (CH5, rezerve, parlaklık=124)
```

Ham byte'lar:
```
01 FE FF FE 01 0A 00 31 03 05 00 7C
│  │  │  │  │  │  │  │  │  │  │  └─ Parlaklık (124 = ~%50)
│  │  │  │  │  │  │  │  │  │  └──── Rezerve (0x00)
│  │  │  │  │  │  │  │  │  └─────── Kanal (5)
│  │  │  │  │  │  │  │  └────────── Veri uzunluğu (3)
│  │  │  │  │  │  │  └───────────── OpCode (0x0031)
│  │  │  │  │  └──────────────────── Hedef cihaz (10)
│  │  │  │  └─────────────────────── Hedef subnet (1)
│  │  └────────────────────────────── Kaynak tipi (0xFFFE)
│  └───────────────────────────────── Kaynak cihaz (254)
└──────────────────────────────────── Kaynak subnet (1)
```

---

## Cihaz Tipleri

### Gateway/Köprü

| Tip | Model | Açıklama |
|-----|-------|----------|
| 186 | Bilinmiyor | TIS Gateway/Köprü |

### Çok Kanallı Röle Modülleri

| Tip | Model | Kanal | Açıklama |
|-----|-------|-------|----------|
| 214 | Bilinmiyor | 24 | RCU-24R20Z (ESKİ tip kodu) |
| **32811** | **RCU-24R20Z** | **24** | **24 kanallı röle (GÜNCEL)** |
| 32813 | RCU-20R20Z-IP | 20 | IP'li 20 kanallı röle |
| 7098 | RCU-8OUT-8IN | 8 | Oda kontrolörü (8 çıkış, 8 giriş) |
| 424 | RLY-4CH-10A | 4 | 4 kanallı 10A röle |
| 428 | RLY-8CH-16A | 8 | 8 kanallı 16A röle |
| 440 | VLC-12CH-10A | 12 | 12 kanallı valf/aydınlatma kontrolörü |

### Dimmer Modülleri

| Tip | Model | Kanal | Açıklama |
|-----|-------|-------|----------|
| 600 | DIM-6CH-2A | 6 | 6 kanallı 2A dimmer |
| 601 | DIM-4CH-3A | 4 | 4 kanallı 3A dimmer |
| 602 | DIM-2CH-6A | 2 | 2 kanallı 6A dimmer |
| 7090 | TIS-DIM-4CH-1A | 4 | 4 kanallı 1A dimmer |
| 7092 | DIM-TE-2CH-3A | 2 | TE 2 kanallı 3A dimmer |
| 7094 | DIM-TE-4CH-1.5A | 4 | TE 4 kanallı 1.5A dimmer |
| 33056 | DIM-TE-8CH-1A | 8 | TE 8 kanallı 1A dimmer |

### DALI Kontrolörleri

| Tip | Model | Kanal | Açıklama |
|-----|-------|-------|----------|
| 7080 | DALI-64 | 64 | DALI 64 kanal kontrolör |
| 7081 | DALI-PRO-64 | 64 | DALI PRO 64 kanal kontrolör |

### Kontrol Panelleri (MARS Serisi)

| Tip | Model | Buton | Açıklama |
|-----|-------|-------|----------|
| 7040 | MRS-4G | 4 | MARS 4 butonlu panel |
| 7050 | MRS-8G | 8 | MARS 8 butonlu panel |
| 7060 | MRS-12G | 12 | MARS 12 butonlu panel |
| 7070 | MRS-AC10G | 10 | MARS AC termostat 10 buton |

### Diğer Cihaz Tipleri

| Tip | Model | Açıklama |
|-----|-------|----------|
| 32 | TIS-DMX-48 | DMX 48 kanal kontrolör |
| 118 | TIS-4DI-IN | 4 bölge dijital giriş |
| 119 | HVAC6-3A-T | HVAC/VAV klima modülü |
| 133 | TIS-PIR-CM | Tavan PIR sensörü |
| 306 | TIS-IR-CUR | Akım sensörlü IR verici |
| 309 | ES-10F-CM | 10 fonksiyonlu sensör |
| 426 | VLC-6CH-3A | Valf/aydınlatma kontrolör 6CH 3A |
| 1108 | TIS-AUT-TMR | Otomasyon zamanlayıcı modül |
| 3049 | TIS-SEC-SM | Güvenlik modülü |

**Veritabanındaki Toplam Cihaz Tipi:** 191

---

## Kanal Yapılandırmaları

### Kanal Eşlemesi Olan Cihazlar

| Tip | Model | Kanal Sayısı |
|-----|-------|--------------|
| 32 | TIS-DMX-48 | 48 |
| 424 | RLY-4CH-10A | 4 |
| 426 | VLC-6CH-3A | 6 |
| 428 | RLY-8CH-16A | 8 |
| 440 | VLC-12CH-10A | 12 |
| 600 | DIM-6CH-2A | 6 |
| 601 | DIM-4CH-3A | 4 |
| 602 | DIM-2CH-6A | 2 |
| 7080 | DALI-64 | 64 |
| 7081 | DALI-PRO-64 | 64 |
| 7090 | TIS-DIM-4CH-1A | 4 |
| 7092 | DIM-TE-2CH-3A | 2 |
| 7094 | DIM-TE-4CH-1.5A | 4 |
| 7098 | RCU-8OUT-8IN | 8 |
| 7099 | RLY-6CH-0-10V | 6 |
| 32798 | ADS-BUS-1D | 1 |
| **32811** | **RCU-24R20Z** | **24** |
| 32813 | RCU-20R20Z-IP | 20 |
| 32816 | DIM-W06CH10A-TE | 6 |
| 32817 | DIM-W12CH10A-TE | 12 |
| 32827 | ADS-3R-BUS | 3 |
| 32832 | ADS-1D-1Z | 1 |
| 32833 | ADS-2R-2Z | 2 |
| 32835 | VEN-4S-4R-HC | 4 |
| 32844 | VEN-2S-2R-HC | 2 |
| 32846 | ADS-4CH-0-10V | 4 |
| 32847 | ADS-3R-3Z | 3 |
| 32849 | AIR-SOCKET-S | 1 |
| 32850 | VEN-1D-UV | 1 |
| 32851 | VEN-3S-3R-HC | 3 |
| 33056 | DIM-TE-8CH-1A | 8 |

**Toplam Yapılandırılmış Cihaz:** 31

---

## Önemli Bulgular

### 1. RCU-24R20Z Tip Kodu Değişikliği

**Keşif:** RCU-24R20Z'nin veritabanında İKİ tip kodu var:
- **Eski Kod:** 214 (db'de model adı yok)
- **Yeni Kod:** 32811 (model adı "RCU-24R20Z" ile)

**Öneri:** Cihaz tespiti için tip kodu **32811** kullanın, ancak geriye dönük uyumluluk için her iki kodu da işleyin.

### 2. Parlaklık Ayrıştırma Hatası

**Sorun:** Orijinal implementasyon her zaman `0xF8` (248) içeren `additional_data[1]`'i okuyordu, bu da %248 parlaklık gösterimine neden oluyordu.

**Çözüm:** Gerçek parlaklık değeri (0-248) için `additional_data[2]`'yi okuyun.

**Etkilenen OpCode'lar:** 0x0032 (geri bildirim)

### 3. Çok Kanallı Sorgu Protokolü

**Keşif:** TIS DevSearch her kanalı ayrı ayrı sorgulamak yerine, tüm kanalları bir kerede almak için OpCode 0x0033/0x0034 kullanıyor.

**Avantajlar:**
- Tek istek ile tüm 24 kanalın durumunu alır
- Ağ trafiğini azaltır
- Daha hızlı cihaz durum güncelleme

### 4. Kanal Adı Desteği

**Keşif:** OpCode 0xF00E/0xF00F cihaz hafızasında saklanan kanal adlarını alır.

**Kullanım:**
- Kanal numarası ile 0xF00E gönder
- UTF-8 kodlu ad ile 0xF00F al
- Ad için maksimum 20 byte
- Türkçe karakterleri destekler

**Gerçek cihazdan örnekler:**
- "Bilinmiyor" (Unknown)
- "KORIDOR TEKLİ" (Tek koridor)
- "LAVABO" (Banyo lavabosu)
- "MUTFAK" (Mutfak)

### 5. Ağ Yapılandırması

**Veritabanından:**
- Host IP: 192.168.2.124 (TIS DevSearch PC'si)
- Filtrelenmiş Subnet: 1 (sadece subnet 1 cihazlarını gösterir)
- Gateway: Subnet 0, Cihaz 0, Tip 186

### 6. Proje Yapısı

**Oda Tanımları:**
- Living Room (Oturma Odası)
- Kitchen (Mutfak)
- Master Room (Ana Oda)
- Kids Room (Çocuk Odası)
- Bath Room (Banyo)
- homepage (varsayılan)

**Sahne Tanımları:**
- 24 sahne yapılandırılmış
- Hepsi Subnet 210, Cihaz 210, Alan 1'de
- Scene-01'den Scene-24'e kadar isimlendirilmiş

### 7. Paket Başlık Formatı

**Keşif:** Tam UDP paketleri şunları içerir:
1. PC IP adresi (4 byte) - gönderenin IP'si
2. "SMARTCLOUD" metni (10 byte) - protokol tanımlayıcı
3. TIS paket verisi (değişken) - gerçek komut/yanıt

**Örnek:**
```
[C0 A8 02 7C] + "SMARTCLOUD" + [01 FE FF FE 01 0A 00 31 03 05 00 7C]
│              │                │
PC IP          Protokol ID      TIS Paketi
192.168.2.124
```

---

## Uygulama Notları

### Home Assistant Entegrasyonu İçin

1. **Cihaz Keşfi:**
   - UDP port 6000'de broadcast'leri dinle
   - "SMARTCLOUD" başlığı olan paketleri ara
   - Cihaz tipini `src_type` alanından ayrıştır
   - RCU-24R20Z'yi tanımlamak için tip kodu 32811 kullan

2. **İlk Durum Sorgusu:**
   - Tüm kanal durumlarını almak için OpCode 0x0033 gönder
   - Her kanal için adları almak için OpCode 0xF00E gönder
   - 0x0034 yanıtını işle (24 byte)
   - 0xF00F yanıtlarını işle (UTF-8 adlar)

3. **Gerçek Zamanlı Geri Bildirim:**
   - OpCode 0x0032 paketlerini dinle
   - `additional_data[2]`'den parlaklığı ayrıştır
   - 0-248'i 0-100%'ye dönüştür
   - Entity durumunu hemen güncelle

4. **Kanal Kontrolü:**
   - Kanal ve parlaklık ile OpCode 0x0031 gönder
   - Format: `[kanal, 0x00, parlaklık_ham]`
   - Yapılandırmadan Gateway IP
   - Kaynak: Subnet 1, Cihaz 254

### TIS Addon İçin

1. **Debug Aracı:**
   - OpCode 0xF00F'u UTF-8 metin olarak decode et
   - Debug çıktısında kanal adlarını göster
   - 0x0034 yanıtından tüm 24 kanalı göster
   - Paket tiplerini renk kodla

2. **Cihaz Listesi:**
   - Tip eşleme için `TIS_DATABASE_ANALYSIS.json` kullan
   - Veritabanından model adını göster
   - Çok kanallı cihazlar için kanal sayısını göster
   - Cihazın kanal adı desteği olup olmadığını belirt

---

## Veritabanı Tabloları Referansı

### Ana Tablolar

1. **tbl_map_type** (191 satır)
   - Cihaz tip kodlarını model adlarına eşler
   - Her cihaz tipi için açıklamalar içerir

2. **tbl_channel** (31 satır)
   - Cihaz tiplerini kanal sayılarına eşler
   - Hangi cihazların çok kanallı olduğunu tanımlar

3. **tbl_project_network** (1 satır)
   - Gateway yapılandırması
   - Sunucu IP ve domain ayarları

4. **tbl_project_room** (6 satır)
   - Oda tanımları
   - Görüntü tipleri ve ikonlar

5. **tbl_project_scene** (24 satır)
   - Sahne yapılandırmaları
   - Subnet, cihaz, alan, sahne numarası eşlemeleri

---

## Gelecek Araştırma Gereksinimleri

### Bilinmeyen OpCode'lar

- **0xF00A/0xF00B:** Bilinmeyen fonksiyon
- **0xF012/0xF013:** Bilinmeyen fonksiyon
- **0xEFFD/0xEFFE:** Cihaz bilgi formatı bilinmiyor

### Eksik Dokümantasyon

- Sahne aktivasyon protokolü
- Güvenlik sistemi komutları
- HVAC/termostat kontrolü
- Ses sistemi komutları
- Sensör veri formatı
- PIR sensör olayları

---

## Revizyon Geçmişi

- **2025-12-05:** İlk dokümantasyon
  - tis.db3 veritabanı analiz edildi
  - 191 cihaz tipi dokümante edildi
  - 31 kanal yapılandırması dokümante edildi
  - OpCode 0xF00F tersine mühendislik yapıldı (kanal adları)
  - OpCode 0x0034 tersine mühendislik yapıldı (çok kanallı durum)

---

**Oluşturan:** TIS Protokol Analiz Aracı  
**Kaynak Dosyalar:**
- `tis.db3` (TIS DevSearch veritabanı)
- `TIS_DATABASE_ANALYSIS.json` (dışa aktarılan veri)
- TIS DevSearch ağ trafiğinden paket yakalamaları

**İlgili Projeler:**
- [TIS Home Assistant Entegrasyonu](https://github.com/Teklojik-Elektronik/tis-homeassistant)
- [TIS Addon](https://github.com/Teklojik-Elektronik/tis_addon)
