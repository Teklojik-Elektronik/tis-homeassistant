"""Support for TIS sensors."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfLength,
    UnitOfTemperature,
    LIGHT_LUX,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TISDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TIS sensors based on a config entry."""
    # Store the add_entities callback for dynamic entity creation
    entry_data = hass.data[DOMAIN][entry.entry_id]
    entry_data["sensor_add_entities"] = async_add_entities
    entry_data["sensor_created_devices"] = set()  # Track created devices
    
    _LOGGER.info("TIS Sensor platform ready for dynamic entity creation")


class TISTemperatureSensor(CoordinatorEntity[TISDataUpdateCoordinator], SensorEntity):
    """Representation of a TIS temperature sensor."""

    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_temperature"
        self._attr_name = f"{entry.title} Temperature"
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "TIS",
            "model": "TIS Control Device",
        }

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            sensors = self.coordinator.data.get("sensors", {})
            return sensors.get("temperature")
        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if self.coordinator.data:
            status = self.coordinator.data.get("status", {})
            return status.get("online", False)
        return False


class TISHumiditySensor(CoordinatorEntity[TISDataUpdateCoordinator], SensorEntity):
    """Representation of a TIS humidity sensor."""

    def __init__(
        self,
        coordinator: TISDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_humidity"
        self._attr_name = f"{entry.title} Humidity"
        self._attr_native_unit_of_measurement = PERCENTAGE
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "manufacturer": "TIS",
            "model": "TIS Control Device",
        }

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            sensors = self.coordinator.data.get("sensors", {})
            return sensors.get("humidity")
        return None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        if self.coordinator.data:
            status = self.coordinator.data.get("status", {})
            return status.get("online", False)
        return False


class TISMotionDistanceSensor(SensorEntity):
    """Representation of a TIS radar motion distance sensor."""

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.CENTIMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        subnet: int,
        device_id: int,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self.entry = entry
        self.subnet = subnet
        self.device_id = device_id
        self.device_key = (subnet, device_id)
        
        self._attr_unique_id = f"{entry.entry_id}_motion_distance_{subnet}_{device_id}"
        self._attr_name = f"{entry.title} Motion Distance"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{subnet}_{device_id}")},
            "name": f"{entry.title} ({subnet}.{device_id})",
            "manufacturer": "TIS",
            "model": "TIS-OS-MMV2-IRE",
        }
        self._value = 0
        self._available = False

    async def async_added_to_hass(self) -> None:
        """Register callback when entity is added."""
        entry_data = self.hass.data[DOMAIN][self.entry.entry_id]
        
        async def radar_callback(radar_data: dict):
            """Update entity when new radar data received."""
            target_count = radar_data.get("target_count", 0)
            if target_count >= 3:  # Motion only valid when 3+ targets
                self._value = radar_data.get("motion_distance_cm", 0)
            else:
                self._value = 0
            self._available = True
            self.async_write_ha_state()
        
        entry_data.setdefault("radar_callbacks", {})[self.device_key] = radar_callback

    @property
    def native_value(self) -> float | None:
        """Return the motion distance in centimeters."""
        return self._value

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available


class TISStationaryDistanceSensor(SensorEntity):
    """Representation of a TIS radar stationary distance sensor."""

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_native_unit_of_measurement = UnitOfLength.CENTIMETERS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        subnet: int,
        device_id: int,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self.entry = entry
        self.subnet = subnet
        self.device_id = device_id
        self.device_key = (subnet, device_id)
        
        self._attr_unique_id = f"{entry.entry_id}_stationary_distance_{subnet}_{device_id}"
        self._attr_name = f"{entry.title} Stationary Distance"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{subnet}_{device_id}")},
            "name": f"{entry.title} ({subnet}.{device_id})",
            "manufacturer": "TIS",
            "model": "TIS-OS-MMV2-IRE",
        }
        self._value = 0
        self._available = False

    async def async_added_to_hass(self) -> None:
        """Register callback when entity is added."""
        entry_data = self.hass.data[DOMAIN][self.entry.entry_id]
        
        async def radar_callback(radar_data: dict):
            """Update entity when new radar data received."""
            self._value = radar_data.get("stationary_distance_cm", 0)
            self._available = True
            self.async_write_ha_state()
        
        entry_data.setdefault("radar_callbacks", {})[self.device_key] = radar_callback

    @property
    def native_value(self) -> float | None:
        """Return the stationary distance in centimeters."""
        return self._value

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available


