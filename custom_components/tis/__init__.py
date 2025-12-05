"""TIS Control Integration for Home Assistant - Works with TIS Addon."""
from __future__ import annotations

import asyncio
import logging
import json
import os
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN

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
    }
    
    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
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
    
    _LOGGER.info(f"TIS Integration loaded with {len(devices)} devices, file watcher started")
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Stop file watcher
    entry_data = hass.data[DOMAIN].get(entry.entry_id)
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

