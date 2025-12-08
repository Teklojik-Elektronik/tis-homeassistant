"""TIS Control Integration for Home Assistant - Works with TIS Addon."""
from __future__ import annotations

import asyncio
import logging
import json
import os
import socket
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .tis_protocol import TISPacket, TISUDPClient

_LOGGER = logging.getLogger(__name__)

# All supported platforms
PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.LIGHT,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.CLIMATE,  # AC/HVAC control ✅
    Platform.COVER,    # Curtain/Blind control ✅
    Platform.FAN,      # Fan speed control ✅
]
DEVICES_FILE = "/config/tis_devices.json"


def load_devices_from_file() -> dict:
    """Load devices from JSON file."""
    if os.path.exists(DEVICES_FILE):
        try:
            with open(DEVICES_FILE, 'r') as f:
                devices = json.load(f)
            _LOGGER.debug(f"Loaded {len(devices)} devices from {DEVICES_FILE}")
            return devices
        except Exception as e:
            _LOGGER.error(f"Failed to load devices: {e}")
            return {}
    return {}


def save_devices_to_file(devices: dict) -> None:
    """Save devices to JSON file."""
    try:
        with open(DEVICES_FILE, 'w') as f:
            json.dump(devices, f, indent=2, ensure_ascii=False)
        _LOGGER.debug(f"Saved {len(devices)} devices to {DEVICES_FILE}")
    except Exception as e:
        _LOGGER.error(f"Failed to save devices: {e}")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TIS Control from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Load devices from TIS Addon's JSON file
    devices = load_devices_from_file()
    
    if not devices:
        _LOGGER.warning(f"No devices found in {DEVICES_FILE}")
        _LOGGER.info("Add devices via TIS Addon Web UI (http://homeassistant.local:8888)")
    else:
        _LOGGER.info(f"Loaded {len(devices)} TIS devices from addon")
    
    # Store integration data
    hass.data[DOMAIN][entry.entry_id] = {
        "devices": devices,
        "gateway_ip": entry.data.get("gateway_ip", "192.168.1.200"),
        "udp_port": entry.data.get("udp_port", 6000),
        "configured": True,
        "file_watcher_task": None,
        "udp_listener_task": None,
        "update_callbacks": {},  # {(subnet, device, channel): callback_func}
    }
    
    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Start UDP listener for real-time state updates
    async def handle_control_response(parsed: dict, entry_data: dict):
        """Handle single channel control response (0x0032)"""
        if len(parsed['additional_data']) >= 3:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            channel = parsed['additional_data'][0]
            brightness_raw = parsed['additional_data'][2]
            
            brightness = int((brightness_raw / 248.0) * 100)
            is_on = brightness_raw > 0
            
            _LOGGER.info(f"🔦 Control response: {src_subnet}.{src_device} CH{channel} → "
                        f"{'ON' if is_on else 'OFF'} ({brightness}%)")
            
            callback_key = (src_subnet, src_device, channel)
            if callback_key in entry_data["update_callbacks"]:
                await entry_data["update_callbacks"][callback_key](is_on, brightness)
    
    async def handle_update_response(parsed: dict, entry_data: dict):
        """Handle multi-channel status response (0x0034)"""
        if len(parsed['additional_data']) >= 25:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            
            _LOGGER.info(f"Multi-channel status from {src_subnet}.{src_device}")
            
            updated_count = 0
            for channel in range(1, 25):
                brightness_raw = parsed['additional_data'][channel]
                brightness = int((brightness_raw / 248.0) * 100)
                is_on = brightness_raw > 0
                
                callback_key = (src_subnet, src_device, channel)
                if callback_key in entry_data["update_callbacks"]:
                    await entry_data["update_callbacks"][callback_key](is_on, brightness)
                    updated_count += 1
            
            _LOGGER.info(f"Updated {updated_count} channels for {src_subnet}.{src_device}")
    
    async def handle_health_feedback(parsed: dict, entry_data: dict):
        """Handle health sensor feedback (0x2024)"""
        if len(parsed['additional_data']) >= 14:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            # Parse health sensor data (temp, humidity, CO2, VOC, PM2.5, lux, noise)
            temperature = int.from_bytes(data[0:2], 'big') / 10.0
            humidity = data[2]
            co2 = int.from_bytes(data[3:5], 'big')
            voc = int.from_bytes(data[5:7], 'big')
            pm25 = int.from_bytes(data[7:9], 'big')
            lux = int.from_bytes(data[9:11], 'big')
            noise = data[11]
            
            _LOGGER.info(f"🏥 Health sensor: {src_subnet}.{src_device} → "
                        f"Temp={temperature}°C, Humidity={humidity}%, CO2={co2}ppm, "
                        f"VOC={voc}ppb, PM2.5={pm25}µg/m³, Lux={lux}, Noise={noise}dB")
            
            # Fire event for sensor platform
            hass.bus.async_fire("tis_health_feedback", {
                "subnet": src_subnet,
                "device": src_device,
                "temperature": temperature,
                "humidity": humidity,
                "co2": co2,
                "voc": voc,
                "pm25": pm25,
                "lux": lux,
                "noise": noise
            })
    
    async def handle_energy_feedback(parsed: dict, entry_data: dict):
        """Handle energy meter feedback (0x2010)"""
        if len(parsed['additional_data']) >= 8:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            channel = data[0] + 1  # Convert 0-based to 1-based
            voltage = int.from_bytes(data[1:3], 'big') / 10.0
            current = int.from_bytes(data[3:5], 'big') / 1000.0
            power = int.from_bytes(data[5:7], 'big')
            energy = int.from_bytes(data[7:9], 'big') / 100.0
            
            _LOGGER.info(f"⚡ Energy meter: {src_subnet}.{src_device} CH{channel} → "
                        f"V={voltage}V, I={current}A, P={power}W, E={energy}kWh")
            
            # Fire event for sensor platform
            hass.bus.async_fire("tis_energy_feedback", {
                "subnet": src_subnet,
                "device": src_device,
                "channel": channel,
                "voltage": voltage,
                "current": current,
                "power": power,
                "energy": energy
            })
    
    async def handle_climate_feedback(parsed: dict, entry_data: dict):
        """Handle AC/climate feedback (0xE0EC)"""
        if len(parsed['additional_data']) >= 5:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            ac_number = data[0]
            state = data[1]  # 0=OFF, 1=ON
            temperature = data[2]
            mode_and_fan = data[3]
            mode = (mode_and_fan >> 4) & 0x0F
            fan_speed = mode_and_fan & 0x0F
            
            mode_names = {0: "Cool", 1: "Heat", 2: "Fan", 3: "Auto"}
            fan_names = {0: "Auto", 1: "High", 2: "Medium", 3: "Low"}
            
            _LOGGER.info(f"❄️ AC feedback: {src_subnet}.{src_device} AC{ac_number} → "
                        f"{'ON' if state else 'OFF'}, {temperature}°C, "
                        f"Mode={mode_names.get(mode, 'Unknown')}, "
                        f"Fan={fan_names.get(fan_speed, 'Unknown')}")
            
            # Fire event for climate platform
            hass.bus.async_fire("tis_climate_feedback", {
                "subnet": src_subnet,
                "device": src_device,
                "ac_number": ac_number,
                "state": state,
                "temperature": temperature,
                "mode": mode,
                "fan_speed": fan_speed
            })
    
    async def handle_security_feedback(parsed: dict, entry_data: dict):
        """Handle security status feedback (0x011E)"""
        if len(parsed['additional_data']) >= 2:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            channel = data[0]
            mode = data[1]  # 1=Vacation, 2=Away, 3=Night, 6=Disarm
            
            mode_names = {1: "Vacation", 2: "Away", 3: "Night", 6: "Disarmed"}
            
            _LOGGER.info(f"🔒 Security feedback: {src_subnet}.{src_device} CH{channel} → "
                        f"Mode={mode_names.get(mode, 'Unknown')}")
            
            # Fire event for alarm_control_panel platform
            hass.bus.async_fire("tis_security_feedback", {
                "subnet": src_subnet,
                "device": src_device,
                "channel": channel,
                "mode": mode
            })
    
    async def udp_listener():
        """Listen for TIS UDP packets and update entity states."""
        entry_data = hass.data[DOMAIN][entry.entry_id]
        udp_port = entry_data["udp_port"]
        
        _LOGGER.info(f"Starting TIS UDP listener on port {udp_port}")
        
        # Create UDP socket for receiving broadcasts
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Enable broadcast reception
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except AttributeError:
            pass  # Not all systems support SO_BROADCAST
        
        try:
            # Bind to all interfaces on the UDP port
            sock.bind(('0.0.0.0', udp_port))
            sock.setblocking(False)
            _LOGGER.info(f"✅ Successfully bound UDP socket to 0.0.0.0:{udp_port}")
        except OSError as e:
            _LOGGER.error(f"❌ CRITICAL: Could not bind to port {udp_port}: {e}")
            _LOGGER.error("UDP listener will NOT work! Check if another process is using the port.")
            sock.close()
            sock = None
        
        try:
            while True:
                # Check if socket is available
                if sock is None:
                    _LOGGER.error("UDP socket not available, using polling mode only")
                    await asyncio.sleep(5)
                    # Polling logic will happen in the except block below
                    raise BlockingIOError("No socket available")
                
                try:
                    # Non-blocking receive with timeout
                    data, addr = await asyncio.wait_for(
                        hass.loop.sock_recvfrom(sock, 4096),
                        timeout=3.0
                    )
                    
                    _LOGGER.info(f"📡 UDP packet from {addr}: {len(data)} bytes")
                    
                    # Parse packet (skip SMARTCLOUD header if present)
                    if b'SMARTCLOUD' in data:
                        smartcloud_index = data.find(b'SMARTCLOUD')
                        tis_data = data[smartcloud_index + 10:]
                    else:
                        tis_data = data
                    
                    parsed = TISPacket.parse(tis_data)
                    
                    if parsed:
                        src_subnet = parsed['src_subnet']
                        src_device = parsed['src_device']
                        op_code = parsed['op_code']
                        
                        _LOGGER.info(f"✅ Parsed: OpCode 0x{op_code:04X} from {src_subnet}.{src_device}")
                        
                        # OpCode-based dispatch system (TISControlProtocol style)
                        try:
                            if op_code == 0x0032:  # Control response
                                await handle_control_response(parsed, entry_data)
                            elif op_code == 0x0034:  # Multi-channel status
                                await handle_update_response(parsed, entry_data)
                            elif op_code == 0x2024:  # Health sensor feedback
                                await handle_health_feedback(parsed, entry_data)
                            elif op_code == 0x2010:  # Energy meter feedback
                                await handle_energy_feedback(parsed, entry_data)
                            elif op_code == 0xE0EC:  # AC/climate feedback
                                await handle_climate_feedback(parsed, entry_data)
                            elif op_code == 0x011E:  # Security feedback
                                await handle_security_feedback(parsed, entry_data)
                            else:
                                _LOGGER.debug(f"Unhandled OpCode: 0x{op_code:04X}")
                        except Exception as e:
                            _LOGGER.error(f"Error in handler for OpCode 0x{op_code:04X}: {e}", exc_info=True)
                
                except asyncio.TimeoutError:
                    # No UDP packet received within timeout, continue listening
                    continue
                    
                except (BlockingIOError, OSError) as e:
                    _LOGGER.debug(f"Socket error (will retry): {e}")
                    await asyncio.sleep(1)
                    continue
                    
                except Exception as e:
                    _LOGGER.error(f"Error processing UDP packet: {e}", exc_info=True)
                    await asyncio.sleep(0.1)
                    
        except asyncio.CancelledError:
            _LOGGER.info("TIS UDP listener stopped")
        finally:
            sock.close()
    
    # Start UDP listener task
    udp_task = hass.loop.create_task(udp_listener())
    hass.data[DOMAIN][entry.entry_id]["udp_listener_task"] = udp_task
    
    # Start file watcher to detect changes in tis_devices.json
    async def watch_devices_file():
        """Watch for changes in devices file and reload integration."""
        last_mtime = 0
        if os.path.exists(DEVICES_FILE):
            last_mtime = os.path.getmtime(DEVICES_FILE)
        
        while True:
            await asyncio.sleep(2)  # Check every 2 seconds
            
            try:
                if os.path.exists(DEVICES_FILE):
                    current_mtime = os.path.getmtime(DEVICES_FILE)
                    if current_mtime != last_mtime:
                        last_mtime = current_mtime
                        _LOGGER.info("Devices file changed, reloading integration...")
                        
                        # Reload the config entry
                        await hass.config_entries.async_reload(entry.entry_id)
            except Exception as e:
                _LOGGER.error(f"Error watching devices file: {e}")
    
    # Start file watcher task
    watcher_task = hass.loop.create_task(watch_devices_file())
    hass.data[DOMAIN][entry.entry_id]["file_watcher_task"] = watcher_task
    
    _LOGGER.info(f"TIS Integration loaded: {len(devices)} devices, UDP listener on port {entry.data.get('udp_port', 6000)}")
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    
    # Stop UDP listener
    if entry_data and entry_data.get("udp_listener_task"):
        udp_task = entry_data["udp_listener_task"]
        udp_task.cancel()
        try:
            await udp_task
        except asyncio.CancelledError:
            pass
    
    # Stop file watcher
    if entry_data and entry_data.get("file_watcher_task"):
        watcher_task = entry_data["file_watcher_task"]
        watcher_task.cancel()
        try:
            await watcher_task
        except asyncio.CancelledError:
            pass
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.info("TIS Integration unloaded successfully")
    
    return unload_ok
    
    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove a device from integration and JSON file."""
    # Get device identifier
    identifiers = list(device_entry.identifiers)
    if not identifiers:
        return True
    
    domain, unique_id = identifiers[0]
    if domain != DOMAIN:
        return True
    
    try:
        _LOGGER.info(f"Removing TIS device: {unique_id}")
        
        # Load current devices
        devices = load_devices_from_file()
        
        # Remove device from JSON
        if unique_id in devices:
            del devices[unique_id]
            save_devices_to_file(devices)
            _LOGGER.info(f"Removed {unique_id} from devices file")
            
            # Update integration data
            entry_data = hass.data[DOMAIN].get(config_entry.entry_id, {})
            if "devices" in entry_data:
                entry_data["devices"] = devices
        else:
            _LOGGER.warning(f"Device {unique_id} not found in devices file")
        
        return True
    
    except Exception as e:
        _LOGGER.error(f"Error removing device: {e}")
        return False

