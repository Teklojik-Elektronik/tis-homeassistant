"""Support for TIS sensors (temperature, humidity, energy, etc.)."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfTemperature,
    PERCENTAGE,
    UnitOfPower,
    UnitOfEnergy,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, HEALTH_SENSOR_TYPES, ENERGY_SENSOR_TYPES
from .device_appliance_mapping import get_device_platforms, get_platform_channel_count

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TIS sensors from addon devices.json."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    devices = entry_data["devices"]
    gateway_ip = entry_data["gateway_ip"]
    udp_port = entry_data["udp_port"]
    
    _LOGGER.info(f"Setting up TIS sensor entities")
    
    entities = []
    for unique_id, device_data in devices.items():
        subnet = device_data.get("subnet")
        device_id = device_data.get("device_id")
        model_name = device_data.get("model_name", "TIS Device")
        device_name = device_data.get("name", f"{model_name} ({subnet}.{device_id})")
        
        # Get supported platforms from device mapping
        platforms = get_device_platforms(model_name)
        health_channels = get_platform_channel_count(model_name, "health_sensor")
        energy_channels = get_platform_channel_count(model_name, "energy_sensor")
        temp_channels = get_platform_channel_count(model_name, "temperature_sensor")
        lux_channels = get_platform_channel_count(model_name, "lux_sensor")
        analog_channels = get_platform_channel_count(model_name, "analog_sensor")
        
        # Check if device has any sensor support
        has_sensors = health_channels > 0 or energy_channels > 0 or temp_channels > 0 or lux_channels > 0 or analog_channels > 0
        
        if has_sensors:
            # Health sensor (temperature, humidity, CO2, VOC, etc.)
            if health_channels > 0:
                for sensor_key, sensor_name in HEALTH_SENSOR_TYPES.items():
                    sensor_entity = TISHealthSensor(
                        hass,
                        entry,
                        unique_id,
                        device_name,
                        model_name,
                        subnet,
                        device_id,
                        gateway_ip,
                        udp_port,
                        sensor_key,
                        sensor_name,
                    )
                    entities.append(sensor_entity)
            
            # Energy meter
            if energy_channels > 0:
                for sensor_key, sensor_name in ENERGY_SENSOR_TYPES.items():
                    sensor_entity = TISEnergySensor(
                        hass,
                        entry,
                        unique_id,
                        device_name,
                        model_name,
                        subnet,
                        device_id,
                        gateway_ip,
                        udp_port,
                        sensor_key,
                        sensor_name,
                    )
                    entities.append(sensor_entity)
            
            # Temperature sensor
            if temp_channels > 0:
                channels = temp_channels
                for channel in range(1, channels + 1):
                    sensor_entity = TISTemperatureSensor(
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
                    entities.append(sensor_entity)
    
    if entities:
        async_add_entities(entities)
        _LOGGER.info(f"Added {len(entities)} TIS sensor entities")


class TISTemperatureSensor(SensorEntity):
    """Representation of a TIS temperature sensor."""

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
        """Initialize the sensor."""
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
        
        self._attr_name = f"{device_name} Temperature CH{channel}"
        self._attr_unique_id = f"{unique_id}_temp_ch{channel}"
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_native_value = None
        
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
                
                # Temperature feedback
                if packet_data.get("feedback_type") == "temp_feedback":
                    if packet_data.get("channel") == self._channel:
                        self._attr_native_value = packet_data.get("temperature")
                        self.async_write_ha_state()
        
        self._listener = self.hass.bus.async_listen("tis_udp_packet", handle_udp_event)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        if self._listener:
            self._listener()
            self._listener = None


class TISHealthSensor(SensorEntity):
    """Representation of a TIS health sensor (temp, humidity, CO2, VOC, noise, lux)."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        unique_id: str,
        device_name: str,
        model_name: str,
        subnet: int,
        device_id: int,
        gateway_ip: str,
        udp_port: int,
        sensor_key: str,
        sensor_name: str,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry = entry
        self._unique_id_prefix = unique_id
        self._device_name = device_name
        self._model_name = model_name
        self._subnet = subnet
        self._device_id = device_id
        self._gateway_ip = gateway_ip
        self._udp_port = udp_port
        self._sensor_key = sensor_key
        
        self._attr_name = f"{device_name} {sensor_name}"
        self._attr_unique_id = f"{unique_id}_health_{sensor_key}"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_value = None
        
        # Set device class and unit based on sensor type
        if sensor_key == "temp":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        elif sensor_key == "humidity":
            self._attr_device_class = SensorDeviceClass.HUMIDITY
            self._attr_native_unit_of_measurement = PERCENTAGE
        elif sensor_key == "eco2_state":
            self._attr_device_class = SensorDeviceClass.CO2
            self._attr_native_unit_of_measurement = "ppm"
        elif sensor_key == "lux":
            self._attr_device_class = SensorDeviceClass.ILLUMINANCE
            self._attr_native_unit_of_measurement = "lx"
        
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
                
                # Health sensor feedback
                if packet_data.get("feedback_type") == "health_feedback":
                    if self._sensor_key in packet_data:
                        self._attr_native_value = packet_data.get(self._sensor_key)
                        self.async_write_ha_state()
        
        self._listener = self.hass.bus.async_listen("tis_udp_packet", handle_udp_event)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        if self._listener:
            self._listener()
            self._listener = None


class TISEnergySensor(SensorEntity):
    """Representation of a TIS energy meter sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        unique_id: str,
        device_name: str,
        model_name: str,
        subnet: int,
        device_id: int,
        gateway_ip: str,
        udp_port: int,
        sensor_key: str,
        sensor_name: str,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self._entry = entry
        self._unique_id_prefix = unique_id
        self._device_name = device_name
        self._model_name = model_name
        self._subnet = subnet
        self._device_id = device_id
        self._gateway_ip = gateway_ip
        self._udp_port = udp_port
        self._sensor_key = sensor_key
        
        self._attr_name = f"{device_name} {sensor_name}"
        self._attr_unique_id = f"{unique_id}_energy_{sensor_key}"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_value = None
        
        # Set device class and unit based on sensor type
        if "voltage" in sensor_key.lower() or sensor_key.startswith("v"):
            self._attr_device_class = SensorDeviceClass.VOLTAGE
            self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
        elif "current" in sensor_key.lower():
            self._attr_device_class = SensorDeviceClass.CURRENT
            self._attr_native_unit_of_measurement = UnitOfElectricCurrent.AMPERE
        elif "power" in sensor_key.lower() or "active" in sensor_key.lower():
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_native_unit_of_measurement = UnitOfPower.WATT
        elif "energy" in sensor_key.lower():
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        elif "pf" in sensor_key.lower():
            self._attr_device_class = SensorDeviceClass.POWER_FACTOR
            self._attr_native_unit_of_measurement = PERCENTAGE
        elif "frq" in sensor_key.lower():
            self._attr_device_class = SensorDeviceClass.FREQUENCY
            self._attr_native_unit_of_measurement = "Hz"
        
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
                
                # Energy sensor feedback
                if packet_data.get("feedback_type") == "energy_feedback":
                    if self._sensor_key in packet_data:
                        self._attr_native_value = packet_data.get(self._sensor_key)
                        self.async_write_ha_state()
        
        self._listener = self.hass.bus.async_listen("tis_udp_packet", handle_udp_event)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        if self._listener:
            self._listener()
            self._listener = None
