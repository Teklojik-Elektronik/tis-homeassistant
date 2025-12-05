"""Support for TIS sensors."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import TISDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TIS sensors based on a config entry."""
    coordinator: TISDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Add sensors based on available data
    entities = []
    
    # Check if device provides sensor data
    if coordinator.data and coordinator.data.get("sensors"):
        sensors = coordinator.data["sensors"]
        
        if "temperature" in sensors:
            entities.append(TISTemperatureSensor(coordinator, entry))
        
        if "humidity" in sensors:
            entities.append(TISHumiditySensor(coordinator, entry))

    async_add_entities(entities)


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
