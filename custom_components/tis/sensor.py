"""Support for TIS sensors (temperature, humidity, energy, etc.)."""
from __future__ import annotations

import logging
from typing import Any
from datetime import timedelta

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
from homeassistant.helpers.event import async_track_time_interval

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
    
    _LOGGER.info(f"Setting up TIS sensor entities from {len(devices)} devices")
    
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
            _LOGGER.info(f"Device {model_name} ({subnet}.{device_id}) - Sensors: health={health_channels}, energy={energy_channels}, temp={temp_channels}, lux={lux_channels}, analog={analog_channels}")
            
            # Health sensor (temperature, humidity, CO2, VOC, etc.)
            if health_channels > 0:
                _LOGGER.debug(f"Creating {len(HEALTH_SENSOR_TYPES)} health sensors for {model_name}")
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
        
        # Device info - group all sensors under same device
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
                
                # Temperature feedback
                if packet_data.get("feedback_type") == "temp_feedback":
                    if packet_data.get("channel") == self._channel:
                        self._attr_native_value = packet_data.get("temperature")
                        self.async_write_ha_state()
        
        self._listener = self.hass.bus.async_listen("tis_udp_packet", handle_udp_event)
        
        # Start periodic query (every 30 seconds)
        async def periodic_update(now):
            """Periodic query for temperature sensor data."""
            await self.async_update()
        
        # Query immediately on startup
        await self.async_update()
        
        # Schedule periodic updates every 30 seconds
        self._update_unsub = async_track_time_interval(
            self.hass,
            periodic_update,
            timedelta(seconds=30)
        )
        
        _LOGGER.info(f"Started periodic updates for {self._attr_name} (every 30s)")
    
    async def async_update(self) -> None:
        """Query temperature sensor data using OpCode 0xE3E7"""
        from .tis_protocol import TISPacket, TISUDPClient
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
            
            # Create temperature query packet
            packet_obj = TISPacket.create_temp_query_packet(self._subnet, self._device_id)
            tis_data = packet_obj.build()
            full_packet = ip_bytes + b'SMARTCLOUD' + tis_data
            
            # Send via UDP
            client = TISUDPClient(self._gateway_ip, self._udp_port)
            await client.async_connect()
            client.send_to(full_packet, self._gateway_ip)
            client.close()
            
            _LOGGER.info(f"🌡️ Sent temperature query to {self._subnet}.{self._device_id} CH{self._channel} (OpCode 0xE3E7)")
        except Exception as e:
            _LOGGER.error(f"Error querying temperature sensor: {e}", exc_info=True)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        if self._listener:
            self._listener()
            self._listener = None
        
        # Cancel periodic updates
        if hasattr(self, '_update_unsub') and self._update_unsub:
            self._update_unsub()
            self._update_unsub = None


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
        self._attr_native_value = None
        
        # Set state_class for measurement sensors only (not for state indicators)
        if sensor_key not in ["eco2_state", "tvoc_state", "co_state"]:
            self._attr_state_class = SensorStateClass.MEASUREMENT
        
        # Set device class and unit based on sensor type (TISControlProtocol format)
        if sensor_key == "temp":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        elif sensor_key == "humidity":
            self._attr_device_class = SensorDeviceClass.HUMIDITY
            self._attr_native_unit_of_measurement = PERCENTAGE
        elif sensor_key == "eco2":
            self._attr_device_class = SensorDeviceClass.CO2
            self._attr_native_unit_of_measurement = "ppm"
            self._attr_icon = "mdi:molecule-co2"
        elif sensor_key == "tvoc":
            self._attr_device_class = SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS
            self._attr_native_unit_of_measurement = "ppb"
            self._attr_icon = "mdi:air-filter"
        elif sensor_key == "co":
            self._attr_device_class = SensorDeviceClass.CO
            self._attr_native_unit_of_measurement = "ppm"
            self._attr_icon = "mdi:molecule-co"
        elif sensor_key == "eco2_state":
            self._attr_native_unit_of_measurement = None
            self._attr_icon = "mdi:molecule-co2"
        elif sensor_key == "tvoc_state":
            self._attr_native_unit_of_measurement = None
            self._attr_icon = "mdi:air-filter"
        elif sensor_key == "co_state":
            self._attr_native_unit_of_measurement = None
            self._attr_icon = "mdi:molecule-co"
        elif sensor_key == "lux":
            self._attr_device_class = SensorDeviceClass.ILLUMINANCE
            self._attr_native_unit_of_measurement = "lx"
        elif sensor_key == "noise":
            self._attr_native_unit_of_measurement = "dB"
            self._attr_icon = "mdi:volume-high"
        
        self._listener = None
        
        # Device info - group all sensors under same device
        self._attr_device_info = {
            "identifiers": {("tis", unique_id)},
            "name": device_name,
            "manufacturer": "TIS",
            "model": model_name,
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to event bus for health sensor feedback."""
        @callback
        def handle_health_feedback(event):
            """Handle health sensor feedback event from __init__.py"""
            data = event.data
            
            # Check if event is for this device
            if data.get("subnet") == self._subnet and data.get("device") == self._device_id:
                # Map sensor_key to event data keys
                # Supports both raw values (ppm/ppb) and state indicators (0-5)
                value_map = {
                    "temp": data.get("temperature"),
                    "humidity": data.get("humidity"),
                    "lux": data.get("lux"),
                    "noise": data.get("noise"),
                    "eco2": data.get("eco2"),              # Raw eCO2 (ppm)
                    "tvoc": data.get("tvoc"),              # Raw TVOC (ppb)
                    "co": data.get("co"),                  # Raw CO (ppm)
                    "eco2_state": data.get("eco2_state"),  # State (0-5)
                    "tvoc_state": data.get("tvoc_state"),  # State (0-5)
                    "co_state": data.get("co_state"),      # State (0-5)
                }
                
                if self._sensor_key in value_map:
                    new_value = value_map[self._sensor_key]
                    if new_value is not None:
                        self._attr_native_value = new_value
                        self.async_write_ha_state()
                        _LOGGER.debug(f"Updated {self._attr_name} = {new_value}")
        
        self._listener = self.hass.bus.async_listen("tis_health_feedback", handle_health_feedback)
        
        # Start periodic query (every 30 seconds like original integration)
        async def periodic_update(now):
            """Periodic query for health sensor data."""
            await self.async_update()
        
        # Query immediately on startup
        await self.async_update()
        
        # Schedule periodic updates every 30 seconds
        self._update_unsub = async_track_time_interval(
            self.hass,
            periodic_update,
            timedelta(seconds=30)
        )
        
        _LOGGER.info(f"Started periodic updates for {self._attr_name} (every 30s)")
    
    async def async_update(self) -> None:
        """Query health sensor data using OpCode 0x2024"""
        from .tis_protocol import TISPacket, TISUDPClient
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
            
            # Create health query packet
            packet_obj = TISPacket.create_health_query_packet(self._subnet, self._device_id)
            tis_data = packet_obj.build()
            full_packet = ip_bytes + b'SMARTCLOUD' + tis_data
            
            # Send via UDP
            client = TISUDPClient(self._gateway_ip, self._udp_port)
            await client.async_connect()
            client.send_to(full_packet, self._gateway_ip)
            client.close()
            
            _LOGGER.info(f"📡 Sent health query to {self._subnet}.{self._device_id} (OpCode 0x2024)")
        except Exception as e:
            _LOGGER.error(f"Error querying health sensor: {e}", exc_info=True)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        if self._listener:
            self._listener()
            self._listener = None
        
        # Cancel periodic updates
        if hasattr(self, '_update_unsub') and self._update_unsub:
            self._update_unsub()
            self._update_unsub = None


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
        
        # Device info - group all sensors under same device
        self._attr_device_info = {
            "identifiers": {("tis", unique_id)},
            "name": device_name,
            "manufacturer": "TIS",
            "model": model_name,
        }

    async def async_added_to_hass(self) -> None:
        """Subscribe to event bus for energy meter feedback."""
        @callback
        def handle_energy_feedback(event):
            """Handle energy feedback event from __init__.py"""
            data = event.data
            
            # Check if event is for this device
            if data.get("subnet") == self._subnet and data.get("device") == self._device_id:
                # Update sensor value based on sensor_key
                value_map = {
                    "v": data.get("voltage"),
                    "voltage": data.get("voltage"),
                    "i": data.get("current"),
                    "current": data.get("current"),
                    "active_power": data.get("power"),
                    "power": data.get("power"),
                    "kwh": data.get("energy"),
                    "energy": data.get("energy")
                }
                
                if self._sensor_key in value_map:
                    new_value = value_map[self._sensor_key]
                    if new_value is not None:
                        self._attr_native_value = new_value
                        self.async_write_ha_state()
                        _LOGGER.debug(f"Updated {self._attr_name} = {new_value}")
        
        self._listener = self.hass.bus.async_listen("tis_energy_feedback", handle_energy_feedback)
        
        # Start periodic query (every 30 seconds like original integration)
        async def periodic_update(now):
            """Periodic query for energy meter data."""
            await self.async_update()
        
        # Query immediately on startup
        await self.async_update()
        
        # Schedule periodic updates every 30 seconds
        self._update_unsub = async_track_time_interval(
            self.hass,
            periodic_update,
            timedelta(seconds=30)
        )
        
        _LOGGER.info(f"Started periodic updates for {self._attr_name} (every 30s)")
    
    async def async_update(self) -> None:
        """Query energy meter data using OpCode 0x2010"""
        from .tis_protocol import TISPacket, TISUDPClient
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
            
            # Create energy query packet (channel 1, current values)
            packet_obj = TISPacket.create_energy_query_packet(self._subnet, self._device_id, channel=1, query_type='current')
            tis_data = packet_obj.build()
            full_packet = ip_bytes + b'SMARTCLOUD' + tis_data
            
            # Send via UDP
            client = TISUDPClient(self._gateway_ip, self._udp_port)
            await client.async_connect()
            client.send_to(full_packet, self._gateway_ip)
            client.close()
            
            _LOGGER.info(f"⚡ Sent energy query to {self._subnet}.{self._device_id} (OpCode 0x2010)")
        except Exception as e:
            _LOGGER.error(f"Error querying energy meter: {e}", exc_info=True)

    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        if self._listener:
            self._listener()
            self._listener = None
        
        # Cancel periodic updates
        if hasattr(self, '_update_unsub') and self._update_unsub:
            self._update_unsub()
            self._update_unsub = None
