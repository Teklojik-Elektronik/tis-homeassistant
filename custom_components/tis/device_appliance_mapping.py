"""
TIS Device to Appliance/Platform Mapping
Orijinal Laravel Addon seeders dosyalarından çıkarıldı.
Her cihaz modeli için hangi platformların kaç kanalla desteklendiğini gösterir.
"""

# Her cihaz modeli için platform desteği
# Format: "model": {"platform": channel_count, ...}
DEVICE_APPLIANCE_MAPPING = {
    # DMX Controllers
    "TIS-DMX-48": {"rgbw": 5},
    
    # Digital Inputs
    "TIS-4DI-IN": {"binary_sensor": 4},
    "TIS-PIR-CM": {"binary_sensor": 1},
    "ES-10F-CM": {"binary_sensor": 1, "ac": 1},
    
    # Relays
    "RLY-4CH-10A": {"switch": 4},
    "VLC-6CH-3A": {"switch": 6},
    "RLY-8CH-16A": {"switch": 8},
    "VLC-12CH-10A": {"switch": 12},
    
    # Dimmers
    "DIM-6CH-2A": {"dimmer": 6},
    "DIM-4CH-3A": {"dimmer": 4},
    "DIM-2CH-6A": {"dimmer": 2},
    "TIS-DIM-4CH-1A": {"dimmer": 4},
    "DIM-TE-2CH-3A": {"dimmer": 2},
    "DIM-TE-4CH-1.5A": {"dimmer": 4},
    "RLY-6CH-0-10V": {"dimmer": 6},
    "DALI-64": {"dimmer": 12},
    "DALI-PRO-64": {"dimmer": 12},
    "DIM-TE-8CH-1A": {"dimmer": 8},
    "DIM-W06CH10A-TE": {"dimmer": 6},
    "DIM-W12CH10A-TE": {"dimmer": 12},
    
    # Security
    "TIS-SEC-SM": {"security": 1},
    
    # IR Controllers
    "TIS-IR-CUR": {"ac": 1},
    
    # Terre Series
    "TER-ACT": {"ac": 1},
    
    # Mars Series  
    "MRS-AC10G": {"ac": 1},
    
    # Luna Series
    "LUNA-TFT-43": {"ac": 1},
    "LUNA-BEDSIDE": {"ac": 1},
    
    # Motors
    "TIS-M3-MOTOR": {"motor": 1},
    "TIS-M7-CURTAIN": {"motor": 1},
    "TIS-TM-120": {"motor": 1},
    
    # Room Control Units
    "RCU-8OUT-8IN": {"switch": 8, "binary_sensor": 8},
    "RCU-24R20Z": {"switch": 24, "binary_sensor": 20},
    "RCU-20R20Z-IP": {"switch": 20, "binary_sensor": 20},
    
    # IO Series
    "IO-AC-4G": {"ac": 1},
    
    # Mercury (MER) Series - AC Control Panels
    "TIS-MER-AC4G-PB": {"ac": 1, "floor_heating": 1},  # 4-Gang Push Button AC Panel with Floor Heating
    
    # Venera Series (AC Models)
    "VEN-AC-3R-HC-BUS": {"ac": 1, "switch": 3},
    "VEN-AC-4R-HC-BUS": {"ac": 1, "switch": 4},
    "VEN-AC-5R-LC-BUS": {"ac": 1, "switch": 5},
    "VEN-4S-4R-HC": {"switch": 4},
    "VEN-AC-5R-LC": {"ac": 1, "switch": 5},
    "VEN-AC-4R-HC": {"ac": 1, "switch": 4},
    "VEN-2S-2R-HC": {"switch": 2},
    "VEN-AC-3R-HC": {"ac": 1, "switch": 3},
    "VEN-3S-3R-HC": {"switch": 3},
    "VEN-1D-UV": {"dimmer": 1},
    "VEN-AC-3R-1.5-OLED-BUS": {"ac": 1, "switch": 3},
    "VEN-AC-4R-1.5-OLED-BUS": {"ac": 1, "switch": 4},
    "VEN-AC-5R-1.5-OLED-BUS": {"ac": 1, "switch": 5},
    "VEN-AC-3R-1.5-OLED": {"ac": 1, "switch": 3},
    "VEN-AC-4R-1.5-OLED": {"ac": 1, "switch": 4},
    "VEN-AC-5R-1.5-OLED": {"ac": 1, "switch": 5},
    
    # ACM Series
    "ACM-1D-2Z": {"dimmer": 1, "binary_sensor": 2},
    "ACM-3Z-IN": {"binary_sensor": 3},
    "ACM-2R-2Z": {"switch": 2, "binary_sensor": 2},
    
    # ADS Series
    "ADS-1D-1Z": {"dimmer": 1, "binary_sensor": 1},
    "ADS-2R-2Z": {"switch": 2, "binary_sensor": 2},
    "ADS-4CH-0-10V": {"rgbw": 1},
    "ADS-3R-3Z": {"switch": 3, "binary_sensor": 3},
    "ADS-3R-BUS": {"switch": 3},
    
    # Health Sensors
    "TIS-HEALTH-CM": {"health_sensor": 1},
    "TIS-HEALTH-CM-RADAR": {"health_sensor": 1},
    
    # Temperature Sensors
    "TIS-4T-IN": {"temperature_sensor": 4},
    
    # PIR Sensors
    "BUS-PIR-CM": {"binary_sensor": 1},
    "AIR-PIR-CM": {"binary_sensor": 1},
    
    # IR Emitters
    "BUS-ES-IR": {"ac": 1},
    "AIR-ES-IR": {"ac": 1},
    "BUS-AUTO-IRE-T": {"ac": 1, "temperature_sensor": 1},
    "AIR-AUTO-IRE-T": {"ac": 1, "temperature_sensor": 1},
    "MINI-AIR-AUTO-IRE-T": {"ac": 1, "temperature_sensor": 1},
    "AIR-1IRE-T": {"ac": 1, "temperature_sensor": 1},
    "AIR-2IRE": {"ac": 2},
    
    # Energy Meters
    "MET-EN-1PH": {"energy_sensor": 1},
    "MET-EN-3PH": {"energy_sensor": 1},
    
    # Tariq Series
    "TARIQ-8G6R5Z": {"switch": 6, "binary_sensor": 5},
    "TARIQ-8G3R5Z1F": {"switch": 3, "binary_sensor": 5, "fan": 1},
    "TARIQ-8G3R5Z2D": {"switch": 3, "dimmer": 2, "binary_sensor": 5},
    "TARIQ-10G6R5Z1F": {"switch": 6, "binary_sensor": 5, "fan": 1},
    "TARIQ-10G3R5Z1F1DA": {"switch": 3, "binary_sensor": 5, "fan": 1, "dimmer": 1},
    "TARIQ-10G3R5Z2D1F": {"switch": 3, "dimmer": 2, "binary_sensor": 5, "fan": 1},
    
    # Shutter/Motor Controllers
    "TIS-SHUTTER-4CH": {"shutter": 4},
    "TIS-MOTOR-4CH": {"motor": 4},
    
    # Analog Sensors
    "TIS-4CH-AIN": {"analog_sensor": 4},
    "TIS-4AI-010V": {"analog_sensor": 4},
    "TIS-4AI-4-20MA": {"analog_sensor": 4},
    
    # Floor Heating
    "FH-6CH": {"floor_heating": 6},
    "FH-12CH": {"floor_heating": 12},
    
    # RGB/RGBW
    "RGB-4CH": {"rgb": 1},  # 4 channels = 1 RGB light (R, G, B, extra)
    "RGBW-4CH": {"rgbw": 1},  # 4 channels = 1 RGBW light
    
    # Universal Switches
    "US-4CH": {"universal_switch": 4},
    "US-8CH": {"universal_switch": 8},
    
    # Lux Sensors
    "LUX-SENSOR": {"lux_sensor": 1},
    
    # Fan Controllers
    "FAN-4CH": {"fan": 4},
    "TIS-FAN-4CH": {"fan": 4},
    
    # Zigbee Devices
    "ZIG-ACM-2R-2Z": {"switch": 2, "binary_sensor": 2},
    "ZIG-VEN-AC-3R-HC": {"ac": 1, "switch": 3},
    "ZIG-VEN-AC-4R-HC": {"ac": 1, "switch": 4},
    "ZIG-VEN-AC-5R-LC": {"ac": 1, "switch": 5},
    "MINI-ZIG-AUTO-IRE-T": {"ac": 1, "temperature_sensor": 1},
    "TIS-ZIG-HEALTH-CM": {"health_sensor": 1},
    
    # Hotel Series
    "LUNA-IN-HOTEL-HRF": {"switch": 1, "binary_sensor": 3},
    "LUNA-IN-HOTEL-3T3L-HRF": {"switch": 3, "binary_sensor": 3},
    "LUNA-OUT-HOTEL-HRF": {"switch": 3, "binary_sensor": 1},
    "LUNA-OUT-HOTEL": {"switch": 3, "binary_sensor": 1},
    "IO-IN-HOTEL-HRF": {"binary_sensor": 3},
    "IO-OUT-HOTEL-HRF": {"switch": 2, "binary_sensor": 1},
    "IO-OUT-HOTEL": {"switch": 2, "binary_sensor": 1},
    "LUNA-IN-HOTEL-LRF": {"switch": 1, "binary_sensor": 3},
    "LUNA-OUT-HOTEL-LRF": {"switch": 3, "binary_sensor": 1},
    "IO-IN-HOTEL-LRF": {"binary_sensor": 3},
    "IO-OUT-HOTEL-LRF": {"switch": 2, "binary_sensor": 1},
    
    # Click Series
    "CLICK-1G-PANEL-BUS": {},
    "CLICK-2G-PANEL-BUS": {},
    "CLICK-3G-PANEL-BUS": {},
    "CLICK-4G-PANEL-BUS": {},
    "CLICK-6G-PANEL-BUS": {},
    "TIS-CLICK-AC-BUS": {"ac": 1},
    "TIS-CLICK-AC-FH-BUS": {"ac": 1, "floor_heating": 1},
    
    # Europa Series
    "TIS-ERO-1G": {},
    "TIS-ERO-2G": {},
    "TIS-ERO-3G": {},
    "TIS-ERO-4G": {},
    "TIS-ERO-6G": {},
    
    # Sirius Series
    "TIS-SIR-2G": {},
    "TIS-SIR-4G": {},
    "TIS-SIR-6G": {},
    "TIS-SIR-8G": {},
    
    # Panel Series
    "TIS-PANEL-2G": {},
    "TIS-PANEL-4G": {},
    "TIS-PANEL-8G": {},
    
    # Audio/Video
    "AMP-5S1Z-MTX": {},  # Audio Matrix
    "PRJ-LFT-15K-130": {"motor": 1},  # Projector Lift
    "TIS-AUD-SRV-4X-160W": {},  # Audio Server
    
    # Gateways
    "IP-COM-PORT": {},
    "TIS-KNX-PORT": {},
    "TIS-AIR-BUS": {},
    "TIS-BUS-CONVERTER": {},
    "TIS-C-BUS-CONVERTER": {},
    "TIS-ZIG-PORT": {},
    "TIS-ZIG-WF-GTY-V4": {},
    "TIS-ZIG-WF-GTY-V5": {},
    
    # Special Devices
    "TIS-WS-71": {},  # Weather Station
    "TIS-TRV-16CNV": {},  # TRV Controller
    "TIS-GTY-1AC": {"ac": 1},
    "TIS-VRF-AC": {"ac": 32},
    "TIS-SEC-PRO": {"security": 1},
    "TIS-22DI-DIN": {"binary_sensor": 22},
    "TIS-UNIVERSAL-SW": {"universal_switch": 1},  # Universal Switch Button
    
    # Saturn Series
    "TIS-SAT-PAD": {},
    "TIS-SAT57": {},
    "TIS-SAT40": {},
    
    # SOL Series
    "TIS-SOL-3G": {},
    "TIS-SOL-TFT": {},
    
    # Other
    "TIS-BEDSIDE-12G": {},
    "TIS-OUTDOOR-BELL": {},
    "AIR-SOCKET-S": {"switch": 1},
}


