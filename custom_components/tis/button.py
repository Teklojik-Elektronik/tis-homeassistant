"""Support for TIS button/universal switch entities."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.button import ButtonEntity
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
    """Set up TIS button entities from config entry."""
    gateway_ip = entry.data.get("gateway_ip", "192.168.1.200")
    udp_port = entry.data.get("udp_port", 6000)
    devices = hass.data[DOMAIN].get("devices", {})
    
    entities = []
    for unique_id, device_data in devices.items():
        subnet = device_data.get("subnet")
        device_id = device_data.get("device_id")
        model_name = device_data.get("model_name", "TIS Device")
        device_name = device_data.get("name", f"{model_name} ({subnet}.{device_id})")
        
        # Check if device has universal switch support
        platforms = get_device_platforms(model_name)
        universal_channels = get_platform_channel_count(model_name, "universal_switch")
        
        if universal_channels > 0:
            _LOGGER.info(f"Creating {universal_channels} button entities for {model_name} ({subnet}.{device_id})")
            
            for channel in range(universal_channels):
                button_entity = TISUniversalSwitch(
                    device_name,
                    unique_id,
                    model_name,
                    subnet,
                    device_id,
                    channel,
                    gateway_ip,
                    udp_port,
                    universal_type=0,  # Default type, can be configured
                )
                entities.append(button_entity)
    
    if entities:
        async_add_entities(entities)


class TISUniversalSwitch(ButtonEntity):
    """Representation of TIS Universal Switch Button."""
    
    def __init__(
        self,
        device_name: str,
        unique_id: str,
        model_name: str,
        subnet: int,
        device_id: int,
        channel: int,
        gateway_ip: str,
        udp_port: int,
        universal_type: int = 0,
    ) -> None:
        """Initialize universal switch button."""
        self._subnet = subnet
        self._device_id = device_id
        self._channel = channel
        self._gateway_ip = gateway_ip
        self._udp_port = udp_port
        self._universal_type = int(universal_type * 255)  # 0-255 range
        
        self._attr_name = f"{device_name} Button {channel + 1}"
        self._attr_unique_id = f"{unique_id}_button_{channel}"
        
        # Device info
        self._attr_device_info = {
            "identifiers": {("tis", unique_id)},
            "name": device_name,
            "manufacturer": "TIS",
            "model": model_name,
        }
    
    async def async_press(self) -> None:
        """Handle button press."""
        try:
            ip_bytes = bytes(map(int, self._gateway_ip.split('.')))
            
            # Create universal switch packet (0xE01C)
            packet_obj = TISPacket.create_universal_switch_packet(
                self._subnet,
                self._device_id,
                self._channel,
                self._universal_type
            )
            tis_data = packet_obj.build()
            full_packet = ip_bytes + b'SMARTCLOUD' + tis_data
            
            client = TISUDPClient(self._gateway_ip, self._udp_port)
            await client.async_connect()
            client.send_to(full_packet, self._gateway_ip)
            client.close()
            
            _LOGGER.info(f"🔘 Pressed button: {self._subnet}.{self._device_id} CH{self._channel} Type={self._universal_type}")
        except Exception as e:
            _LOGGER.error(f"Error pressing button: {e}", exc_info=True)
