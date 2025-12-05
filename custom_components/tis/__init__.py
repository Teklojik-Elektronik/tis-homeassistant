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
from .tis_protocol import (
    TISPacket,
    parse_radar_motion_packet,
    parse_environment_status_packet,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.BINARY_SENSOR, Platform.SENSOR]


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
        "devices_file": devices_file,
        "gateway_ip": entry.data.get("gateway_ip", "192.168.1.200"),
        "udp_port": entry.data.get("udp_port", 6000),
        "update_callbacks": {},  # {(subnet, device, channel): callback_func}
        "radar_callbacks": {},  # {(subnet, device): callback_func} for radar sensors
        "lux_callbacks": {},  # {(subnet, device): callback_func} for LUX sensors
        "radar_data": {},  # {(subnet, device): radar_motion_data}
        "lux_data": {},  # {(subnet, device): lux_data}
        "listener_task": None,
        "file_watcher_task": None,
    }
    
    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Start UDP listener
    listener_task = hass.loop.create_task(_udp_listener(hass, entry))
    hass.data[DOMAIN][entry.entry_id]["listener_task"] = listener_task
    
    # Start file watcher to detect when devices are added via web UI
    file_watcher_task = hass.loop.create_task(_watch_devices_file(hass, entry))
    hass.data[DOMAIN][entry.entry_id]["file_watcher_task"] = file_watcher_task
    
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


