"""Discovery helpers for TIS devices via UDP."""
import logging
import socket
import time
from typing import Any, Dict

from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant

from .const import UDP_PORT, DISCOVERY_TIMEOUT, get_device_info
from .tis_protocol import TISPacket

_LOGGER = logging.getLogger(__name__)

def get_local_ip() -> str:
    """Get local IP address."""
    try:
        # UDP socket kullanarak local IP'yi tespit et (gerçek bağlantı kurmaz)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "192.168.1.1"  # Fallback

# Discovery OpCodes
# Resmi TIS uygulamasının debug ekranında 0xF003 (Discovery Request) kullanıldığı görüldü.
# Kullanıcı görselinde: 0B 01 FE FF FE F0 03 FF FF ... paketi gönderiliyor.
# Bu paket: Len=11, Src=1.254, Type=0xFFFE, Op=0xF003, Tgt=255.255
DISCOVERY_OP_CODE = 0xF003
DISCOVERY_RETRIES = 10
DISCOVERY_INTERVAL = 1.0

def _run_discovery(timeout: int = DISCOVERY_TIMEOUT) -> Dict[str, Dict[str, Any]]:
    """Run discovery in a sync way (to be run in executor)."""
    discovered = {}
    sock = None
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            # Raspberry Pi 4 gibi güçlü cihazlarda buffer'ı çok daha yüksek tutabiliriz
            # 64KB yerine 4MB yaparak "Broadcast Storm" anında paket kaybını önlüyoruz
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024) 
        except Exception:
            pass
            
        sock.settimeout(0.5) # Short timeout for loop
        # Bind to all interfaces
        sock.bind(('', UDP_PORT))
        
        # TISControlProtocol stratejisi: Tekrar tekrar sorgula (Retry Strategy)
        # Tek bir sefer gönderip beklemek yerine, paketi periyodik olarak gönderiyoruz.
        # Bu sayede meşgul olan veya ilk paketi kaçıran cihazlar yakalanabilir.
        
        # Local IP al ve SMARTCLOUD header için hazırla
        local_ip = get_local_ip()
        ip_bytes = bytes([int(x) for x in local_ip.split('.')])
        smartcloud_header = b'SMARTCLOUD'
        
        for i in range(DISCOVERY_RETRIES):
            _LOGGER.info(f"TIS discovery broadcast {i+1}/{DISCOVERY_RETRIES} for OpCode: 0x{DISCOVERY_OP_CODE:04X}")
            
            packet = TISPacket()
            packet.op_code = DISCOVERY_OP_CODE
            packet.tgt_subnet = 255
            packet.tgt_device = 255
            tis_data = packet.build()
            
            # SMARTCLOUD header ekle (gateway için gerekli)
            data = ip_bytes + smartcloud_header + tis_data
            
            sock.sendto(data, ('255.255.255.255', UDP_PORT))
            
            # Her gönderimden sonra belirli bir süre dinle
            sub_end_time = time.time() + DISCOVERY_INTERVAL
            while time.time() < sub_end_time:
                try:
                    data, addr = sock.recvfrom(4096)
                    ip = addr[0]
                    
                    # Gateway SMARTCLOUD header'ı varsa çıkar (14 byte: 4 IP + 10 SMARTCLOUD)
                    if len(data) > 14 and data[4:14] == b'SMARTCLOUD':
                        data = data[14:]  # SMARTCLOUD header'dan sonraki TIS data
                    
                    parsed = TISPacket.parse(data)
                    if parsed:
                        # Unique ID based on Subnet.Device
                        subnet = parsed['src_subnet']
                        device = parsed['src_device']
                        unique_id = f"tis_{subnet}_{device}"
                        
                        # Get Device Info
                        device_type_id = parsed['src_type']
                        model_name, channels = get_device_info(device_type_id)
                        
                        # Extract Device Name from 0x000F response
                        device_name_from_packet = None
                        if parsed['op_code'] == 0x000F and parsed.get('additional_data'):
                            try:
                                # Null terminated string
                                raw_name = parsed['additional_data']
                                null_pos = raw_name.find(0)
                                if null_pos != -1:
                                    raw_name = raw_name[:null_pos]
                                device_name_from_packet = raw_name.decode('utf-8', errors='ignore').strip()
                            except Exception:
                                pass
                        
                        # Determine final name
                        final_name = f"{model_name} ({subnet}.{device})"
                        if device_name_from_packet:
                            final_name = f"{device_name_from_packet} ({subnet}.{device})"
                        
                        # Log every packet found to debug
                        _LOGGER.debug(f"Discovery Packet: {ip} -> {subnet}.{device} Type: {hex(device_type_id)} Op: {hex(parsed['op_code'])}")

                        if unique_id not in discovered:
                            _LOGGER.info(f"Found TIS Device: {ip} ({subnet}.{device}) - {model_name} (Type: {hex(device_type_id)})")
                            discovered[unique_id] = {
                                CONF_HOST: ip,
                                "subnet": subnet,
                                "device": device,
                                "device_type": device_type_id,
                                "device_type_hex": f"0x{device_type_id:04X}",
                                "model_name": model_name,
                                "channels": channels,
                                "name": final_name,
                            }
                        elif device_name_from_packet:
                            # Update name if we found it later
                            discovered[unique_id]["name"] = final_name
                            
                except socket.timeout:
                    continue
                except Exception as e:
                    _LOGGER.error(f"Socket error: {e}")
        
        # Final wait to catch stragglers (Fixed 4 seconds)
        _LOGGER.info("Waiting for final responses...")
        final_end_time = time.time() + 4.0
        while time.time() < final_end_time:
            try:
                data, addr = sock.recvfrom(4096)
                ip = addr[0]
                
                # Gateway SMARTCLOUD header'ı varsa çıkar (14 byte: 4 IP + 10 SMARTCLOUD)
                if len(data) > 14 and data[4:14] == b'SMARTCLOUD':
                    data = data[14:]  # SMARTCLOUD header'dan sonraki TIS data
                
                parsed = TISPacket.parse(data)
                if parsed:
                    subnet = parsed['src_subnet']
                    device = parsed['src_device']
                    unique_id = f"tis_{subnet}_{device}"
                    device_type_id = parsed['src_type']
                    model_name, channels = get_device_info(device_type_id)
                    
                    device_name_from_packet = None
                    if parsed['op_code'] == 0x000F and parsed.get('additional_data'):
                        try:
                            raw_name = parsed['additional_data']
                            null_pos = raw_name.find(0)
                            if null_pos != -1:
                                raw_name = raw_name[:null_pos]
                            device_name_from_packet = raw_name.decode('utf-8', errors='ignore').strip()
                        except Exception:
                            pass
                            
                    final_name = f"{model_name} ({subnet}.{device})"
                    if device_name_from_packet:
                        final_name = f"{device_name_from_packet} ({subnet}.{device})"

                    if unique_id not in discovered:
                        _LOGGER.info(f"Found TIS Device: {ip} ({subnet}.{device}) - {model_name}")
                        discovered[unique_id] = {
                            CONF_HOST: ip,
                            "subnet": subnet,
                            "device": device,
                            "device_type": device_type_id,
                            "device_type_hex": f"0x{device_type_id:04X}",
                            "model_name": model_name,
                            "channels": channels,
                            "name": final_name,
                        }
                    elif device_name_from_packet:
                        discovered[unique_id]["name"] = final_name
                        
            except socket.timeout:
                continue
            except Exception:
                pass
                
    except Exception as e:
        _LOGGER.error(f"Discovery error: {e}")
    finally:
        if sock:
            sock.close()
            
    return discovered

async def discover_tis_devices(hass: HomeAssistant, timeout: int = DISCOVERY_TIMEOUT) -> Dict[str, Dict[str, Any]]:
    """Async wrapper for discovery."""
    return await hass.async_add_executor_job(_run_discovery, timeout)