# Platform'a göre ters mapping - hangi cihazlar hangi platformu destekliyor
PLATFORM_TO_DEVICES = {}
for device, platforms in DEVICE_APPLIANCE_MAPPING.items():
    for platform in platforms.keys():
        if platform not in PLATFORM_TO_DEVICES:
            PLATFORM_TO_DEVICES[platform] = []
        PLATFORM_TO_DEVICES[platform].append(device)


def get_device_platforms(model_name: str) -> dict:
    """
    Cihaz modeli için desteklenen platformları ve kanal sayılarını döndürür.
    
    Args:
        model_name: Cihaz model adı (örn: "RCU-24R20Z")
        
    Returns:
        Dict: {"platform": channel_count} şeklinde sözlük
        Örn: {"switch": 24, "binary_sensor": 20}
    """
    return DEVICE_APPLIANCE_MAPPING.get(model_name, {})


def supports_platform(model_name: str, platform: str) -> bool:
    """
    Cihazın belirli bir platformu destekleyip desteklemediğini kontrol eder.
    
    Args:
        model_name: Cihaz model adı
        platform: Platform adı (switch, dimmer, ac, vb.)
        
    Returns:
        bool: Platform destekleniyorsa True
    """
    platforms = DEVICE_APPLIANCE_MAPPING.get(model_name, {})
    return platform in platforms


