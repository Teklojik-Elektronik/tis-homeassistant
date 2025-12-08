"""Support for TIS lights and dimmers."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON, STATE_OFF, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .tis_protocol import TISPacket, TISUDPClient
from .device_appliance_mapping import get_device_platforms, get_platform_channel_count

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TIS lights from addon devices.json."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    devices = entry_data["devices"]
    gateway_ip = entry_data["gateway_ip"]
    udp_port = entry_data["udp_port"]
    
    _LOGGER.info(f"Setting up TIS light entities from {len(devices)} devices")
    
    entities = []
    for unique_id, device_data in devices.items():
        subnet = device_data.get("subnet")
        device_id = device_data.get("device_id")
        model_name = device_data.get("model_name", "TIS Device")
        device_name = device_data.get("name", f"{model_name} ({subnet}.{device_id})")
        
        # Get supported platforms from device mapping
        platforms = get_device_platforms(model_name)
        dimmer_channels = get_platform_channel_count(model_name, "dimmer")
        rgb_channels = get_platform_channel_count(model_name, "rgb")
        rgbw_channels = get_platform_channel_count(model_name, "rgbw")
        
        # Check if device has light support
        total_light_channels = dimmer_channels + rgb_channels + rgbw_channels
        
        if total_light_channels > 0:
            _LOGGER.info(f"Device {model_name} ({subnet}.{device_id}) - Lights: dimmer={dimmer_channels}, rgb={rgb_channels}, rgbw={rgbw_channels}")
            
            # For now, only implement dimmer support
            if dimmer_channels > 0:
                channels = dimmer_channels
                channel_names = device_data.get("channel_names", {})
                initial_states = device_data.get("initial_states", {})
                
                for channel in range(1, channels + 1):
                    predefined_name = channel_names.get(str(channel))
                    initial_state = initial_states.get(str(channel))
                
                light_entity = TISLight(
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
                entities.append(light_entity)
    
    if entities:
        async_add_entities(entities)
        _LOGGER.info(f"Added {len(entities)} TIS light entities")


class TISLight(LightEntity):
    """Representation of a TIS light/dimmer."""

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
        """Initialize the light."""
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
        
        self._attr_unique_id = f"{unique_id}_ch{channel}_light"
        
        # Light properties
        self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        self._attr_color_mode = ColorMode.BRIGHTNESS
        
        # Initial state
        if initial_state and isinstance(initial_state, dict):
            brightness_pct = initial_state.get("brightness", 0)
            # Convert from 0-248 (TIS) to 0-255 (Home Assistant)
            self._attr_brightness = int((brightness_pct / 248.0) * 255) if brightness_pct > 0 else 0
            self._attr_is_on = brightness_pct > 0
        else:
            self._attr_brightness = None
            self._attr_is_on = None
        
        self._listener = None

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
                        brightness_raw = packet_data.get("brightness", 0)
                        # Convert from 0-248 (TIS) to 0-255 (HA)
                        self._attr_brightness = int((brightness_raw / 248.0) * 255) if brightness_raw > 0 else 0
                        self._attr_is_on = brightness_raw > 0
                        self.async_write_ha_state()
                
                # OpCode 0x0034: Multi-channel status response
                elif op_code == 0x0034:
                    channel_states = packet_data.get("channel_states", {})
                    if self._channel in channel_states:
                        brightness_raw = channel_states[self._channel]
                        self._attr_brightness = int((brightness_raw / 248.0) * 255) if brightness_raw > 0 else 0
                        self._attr_is_on = brightness_raw > 0
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
        
        # Remove callback
        entry_data = self.hass.data[DOMAIN][self._entry.entry_id]
        key = (self._subnet, self._device_id, self._channel)
        entry_data["update_callbacks"].pop(key, None)

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light (0-255)."""
        return self._attr_brightness

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._attr_is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        # Get brightness from kwargs or use max
        brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
        
        # Convert from 0-255 (HA) to 0-248 (TIS)
        brightness_tis = int((brightness / 255.0) * 248)
        brightness_tis = max(1, min(248, brightness_tis))  # Clamp to 1-248
        
        # Send control packet
        try:
            client = TISUDPClient(self._gateway_ip, self._udp_port)
            await client.async_connect(bind=False)
            
            # Get local IP for SMARTCLOUD header
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
            finally:
                s.close()
            
            ip_bytes = bytes([int(x) for x in local_ip.split('.')])
            
            # Build control packet (OpCode 0x0031)
            packet = TISPacket()
            packet.src_subnet = 1
            packet.src_device = 254
            packet.src_type = 0xFFFE
            packet.tgt_subnet = self._subnet
            packet.tgt_device = self._device_id
            packet.op_code = 0x0031  # Control command
            packet.additional_data = bytes([self._channel - 1, 0x00, brightness_tis])
            
            tis_data = packet.build()
            full_packet = ip_bytes + b'SMARTCLOUD' + tis_data
            client.send_to(full_packet, self._gateway_ip)
            
            client.close()
            
            # Update state optimistically
            self._attr_brightness = brightness
            self._attr_is_on = True
            self.async_write_ha_state()
            
            _LOGGER.debug(f"Turned on {self.name} to brightness {brightness} ({brightness_tis} TIS)")
        except Exception as e:
            _LOGGER.error(f"Failed to turn on {self.name}: {e}")

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        try:
            client = TISUDPClient(self._gateway_ip, self._udp_port)
            await client.async_connect(bind=False)
            
            # Get local IP
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
            finally:
                s.close()
            
            ip_bytes = bytes([int(x) for x in local_ip.split('.')])
            
            # Build control packet with brightness 0
            packet = TISPacket()
            packet.src_subnet = 1
            packet.src_device = 254
            packet.src_type = 0xFFFE
            packet.tgt_subnet = self._subnet
            packet.tgt_device = self._device_id
            packet.op_code = 0x0031  # Control command
            packet.additional_data = bytes([self._channel - 1, 0x00, 0])  # Brightness 0
            
            tis_data = packet.build()
            full_packet = ip_bytes + b'SMARTCLOUD' + tis_data
            client.send_to(full_packet, self._gateway_ip)
            
            client.close()
            
            # Update state optimistically
            self._attr_brightness = 0
            self._attr_is_on = False
            self.async_write_ha_state()
            
            _LOGGER.debug(f"Turned off {self.name}")
        except Exception as e:
            _LOGGER.error(f"Failed to turn off {self.name}: {e}")
