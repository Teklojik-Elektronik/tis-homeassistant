"""Support for TIS cover devices (curtains, blinds, shutters)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityFeature,
    CoverDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
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
    """Set up TIS cover entities from addon devices.json."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    devices = entry_data["devices"]
    gateway_ip = entry_data["gateway_ip"]
    udp_port = entry_data["udp_port"]
    
    _LOGGER.info(f"Setting up TIS cover entities from {len(devices)} devices")
    
    entities = []
    for unique_id, device_data in devices.items():
        subnet = device_data.get("subnet")
        device_id = device_data.get("device_id")
        model_name = device_data.get("model_name", "TIS Device")
        device_name = device_data.get("name", f"{model_name} ({subnet}.{device_id})")
        
        # Check if device has cover support
        platforms = get_device_platforms(model_name)
        cover_channels = get_platform_channel_count(model_name, "cover")
        
        if cover_channels > 0:
            _LOGGER.info(f"Creating {cover_channels} cover entities for {model_name} ({subnet}.{device_id})")
            
            # Cover kontrolü genellikle 2 kanal kullanır (UP + DOWN)
            # Her cover için 2 kanal gerekir
            for cover_index in range(cover_channels // 2):
                up_channel = (cover_index * 2) + 1
                down_channel = (cover_index * 2) + 2
                
                cover_entity = TISCover(
                    hass,
                    entry,
                    unique_id,
                    device_name,
                    model_name,
                    subnet,
                    device_id,
                    up_channel,
                    down_channel,
                    cover_index + 1,
                    gateway_ip,
                    udp_port,
                )
                entities.append(cover_entity)
    
    if entities:
        async_add_entities(entities)
        _LOGGER.info(f"Added {len(entities)} TIS cover entities")


class TISCover(CoverEntity):
    """Representation of a TIS cover device (curtain/blind/shutter)."""

    _attr_device_class = CoverDeviceClass.CURTAIN
    _attr_supported_features = (
        CoverEntityFeature.OPEN
        | CoverEntityFeature.CLOSE
        | CoverEntityFeature.STOP
    )

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        unique_id: str,
        device_name: str,
        model_name: str,
        subnet: int,
        device_id: int,
        up_channel: int,
        down_channel: int,
        cover_number: int,
        gateway_ip: str,
        udp_port: int,
    ) -> None:
        """Initialize the cover."""
        self.hass = hass
        self._entry = entry
        self._unique_id_prefix = unique_id
        self._device_name = device_name
        self._model_name = model_name
        self._subnet = subnet
        self._device_id = device_id
        self._up_channel = up_channel
        self._down_channel = down_channel
        self._cover_number = cover_number
        self._gateway_ip = gateway_ip
        self._udp_port = udp_port
        
        self._attr_name = f"{device_name} Cover {cover_number}"
        self._attr_unique_id = f"{unique_id}_cover_{cover_number}"
        
        # State
        self._attr_is_closed = None
        self._attr_is_opening = False
        self._attr_is_closing = False
        
        self._update_callback_key_up = None
        self._update_callback_key_down = None
        
        # Device info - group all entities under same device
        self._attr_device_info = {
            "identifiers": {("tis", unique_id)},
            "name": device_name,
            "manufacturer": "TIS",
            "model": model_name,
        }

    async def async_added_to_hass(self) -> None:
        """Register state update callbacks."""
        entry_data = self.hass.data[DOMAIN][self._entry.entry_id]
        
        # Callback for UP channel
        async def update_up_state(is_on: bool, brightness: int):
            self._attr_is_opening = is_on
            if is_on:
                self._attr_is_closing = False
                self._attr_is_closed = False
            self.async_write_ha_state()
        
        # Callback for DOWN channel
        async def update_down_state(is_on: bool, brightness: int):
            self._attr_is_closing = is_on
            if is_on:
                self._attr_is_opening = False
                self._attr_is_closed = True
            self.async_write_ha_state()
        
        # Register callbacks
        self._update_callback_key_up = (self._subnet, self._device_id, self._up_channel)
        self._update_callback_key_down = (self._subnet, self._device_id, self._down_channel)
        
        entry_data["update_callbacks"][self._update_callback_key_up] = update_up_state
        entry_data["update_callbacks"][self._update_callback_key_down] = update_down_state

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callbacks."""
        entry_data = self.hass.data[DOMAIN][self._entry.entry_id]
        
        if self._update_callback_key_up in entry_data["update_callbacks"]:
            del entry_data["update_callbacks"][self._update_callback_key_up]
        if self._update_callback_key_down in entry_data["update_callbacks"]:
            del entry_data["update_callbacks"][self._update_callback_key_down]

    async def async_open_cover(self, **kwargs: Any) -> None:
        """Open the cover."""
        _LOGGER.info(f"{self._attr_name}: Opening (UP channel ON, DOWN channel OFF)")
        
        # UP channel ON
        await self._send_control(self._up_channel, 100)
        # DOWN channel OFF
        await self._send_control(self._down_channel, 0)
        
        self._attr_is_opening = True
        self._attr_is_closing = False
        self._attr_is_closed = False
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        """Close the cover."""
        _LOGGER.info(f"{self._attr_name}: Closing (UP channel OFF, DOWN channel ON)")
        
        # UP channel OFF
        await self._send_control(self._up_channel, 0)
        # DOWN channel ON
        await self._send_control(self._down_channel, 100)
        
        self._attr_is_opening = False
        self._attr_is_closing = True
        self._attr_is_closed = True
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        """Stop the cover."""
        _LOGGER.info(f"{self._attr_name}: Stopping (both channels OFF)")
        
        # Both channels OFF
        await self._send_control(self._up_channel, 0)
        await self._send_control(self._down_channel, 0)
        
        self._attr_is_opening = False
        self._attr_is_closing = False
        self.async_write_ha_state()

    async def _send_control(self, channel: int, value: int) -> None:
        """Send control packet using OpCode 0x0031"""
        import socket
        
        try:
            # Get local IP for SMARTCLOUD header
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
            finally:
                s.close()
            
            ip_bytes = bytes([int(x) for x in local_ip.split('.')])
            
            # Create control packet
            packet_obj = TISPacket.create_control_packet(
                self._subnet,
                self._device_id,
                channel,
                value,
                speed=0
            )
            tis_data = packet_obj.build()
            full_packet = ip_bytes + b'SMARTCLOUD' + tis_data
            
            # Send via UDP
            client = TISUDPClient(self._gateway_ip, self._udp_port)
            await client.async_connect()
            client.send_to(full_packet, self._gateway_ip)
            client.close()
            
            _LOGGER.info(f"🏛️ Sent cover control to {self._subnet}.{self._device_id} CH{channel}: {value}")
        except Exception as e:
            _LOGGER.error(f"Error sending cover control: {e}", exc_info=True)
        except Exception as e:
            _LOGGER.error(f"Error sending cover control: {e}")
