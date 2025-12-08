"""Support for TIS select entities (Security Mode)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .device_appliance_mapping import get_device_platforms, get_platform_channel_count

_LOGGER = logging.getLogger(__name__)

# Security mode mapping
SECURITY_OPTIONS = {
    "vacation": 1,
    "away": 2,
    "night": 3,
    "disarm": 6,
}

SECURITY_FEEDBACK_OPTIONS = {
    1: "vacation",
    2: "away",
    3: "night",
    6: "disarm",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TIS select entities from config entry."""
    gateway_ip = entry.data.get("gateway_ip", "192.168.1.200")
    udp_port = entry.data.get("udp_port", 6000)
    devices = hass.data[DOMAIN].get("devices", {})
    
    entities = []
    for unique_id, device_data in devices.items():
        subnet = device_data.get("subnet")
        device_id = device_data.get("device_id")
        model_name = device_data.get("model_name", "TIS Device")
        device_name = device_data.get("name", f"{model_name} ({subnet}.{device_id})")
        
        # Check if device has security support
        platforms = get_device_platforms(model_name)
        security_channels = get_platform_channel_count(model_name, "security")
        
        if security_channels > 0:
            _LOGGER.info(f"Creating {security_channels} security select entities for {model_name} ({subnet}.{device_id})")
            
            for channel in range(security_channels):
                select_entity = TISSecurityMode(
                    device_name,
                    unique_id,
                    model_name,
                    subnet,
                    device_id,
                    channel,
                    gateway_ip,
                    udp_port,
                    hass,
                )
                entities.append(select_entity)
    
    if entities:
        async_add_entities(entities)


