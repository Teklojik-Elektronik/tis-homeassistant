"""Constants for the TIS Control integration."""

DOMAIN = "tis"
DEFAULT_NAME = "TIS Control"

# UDP Communication
UDP_PORT = 6000  # TIS UDP Port
DISCOVERY_TIMEOUT = 30
DISCOVERY_OP_CODE = 0x000E  # Status Request için discovery

# Device communication
CONF_HOST = "host"
CONF_PORT = "port"
CONF_DEVICE_ID = "device_id"
CONF_SUBNET = "subnet"
CONF_DEVICE = "device"

# Update interval
UPDATE_INTERVAL = 30  # seconds

# TIS Device Types (Model ID -> Name, Channels)
# Format: (HighByte, LowByte): ("Model Name", ChannelCount)
# Complete TIS Product Database - 191 Devices
TIS_DEVICE_TYPES = {
    # Basic Controllers & Relays
    (0x00, 0x20): ("TIS-DMX-48", 48),
    (0x00, 0x76): ("TIS-4DI-IN", 4),
    (0x00, 0x77): ("HVAC6-3A-T", 6),
    (0x00, 0x85): ("TIS-PIR-CM", 1),
    (0x01, 0x32): ("TIS-IR-CUR", 1),
    (0x01, 0x35): ("ES-10F-CM", 10),
    (0x01, 0xA8): ("RLY-4CH-10A", 4),
    (0x01, 0xAA): ("VLC-6CH-3A", 6),
    (0x01, 0xAC): ("RLY-8CH-16A", 8),
    (0x01, 0xB8): ("VLC-12CH-10A", 12),
    
    # Dimmers
    (0x02, 0x58): ("DIM-6CH-2A", 6),
    (0x02, 0x59): ("DIM-4CH-3A", 4),
    (0x02, 0x5A): ("DIM-2CH-6A", 2),
    (0x1B, 0xB2): ("TIS-DIM-4CH-1A", 4),
    (0x1B, 0xB4): ("DIM-TE-2CH-3A", 2),
    (0x1B, 0xB6): ("DIM-TE-4CH-1.5A", 4),
    (0x80, 0x30): ("DIM-W06CH10A-TE", 6),
    (0x80, 0x31): ("DIM-W12CH10A-TE", 12),
    (0x81, 0x20): ("DIM-TE-8CH-1A", 8),
    
    # Automation & Timer
    (0x04, 0x54): ("TIS-AUT-TMR", 1),
    (0x04, 0xB1): ("IP-COM-PORT-OLD", 1),
    (0x0B, 0xE9): ("TIS-SEC-SM", 1),
    
    # Terre Series
    (0x17, 0x70): ("TER-4G", 4),
    (0x17, 0x7A): ("TER-ACT", 1),
    (0x17, 0x84): ("TER-AUD", 1),
    (0x80, 0x95): ("TER-2G", 2),
    
    # Mars Series
    (0x1B, 0x80): ("MRS-4G", 4),
    (0x1B, 0x8A): ("MRS-8G", 8),
    (0x1B, 0x94): ("MRS-12G", 12),
    (0x1B, 0x9E): ("MRS-AC10G", 10),
    
    # DALI Controllers
    (0x1B, 0xA8): ("DALI-64", 64),
    (0x1B, 0xA9): ("DALI-PRO-64", 64),
    
    # Room Control Units
    (0x1B, 0xBA): ("RCU-8OUT-8IN", 8),
    (0x1B, 0xBB): ("RLY-6CH-0-10V", 6),
    (0x80, 0x2B): ("RCU-24R20Z", 24),
    (0x80, 0x2D): ("RCU-20R20Z-IP", 20),
    
    # Luna Series
    (0x23, 0x32): ("LUNA-TFT-43", 18),
    (0x23, 0x96): ("LUNA-9GANGS", 9),
    (0x23, 0xFA): ("LUNA-BEDSIDE", 8),
    (0x24, 0x5E): ("LUNA-BELL-3S", 3),
    (0x80, 0x64): ("LUNA-IN-HOTEL-HRF", 1),
    (0x80, 0x65): ("LUNA-IN-HOTEL-3T3L-HRF", 3),
    (0x80, 0x67): ("LUNA-OUT-HOTEL-HRF", 1),
    (0x80, 0x68): ("LUNA-OUT-HOTEL", 1),
    (0x80, 0x6F): ("LUNA-IN-HOTEL-LRF", 1),
    (0x80, 0x70): ("LUNA-OUT-HOTEL-LRF", 1),
    (0x80, 0x71): ("LUNA-IN-HOTEL-3T3L-LRF", 3),
    (0x80, 0x9C): ("LUNA-OUT-HOTEL-HRF-809C", 1),
    (0x80, 0x9D): ("LUNA-OUT-HOTEL-809D", 1),
    
    # Motors
    (0x80, 0x10): ("TIS-M3-MOTOR", 1),
    (0x80, 0x1C): ("TIS-M7-CURTAIN", 1),
    (0x81, 0x10): ("TIS-TM-120", 1),
    
    # IO & Titan Series
    (0x80, 0x13): ("IO-8G", 8),
    (0x80, 0x14): ("IO-AC-4G", 4),
    (0x80, 0x17): ("TIT-2G-BUS", 2),
    (0x80, 0x18): ("TIT-3G-BUS", 3),
    (0x80, 0x19): ("TIT-4G-BUS", 4),
    (0x80, 0x2C): ("TIT-TFT-BUS", 12),
    (0x80, 0x66): ("IO-IN-HOTEL-HRF", 3),
    (0x80, 0x69): ("IO-OUT-HOTEL-HRF", 1),
    (0x80, 0x6A): ("IO-OUT-HOTEL", 1),
    (0x80, 0x6D): ("IO-IN-HOTEL-LRF", 3),
    (0x80, 0x6E): ("IO-OUT-HOTEL-LRF", 1),
    (0x80, 0x9A): ("IO-OUT-HOTEL-HRF-809A", 1),
    (0x80, 0x9B): ("IO-OUT-HOTEL-809B", 1),
    (0x80, 0x9E): ("IO-IN-HOTEL-HRF-809E", 3),
    
    # Venera Series
    (0x80, 0x15): ("VEN-6S-BUS", 6),
    (0x80, 0x24): ("VEN-2S-BUS", 2),
    (0x80, 0x25): ("VEN-3S-BUS", 3),
    (0x80, 0x26): ("VEN-4S-BUS", 4),
    (0x80, 0x27): ("VEN-AC-3R-HC-BUS", 3),
    (0x80, 0x28): ("VEN-AC-4R-HC-BUS", 4),
    (0x80, 0x29): ("VEN-AC-5R-LC-BUS", 5),
    (0x80, 0x43): ("VEN-4S-4R-HC", 4),
    (0x80, 0x44): ("VEN-AC-5R-LC", 5),
    (0x80, 0x45): ("VEN-AC-4R-HC", 4),
    (0x80, 0x4C): ("VEN-2S-2R-HC", 2),
    (0x80, 0x4D): ("VEN-AC-3R-HC", 3),
    (0x80, 0x52): ("VEN-1D-UV", 1),
    (0x80, 0x53): ("VEN-3S-3R-HC", 3),
    (0x80, 0x7E): ("VEN-2G-HC-BUS-B", 2),
    (0x80, 0x7F): ("VEN-3G-HC-BUS-B", 3),
    (0x80, 0x80): ("VEN-4G-HC-BUS-B", 4),
    (0x80, 0x81): ("VEN-AC-3R-1.5-OLED-BUS", 3),
    (0x80, 0x82): ("VEN-AC-4R-1.5-OLED-BUS", 4),
    (0x80, 0x83): ("VEN-AC-5R-1.5-OLED-BUS", 5),
    (0x80, 0x85): ("VEN-AC-3R-1.5-OLED", 3),
    (0x80, 0x86): ("VEN-AC-4R-1.5-OLED", 4),
    (0x80, 0x87): ("VEN-AC-5R-1.5-OLED", 5),
    (0x80, 0x8B): ("VEN-2G-HC-AIR-A", 2),
    (0x80, 0x8C): ("VEN-3G-HC-AIR-A", 3),
    (0x80, 0x8D): ("VEN-4G-HC-AIR-A", 4),
    
    # Tariq Series
    (0x80, 0x1A): ("TARIQ-8G6R5Z", 8),
    (0x80, 0x1B): ("TARIQ-8G3R5Z1F", 8),
    (0x80, 0x1C): ("TARIQ-8G3R5Z2D", 8),
    (0x80, 0xD0): ("TARIQ-10G6R5Z1F", 10),
    (0x80, 0xD1): ("TARIQ-10G3R5Z1F1DA", 10),
    (0x80, 0xD2): ("TARIQ-10G3R5Z2D1F", 10),
    
    # AC Modules & Valves
    (0x80, 0x1D): ("AC-6VAL-6T", 6),
    (0x80, 0x2E): ("ACM-1D-2Z", 1),
    (0x80, 0x3C): ("ACM-3Z-IN", 3),
    (0x80, 0x4B): ("ACM-2R-2Z", 2),
    
    # ADS Series
    (0x80, 0x1E): ("ADS-BUS-1D", 1),
    (0x80, 0x3B): ("ADS-3R-BUS", 3),
    (0x80, 0x40): ("ADS-1D-1Z", 1),
    (0x80, 0x41): ("ADS-2R-2Z", 2),
    (0x80, 0x4E): ("ADS-4CH-0-10V", 4),
    (0x80, 0x4F): ("ADS-3R-3Z", 3),
    
    # Mercury Series
    (0x80, 0x1F): ("TIS-MER-ROTATE", 1),
    (0x80, 0x20): ("TIS-MER-6G-PB", 6),
    (0x80, 0x21): ("TIS-MER-9G-PB", 9),
    (0x80, 0x6B): ("TIS-MER-8G-PB", 8),
    (0x80, 0x6C): ("TIS-MER-AC4G-PB", 4),
    (0x80, 0x94): ("MER-IN-HOTEL-LRF", 1),
    (0x80, 0x98): ("MER-OUT-HOTEL-LRF", 1),
    (0x80, 0x9A): ("MER-IN-HOTEL-HRF-80AA", 1),
    (0x80, 0x9D): ("MER-OUT-HOTEL-HRF-80AD", 1),
    (0x81, 0x21): ("TIS-MER-AC-TFT-2G", 2),
    
    # Health & Sensors
    (0x80, 0x22): ("TIS-HEALTH-CM", 1),
    (0x80, 0x2F): ("TIS-4T-IN", 4),
    (0x80, 0x37): ("BUS-PIR-CM", 1),
    (0x80, 0x38): ("BUS-ES-IR", 12),
    (0x80, 0x3E): ("BUS-AUTO-IRE-T", 1),
    (0x80, 0x3F): ("AIR-ES-IR", 12),
    (0x80, 0x42): ("AIR-PIR-CM", 1),
    (0x80, 0x46): ("AIR-1IRE-T", 1),
    (0x80, 0x48): ("AIR-2IRE", 2),
    (0x80, 0x49): ("AIR-SOCKET-S", 1),
    (0x80, 0x90): ("TIS-4T-IN", 4),
    (0x80, 0x9E): ("TIS-HEALTH-CM-RADAR", 1),
    (0x80, 0xB0): ("TIS-4CH-AIN", 4),
    (0x80, 0xB8): ("TIS-OS-MMV2-IC", 1),
    (0x80, 0xBA): ("TIS-OS-MMV2-IRE", 1),
    (0x80, 0xBB): ("TIS-4AI-010V", 4),
    (0x80, 0xBC): ("TIS-4AI-4-20MA", 4),
    
    # AIR Series
    (0x80, 0x3A): ("MINI-AIR-AUTO-IRE-T", 1),
    (0x80, 0x3D): ("AIR-AUTO-IRE-T", 1),
    (0x80, 0x54): ("TIS-AIR-BUS", 1),
    
    # Gateways & Converters
    (0x80, 0x58): ("IP-COM-PORT", 1),
    (0x80, 0x60): ("MET-EN-1PH", 1),
    (0x80, 0x61): ("TIS-KNX-PORT", 1),
    (0x80, 0x62): ("TIS-TRV-16CNV", 16),
    (0x80, 0x7A): ("TIS-GTY-1AC", 1),
    (0x80, 0x89): ("TIS-VRF-AC", 32),
    (0x80, 0x90): ("TIS-BUS-CONVERTER", 1),
    (0x80, 0xC0): ("TIS-C-BUS-CONVERTER", 1),
    
    # Audio & Projector
    (0x80, 0x50): ("AMP-5S1Z-MTX", 5),
    (0x80, 0x55): ("PRJ-LFT-15K-130", 1),
    (0x80, 0x57): ("TIS-WS-71", 1),
    (0x80, 0xCB): ("TIS-AUD-SRV-4X-160W", 4),
    
    # Zigbee Series
    (0x80, 0x32): ("ZIG-ACM-2R-2Z", 2),
    (0x80, 0x33): ("ZIG-VEN-OUT-HOTEL-HRF-8033", 1),
    (0x80, 0xCA): ("TIS-ZIG-PORT", 1),
    (0x80, 0xCF): ("TIS-ZIG-WF-GTY-V4", 1),
    (0x80, 0xD5): ("TIS-ZIG-WF-GTY-V5", 1),
    (0x81, 0x0A): ("ZIG-VEN-AC-3R-HC", 3),
    (0x81, 0x0B): ("ZIG-VEN-AC-4R-HC", 4),
    (0x81, 0x0C): ("ZIG-VEN-AC-5R-LC", 5),
    (0x81, 0x0D): ("MINI-ZIG-AUTO-IRE-T", 1),
    (0x81, 0x0F): ("TIS-ZIG-OS-MMV2-IRE", 1),
    (0x81, 0x11): ("TIS-ZIG-VEN-4G-IRE", 4),
    (0x81, 0x14): ("TIS-ZIG-HEALTH-CM", 1),
    (0x81, 0x16): ("TIS-ZIG-BUS-CONVERTER", 1),
    
    # SOL & Other Panels
    (0x80, 0x8F): ("TIS-BEDSIDE-12G", 12),
    (0x80, 0x91): ("TIS-OUTDOOR-BELL", 1),
    (0x80, 0x93): ("TIS-SOL-3G", 3),
    (0x80, 0x96): ("TIS-SOL-TFT", 12),
    (0x80, 0xA7): ("TIS-SEC-PRO", 1),
    (0x80, 0xA8): ("TIS-CLICK-AC-BUS", 1),
    (0x80, 0xA9): ("TIS-22DI-DIN", 22),
    (0x80, 0xBF): ("TIS-CLICK-AC-FH-BUS", 1),
    (0x80, 0xC1): ("TIS-FAN-4CH", 4),
    
    # Click Series
    (0x80, 0xA1): ("CLICK-1G-PANEL-BUS", 1),
    (0x80, 0xA2): ("CLICK-2G-PANEL-BUS", 2),
    (0x80, 0xA3): ("CLICK-3G-PANEL-BUS", 3),
    (0x80, 0xA4): ("CLICK-4G-PANEL-BUS", 4),
    (0x80, 0xA6): ("CLICK-6G-PANEL-BUS", 6),
    
    # Europa Series
    (0x80, 0xB9): ("TIS-ERO-1G", 1),
    (0x80, 0xBA): ("TIS-ERO-2G", 2),
    (0x80, 0xBB): ("TIS-ERO-3G", 3),
    (0x80, 0xBC): ("TIS-ERO-4G", 4),
    (0x80, 0xBE): ("TIS-ERO-6G", 6),
    
    # Sirius Series
    (0x80, 0xC2): ("TIS-SIR-2G", 2),
    (0x80, 0xC4): ("TIS-SIR-4G", 4),
    (0x80, 0xC6): ("TIS-SIR-6G", 6),
    (0x80, 0xC8): ("TIS-SIR-8G", 8),
    
    # Panel Series
    (0x81, 0x16): ("TIS-PANEL-2G", 2),
    (0x81, 0x18): ("TIS-PANEL-4G", 4),
    (0x81, 0x19): ("TIS-PANEL-8G", 8),
    
    # Saturn Series
    (0xCC, 0xB3): ("TIS-SAT-PAD", 1),
    (0xCC, 0xB4): ("TIS-SAT57", 1),
    (0xCC, 0xB5): ("TIS-SAT40", 1),
}

def get_device_info(device_type_id):
    """Get device info from type ID."""
    # device_type_id is int, convert to (high, low)
    high = (device_type_id >> 8) & 0xFF
    low = device_type_id & 0xFF
    return TIS_DEVICE_TYPES.get((high, low), ("Unknown Device", 1))
