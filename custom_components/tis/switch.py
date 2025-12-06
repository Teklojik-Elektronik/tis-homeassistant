"""Support for TIS switches - Reads from Addon devices.json."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .tis_protocol import TISUDPClient, TISPacket

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TIS switches from addon devices.json."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    devices = entry_data["devices"]
    gateway_ip = entry_data["gateway_ip"]
    udp_port = entry_data["udp_port"]
    
    _LOGGER.info(f"Setting up {len(devices)} TIS switch entities")
    
    entities = []
    for unique_id, device_data in devices.items():
        subnet = device_data.get("subnet")
        device_id = device_data.get("device_id")
        model_name = device_data.get("model_name", "TIS Device")
        channels = device_data.get("channels", 1)
        device_name = device_data.get("name", f"{model_name} ({subnet}.{device_id})")
        channel_names = device_data.get("channel_names", {})  # Get channel names from JSON
        
        _LOGGER.debug(f"Device {unique_id} has {len(channel_names)} channel names in JSON")
        
        # Create switch entity for each channel
        for channel in range(1, channels + 1):  # Channels start from 1
            # Get pre-defined channel name from JSON (if available)
            predefined_name = channel_names.get(str(channel))
            
            entities.append(
                TISSwitch(
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
                    predefined_name  # Pass channel name from JSON
                )
            )
    
    async_add_entities(entities)
    _LOGGER.info(f"Added {len(entities)} TIS switch entities")


class TISSwitch(SwitchEntity):
    """Representation of a TIS switch."""

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
        predefined_name: str = None
    ) -> None:
        """Initialize the switch."""
        self.hass = hass
        self._entry = entry
        self._subnet = subnet
        self._device_id = device_id
        self._channel = channel
        self._gateway_ip = gateway_ip
        self._udp_port = udp_port
        self._is_on = False
        self._brightness = 0
        self._channel_name = predefined_name  # Use predefined name from JSON
        self._device_name = device_name
        
        # Entity attributes
        if channel > 0:
            self._attr_unique_id = f"{unique_id}_ch{channel}"
            # Use predefined name if available, otherwise CH number
            if predefined_name:
                self._name = f"{device_name} {predefined_name}"
                _LOGGER.info(f"Created entity with predefined name: {self._name}")
            else:
                self._name = f"{device_name} CH{channel}"  # Will be updated by UDP response
        else:
            self._attr_unique_id = unique_id
            self._name = device_name
        
        # Device info - all channels share same device identifier
        # This groups all CH1, CH2, etc. under one device
        self._attr_device_info = {
            "identifiers": {(DOMAIN, unique_id)},  # Same for all channels
            "name": device_name,
            "manufacturer": "TIS",
            "model": model_name,
            "suggested_area": "Living Room",
        }
        
    async def async_added_to_hass(self) -> None:
        """Register update callback when entity is added."""
        entry_data = self.hass.data[DOMAIN][self._entry.entry_id]
        callback_key = (self._subnet, self._device_id, self._channel)
        
        # Register state update callback
        entry_data["update_callbacks"][callback_key] = self._handle_feedback
        
        # Register channel name callback
        if "name_callbacks" not in entry_data:
            entry_data["name_callbacks"] = {}
        entry_data["name_callbacks"][callback_key] = self._handle_channel_name
        
        _LOGGER.debug(f"Registered callbacks for {self._subnet}.{self._device_id} CH{self._channel}")
        
        # Request initial state and channel name from device
        await self._request_state()
        
        # Retry channel name request after 2 seconds if not received
        async def retry_channel_name():
            await asyncio.sleep(2)
            if self._channel_name is None:
                _LOGGER.info(f"Retrying channel name request for {self._subnet}.{self._device_id} CH{self._channel}")
                await self._request_channel_name_only()
        
        self.hass.async_create_task(retry_channel_name())
    
    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        entry_data = self.hass.data[DOMAIN][self._entry.entry_id]
        callback_key = (self._subnet, self._device_id, self._channel)
        
        # Unregister callbacks
        entry_data["update_callbacks"].pop(callback_key, None)
        if "name_callbacks" in entry_data:
            entry_data["name_callbacks"].pop(callback_key, None)
        
        _LOGGER.debug(f"Unregistered callbacks for {self._subnet}.{self._device_id} CH{self._channel}")
    
    async def _request_state(self) -> None:
        """Request current state and channel name from device."""
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
            
            # Request 1: Multi-channel status (OpCode 0x0033)
            packet1 = TISPacket()
            packet1.src_subnet = 1
            packet1.src_device = 254
            packet1.src_type = 0xFFFE
            packet1.tgt_subnet = self._subnet
            packet1.tgt_device = self._device_id
            packet1.op_code = 0x0033  # Multi-channel status query
            packet1.additional_data = bytes([])
            
            tis_data1 = packet1.build()
            full_packet1 = ip_bytes + b'SMARTCLOUD' + tis_data1
            client.send_to(full_packet1, self._gateway_ip)
            
            # Request 2: Channel name (OpCode 0xF00E)
            packet2 = TISPacket()
            packet2.src_subnet = 1
            packet2.src_device = 254
            packet2.src_type = 0xFFFE
            packet2.tgt_subnet = self._subnet
            packet2.tgt_device = self._device_id
            packet2.op_code = 0xF00E  # Channel name query
            packet2.additional_data = bytes([self._channel])
            
            tis_data2 = packet2.build()
            full_packet2 = ip_bytes + b'SMARTCLOUD' + tis_data2
            client.send_to(full_packet2, self._gateway_ip)
            
            client.close()
            
            _LOGGER.debug(f"Requested state and name from {self._subnet}.{self._device_id} CH{self._channel}")
        except Exception as e:
            _LOGGER.error(f"Failed to request state: {e}")
    
    async def _request_channel_name_only(self) -> None:
        """Request only channel name from device (for retry)."""
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
            
            # Request channel name (OpCode 0xF00E)
            packet = TISPacket()
            packet.src_subnet = 1
            packet.src_device = 254
            packet.src_type = 0xFFFE
            packet.tgt_subnet = self._subnet
            packet.tgt_device = self._device_id
            packet.op_code = 0xF00E  # Channel name query
            packet.additional_data = bytes([self._channel])
            
            tis_data = packet.build()
            full_packet = ip_bytes + b'SMARTCLOUD' + tis_data
            client.send_to(full_packet, self._gateway_ip)
            
            client.close()
            
            _LOGGER.debug(f"Retry: Requested channel name from {self._subnet}.{self._device_id} CH{self._channel}")
        except Exception as e:
            _LOGGER.error(f"Failed to request channel name: {e}")
    
    async def _handle_feedback(self, is_on: bool, brightness: int):
        """Handle feedback from UDP listener."""
        self._is_on = is_on
        self._brightness = brightness
        self.async_write_ha_state()
        _LOGGER.debug(f"Updated {self.name}: is_on={is_on}, brightness={brightness}%")
    
    async def _handle_channel_name(self, name: str):
        """Handle channel name from UDP listener."""
        self._channel_name = name
        
        # Update entity name if channel name is valid
        if name:  # Not None and not empty
            self._name = f"{self._device_name} {name}"
            _LOGGER.info(f"Updated entity name to: {self._name}")
        else:
            # Keep CH number for undefined channels (0xFF response)
            self._name = f"{self._device_name} CH{self._channel}"
            _LOGGER.debug(f"Channel {self._channel} name is undefined, using CH{self._channel}")
        
        self.async_write_ha_state()

    @property
    def name(self) -> str:
        """Return the name of the switch (dynamically updated)."""
        return self._name
    
    @property
    def is_on(self) -> bool:
        """Return true if switch is on."""
        return self._is_on
    
    @property
    def extra_state_attributes(self) -> dict:
        """Return entity specific state attributes."""
        attrs = {
            "subnet": self._subnet,
            "device_id": self._device_id,
            "channel": self._channel,
            "brightness": self._brightness,
        }
        if self._channel_name:
            attrs["channel_name"] = self._channel_name
        return attrs

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._send_command(1)
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._send_command(0)
        self._is_on = False
        self.async_write_ha_state()

    async def _send_command(self, state: int) -> None:
        """Send UDP command to TIS device."""
        try:
            # Create TIS protocol client
            client = TISUDPClient(self._gateway_ip, self._udp_port)
            await client.async_connect(bind=False)  # No bind, just send
            
            # Build packet
            packet = TISPacket()
            packet.src_subnet = 1
            packet.src_device = 254
            packet.src_type = 0xFFFE
            packet.tgt_subnet = self._subnet
            packet.tgt_device = self._device_id
            packet.op_code = 0x0031  # Control command
            
            # Additional data: [channel, brightness (0-248), 0, 0]
            # For ON: brightness=248 (100%), for OFF: brightness=0
            brightness = 248 if state else 0
            packet.additional_data = bytes([self._channel, brightness, 0, 0])
            
            tis_data = packet.build()
            
            # Add SMARTCLOUD header
            from .discovery import get_local_ip
            local_ip = get_local_ip()
            ip_bytes = bytes([int(x) for x in local_ip.split('.')])
            full_packet = ip_bytes + b'SMARTCLOUD' + tis_data
            
            # Send to gateway directly (unicast)
            client.send_to(full_packet, self._gateway_ip)
            client.close()
            
            _LOGGER.info(f"Sent command to {self._subnet}.{self._device_id} CH{self._channel}: {'ON' if state else 'OFF'}")
            
        except Exception as e:
            _LOGGER.error(f"Failed to send command: {e}", exc_info=True)
