"""TIS Protocol Implementation - UDP Based"""
import socket
import struct
import logging
from typing import Optional, Tuple, Dict, Any

_LOGGER = logging.getLogger(__name__)

# CRC Lookup Table (TIS Documentation - Complete)
CRC_TABLE = [
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
    0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
    0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
    0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
    0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
    0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
    0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
    0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
    0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
    0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
    0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
    0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
    0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
    0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
    0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
    0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
    0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
    0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
    0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
    0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
    0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
    0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
    0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0
]

def calculate_crc(data: bytes) -> int:
    """
    TIS CRC hesaplama - C kodu ile %100 uyumlu
    TIS dokümantasyonundaki Pack_crc fonksiyonu
    """
    crc = 0
    for byte in data:
        dat = (crc >> 8) & 0xFF
        crc = (crc << 8) & 0xFFFF
        crc ^= CRC_TABLE[dat ^ byte]
    return crc


class TISPacket:
    """TIS UDP Packet Builder"""
    
    def __init__(self):
        self.start_code = 0xAAAA
        self.src_subnet = 1
        self.src_device = 254
        self.src_type = 0xFFFE
        self.op_code = 0x0031
        self.tgt_subnet = 1
        self.tgt_device = 1
        self.additional_data = b''
    
    def build(self) -> bytes:
        """Paketi oluştur"""
        # Data package (SN3-SN10 + additional data)
        data_pkg = bytearray()
        data_pkg.append(self.src_subnet)          # SN3
        data_pkg.append(self.src_device)          # SN4
        data_pkg.extend([(self.src_type >> 8) & 0xFF, self.src_type & 0xFF])  # SN5-6
        data_pkg.extend([(self.op_code >> 8) & 0xFF, self.op_code & 0xFF])    # SN7-8
        data_pkg.append(self.tgt_subnet)          # SN9
        data_pkg.append(self.tgt_device)          # SN10
        data_pkg.extend(self.additional_data)     # SN11-N
        
        # Length hesapla (SN2: 1 + data_package + 2 CRC)
        length = 1 + len(data_pkg) + 2
        
        # CRC hesapla (Length + Data Package)
        crc_data = bytes([length]) + bytes(data_pkg)
        crc = calculate_crc(crc_data)
        
        # Tam paket: Start Code + Length + Data Package + CRC
        packet = (
            bytes([(self.start_code >> 8) & 0xFF, self.start_code & 0xFF]) +
            bytes([length]) +
            bytes(data_pkg) +
            bytes([(crc >> 8) & 0xFF, crc & 0xFF])
        )
        
        return packet
    
    @staticmethod
    def parse(packet: bytes) -> Optional[Dict[str, Any]]:
        """Paketi parse et"""
        try:
            # Find AA AA header
            if b'\xAA\xAA' in packet:
                # Split and take the part after AA AA
                # Note: We need to reconstruct the full packet for parsing logic below which expects AA AA at start
                # But wait, the logic below uses indices assuming packet starts with AA AA.
                # So we just need to find where AA AA starts.
                start_index = packet.find(b'\xAA\xAA')
                packet = packet[start_index:]
            
            if len(packet) < 13:
                return None
            
            parsed = {
                'start_code': (packet[0] << 8) | packet[1],
                'length': packet[2],
                'src_subnet': packet[3],
                'src_device': packet[4],
                'src_type': (packet[5] << 8) | packet[6],
                'op_code': (packet[7] << 8) | packet[8],
                'tgt_subnet': packet[9],
                'tgt_device': packet[10],
                'additional_data': b'',
                'crc': (packet[-2] << 8) | packet[-1]
            }
            
            # Additional data (SN11-N, CRC hariç)
            if parsed['length'] > 11:
                additional_start = 11
                crc_start = parsed['length'] + 2 - 2
                # Adjust for packet structure: Length byte is at index 2.
                # Length value includes itself (1) + data + CRC (2).
                # So total packet length from index 2 is `length`.
                # Data starts at index 3.
                # additional_data starts after tgt_device (index 10), so at index 11.
                # CRC is at the end.
                
                # Let's verify length calculation from build():
                # length = 1 + len(data_pkg) + 2
                # data_pkg = src_subnet(1) + src_device(1) + src_type(2) + op_code(2) + tgt_subnet(1) + tgt_device(1) + additional(...)
                # data_pkg header size = 1+1+2+2+1+1 = 8 bytes.
                # So length = 1 + 8 + len(additional) + 2 = 11 + len(additional).
                
                # If length > 11, there is additional data.
                # additional_data is from index 11 up to (but not including) CRC.
                # CRC is at index 2 + length - 2 = length.
                # Wait, packet indices:
                # 0,1: AA AA
                # 2: Length
                # 3..10: Header fields
                # 11..: Additional data
                # End: CRC (2 bytes)
                
                # Total bytes from index 2 is `length`.
                # So last byte index is 2 + length - 1.
                # CRC is at 2 + length - 2 and 2 + length - 1.
                
                crc_index = 2 + parsed['length'] - 2
                if 11 < crc_index <= len(packet):
                     parsed['additional_data'] = packet[11:crc_index]
            
            return parsed
            
        except Exception as e:
            _LOGGER.error(f"Paket parse hatası: {e}")
            return None


