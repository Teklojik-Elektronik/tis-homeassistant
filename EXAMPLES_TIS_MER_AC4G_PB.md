# TIS-MER-AC4G-PB Kullanım Örnekleri

## 🌡️ Sıcaklık Bilgilerine Erişim

### Climate Entity Yapısı

Cihazınız Home Assistant'da **2 adet Climate Entity** olarak görünür:

1. **`climate.tis_mer_ac4g_pb_ac1`** - AC (Klima) Kontrolü
   - `current_temperature` → Oda sıcaklığı (Luna Temp sensöründen)
   - `target_temperature` → AC için set edilmiş sıcaklık (Cool/Heat/Auto moduna göre)
   - `hvac_mode` → OFF, COOL, HEAT, AUTO
   - `fan_mode` → AUTO, LOW, MEDIUM, HIGH

2. **`climate.tis_mer_ac4g_pb_floor_heater_1`** - Yerden Isıtma
   - `target_temperature` → Yerden ısıtma için set edilmiş sıcaklık
   - `hvac_mode` → OFF, HEAT
   - `current_temperature` → Luna Temp sensöründen (paylaşımlı)

---

## 📊 Lovelace Dashboard Örnekleri

### 1. Basit Thermostat Card

```yaml
type: thermostat
entity: climate.tis_mer_ac4g_pb_ac1
name: Salon Klima
features:
  - type: climate-hvac-modes
    hvac_modes:
      - "off"
      - cool
      - heat
      - auto
```

### 2. Detaylı Sıcaklık Gösterimi

```yaml
type: entities
entities:
  - entity: climate.tis_mer_ac4g_pb_ac1
    name: Salon AC
    secondary_info: last-changed
  - type: attribute
    entity: climate.tis_mer_ac4g_pb_ac1
    attribute: current_temperature
    name: Oda Sıcaklığı
    suffix: "°C"
  - type: attribute
    entity: climate.tis_mer_ac4g_pb_ac1
    attribute: temperature
    name: AC Hedef Sıcaklık
    suffix: "°C"
  - entity: climate.tis_mer_ac4g_pb_floor_heater_1
    name: Yerden Isıtma
  - type: attribute
    entity: climate.tis_mer_ac4g_pb_floor_heater_1
    attribute: temperature
    name: Zemin Hedef Sıcaklık
    suffix: "°C"
```

### 3. Template Sensor ile Sıcaklık Farkı

```yaml
# configuration.yaml içine ekleyin
template:
  - sensor:
      - name: "Salon Sıcaklık Farkı"
        unique_id: salon_temp_difference
        unit_of_measurement: "°C"
        state: >
          {% set current = state_attr('climate.tis_mer_ac4g_pb_ac1', 'current_temperature') %}
          {% set target = state_attr('climate.tis_mer_ac4g_pb_ac1', 'temperature') %}
          {% if current and target %}
            {{ (target - current) | round(1) }}
          {% else %}
            unavailable
          {% endif %}
        attributes:
          friendly_name: "Hedef ile Mevcut Sıcaklık Farkı"
```

---

## 🤖 Automation Örnekleri

### 1. Oda Çok Sıcaksa AC'yi Aç

```yaml
automation:
  - alias: "Salon çok sıcak olunca AC aç"
    trigger:
      - platform: numeric_state
        entity_id: climate.tis_mer_ac4g_pb_ac1
        attribute: current_temperature
        above: 26
    condition:
      - condition: state
        entity_id: climate.tis_mer_ac4g_pb_ac1
        state: "off"
    action:
      - service: climate.set_hvac_mode
        target:
          entity_id: climate.tis_mer_ac4g_pb_ac1
        data:
          hvac_mode: cool
      - service: climate.set_temperature
        target:
          entity_id: climate.tis_mer_ac4g_pb_ac1
        data:
          temperature: 24
```

### 2. Gece Yerden Isıtmayı Otomatik Ayarla

```yaml
automation:
  - alias: "Gece yerden ısıtmayı düşür"
    trigger:
      - platform: time
        at: "23:00:00"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.tis_mer_ac4g_pb_floor_heater_1
        data:
          temperature: 20
  
  - alias: "Sabah yerden ısıtmayı artır"
    trigger:
      - platform: time
        at: "06:00:00"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.tis_mer_ac4g_pb_floor_heater_1
        data:
          temperature: 24
```

