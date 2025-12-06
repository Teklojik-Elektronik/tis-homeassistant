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

PLATFORMS: list[Platform] = [Platform.SWITCH]
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
    async def udp_listener():
        """Listen for TIS UDP packets and update entity states."""
        entry_data = hass.data[DOMAIN][entry.entry_id]
        udp_port = entry_data["udp_port"]
        
        _LOGGER.info(f"Starting TIS UDP listener on port {udp_port}")
        
        # Try to bind to UDP port (may fail if gateway uses same port)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            sock.bind(('', udp_port))
            sock.setblocking(False)
            _LOGGER.info(f"Successfully bound to UDP port {udp_port}")
        except OSError as e:
            _LOGGER.warning(f"Could not bind to port {udp_port}: {e}")
            _LOGGER.info("Will use polling-only mode (no real-time UDP updates)")
            sock.close()
            sock = None
        
        try:
            while True:
                try:
                    # Non-blocking receive with asyncio
                    data, addr = await hass.loop.sock_recvfrom(sock, 1024)
                    
                    _LOGGER.info(f"📡 Received UDP packet from {addr}: {len(data)} bytes")
                    _LOGGER.debug(f"Raw data: {data.hex()}")
                    
                    # Parse packet (skip SMARTCLOUD header if present)
                    if b'SMARTCLOUD' in data:
                        smartcloud_index = data.find(b'SMARTCLOUD')
                        tis_data = data[smartcloud_index + 10:]
                        _LOGGER.debug(f"Found SMARTCLOUD header at index {smartcloud_index}")
                    else:
                        tis_data = data
                    
                    parsed = TISPacket.parse(tis_data)
                    
                    if parsed:
                        src_subnet = parsed['src_subnet']
                        src_device = parsed['src_device']
                        op_code = parsed['op_code']
                        
                        _LOGGER.info(f"✅ Parsed: OpCode 0x{op_code:04X} from {src_subnet}.{src_device}")
                        
                        # Handle feedback packet (OpCode 0x0032)
                        if parsed['op_code'] == 0x0032:
                            if len(parsed['additional_data']) >= 3:
                                # Protocol: data[0]=channel(0-23), data[1]=0xF8, data[2]=brightness(0-248)
                                channel_index = parsed['additional_data'][0]  # 0-23
                                channel = channel_index + 1  # Convert to 1-24 for switch entities
                                brightness_raw = parsed['additional_data'][2]
                                
                                # TIS uses 0-248 scale for 0-100%
                                brightness = int((brightness_raw / 248.0) * 100)
                                is_on = brightness_raw > 0
                                
                                _LOGGER.info(f"🔦 Single channel feedback: {src_subnet}.{src_device} CH{channel} → "
                                            f"{'ON' if is_on else 'OFF'} ({brightness}%)")
                                
                                # Find callback and update entity
                                callback_key = (src_subnet, src_device, channel)
                                if callback_key in entry_data["update_callbacks"]:
                                    callback = entry_data["update_callbacks"][callback_key]
                                    await callback(is_on, brightness)
                                    _LOGGER.info(f"✅ Updated entity for CH{channel}")
                                else:
                                    _LOGGER.warning(f"⚠️ No callback registered for {callback_key}")                        # Handle multi-channel status (OpCode 0x0034)
                        elif parsed['op_code'] == 0x0034:
                            if len(parsed['additional_data']) >= 24:
                                _LOGGER.info(f"Multi-channel status from {src_subnet}.{src_device} (Initial state sync)")
                                
                                # Protocol: data[0-23] contains brightness for channels 1-24
                                updated_count = 0
                                for channel in range(1, 25):  # Channels 1-24
                                    channel_index = channel - 1  # Array index 0-23
                                    brightness_raw = parsed['additional_data'][channel_index]
                                    brightness = int((brightness_raw / 248.0) * 100)
                                    is_on = brightness_raw > 0
                                    
                                    callback_key = (src_subnet, src_device, channel)
                                    if callback_key in entry_data["update_callbacks"]:
                                        callback = entry_data["update_callbacks"][callback_key]
                                        await callback(is_on, brightness)
                                        updated_count += 1
                                        if is_on:
                                            _LOGGER.debug(f"  CH{channel}: ON ({brightness}%)")
                                
                                _LOGGER.info(f"Updated {updated_count} channels for {src_subnet}.{src_device}")
                
                except BlockingIOError:
                    # No UDP data available, poll device states instead
                    await asyncio.sleep(5)  # Poll every 5 seconds (reduced from 3)
                    
                    # Query all devices for state updates
                    for device_key, device_data in entry_data["devices"].items():
                        subnet = device_data.get("subnet")
                        device_id = device_data.get("device_id")
                        
                        if subnet and device_id:
                            try:
                                # Send OpCode 0x0033 to query all channel states
                                client = TISUDPClient(entry_data["gateway_ip"], udp_port)
                                await client.async_connect(bind=False)
                                
                                # Get local IP for SMARTCLOUD header
                                import socket as sock_module
                                s = sock_module.socket(sock_module.AF_INET, sock_module.SOCK_DGRAM)
                                try:
                                    s.connect(('8.8.8.8', 80))
                                    local_ip = s.getsockname()[0]
                                finally:
                                    s.close()
                                
                                ip_bytes = bytes([int(x) for x in local_ip.split('.')])
                                
                                packet = TISPacket()
                                packet.src_subnet = 1
                                packet.src_device = 254
                                packet.src_type = 0xFFFE
                                packet.tgt_subnet = subnet
                                packet.tgt_device = device_id
                                packet.op_code = 0x0033
                                packet.additional_data = bytes([])
                                
                                tis_data = packet.build()
                                full_packet = ip_bytes + b'SMARTCLOUD' + tis_data
                                client.send_to(full_packet, entry_data["gateway_ip"])
                                client.close()
                                
                                _LOGGER.debug(f"Polling: Queried state for {subnet}.{device_id}")
                            except Exception as poll_error:
                                _LOGGER.debug(f"Polling error for {subnet}.{device_id}: {poll_error}")
                    
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