class TISUDPClient:
    """TIS UDP İletişim Client"""
    
    def __init__(self, gateway_ip: str = None, port: int = 6000):
        self.gateway_ip = gateway_ip
        self.port = port
        self.sock = None
        self.is_connected = False
        
    async def async_connect(self, bind: bool = False) -> bool:
        """UDP socket aç"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.settimeout(1.0)
            
            if bind:
                self.sock.bind(('', self.port))
                _LOGGER.info(f"TIS UDP client bind edildi (port {self.port})")
            
            self.is_connected = True
            return True
        except Exception as e:
            _LOGGER.error(f"UDP socket açma hatası: {e}")
            return False
    
    def send_broadcast(self, packet: bytes):
        """UDP broadcast gönder"""
        try:
            if self.sock:
                self.sock.sendto(packet, ('<broadcast>', self.port))
                _LOGGER.debug(f"UDP broadcast gönderildi: {packet.hex()}")
        except Exception as e:
            _LOGGER.error(f"UDP broadcast hatası: {e}")
    
    def send_to(self, packet: bytes, ip: str):
        """Belirli IP'ye gönder"""
        try:
            if self.sock:
                self.sock.sendto(packet, (ip, self.port))
                _LOGGER.debug(f"UDP paketi gönderildi {ip}: {packet.hex()}")
        except Exception as e:
            _LOGGER.error(f"UDP gönderme hatası: {e}")
    
    def receive(self, timeout=1.0) -> Tuple[Optional[bytes], Optional[str]]:
        """UDP paketi al"""
        try:
            if self.sock:
                self.sock.settimeout(timeout)
                data, addr = self.sock.recvfrom(1024)
                return data, addr[0]
        except socket.timeout:
            return None, None
        except Exception as e:
            _LOGGER.error(f"UDP alma hatası: {e}")
            return None, None
    
    def close(self):
        """Socket kapat"""
        if self.sock:
            self.sock.close()
            self.is_connected = False


def parse_radar_motion_packet(data: bytes) -> dict | None:
    """
    Parse TIS radar motion detection packet (OpCode 0x2025, 62 bytes).
    
    Returns motion detection data including:
    - target_count: Number of detected targets (2=stationary only, 3=motion+stationary)
    - motion_distance_cm: Distance to moving target in centimeters
    - stationary_distance_cm: Distance to stationary target in centimeters  
    - motion_detected: Boolean indicating if motion is detected
    - state: Motion state (idle/motion/occupancy/occupancy_strong)
    - state_raw: Raw state byte value
    """
    try:
        if len(data) != 62:
            return None
        
        # Check OpCode 0x2025
        if data[5:7] != b'\x20\x25':
            return None
        
        # Check if this is motion detection packet (not environment status)
        # Motion packets have subtype FF FF at bytes 7-8
        if data[7:9] != b'\xFF\xFF':
            return None
        
        target_count = data[19]
        motion_distance = (data[21] << 8) | data[20]  # Little-endian
        stationary_distance = (data[23] << 8) | data[22]  # Little-endian
        motion_state = data[55]
        
        # State mapping
        state_map = {
            0x00: 'idle',
            0x55: 'idle',
            0x01: 'motion',
            0x02: 'occupancy_strong',
            0xF1: 'occupancy',
            0xF2: 'occupancy'
        }
        
        return {
            'target_count': target_count,
            'motion_distance_cm': motion_distance if target_count >= 3 else 0,
            'stationary_distance_cm': stationary_distance,
            'motion_detected': target_count >= 3 and motion_state in [0x01, 0x02, 0xF1, 0xF2],
            'state': state_map.get(motion_state, 'unknown'),
            'state_raw': motion_state
        }
    except Exception as e:
        _LOGGER.error(f"Radar motion packet parse error: {e}")
        return None


def parse_environment_status_packet(data: bytes) -> dict | None:
    """
    Parse TIS environment status packet (OpCode 0x2025, Subtype 0x14, 37 bytes).
    
    Returns environment data including:
    - lux: Room brightness in lux (0-5000 range)
    - threshold_low: LUX threshold low value
    - threshold_high: LUX threshold high value
    """
    try:
        if len(data) != 37:
            return None
        
        # Check OpCode 0x2025
        if data[5:7] != b'\x20\x25':
            return None
        
        # Check subtype 0x01 0xFE (environment status marker)
        if data[7:9] != b'\x01\xFE':
            return None
        
        # Check subtype 0x14 0x00
        subtype = (data[9] << 8) | data[10]
        if subtype != 0x1400:
            return None
        
        lux_value = (data[16] << 8) | data[15]  # Little-endian, bytes 15-16
        threshold_low = (data[21] << 8) | data[20]  # Bytes 20-21
        threshold_high = (data[23] << 8) | data[22]  # Bytes 22-23
        
        return {
            'lux': lux_value,
            'threshold_low': threshold_low,
            'threshold_high': threshold_high,
            'unit': 'lx'
        }
    except Exception as e:
        _LOGGER.error(f"Environment status packet parse error: {e}")
        return None
