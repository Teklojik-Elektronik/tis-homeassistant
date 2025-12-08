"""Support for TIS fan devices."""
from __future__ import annotations

import logging
import math
from typing import Any

from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .const import DOMAIN
from .device_appliance_mapping import get_device_platforms, get_platform_channel_count
from .tis_protocol import TISPacket, TISUDPClient

_LOGGER = logging.getLogger(__name__)

# Fan speed presets (TIS uses 0-100 scale)
ORDERED_NAMED_FAN_SPEEDS = ["Low", "Medium", "High"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TIS fan entities from addon devices.json."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    devices = entry_data["devices"]
    gateway_ip = entry_data["gateway_ip"]
    udp_port = entry_data["udp_port"]
    
    _LOGGER.info(f"Setting up TIS fan entities from {len(devices)} devices")
    
    entities = []
    for unique_id, device_data in devices.items():
        subnet = device_data.get("subnet")
        device_id = device_data.get("device_id")
        model_name = device_data.get("model_name", "TIS Device")
        device_name = device_data.get("name", f"{model_name} ({subnet}.{device_id})")
        
        # Check if device has fan support
        platforms = get_device_platforms(model_name)
        fan_channels = get_platform_channel_count(model_name, "fan")
        
        if fan_channels > 0:
            _LOGGER.info(f"Creating {fan_channels} fan entities for {model_name} ({subnet}.{device_id})")
            
            for channel in range(1, fan_channels + 1):
                fan_entity = TISFan(
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
                )
                entities.append(fan_entity)
    
    if entities:
        async_add_entities(entities)
        _LOGGER.info(f"Added {len(entities)} TIS fan entities")


class TISFan(FanEntity):
    """Representation of a TIS fan device."""

    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_speed_count = 100  # TIS uses 0-100 scale

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
    ) -> None:
        """Initialize the fan."""
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
        
        self._attr_name = f"{device_name} Fan CH{channel}"
        self._attr_unique_id = f"{unique_id}_fan_ch{channel}"
        
        # State
        self._attr_is_on = False
        self._attr_percentage = 0
        
        self._update_callback_key = None
        
        # Device info - group all entities under same device
        self._attr_device_info = {
            "identifiers": {("tis", unique_id)},
            "name": device_name,
            "manufacturer": "TIS",
            "model": model_name,
        }

    async def async_added_to_hass(self) -> None:
        """Register state update callback."""
        entry_data = self.hass.data[DOMAIN][self._entry.entry_id]
        
        async def update_state(is_on: bool, brightness: int):
            """Update fan state from UDP feedback."""
            self._attr_is_on = is_on
            self._attr_percentage = brightness
            self.async_write_ha_state()
            _LOGGER.debug(f"Updated {self._attr_name}: {'ON' if is_on else 'OFF'} ({brightness}%)")
        
        # Register callback
        self._update_callback_key = (self._subnet, self._device_id, self._channel)
        entry_data["update_callbacks"][self._update_callback_key] = update_state
        
        # Query initial state
        await self.async_update()

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callback."""
        entry_data = self.hass.data[DOMAIN][self._entry.entry_id]
        
        if self._update_callback_key in entry_data["update_callbacks"]:
            del entry_data["update_callbacks"][self._update_callback_key]

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if percentage is None:
            percentage = 100  # Full speed
        
        _LOGGER.info(f"{self._attr_name}: Turning ON at {percentage}%")
        await self._send_control(percentage)
        
        self._attr_is_on = True
        self._attr_percentage = percentage
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        _LOGGER.info(f"{self._attr_name}: Turning OFF")
        await self._send_control(0)
        
        self._attr_is_on = False
        self._attr_percentage = 0
        self.async_write_ha_state()

    async def async_set_percentage(self, percentage: int) -> None:
        """Set the speed percentage of the fan."""
        _LOGGER.info(f"{self._attr_name}: Setting speed to {percentage}%")
        
        if percentage == 0:
            await self.async_turn_off()
        else:
            await self._send_control(percentage)
            self._attr_is_on = True
            self._attr_percentage = percentage
            self.async_write_ha_state()

    async def async_update(self) -> None:
        """Query fan status using OpCode 0x0033"""
        try:
            # Create query packet
            packet_obj = TISPacket.create_query_packet(self._subnet, self._device_id)
            packet_bytes = packet_obj.build()
            
            # Send via UDP
            client = TISUDPClient(self._gateway_ip, self._udp_port)
            await client.async_connect()
            client.send_to(packet_bytes, self._gateway_ip)
            client.close()
            
            _LOGGER.debug(f"Sent fan query to {self._subnet}.{self._device_id}")
        except Exception as e:
            _LOGGER.error(f"Error querying fan status: {e}")

    async def _send_control(self, percentage: int) -> None:
        """Send control packet using OpCode 0x0031"""
        try:
            # Create control packet
            packet_obj = TISPacket.create_control_packet(
                self._subnet,
                self._device_id,
                self._channel,
                percentage,
                speed=0
            )
            packet_bytes = packet_obj.build()
            
            # Send via UDP
            client = TISUDPClient(self._gateway_ip, self._udp_port)
            await client.async_connect()
            client.send_to(packet_bytes, self._gateway_ip)
            client.close()
            
            _LOGGER.debug(f"Sent fan control to {self._subnet}.{self._device_id} CH{self._channel}: {percentage}%")
        except Exception as e:
            _LOGGER.error(f"Error sending fan control: {e}")
