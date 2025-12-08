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
    
    # OpCode Tanımları (TISControlProtocol ile uyumlu)
    OPERATION_CONTROL = 0x0031              # Tek kanal kontrol (ON/OFF/DIM)
    OPERATION_CONTROL_UPDATE = 0x0033       # Durum sorgulama (Multi-channel)
    OPERATION_GET_TEMP = 0xE3E7             # Sıcaklık sensörü
    OPERATION_GET_HEALTH = 0x2024           # Health sensör (TIS-HEALTH-CM)
    OPERATION_GET_WEATHER = 0x2020          # Hava durumu sensörü
    OPERATION_ANALOG_UPDATE = 0xEF00        # Analog girişler
    OPERATION_ENERGY_UPDATE = 0x2010        # Enerji ölçer
    OPERATION_DISCOVERY = 0x000E            # Cihaz keşfi (broadcast)
    OPERATION_CONTROL_SECURITY = 0x0104     # Güvenlik modu ayarla
    OPERATION_SECURITY_UPDATE = 0x011E      # Güvenlik durumu sorgula
    OPERATION_CONTROL_AC = 0xE0EE           # Klima kontrolü
    OPERATION_AC_UPDATE = 0xE0EC            # Klima durumu sorgula
    OPERATION_FLOOR_UPDATE = 0x1944         # Yerden ısıtma durumu
    OPERATION_FLOOR_CONTROL = 0xE3D8        # Yerden ısıtma kontrolü
    OPERATION_UNIVERSAL_SWITCH = 0xE01C     # Evrensel switch
    
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
            # Find AA AA header (always present in real UDP packets)
            if b'\xAA\xAA' in packet:
                start_index = packet.find(b'\xAA\xAA')
                packet = packet[start_index:]
            else:
                # If no AA AA found, packet might be truncated or from debug console
                # Log warning and try to parse anyway
                _LOGGER.warning(f"Packet missing AA AA header, length={len(packet)}")
            
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
    
    # ==================== Static Helper Methods ====================
    # TISControlProtocol referans alınarak eklendi
    
    @staticmethod
    def create_control_packet(subnet: int, device: int, channel: int, value: int, speed: int = 0) -> 'TISPacket':
        """
        Switch/Light kontrol paketi oluştur (0x0031)
        
        Args:
            subnet: Hedef subnet
            device: Hedef device ID
            channel: Kanal numarası
            value: 0=OFF, 1-100=ON/DIM
            speed: Transition speed (default 0)
        """
        packet = TISPacket()
        packet.op_code = TISPacket.OPERATION_CONTROL
        packet.tgt_subnet = subnet
        packet.tgt_device = device
        packet.additional_data = bytes([channel, value, speed, 0x00])
        return packet
    
    @staticmethod
    def create_query_packet(subnet: int, device: int) -> 'TISPacket':
        """
        Multi-channel durum sorgulama paketi (0x0033)
        
        Args:
            subnet: Hedef subnet
            device: Hedef device ID
        """
        packet = TISPacket()
        packet.op_code = TISPacket.OPERATION_CONTROL_UPDATE
        packet.tgt_subnet = subnet
        packet.tgt_device = device
        packet.additional_data = b''
        return packet
    
    @staticmethod
    def create_health_query_packet(subnet: int, device: int) -> 'TISPacket':
        """
        Health sensör sorgulama paketi (0x2024) - TIS-HEALTH-CM için
        
        Args:
            subnet: Hedef subnet
            device: Hedef device ID
        """
        packet = TISPacket()
        packet.op_code = TISPacket.OPERATION_GET_HEALTH
        packet.tgt_subnet = subnet
        packet.tgt_device = device
        packet.additional_data = bytes([0x14, 0x00])  # Health sensor type
        return packet
    
    @staticmethod
    def create_temp_query_packet(subnet: int, device: int) -> 'TISPacket':
        """
        Sıcaklık sensörü sorgulama paketi (0xE3E7)
        
        Args:
            subnet: Hedef subnet
            device: Hedef device ID
        """
        packet = TISPacket()
        packet.op_code = TISPacket.OPERATION_GET_TEMP
        packet.tgt_subnet = subnet
        packet.tgt_device = device
        packet.additional_data = bytes([0x00])
        return packet
    
    @staticmethod
    def create_energy_query_packet(subnet: int, device: int, channel: int, query_type: str = 'current') -> 'TISPacket':
        """
        Enerji ölçer sorgulama paketi (0x2010)
        
        Args:
            subnet: Hedef subnet
            device: Hedef device ID
            channel: Kanal numarası (1-based)
            query_type: 'current' veya 'monthly'
        """
        packet = TISPacket()
        packet.op_code = TISPacket.OPERATION_ENERGY_UPDATE
        packet.tgt_subnet = subnet
        packet.tgt_device = device
        
        if query_type == 'monthly':
            packet.additional_data = bytes([channel - 1, 0xDA, 0x64])
        else:
            packet.additional_data = bytes([channel - 1, 0x65])
        
        return packet
    
    @staticmethod
    def create_security_control_packet(subnet: int, device: int, channel: int, mode: int) -> 'TISPacket':
        """
        Güvenlik modu kontrol paketi (0x0104)
        
        Args:
            subnet: Hedef subnet
            device: Hedef device ID
            channel: Kanal numarası
            mode: 1=Vacation, 2=Away, 3=Night, 6=Disarm
        """
        packet = TISPacket()
        packet.op_code = TISPacket.OPERATION_CONTROL_SECURITY
        packet.tgt_subnet = subnet
        packet.tgt_device = device
        packet.additional_data = bytes([channel, mode])
        return packet
    
    @staticmethod
    def create_channel_query_packet(subnet: int, device: int, channel: int) -> 'TISPacket':
        """
        Kanal durumu sorgulama paketi (0x0033)
        
        Args:
            subnet: Hedef subnet
            device: Hedef device ID
            channel: Kanal numarası
        """
        packet = TISPacket()
        packet.op_code = TISPacket.OPERATION_CONTROL_UPDATE
        packet.tgt_subnet = subnet
        packet.tgt_device = device
        packet.additional_data = bytes([channel])
        return packet
    
    @staticmethod
    def create_ac_control_packet(subnet: int, device: int, ac_number: int, state: int, 
                                 temperature: int, mode: int, fan_speed: int) -> 'TISPacket':
        """
        AC/Klima kontrol paketi (0xE0EE)
        
        Args:
            subnet: Hedef subnet
            device: Hedef device ID
            ac_number: AC numarası
            state: 0=OFF, 1=ON
            temperature: Hedef sıcaklık (°C)
            mode: 0=Cool, 1=Heat, 2=Fan, 3=Auto
            fan_speed: 0=Auto, 1=High, 2=Medium, 3=Low
        """
        packet = TISPacket()
        packet.op_code = TISPacket.OPERATION_CONTROL_AC
        packet.tgt_subnet = subnet
        packet.tgt_device = device
        
        mode_and_fan = (mode << 4) | fan_speed
        packet.additional_data = bytes([
            ac_number, state, temperature, mode_and_fan,
            0x01, temperature, temperature, temperature, 0x00
        ])
        return packet
    
    @staticmethod
    def create_ac_query_packet(subnet: int, device: int, ac_number: int) -> 'TISPacket':
        """
        AC/Klima durum sorgulama paketi (0xE0EC)
        
        Args:
            subnet: Hedef subnet
            device: Hedef device ID
            ac_number: AC numarası
        """
        packet = TISPacket()
        packet.op_code = TISPacket.OPERATION_AC_UPDATE
        packet.tgt_subnet = subnet
        packet.tgt_device = device
        packet.additional_data = bytes([ac_number])
        return packet
    
    @staticmethod
    def create_floor_heating_control_packet(subnet: int, device: int, heater_number: int, 
                                            action: str, value: int) -> 'TISPacket':
        """
        Yerden ısıtma kontrol paketi (0xE3D8)
        
        Args:
            subnet: Hedef subnet
            device: Hedef device ID
            heater_number: Heater numarası (0-based)
            action: 'power' veya 'temperature'
            value: action='power' -> 0=OFF, 1=ON | action='temperature' -> sıcaklık değeri
        """
        packet = TISPacket()
        packet.op_code = TISPacket.OPERATION_FLOOR_CONTROL
        packet.tgt_subnet = subnet
        packet.tgt_device = device
        
        if heater_number == 0:
            if action == 'power':
                packet.additional_data = bytes([0x14, value])
            else:  # temperature
                packet.additional_data = bytes([0x18, value])
        elif heater_number == 1:
            if action == 'power':
                packet.additional_data = bytes([0x23, 0x14, value])
            else:  # temperature
                packet.additional_data = bytes([0x23, 0x18, value])
        else:
            if action == 'power':
                packet.additional_data = bytes([0x2E, heater_number + 1, 0x03, value])
            else:  # temperature
                packet.additional_data = bytes([0x2E, heater_number + 1, 0x04, value])
        
        return packet
    
    @staticmethod
    def create_floor_heating_query_packet(subnet: int, device: int, heater_number: int) -> 'TISPacket':
        """
        Yerden ısıtma durum sorgulama paketi (0x1944)
        
        Args:
            subnet: Hedef subnet
            device: Hedef device ID
            heater_number: Heater numarası
        """
        packet = TISPacket()
        packet.op_code = TISPacket.OPERATION_FLOOR_UPDATE
        packet.tgt_subnet = subnet
        packet.tgt_device = device
        packet.additional_data = bytes([heater_number])
        return packet
    
    @staticmethod
    def create_discovery_packet() -> 'TISPacket':
        """
        Cihaz keşfi broadcast paketi (0x000E)
        """
        packet = TISPacket()
        packet.op_code = TISPacket.OPERATION_DISCOVERY
        packet.tgt_subnet = 0xFF
        packet.tgt_device = 0xFF
        packet.additional_data = b''
        return packet


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
    
    @staticmethod
    def create_universal_switch_packet(subnet: int, device: int, channel: int, universal_type: int) -> 'TISPacket':
        """
        Universal Switch paketi (0xE01C)
        
        Args:
            subnet: Hedef subnet
            device: Hedef device ID
            channel: Kanal numarası
            universal_type: Universal type değeri (0-255)
        """
        packet = TISPacket()
        packet.op_code = TISPacket.OPERATION_UNIVERSAL_SWITCH
        packet.tgt_subnet = subnet
        packet.tgt_device = device
        packet.additional_data = bytes([channel, universal_type])
        return packet
    
    @staticmethod
    def create_security_control_packet(subnet: int, device: int, channel: int, mode: int) -> 'TISPacket':
        """
        Güvenlik modu kontrol paketi (0x0104)
        
        Args:
            subnet: Hedef subnet
            device: Hedef device ID
            channel: Kanal numarası
            mode: 1=Vacation, 2=Away, 3=Night, 6=Disarm
        """
        packet = TISPacket()
        packet.op_code = TISPacket.OPERATION_CONTROL_SECURITY
        packet.tgt_subnet = subnet
        packet.tgt_device = device
        packet.additional_data = bytes([channel, mode])
        return packet
    
    @staticmethod
    def create_security_query_packet(subnet: int, device: int, channel: int) -> 'TISPacket':
        """
        Güvenlik durumu sorgulama paketi (0x011E)
        
        Args:
            subnet: Hedef subnet
            device: Hedef device ID
            channel: Kanal numarası
        """
        packet = TISPacket()
        packet.op_code = TISPacket.OPERATION_SECURITY_UPDATE
        packet.tgt_subnet = subnet
        packet.tgt_device = device
        packet.additional_data = bytes([channel])
        return packet

         @ s t a t i c m e t h o d 
         d e f   c r e a t e _ w e a t h e r _ q u e r y _ p a c k e t ( s u b n e t :   i n t ,   d e v i c e :   i n t )   - >   ' T I S P a c k e t ' : 
                 " " " H a v a   d u r u m u   s o r g u l a m a   p a k e t i   ( 0 x 2 0 2 0 ) " " " 
                 p a c k e t   =   T I S P a c k e t ( ) 
                 p a c k e t . o p _ c o d e   =   T I S P a c k e t . O P E R A T I O N _ G E T _ W E A T H E R 
                 p a c k e t . t g t _ s u b n e t   =   s u b n e t 
                 p a c k e t . t g t _ d e v i c e   =   d e v i c e 
                 p a c k e t . a d d i t i o n a l _ d a t a   =   b ' ' 
                 r e t u r n   p a c k e t 
 
 