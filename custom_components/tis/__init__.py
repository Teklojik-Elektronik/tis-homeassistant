"""TIS Control Integration for Home Assistant - Works with TIS Addon."""
from __future__ import annotations

import asyncio
import logging
import json
import os
import socket

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .tis_protocol import TISPacket

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
    
    # Store devices and callbacks in integration data
    hass.data[DOMAIN][entry.entry_id] = {
        "devices": devices,
        "gateway_ip": entry.data.get("gateway_ip", "192.168.1.200"),
        "udp_port": entry.data.get("udp_port", 6000),
        "update_callbacks": {},  # {(subnet, device, channel): callback_func}
        "listener_task": None,
    }
    
    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Start UDP listener
    listener_task = hass.loop.create_task(_udp_listener(hass, entry))
    hass.data[DOMAIN][entry.entry_id]["listener_task"] = listener_task
    
    _LOGGER.info(f"TIS Integration loaded with {len(devices)} devices, UDP listener started")
    
    return True


async def _udp_listener(hass: HomeAssistant, entry: ConfigEntry):
    """Background task to listen for TIS UDP packets and update switch states."""
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
                
                # Parse packet
                # Check for SMARTCLOUD header
                if b'SMARTCLOUD' in data:
                    smartcloud_index = data.find(b'SMARTCLOUD')
                    tis_data = data[smartcloud_index + 10:]  # Skip "SMARTCLOUD" (10 bytes)
                else:
                    tis_data = data
                
                parsed = TISPacket.parse(tis_data)
                
                if parsed:
                    src_subnet = parsed['src_subnet']
                    src_device = parsed['src_device']
                    
                    # Check if it's a feedback packet (OpCode 0x0032)
                    if parsed['op_code'] == 0x0032:
                        # Parse feedback data: [channel, 0xF8, actual_brightness, ...]
                        # Index 0: Channel
                        # Index 1: Always 0xF8 (max brightness constant)
                        # Index 2: Actual brightness (0-248)
                        if len(parsed['additional_data']) >= 3:
                            channel = parsed['additional_data'][0]
                            brightness_raw = parsed['additional_data'][2]  # 3rd byte!
                            
                            # TIS uses 0-248 scale for 0-100%
                            brightness = int((brightness_raw / 248.0) * 100)
                            
                            # Determine state (ON if brightness > 0)
                            is_on = brightness_raw > 0
                            
                            _LOGGER.info(f"Feedback from {src_subnet}.{src_device} CH{channel}: raw={brightness_raw}, pct={brightness}%, state={'ON' if is_on else 'OFF'}")
                            
                            # Find callback and update entity
                            callback_key = (src_subnet, src_device, channel)
                            if callback_key in entry_data["update_callbacks"]:
                                callback = entry_data["update_callbacks"][callback_key]
                                await callback(is_on, brightness)
                            else:
                                _LOGGER.warning(f"No callback registered for {callback_key}")
                    
                    # Handle multi-channel status response (OpCode 0x0034)
                    elif parsed['op_code'] == 0x0034:
                        # Response to 0x0033 query: 24 bytes, one per channel
                        # Each byte = brightness (0-248)
                        if len(parsed['additional_data']) >= 24:
                            _LOGGER.info(f"Multi-channel status from {src_subnet}.{src_device}")
                            
                            for channel in range(24):
                                brightness_raw = parsed['additional_data'][channel]
                                brightness = int((brightness_raw / 248.0) * 100)
                                is_on = brightness_raw > 0
                                
                                # Update entity if registered
                                callback_key = (src_subnet, src_device, channel)
                                if callback_key in entry_data["update_callbacks"]:
                                    callback = entry_data["update_callbacks"][callback_key]
                                    await callback(is_on, brightness)
                    
                    # Handle channel name response (OpCode 0xF00F)
                    elif parsed['op_code'] == 0xF00F:
                        # Response to 0xF00E query: [channel, ...UTF-8 name bytes...]
                        if len(parsed['additional_data']) >= 1:
                            channel = parsed['additional_data'][0]
                            
                            # Decode UTF-8 channel name (handle Turkish characters)
                            try:
                                name_bytes = bytes(parsed['additional_data'][1:])
                                # Remove null terminators and 0xFF (undefined channel name marker)
                                name_bytes = name_bytes.rstrip(b'\x00').rstrip(b'\xff')
                                
                                # Check if name is empty or all 0xFF (undefined)
                                if len(name_bytes) == 0 or all(b == 0xFF for b in name_bytes):
                                    channel_name = None  # Will use CH number
                                    _LOGGER.debug(f"Channel name from {src_subnet}.{src_device} CH{channel}: undefined (0xFF)")
                                else:
                                    channel_name = name_bytes.decode('utf-8').strip()
                                    _LOGGER.info(f"Channel name from {src_subnet}.{src_device} CH{channel}: '{channel_name}'")
                                
                                # Update entity if registered
                                callback_key = (src_subnet, src_device, channel)
                                if callback_key in entry_data.get("name_callbacks", {}):
                                    callback = entry_data["name_callbacks"][callback_key]
                                    await callback(channel_name)
                            except UnicodeDecodeError as e:
                                _LOGGER.error(f"Failed to decode channel name: {e}")
                    
                    # Also handle OpCode 0x0031 (control commands from other sources)
                    elif parsed['op_code'] == 0x0031:
                        tgt_subnet = parsed['tgt_subnet']
                        tgt_device = parsed['tgt_device']
                        
                        if len(parsed['additional_data']) >= 2:
                            channel = parsed['additional_data'][0]
                            brightness_raw = parsed['additional_data'][1]
                            brightness = int((brightness_raw / 248.0) * 100)
                            
                            _LOGGER.info(f"Control command to {tgt_subnet}.{tgt_device} CH{channel}: raw={brightness_raw}, state={'ON' if brightness_raw else 'OFF'}")
                            
                            # Update entity if we have it
                            callback_key = (tgt_subnet, tgt_device, channel)
                            if callback_key in entry_data["update_callbacks"]:
                                callback = entry_data["update_callbacks"][callback_key]
                                await callback(bool(brightness_raw), brightness)
                
            except BlockingIOError:
                # No data available, wait a bit
                await asyncio.sleep(0.1)
            except Exception as e:
                _LOGGER.error(f"Error processing UDP packet: {e}", exc_info=True)
                await asyncio.sleep(0.1)
                
    except asyncio.CancelledError:
        _LOGGER.info("TIS UDP listener stopped")
    finally:
        sock.close()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Stop UDP listener
    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    if entry_data and entry_data.get("listener_task"):
        listener_task = entry_data["listener_task"]
        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            pass
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    
    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove a config entry from a device (Red Delete button support)."""
    # Get device identifier
    identifiers = list(device_entry.identifiers)
    if not identifiers:
        return True
    
    domain, unique_id = identifiers[0]
    if domain != DOMAIN:
        return True
    
    try:
        # Parse unique_id format: "tis_1_10" -> subnet 1, device 10
        parts = unique_id.split('_')
        if len(parts) >= 3:
            subnet = int(parts[1])
            device_id = int(parts[2])
            
            _LOGGER.info(f"Removing TIS device: {unique_id} (Subnet {subnet}, Device {device_id})")
            
            # Remove from TIS Addon devices file
            devices_file = "/config/tis_devices.json"
            if os.path.exists(devices_file):
                try:
                    with open(devices_file, 'r') as f:
                        devices = json.load(f)
                    
                    device_key = f"{subnet}.{device_id}"
                    if device_key in devices:
                        del devices[device_key]
                        with open(devices_file, 'w') as f:
                            json.dump(devices, f, indent=2)
                        _LOGGER.info(f"Removed {device_key} from devices file")
                except Exception as e:
                    _LOGGER.error(f"Failed to update devices file: {e}")
            
            # Clean up all callbacks for this device
            entry_data = hass.data[DOMAIN].get(config_entry.entry_id, {})
            if "update_callbacks" in entry_data:
                keys_to_remove = [
                    k for k in entry_data["update_callbacks"].keys()
                    if k[0] == subnet and k[1] == device_id
                ]
                for key in keys_to_remove:
                    entry_data["update_callbacks"].pop(key, None)
            
            if "name_callbacks" in entry_data:
                keys_to_remove = [
                    k for k in entry_data["name_callbacks"].keys()
                    if k[0] == subnet and k[1] == device_id
                ]
                for key in keys_to_remove:
                    entry_data["name_callbacks"].pop(key, None)
            
            _LOGGER.info(f"Device {device_key} and all its channels removed successfully")
            return True
    
    except Exception as e:
        _LOGGER.error(f"Error removing device: {e}")
        return False
    
    return True


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove a config entry from a device.
    
    This allows users to delete TIS devices from the UI (red "Delete" button).
    """
    # Get device identifier
    identifiers = list(device_entry.identifiers)
    if not identifiers:
        return True
    
    # Extract subnet and device_id from identifier
    domain, unique_id = identifiers[0]
    if domain != DOMAIN:
        return True
    
    try:
        # Parse unique_id format: "tis_1_10" -> subnet 1, device 10
        parts = unique_id.split('_')
        if len(parts) >= 3:
            subnet = int(parts[1])
            device_id = int(parts[2])
            
            _LOGGER.info(f"Removing TIS device: Subnet {subnet}, Device {device_id}")
            
            # Remove device from TIS Addon's devices file
            devices_file = "/config/tis_devices.json"
            if os.path.exists(devices_file):
                try:
                    with open(devices_file, 'r') as f:
                        devices = json.load(f)
                    
                    # Remove device from JSON
                    device_key = f"{subnet}.{device_id}"
                    if device_key in devices:
                        del devices[device_key]
                        
                        # Save updated devices
                        with open(devices_file, 'w') as f:
                            json.dump(devices, f, indent=2)
                        
                        _LOGGER.info(f"Removed device {device_key} from TIS Addon devices file")
                    else:
                        _LOGGER.warning(f"Device {device_key} not found in devices file")
                
                except Exception as e:
                    _LOGGER.error(f"Failed to update devices file: {e}")
            
            # Clean up callbacks for all channels of this device
            entry_data = hass.data[DOMAIN].get(config_entry.entry_id, {})
            if "update_callbacks" in entry_data:
                # Remove all callbacks for this device (all channels)
                callbacks_to_remove = [
                    key for key in entry_data["update_callbacks"].keys()
                    if key[0] == subnet and key[1] == device_id
                ]
                for key in callbacks_to_remove:
                    entry_data["update_callbacks"].pop(key, None)
                    _LOGGER.debug(f"Removed callback for {key}")
            
            if "name_callbacks" in entry_data:
                # Remove all name callbacks for this device
                callbacks_to_remove = [
                    key for key in entry_data["name_callbacks"].keys()
                    if key[0] == subnet and key[1] == device_id
                ]
                for key in callbacks_to_remove:
                    entry_data["name_callbacks"].pop(key, None)
            
            _LOGGER.info(f"Device {subnet}.{device_id} successfully removed")
            return True
    
    except Exception as e:
        _LOGGER.error(f"Error removing device: {e}")
        return False
    
    return True