class TISTargetCountSensor(SensorEntity):
    """Representation of a TIS radar target count sensor."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        subnet: int,
        device_id: int,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self.entry = entry
        self.subnet = subnet
        self.device_id = device_id
        self.device_key = (subnet, device_id)
        
        self._attr_unique_id = f"{entry.entry_id}_target_count_{subnet}_{device_id}"
        self._attr_name = f"{entry.title} Target Count"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{subnet}_{device_id}")},
            "name": f"{entry.title} ({subnet}.{device_id})",
            "manufacturer": "TIS",
            "model": "TIS-OS-MMV2-IRE",
        }
        self._value = 0
        self._available = False

    async def async_added_to_hass(self) -> None:
        """Register callback when entity is added."""
        entry_data = self.hass.data[DOMAIN][self.entry.entry_id]
        
        async def radar_callback(radar_data: dict):
            """Update entity when new radar data received."""
            self._value = radar_data.get("target_count", 0)
            self._available = True
            self.async_write_ha_state()
        
        entry_data.setdefault("radar_callbacks", {})[self.device_key] = radar_callback

    @property
    def native_value(self) -> int | None:
        """Return the number of detected targets."""
        return self._value

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available


class TISMotionStateSensor(SensorEntity):
    """Representation of a TIS radar motion state sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        subnet: int,
        device_id: int,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self.entry = entry
        self.subnet = subnet
        self.device_id = device_id
        self.device_key = (subnet, device_id)
        
        self._attr_unique_id = f"{entry.entry_id}_motion_state_{subnet}_{device_id}"
        self._attr_name = f"{entry.title} Motion State"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{subnet}_{device_id}")},
            "name": f"{entry.title} ({subnet}.{device_id})",
            "manufacturer": "TIS",
            "model": "TIS-OS-MMV2-IRE",
        }
        self._value = "unknown"
        self._state_raw = 0
        self._available = False

    async def async_added_to_hass(self) -> None:
        """Register callback when entity is added."""
        entry_data = self.hass.data[DOMAIN][self.entry.entry_id]
        
        async def radar_callback(radar_data: dict):
            """Update entity when new radar data received."""
            self._value = radar_data.get("state", "unknown")
            self._state_raw = radar_data.get("state_raw", 0)
            self._available = True
            self.async_write_ha_state()
        
        entry_data.setdefault("radar_callbacks", {})[self.device_key] = radar_callback

    @property
    def native_value(self) -> str | None:
        """Return the motion state (idle/motion/occupancy/occupancy_strong)."""
        return self._value

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the state attributes."""
        return {
            "state_raw": self._state_raw,
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available


class TISLuxSensor(SensorEntity):
    """Representation of a TIS LUX/illuminance sensor."""

    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_native_unit_of_measurement = LIGHT_LUX
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        subnet: int,
        device_id: int,
    ) -> None:
        """Initialize the sensor."""
        self.hass = hass
        self.entry = entry
        self.subnet = subnet
        self.device_id = device_id
        self.device_key = (subnet, device_id)
        
        self._attr_unique_id = f"{entry.entry_id}_illuminance_{subnet}_{device_id}"
        self._attr_name = f"{entry.title} Room Brightness"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{subnet}_{device_id}")},
            "name": f"{entry.title} ({subnet}.{device_id})",
            "manufacturer": "TIS",
            "model": "TIS-OS-MMV2-IRE",
        }
        self._value = None
        self._threshold_low = 0
        self._threshold_high = 0
        self._available = False

    async def async_added_to_hass(self) -> None:
        """Register callback when entity is added."""
        entry_data = self.hass.data[DOMAIN][self.entry.entry_id]
        
        async def lux_callback(lux_data: dict):
            """Update entity when new LUX data received."""
            self._value = lux_data.get("lux", 0)
            self._threshold_low = lux_data.get("threshold_low", 0)
            self._threshold_high = lux_data.get("threshold_high", 0)
            self._available = True
            self.async_write_ha_state()
        
        entry_data.setdefault("lux_callbacks", {})[self.device_key] = lux_callback

    @property
    def native_value(self) -> float | None:
        """Return the illuminance in lux."""
        return self._value

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the state attributes."""
        return {
            "threshold_low": self._threshold_low,
            "threshold_high": self._threshold_high,
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available
