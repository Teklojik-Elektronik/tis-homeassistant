"""Support for TIS weather station entities."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.weather import (
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfTemperature,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfPrecipitationDepth,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval

from .const import DOMAIN
from .device_appliance_mapping import get_device_platforms, get_platform_channel_count

_LOGGER = logging.getLogger(__name__)

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=30)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TIS weather station entities from config entry."""
    gateway_ip = entry.data.get("gateway_ip", "192.168.1.200")
    udp_port = entry.data.get("udp_port", 6000)
    devices = hass.data[DOMAIN].get("devices", {})
    
    entities = []
    for unique_id, device_data in devices.items():
        subnet = device_data.get("subnet")
        device_id = device_data.get("device_id")
        model_name = device_data.get("model_name", "TIS Device")
        device_name = device_data.get("name", f"{model_name} ({subnet}.{device_id})")
        
        # Check if device is a weather station
        if model_name in ["TIS-WS-71", "TIS-WEATHER-STATION"]:
            _LOGGER.info(f"Creating weather station entity for {model_name} ({subnet}.{device_id})")
            
            weather_entity = TISWeatherStation(
                device_name,
                unique_id,
                model_name,
                subnet,
                device_id,
                gateway_ip,
                udp_port,
                hass,
            )
            entities.append(weather_entity)
    
    if entities:
        async_add_entities(entities, update_before_add=True)


class TISWeatherStation(WeatherEntity):
    """Representation of TIS Weather Station."""
    
    def __init__(
        self,
        device_name: str,
        unique_id: str,
        model_name: str,
        subnet: int,
        device_id: int,
        gateway_ip: str,
        udp_port: int,
        hass: HomeAssistant,
    ) -> None:
        """Initialize weather station."""
        self._subnet = subnet
        self._device_id = device_id
        self._gateway_ip = gateway_ip
        self._udp_port = udp_port
        self.hass = hass
        
        self._attr_name = f"{device_name} Weather"
        self._attr_unique_id = f"{unique_id}_weather"
        
        # Weather data
        self._attr_native_temperature = None
        self._attr_native_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_humidity = None
        self._attr_native_wind_speed = None
        self._attr_native_wind_speed_unit = UnitOfSpeed.KILOMETERS_PER_HOUR
        self._attr_wind_bearing = None
        self._attr_native_pressure = None
        self._attr_native_pressure_unit = UnitOfPressure.HPA
        self._attr_uv_index = None
        self._attr_condition = None
        
        self._listener = None
        self._update_interval = SCAN_INTERVAL
        
        # Device info
        self._attr_device_info = {
            "identifiers": {("tis", unique_id)},
            "name": device_name,
            "manufacturer": "TIS",
            "model": model_name,
        }
        
        # Supported features
        self._attr_supported_features = 0
    
    async def async_added_to_hass(self) -> None:
        """Subscribe to weather feedback events."""
        @callback
        def handle_weather_feedback(event):
            """Handle weather feedback event from __init__.py"""
            data = event.data
            
            # Check if event is for this device
            if (data.get("subnet") == self._subnet and 
                data.get("device") == self._device_id):
                
                # Update weather data
                if "temperature" in data:
                    self._attr_native_temperature = data["temperature"]
                if "humidity" in data:
                    self._attr_humidity = data["humidity"]
                if "wind_speed" in data:
                    self._attr_native_wind_speed = data["wind_speed"]
                if "wind_bearing" in data:
                    self._attr_wind_bearing = data["wind_bearing"]
                if "pressure" in data:
                    self._attr_native_pressure = data["pressure"]
                if "uv_index" in data:
                    self._attr_uv_index = data["uv_index"]
                if "condition" in data:
                    self._attr_condition = data["condition"]
                
                self.async_write_ha_state()
                _LOGGER.info(f"☁️ Updated {self._attr_name}: Temp={self._attr_native_temperature}°C, "
                           f"Humidity={self._attr_humidity}%, UV={self._attr_uv_index}")
        
        self._listener = self.hass.bus.async_listen("tis_weather_feedback", handle_weather_feedback)
        
        # Start periodic updates
        async_track_time_interval(self.hass, self.async_update, self._update_interval)
        
        # Query initial state
        await self.async_update()
    
    async def async_will_remove_from_hass(self) -> None:
        """Unsubscribe when removed."""
        if self._listener:
            self._listener()
            self._listener = None
    
    @property
    def name(self) -> str:
        """Return the name of the weather station."""
        return self._attr_name
    
    @property
    def native_temperature(self) -> float | None:
        """Return the temperature."""
        return self._attr_native_temperature
    
    @property
    def native_temperature_unit(self) -> str:
        """Return the temperature unit."""
        return self._attr_native_temperature_unit
    
    @property
    def humidity(self) -> float | None:
        """Return the humidity."""
        return self._attr_humidity
    
    @property
    def native_wind_speed(self) -> float | None:
        """Return the wind speed."""
        return self._attr_native_wind_speed
    
    @property
    def wind_bearing(self) -> float | None:
        """Return the wind bearing."""
        return self._attr_wind_bearing
    
    @property
    def native_pressure(self) -> float | None:
        """Return the pressure."""
        return self._attr_native_pressure
    
    @property
    def uv_index(self) -> float | None:
        """Return the UV index."""
        return self._attr_uv_index
    
    @property
    def condition(self) -> str | None:
        """Return the weather condition."""
        return self._attr_condition
    
    async def async_update(self, *args: Any) -> None:
        """Query weather station state."""
        try:
            ip_bytes = bytes(map(int, self._gateway_ip.split('.')))
            
            # Create weather update query packet (0x2020)
            packet_obj = TISPacket.create_weather_query_packet(
                self._subnet,
                self._device_id
            )
            tis_data = packet_obj.build()
            full_packet = ip_bytes + b'SMARTCLOUD' + tis_data
            
            client = TISUDPClient(self._gateway_ip, self._udp_port)
            await client.async_connect()
            client.send_to(full_packet, self._gateway_ip)
            client.close()
            
            _LOGGER.debug(f"☁️ Queried weather: {self._subnet}.{self._device_id}")
        except Exception as e:
            _LOGGER.error(f"Error querying weather: {e}", exc_info=True)
