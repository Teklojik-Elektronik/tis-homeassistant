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
from .tis_protocol import TISPacket

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
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', udp_port))
        sock.setblocking(False)
        
        try:
            while True:
                try:
                    # Non-blocking receive with asyncio
                    data, addr = await hass.loop.sock_recvfrom(sock, 1024)
                    
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
                        
                        # Handle feedback packet (OpCode 0x0032)
                        if parsed['op_code'] == 0x0032:
                            if len(parsed['additional_data']) >= 3:
                                channel = parsed['additional_data'][0]
                                brightness_raw = parsed['additional_data'][2]
                                
                                # TIS uses 0-248 scale for 0-100%
                                brightness = int((brightness_raw / 248.0) * 100)
                                is_on = brightness_raw > 0
                                
                                _LOGGER.debug(f"Feedback from {src_subnet}.{src_device} CH{channel}: "
                                            f"raw={brightness_raw}, pct={brightness}%, state={'ON' if is_on else 'OFF'}")
                                
                                # Find callback and update entity
                                callback_key = (src_subnet, src_device, channel)
                                if callback_key in entry_data["update_callbacks"]:
                                    callback = entry_data["update_callbacks"][callback_key]
                                    await callback(is_on, brightness)
                        
                        # Handle multi-channel status (OpCode 0x0034)
                        elif parsed['op_code'] == 0x0034:
                            if len(parsed['additional_data']) >= 24:
                                _LOGGER.debug(f"Multi-channel status from {src_subnet}.{src_device}")
                                
                                for channel in range(1, 25):  # Channels 1-24
                                    brightness_raw = parsed['additional_data'][channel - 1]
                                    brightness = int((brightness_raw / 248.0) * 100)
                                    is_on = brightness_raw > 0
                                    
                                    callback_key = (src_subnet, src_device, channel)
                                    if callback_key in entry_data["update_callbacks"]:
                                        callback = entry_data["update_callbacks"][callback_key]
                                        await callback(is_on, brightness)
                
                except BlockingIOError:
                    await asyncio.sleep(0.1)
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