async def _create_radar_entities_if_needed(hass: HomeAssistant, entry: ConfigEntry, subnet: int, device_id: int):
    \"\"\"Create radar sensor entities dynamically when device is detected.\"\"\"
    entry_data = hass.data[DOMAIN][entry.entry_id]
    device_key = (subnet, device_id)
    
    # Check if binary sensor entities already created
    if \"binary_sensor_add_entities\" in entry_data:
        created = entry_data.get(\"binary_sensor_created_devices\", set())
        if device_key not in created:
            # Import here to avoid circular dependency
            from .binary_sensor import TISRadarMotionSensor
            
            entities = [TISRadarMotionSensor(hass, entry, subnet, device_id)]
            entry_data[\"binary_sensor_add_entities\"](entities)
            created.add(device_key)
            _LOGGER.info(f\"✅ Created binary sensor entities for TIS Radar {subnet}.{device_id}\")
    
    # Check if sensor entities already created
    if \"sensor_add_entities\" in entry_data:
        created = entry_data.get(\"sensor_created_devices\", set())
        if device_key not in created:
            # Import here to avoid circular dependency
            from .sensor import (
                TISMotionDistanceSensor,
                TISStationaryDistanceSensor,
                TISTargetCountSensor,
                TISMotionStateSensor,
                TISLuxSensor,
            )
            
            entities = [
                TISMotionDistanceSensor(hass, entry, subnet, device_id),
                TISStationaryDistanceSensor(hass, entry, subnet, device_id),
                TISTargetCountSensor(hass, entry, subnet, device_id),
                TISMotionStateSensor(hass, entry, subnet, device_id),
                TISLuxSensor(hass, entry, subnet, device_id),
            ]
            entry_data[\"sensor_add_entities\"](entities)
            created.add(device_key)
            _LOGGER.info(f\"✅ Created sensor entities for TIS Radar {subnet}.{device_id}\")


async def _watch_devices_file(hass: HomeAssistant, entry: ConfigEntry):
    \"\"\"Watch tis_devices.json for changes and reload devices list.\"\"\"
    entry_data = hass.data[DOMAIN][entry.entry_id]
    devices_file = entry_data[\"devices_file\"]
    last_mtime = 0
    
    try:
        while True:
            await asyncio.sleep(5)  # Check every 5 seconds
            
            try:
                if os.path.exists(devices_file):
                    current_mtime = os.path.getmtime(devices_file)
                    
                    if current_mtime != last_mtime:
                        last_mtime = current_mtime
                        
                        # Reload devices
                        with open(devices_file, 'r') as f:
                            new_devices = json.load(f)
                        
                        old_devices = entry_data[\"devices\"]
                        
                        # Find newly added devices
                        new_device_keys = set(new_devices.keys()) - set(old_devices.keys())
                        
                        if new_device_keys:
                            _LOGGER.info(f\"🔄 Detected {len(new_device_keys)} new devices in Web UI: {new_device_keys}\")
                            
                            # Update devices dict
                            entry_data[\"devices\"] = new_devices
                            
                            # For each new radar device, if we already have data, create entities
                            for device_str in new_device_keys:
                                try:
                                    parts = device_str.split('.')
                                    if len(parts) == 2:
                                        subnet = int(parts[0])
                                        device_id = int(parts[1])
                                        device_key = (subnet, device_id)
                                        
                                        # Check if we have radar data for this device
                                        if device_key in entry_data.get(\"radar_data\", {}) or device_key in entry_data.get(\"lux_data\", {}):
                                            await _create_radar_entities_if_needed(hass, entry, subnet, device_id)
                                        else:
                                            _LOGGER.info(f\"⏳ Device {device_str} added to config, waiting for radar packets...\")
                                except Exception as e:
                                    _LOGGER.error(f\"Error processing new device {device_str}: {e}\")
            
            except Exception as e:
                _LOGGER.error(f\"Error watching devices file: {e}\")
    
    except asyncio.CancelledError:
        _LOGGER.info(\"TIS devices file watcher stopped\")
    except Exception as e:
        _LOGGER.error(f\"Fatal error in devices file watcher: {e}\")
    
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
                    
                    # Handle radar motion detection (OpCode 0x2025, 62 bytes)
                    elif parsed['op_code'] == 0x2025 and len(tis_data) == 62:
                        radar_data = parse_radar_motion_packet(tis_data)
                        if radar_data:
                            _LOGGER.debug(f"Radar motion from {src_subnet}.{src_device}: {radar_data['state']}, targets={radar_data['target_count']}")
                            
                            # Store radar data
                            device_key = (src_subnet, src_device)
                            entry_data["radar_data"][device_key] = radar_data
                            
                            # Check if device is in tis_devices.json (added via web UI)
                            devices = entry_data.get("devices", {})
                            device_str = f"{src_subnet}.{src_device}"
                            
                            if device_str in devices:
                                # Device exists in web UI config - create entities if not already created
                                await _create_radar_entities_if_needed(hass, entry, src_subnet, src_device)
                            
                            # Call registered callback
                            if device_key in entry_data["radar_callbacks"]:
                                callback = entry_data["radar_callbacks"][device_key]
                                await callback(radar_data)
                    
                    # Handle environment status / LUX sensor (OpCode 0x2025, 37 bytes)
                    elif parsed['op_code'] == 0x2025 and len(tis_data) == 37:
                        lux_data = parse_environment_status_packet(tis_data)
                        if lux_data:
                            _LOGGER.debug(f"LUX sensor from {src_subnet}.{src_device}: {lux_data['lux']} lx")
                            
                            # Store LUX data
                            device_key = (src_subnet, src_device)
                            entry_data["lux_data"][device_key] = lux_data
                            
                            # Check if device is in tis_devices.json (added via web UI)
                            devices = entry_data.get("devices", {})
                            device_str = f"{src_subnet}.{src_device}"
                            
                            if device_str in devices:
                                # Device exists in web UI config - create entities if not already created
                                await _create_radar_entities_if_needed(hass, entry, src_subnet, src_device)
                            
                            # Call registered callback
                            if device_key in entry_data["lux_callbacks"]:
                                callback = entry_data["lux_callbacks"][device_key]
                                await callback(lux_data)
                    
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
    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    
    if entry_data:
        # Stop UDP listener
        if entry_data.get("listener_task"):
            listener_task = entry_data["listener_task"]
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass
        
        # Stop file watcher
        if entry_data.get("file_watcher_task"):
            file_watcher_task = entry_data["file_watcher_task"]
            file_watcher_task.cancel()
            try:
                await file_watcher_task
            except asyncio.CancelledError:
                pass
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.info("TIS Integration unloaded successfully")
    
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle removal of an entry (integration deleted completely)."""
    _LOGGER.warning("TIS Integration is being removed - cleaning up all devices...")
    
    # Clean up /config/tis_devices.json file
    devices_file = "/config/tis_devices.json"
    try:
        if os.path.exists(devices_file):
            # Backup before deleting
            backup_file = "/config/tis_devices.json.backup"
            import shutil
            shutil.copy2(devices_file, backup_file)
            _LOGGER.info(f"Backup created: {backup_file}")
            
            # Delete the devices file
            os.remove(devices_file)
            _LOGGER.info(f"✅ Deleted {devices_file} - All TIS devices removed")
        else:
            _LOGGER.info("No devices file to clean up")
    except Exception as e:
        _LOGGER.error(f"Failed to clean up devices file: {e}", exc_info=True)


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