### 3. Sıcaklık Bildirimi

```yaml
automation:
  - alias: "Sıcaklık hedefine ulaştı bildirimi"
    trigger:
      - platform: template
        value_template: >
          {% set current = state_attr('climate.tis_mer_ac4g_pb_ac1', 'current_temperature') %}
          {% set target = state_attr('climate.tis_mer_ac4g_pb_ac1', 'temperature') %}
          {{ current and target and (current - target)|abs < 0.5 }}
    condition:
      - condition: not
        conditions:
          - condition: state
            entity_id: climate.tis_mer_ac4g_pb_ac1
            state: "off"
    action:
      - service: notify.mobile_app
        data:
          title: "Klima Hedefine Ulaştı"
          message: >
            Salon sıcaklığı {{ state_attr('climate.tis_mer_ac4g_pb_ac1', 'current_temperature') }}°C 
            (Hedef: {{ state_attr('climate.tis_mer_ac4g_pb_ac1', 'temperature') }}°C)
```

---

## 🔧 Developer Tools'da Test

### States Sekmesinde

Entity'yi seçin ve attribute'lara bakın:
```
climate.tis_mer_ac4g_pb_ac1
  current_temperature: 23.5
  temperature: 24
  hvac_mode: cool
  fan_mode: auto
```

### Services Sekmesinde Test

#### AC Sıcaklığını Değiştir
```yaml
service: climate.set_temperature
target:
  entity_id: climate.tis_mer_ac4g_pb_ac1
data:
  temperature: 22
```

#### Yerden Isıtma Sıcaklığını Değiştir
```yaml
service: climate.set_temperature
target:
  entity_id: climate.tis_mer_ac4g_pb_floor_heater_1
data:
  temperature: 25
```

---

## 📝 Python Script ile Erişim

```python
# custom_components/python_scripts/get_temperatures.py
hass = hass  # noqa: F821

# AC entity
ac_entity = "climate.tis_mer_ac4g_pb_ac1"
ac_state = hass.states.get(ac_entity)

current_temp = ac_state.attributes.get('current_temperature')
target_temp = ac_state.attributes.get('temperature')
hvac_mode = ac_state.state

# Floor heating entity
floor_entity = "climate.tis_mer_ac4g_pb_floor_heater_1"
floor_state = hass.states.get(floor_entity)
floor_target = floor_state.attributes.get('temperature')

# Log to Home Assistant
logger.info(f"Oda Sıcaklığı: {current_temp}°C")
logger.info(f"AC Hedef: {target_temp}°C")
logger.info(f"Zemin Hedef: {floor_target}°C")
logger.info(f"AC Mod: {hvac_mode}")
```

---

## 🎯 Özet

| **Bilgi** | **Entity** | **Attribute** | **Açıklama** |
|-----------|-----------|---------------|--------------|
| Oda Sıcaklığı | `climate.tis_mer_ac4g_pb_ac1` | `current_temperature` | Luna Temp sensöründen gelen gerçek oda sıcaklığı |
| AC Hedef Sıcaklık | `climate.tis_mer_ac4g_pb_ac1` | `temperature` | Kullanıcının set ettiği AC hedef sıcaklığı |
| Zemin Hedef Sıcaklık | `climate.tis_mer_ac4g_pb_floor_heater_1` | `temperature` | Yerden ısıtma hedef sıcaklığı |
| AC Modu | `climate.tis_mer_ac4g_pb_ac1` | `state` | OFF, COOL, HEAT, AUTO |
| Zemin Modu | `climate.tis_mer_ac4g_pb_floor_heater_1` | `state` | OFF, HEAT |

---

## 🔍 Debug ve Log Takibi

Home Assistant loglarında şu satırları arayın:

```
🌡️ Luna temp: 1.103 → 23°C              # Oda sıcaklığı
❄️ AC feedback: 1.103 AC0 → ON, Cool=24°C  # AC hedef sıcaklık
🔥 Floor binary feedback: 1.103 Heater0 → ON, Temp=22°C  # Zemin hedef sıcaklık
```

Log seviyesini artırmak için `configuration.yaml`:
```yaml
logger:
  default: info
  logs:
    custom_components.tis: debug
```