class TISSecurityMode(SelectEntity):
    """Representation of TIS Security Mode Select."""
    
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
        hass: HomeAssistant,
    ) -> None:
        """Initialize security mode select."""
        self._subnet = subnet
        self._device_id = device_id
        self._channel = channel
        self._gateway_ip = gateway_ip
        self._udp_port = udp_port
        self.hass = hass
        
        self._attr_name = f"{device_name} Security CH{channel + 1}"
        self._attr_unique_id = f"{unique_id}_security_{channel}"
        self._attr_options = list(SECURITY_OPTIONS.keys())
        self._attr_current_option = "disarm"  # Start disarmed
        self._attr_icon = "mdi:shield"
        
        # Protection state (linked to Lock entity)
        self._is_protected = True
        self._read_only = True
        
        self._listener = None
        
        # Device info
        self._attr_device_info = {
            "identifiers": {("tis", unique_id)},
            "name": device_name,
            "manufacturer": "TIS",
            "model": model_name,
        }
    
    async def async_added_to_hass(self) -> None:
        """Subscribe to admin lock events."""
        @callback
        def handle_admin_lock(event):
            """Handle admin lock state changes."""
            locked = event.data.get("locked")
            if locked:
                self._read_only = True
                _LOGGER.info(f"🔒 Security {self._attr_name}: Protection ENABLED (read-only)")
            else:
                self._read_only = False
                _LOGGER.info(f"🔓 Security {self._attr_name}: Protection DISABLED (writable)")
            self.async_write_ha_state()
        
        @callback
        def handle_security_feedback(event):
            """Handle security feedback from TIS devices."""
            data = event.data
            
            # Filter by feedback_type
            if data.get("feedback_type") != "security_feedback":
                return
            
            # Check if event is for this device and channel
            device_id = data.get("device_id")
            if (not device_id or device_id[0] != self._subnet or device_id[1] != self._device_id or
                data.get("channel") != self._channel):
                return
                
                mode = data.get("mode")
                if mode in SECURITY_FEEDBACK_OPTIONS:
                    option = SECURITY_FEEDBACK_OPTIONS[mode]
                    self._attr_current_option = option
                    self.async_write_ha_state()
                    _LOGGER.info(f"🛡️ Security feedback: {self._attr_name} → {option}")
        
        device_id_str = f"[{self._subnet}, {self._device_id}]"
        self._listener = self.hass.bus.async_listen("admin_lock", handle_admin_lock)
        self._listener_feedback = self.hass.bus.async_listen(device_id_str, handle_security_feedback)
        
        # Query initial state
        await self.async_update()
    
    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        if self._listener:
            self._listener()
            self._listener = None
        if self._listener_feedback:
            self._listener_feedback()
            self._listener_feedback = None
    
    @property
    def name(self) -> str:
        """Return the name of the select."""
        return self._attr_name
    
    @property
    def options(self) -> list[str]:
        """Return available options."""
        return self._attr_options
    
    @property
    def current_option(self) -> str | None:
        """Return current selected option."""
        return self._attr_current_option if self._attr_current_option in SECURITY_FEEDBACK_OPTIONS.values() else None
    
    async def async_select_option(self, option: str) -> None:
        """Select new security mode using TISControlProtocol."""
        if self._is_protected and self._read_only:
            _LOGGER.error(f"🔒 Security {self._attr_name}: Cannot change mode - Admin Lock is LOCKED")
            self._attr_current_option = STATE_UNAVAILABLE
            self.async_write_ha_state()
            raise ValueError("The security module is protected and read-only. Unlock Admin Lock first.")
        
        if option not in self._attr_options:
            raise ValueError(f"Invalid option: {option} (possible options: {self._attr_options})")
        
        # Get mode code
        mode_code = SECURITY_OPTIONS.get(option)
        if mode_code is None:
            raise ValueError(f"Unknown security mode: {option}")
        
        try:
            # Get TISControlProtocol API from hass.data
            entry_data = self.hass.data[DOMAIN]
            entry_id = list(entry_data.keys())[0]  # Get first (and only) entry
            api = entry_data[entry_id].get("api")
            protocol = entry_data[entry_id].get("protocol")
            protocol_handler = entry_data[entry_id].get("protocol_handler")
            
            if not (api and protocol and protocol_handler):
                raise ValueError("TISControlProtocol not available")
            
            # Create TISPacket using TISProtocolHandler
            # Temporary entity mock for generate_control_security_packet
            class EntityMock:
                def __init__(self, subnet, device, channel, gateway, api_instance):
                    self.device_id = [subnet, device]
                    self.channel_number = channel
                    self.gateway = gateway
                    self.api = api_instance
            
            entity_mock = EntityMock(
                self._subnet,
                self._device_id,
                self._channel,
                self._gateway_ip,
                api
            )
            
            # Generate security control packet (0x0104)
            packet = protocol_handler.generate_control_security_packet(entity_mock, mode_code)
            
            # Send packet with ACK (15 retries, 1s timeout)
            ack_received = await protocol.sender.send_packet_with_ack(packet, attempts=15, timeout=1.0)
            
            if ack_received:
                self._attr_current_option = option
                self.async_write_ha_state()
                _LOGGER.info(f"✅ Security mode set: {self._attr_name} → {option} (ACK received)")
            else:
                _LOGGER.warning(f"⚠️ Security mode set: {self._attr_name} → {option} (NO ACK after 15 attempts)")
                # Still update optimistically
                self._attr_current_option = option
                self.async_write_ha_state()
            
        except Exception as e:
            _LOGGER.error(f"❌ Error setting security mode: {e}", exc_info=True)
            self._attr_current_option = STATE_UNAVAILABLE
            self.async_write_ha_state()
            raise
    
    async def async_update(self) -> None:
        """Query device state using TISControlProtocol (0x011E security update query)."""
        try:
            # Get TISControlProtocol API from hass.data
            entry_data = self.hass.data[DOMAIN]
            entry_id = list(entry_data.keys())[0]
            api = entry_data[entry_id].get("api")
            protocol = entry_data[entry_id].get("protocol")
            protocol_handler = entry_data[entry_id].get("protocol_handler")
            
            if not (api and protocol and protocol_handler):
                _LOGGER.warning("TISControlProtocol not available for update")
                return
            
            # Create entity mock for generate_security_update_packet
            class EntityMock:
                def __init__(self, subnet, device, channel, gateway, api_instance):
                    self.device_id = [subnet, device]
                    self.channel_number = channel
                    self.gateway = gateway
                    self.api = api_instance
            
            entity_mock = EntityMock(
                self._subnet,
                self._device_id,
                self._channel,
                self._gateway_ip,
                api
            )
            
            # Generate security update query packet (0x011E)
            packet = protocol_handler.generate_security_update_packet(entity_mock)
            
            # Send packet (update query doesn't need ACK wait)
            await protocol.sender.send_packet(packet)
            
            _LOGGER.debug(f"🛡️ Queried security: {self._subnet}.{self._device_id} CH{self._channel}")
        except Exception as e:
            _LOGGER.error(f"Error querying security: {e}", exc_info=True)
