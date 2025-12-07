# TIS Entity Registry Düzeltme

## Problem
Home Assistant'ta alfabetik sıralama nedeniyle yanlış entity'ler kontrol ediliyor.

## Çözüm Adımları

### 1. Home Assistant'ı Durdur
```bash
docker stop homeassistant
```

### 2. Entity Registry'yi Sil
```bash
docker exec homeassistant rm /config/.storage/core.entity_registry
```

VEYA manuel olarak:
```
C:\Users\Murat\.homeassistant\.storage\core.entity_registry
```
dosyasını sil.

### 3. Home Assistant'ı Başlat
```bash
docker start homeassistant
```

### 4. TIS Integration'ı Yeniden Ekle
- Settings → Devices & Services
- TIS Control integration'ını SİL
- Yeniden EKLE

### 5. Test Et
Her kanalın doğru çalıştığını kontrol et.

## Alternatif: Entity ID'leri Kontrol Et

Home Assistant Developer Tools → States bölümünden:
- `switch.rcu_24r20z_1_1_bilinmiyor` entity'sinin `channel` attribute'üne bak
- Eğer channel=1 değilse, entity registry bozulmuş demektir

## Debug Logları

Yeni loglar artık entity adını gösteriyor:
```
🔍 COMMAND: Entity='RCU-24R20Z (1.1) Bilinmiyor' → CH1, channel_number=1, brightness=100
```

Bu log, UI'da hangi butona bastığını ve hangi kanalın kontrol edildiğini gösterecek.
