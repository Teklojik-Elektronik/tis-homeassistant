"""Support for TIS binary sensors (motion, occupancy, etc.)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_OFF
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .device_appliance_mapping import get_device_platforms, get_platform_channel_count

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TIS binary sensors from addon devices.json."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    devices = entry_data["devices"]
    gateway_ip = entry_data["gateway_ip"]
    udp_port = entry_data["udp_port"]
    
    _LOGGER.info(f"Setting up TIS binary sensor entities from {len(devices)} devices")
    
    entities = []
    for unique_id, device_data in devices.items():
        subnet = device_data.get("subnet")
        device_id = device_data.get("device_id")
        model_name = device_data.get("model_name", "TIS Device")
        device_name = device_data.get("name", f"{model_name} ({subnet}.{device_id})")
        
        # Get supported platforms from device mapping
        platforms = get_device_platforms(model_name)
        binary_sensor_channels = get_platform_channel_count(model_name, "binary_sensor")
        security_channels = get_platform_channel_count(model_name, "security")
        
        # Check if device has binary sensor support
        total_binary_channels = binary_sensor_channels + security_channels
        
        if total_binary_channels > 0:
            _LOGGER.info(f"Device {model_name} ({subnet}.{device_id}) - Binary sensors: {total_binary_channels} (binary={binary_sensor_channels}, security={security_channels})")
            channels = total_binary_channels
            channel_names = device_data.get("channel_names", {})
            initial_states = device_data.get("initial_states", {})
            
            for channel in range(1, channels + 1):
                predefined_name = channel_names.get(str(channel))
                initial_state = initial_states.get(str(channel))
                
                sensor_entity = TISBinarySensor(
                    hass,
                    entry,
                    unique_id,
                    device_name,
                    model_name,
                    subnet,
                    device_id,
                    channel,
                    gateway_ip,
                    udp_port,
                    predefined_name,
                    initial_state
                )
                entities.append(sensor_entity)
    
    if entities:
        async_add_entities(entities)
        _LOGGER.info(f"Added {len(entities)} TIS binary sensor entities")


class TISBinarySensor(BinarySensorEntity):
    """Representation of a TIS binary sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        unique_id: str,
        device_name: str,
        model_name: str,
        subnet: int,
        device_id: int,
        channel: int,
        gateway_ip: str,
        udp_port: int,
        predefined_name: str = None,
        initial_state: dict = None,
    ) -> None:
        """Initialize the binary sensor."""
        self.hass = hass
        self._entry = entry
        self._unique_id_prefix = unique_id
        self._device_name = device_name
        self._model_name = model_name
        self._subnet = subnet
        self._device_id = device_id
        self._channel = channel
        self._gateway_ip = gateway_ip
        self._udp_port = udp_port
        
        # Set entity name
        if predefined_name:
            self._attr_name = f"{device_name} {predefined_name}"
        else:
            self._attr_name = f"{device_name} CH{channel}"
        
        self._attr_unique_id = f"{unique_id}_ch{channel}_binary"
        
        # Set device class based on model
        if "PIR" in model_name.upper() or "MOTION" in model_name.upper():
            self._attr_device_class = BinarySensorDeviceClass.MOTION
        elif "OCCUPANCY" in model_name.upper():
            self._attr_device_class = BinarySensorDeviceClass.OCCUPANCY
        else:
            self._attr_device_class = BinarySensorDeviceClass.MOTION
        
        # Initial state
        if initial_state and isinstance(initial_state, dict):
            brightness = initial_state.get("brightness", 0)
            self._attr_is_on = brightness > 0
        else:
            self._attr_is_on = None
        
        self._listener = None
        
        # Device info - group all entities under same device
        self._attr_device_info = {
            "identifiers": {("tis", unique_id)},
            "name": device_name,
            "manufacturer": "TIS",
            "model": model_name,
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to UDP events when added to hass."""
        @callback
        async def handle_udp_event(event):
            """Handle UDP packet events."""
            packet_data = event.data
            
            # Check if packet is for this device
            if (packet_data.get("tgt_subnet") == self._subnet and 
                packet_data.get("tgt_device") == self._device_id):
                
                op_code = packet_data.get("op_code")
                
                # OpCode 0x0032: Single channel feedback
                if op_code == 0x0032:
                    channel_num = packet_data.get("channel_number")
                    if channel_num == self._channel:
                        brightness = packet_data.get("brightness", 0)
                        self._attr_is_on = brightness > 0
                        self.async_write_ha_state()
                
                # OpCode 0x0034: Multi-channel status response
                elif op_code == 0x0034:
                    channel_states = packet_data.get("channel_states", {})
                    if self._channel in channel_states:
                        brightness = channel_states[self._channel]
                        self._attr_is_on = brightness > 0
                        self.async_write_ha_state()
        
        # Register callback
        entry_data = self.hass.data[DOMAIN][self._entry.entry_id]
        key = (self._subnet, self._device_id, self._channel)
        entry_data["update_callbacks"][key] = handle_udp_event
        
        self._listener = self.hass.bus.async_listen("tis_udp_packet", handle_udp_event)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        if self._listener:
            self._listener()
            self._listener = None

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self._attr_is_on
