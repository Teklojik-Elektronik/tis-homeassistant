"""TIS Control Integration for Home Assistant - Works with TIS Addon."""
from __future__ import annotations

import asyncio
import logging
import json
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SWITCH]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TIS Control from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Load devices from TIS Addon's JSON file
    devices_file = "/config/tis_devices.json"
    devices = {}
    
    if os.path.exists(devices_file):
        try:
            with open(devices_file, 'r') as f:
                devices = json.load(f)
            _LOGGER.info(f"Loaded {len(devices)} TIS devices from addon")
        except Exception as e:
            _LOGGER.error(f"Failed to load devices from {devices_file}: {e}")
    else:
        _LOGGER.warning(f"TIS Addon devices file not found: {devices_file}")
        _LOGGER.info("Install TIS Addon and add devices via Web UI first")
    
    # Store devices in integration data
    hass.data[DOMAIN][entry.entry_id] = {
        "devices": devices,
        "gateway_ip": entry.data.get("gateway_ip", "192.168.1.200"),
        "udp_port": entry.data.get("udp_port", 6000),
        "configured": True,
    }
    
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    _LOGGER.info(f"TIS Integration loaded with {len(devices)} devices")
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.info("TIS Integration unloaded successfully")
    
    return unload_ok
