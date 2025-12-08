"""Support for TIS climate devices (AC, HVAC)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
    FAN_AUTO,
    FAN_HIGH,
    FAN_LOW,
    FAN_MEDIUM,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .device_appliance_mapping import get_device_platforms, get_platform_channel_count
from .tis_protocol import TISPacket, TISUDPClient

_LOGGER = logging.getLogger(__name__)

# TIS HVAC Mode mapping
TIS_HVAC_MODES = {
    0: HVACMode.COOL,
    1: HVACMode.HEAT,
    2: HVACMode.FAN_ONLY,
    3: HVACMode.AUTO,
}

HVAC_MODE_TO_TIS = {
    HVACMode.OFF: None,  # Handled by state
    HVACMode.COOL: 0,
    HVACMode.HEAT: 1,
    HVACMode.FAN_ONLY: 2,
    HVACMode.AUTO: 3,
}

# TIS Fan Speed mapping
TIS_FAN_MODES = {
    0: FAN_AUTO,
    1: FAN_HIGH,
    2: FAN_MEDIUM,
    3: FAN_LOW,
}

FAN_MODE_TO_TIS = {
    FAN_AUTO: 0,
    FAN_HIGH: 1,
    FAN_MEDIUM: 2,
    FAN_LOW: 3,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TIS climate entities from addon devices.json."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    devices = entry_data["devices"]
    gateway_ip = entry_data["gateway_ip"]
    udp_port = entry_data["udp_port"]
    
    _LOGGER.info(f"Setting up TIS climate entities from {len(devices)} devices")
    
    entities = []
    for unique_id, device_data in devices.items():
        subnet = device_data.get("subnet")
        device_id = device_data.get("device_id")
        model_name = device_data.get("model_name", "TIS Device")
        device_name = device_data.get("name", f"{model_name} ({subnet}.{device_id})")
        
        # Check if device has HVAC/climate support
        platforms = get_device_platforms(model_name)
        hvac_channels = get_platform_channel_count(model_name, "hvac")
        
        if hvac_channels > 0:
            _LOGGER.info(f"Creating {hvac_channels} climate entities for {model_name} ({subnet}.{device_id})")
            
            for ac_number in range(1, hvac_channels + 1):
                climate_entity = TISClimate(
                    hass,
                    entry,
                    unique_id,
                    device_name,
                    model_name,
                    subnet,
                    device_id,
                    ac_number,
                    gateway_ip,
                    udp_port,
                )
                entities.append(climate_entity)
    
    if entities:
        async_add_entities(entities)
        _LOGGER.info(f"Added {len(entities)} TIS climate entities")


class TISClimate(ClimateEntity):
    """Representation of a TIS climate device (AC/HVAC)."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.HEAT,
        HVACMode.FAN_ONLY,
        HVACMode.AUTO,
    ]
    _attr_fan_modes = [FAN_AUTO, FAN_HIGH, FAN_MEDIUM, FAN_LOW]
    _attr_min_temp = 16
    _attr_max_temp = 30
    _attr_target_temperature_step = 1

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        unique_id: str,
        device_name: str,
        model_name: str,
        subnet: int,
        device_id: int,
        ac_number: int,
        gateway_ip: str,
        udp_port: int,
    ) -> None:
        """Initialize the climate device."""
        self.hass = hass
        self._entry = entry
        self._unique_id_prefix = unique_id
        self._device_name = device_name
        self._model_name = model_name
        self._subnet = subnet
        self._device_id = device_id
        self._ac_number = ac_number
        self._gateway_ip = gateway_ip
        self._udp_port = udp_port
        
        self._attr_name = f"{device_name} AC{ac_number}"
        self._attr_unique_id = f"{unique_id}_climate_ac{ac_number}"
        
        # State
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_fan_mode = FAN_AUTO
        self._attr_target_temperature = 24
        self._attr_current_temperature = None
        
        self._listener = None
        
        # Device info - group all entities under same device
        self._attr_device_info = {
            "identifiers": {("tis", unique_id)},
            "name": device_name,
            "manufacturer": "TIS",
            "model": model_name,
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to event bus for climate feedback."""
        @callback
        def handle_climate_feedback(event):
            """Handle climate feedback event from __init__.py"""
            data = event.data
            
            # Check if event is for this device and AC unit
            if (data.get("subnet") == self._subnet and 
                data.get("device") == self._device_id and
                data.get("ac_number") == self._ac_number):
                
                # Update state
                state = data.get("state")
                if state == 0:
                    self._attr_hvac_mode = HVACMode.OFF
                else:
                    # Get mode from feedback
                    mode = data.get("mode")
                    self._attr_hvac_mode = TIS_HVAC_MODES.get(mode, HVACMode.AUTO)
                
                # Update temperature
                temperature = data.get("temperature")
                if temperature is not None:
                    self._attr_target_temperature = temperature
                
                # Update fan mode
                fan_speed = data.get("fan_speed")
                if fan_speed is not None:
                    self._attr_fan_mode = TIS_FAN_MODES.get(fan_speed, FAN_AUTO)
                
                self.async_write_ha_state()
                _LOGGER.info(f"Updated {self._attr_name}: {self._attr_hvac_mode}, {self._attr_target_temperature}°C, Fan={self._attr_fan_mode}")
        
        self._listener = self.hass.bus.async_listen("tis_climate_feedback", handle_climate_feedback)
        
        # Query initial state
        await self.async_update()

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        if self._listener:
            self._listener()
            self._listener = None

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new HVAC mode."""
        _LOGGER.info(f"{self._attr_name}: Setting HVAC mode to {hvac_mode}")
        
        if hvac_mode == HVACMode.OFF:
            # Turn off AC
            await self._send_ac_control(state=0)
        else:
            # Turn on with specific mode
            tis_mode = HVAC_MODE_TO_TIS.get(hvac_mode, 3)  # Default to AUTO
            await self._send_ac_control(state=1, mode=tis_mode)
        
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        
        temperature = int(temperature)
        _LOGGER.info(f"{self._attr_name}: Setting temperature to {temperature}°C")
        
        # If currently OFF, turn on with last mode
        if self._attr_hvac_mode == HVACMode.OFF:
            self._attr_hvac_mode = HVACMode.AUTO
        
        await self._send_ac_control(state=1, temperature=temperature)
        
        self._attr_target_temperature = temperature
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set new fan mode."""
        _LOGGER.info(f"{self._attr_name}: Setting fan mode to {fan_mode}")
        
        tis_fan_speed = FAN_MODE_TO_TIS.get(fan_mode, 0)  # Default to AUTO
        await self._send_ac_control(state=1, fan_speed=tis_fan_speed)
        
        self._attr_fan_mode = fan_mode
        self.async_write_ha_state()

    async def async_turn_on(self) -> None:
        """Turn on AC."""
        _LOGGER.info(f"{self._attr_name}: Turning ON")
        await self.async_set_hvac_mode(HVACMode.AUTO)

    async def async_turn_off(self) -> None:
        """Turn off AC."""
        _LOGGER.info(f"{self._attr_name}: Turning OFF")
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_update(self) -> None:
        """Query AC status using OpCode 0xE0EC"""
        try:
            # Create AC query packet
            packet_obj = TISPacket.create_ac_query_packet(
                self._subnet, 
                self._device_id, 
                self._ac_number
            )
            packet_bytes = packet_obj.build()
            
            # Send via UDP
            client = TISUDPClient(self._gateway_ip, self._udp_port)
            await client.async_connect()
            client.send_to(packet_bytes, self._gateway_ip)
            client.close()
            
            _LOGGER.debug(f"Sent AC query to {self._subnet}.{self._device_id} AC{self._ac_number}")
        except Exception as e:
            _LOGGER.error(f"Error querying AC status: {e}")

    async def _send_ac_control(
        self, 
        state: int = 1, 
        temperature: int | None = None,
        mode: int | None = None,
        fan_speed: int | None = None
    ) -> None:
        """Send AC control packet using OpCode 0xE0EE"""
        try:
            # Use current values if not provided
            if temperature is None:
                temperature = int(self._attr_target_temperature)
            if mode is None:
                mode = HVAC_MODE_TO_TIS.get(self._attr_hvac_mode, 3)
            if fan_speed is None:
                fan_speed = FAN_MODE_TO_TIS.get(self._attr_fan_mode, 0)
            
            # Create AC control packet
            packet_obj = TISPacket.create_ac_control_packet(
                self._subnet,
                self._device_id,
                self._ac_number,
                state,
                temperature,
                mode,
                fan_speed
            )
            packet_bytes = packet_obj.build()
            
            # Send via UDP
            client = TISUDPClient(self._gateway_ip, self._udp_port)
            await client.async_connect()
            client.send_to(packet_bytes, self._gateway_ip)
            client.close()
            
            _LOGGER.info(f"Sent AC control to {self._subnet}.{self._device_id} AC{self._ac_number}: "
                        f"State={state}, Temp={temperature}°C, Mode={mode}, Fan={fan_speed}")
        except Exception as e:
            _LOGGER.error(f"Error sending AC control: {e}")