def get_platform_channel_count(model_name: str, platform: str) -> int:
    """
    Cihazın belirli platformu için kanal sayısını döndürür.
    
    Args:
        model_name: Cihaz model adı
        platform: Platform adı
        
    Returns:
        int: Kanal sayısı, desteklenmiyorsa 0
    """
    platforms = DEVICE_APPLIANCE_MAPPING.get(model_name, {})
    return platforms.get(platform, 0)


# TIS Appliance tipleri
TIS_APPLIANCES = [
    "switch",
    "dimmer",  # Light platform
    "rgbw",    # Light platform
    "rgb",     # Light platform
    "ac",      # Climate platform (HVAC/AC control)
    "hvac",    # Climate platform (Generic HVAC)
    "floor_heating",  # Climate platform
    "shutter",  # Cover platform (Curtain/Blind)
    "motor",    # Cover platform (Generic motor)
    "curtain",  # Cover platform (Curtain specific)
    "binary_sensor",
    "security",  # Binary sensor + Alarm panel
    "analog_sensor",  # Sensor platform
    "energy_sensor",  # Sensor platform
    "universal_switch",
    "health_sensor",  # Sensor platform (multiple sensors: temp, humidity, CO2, VOC, PM2.5, lux, noise)
    "lux_sensor",     # Sensor platform
    "temperature_sensor",  # Sensor platform
    "fan",  # Fan platform (speed control)
]


# Home Assistant platform mapping
APPLIANCE_TO_HA_PLATFORM = {
    "switch": "switch",
    "dimmer": "light",
    "rgbw": "light",
    "rgb": "light",
    "ac": "climate",
    "hvac": "climate",
    "floor_heating": "climate",
    "shutter": "cover",
    "motor": "cover",
    "curtain": "cover",
    "binary_sensor": "binary_sensor",
    "security": "select",  # Security mode selection
    "analog_sensor": "sensor",
    "energy_sensor": "sensor",
    "universal_switch": "button",  # Button platform
    "universal_switch": "switch",
    "health_sensor": "sensor",
    "lux_sensor": "sensor",
    "temperature_sensor": "sensor",
    "fan": "fan",
}
