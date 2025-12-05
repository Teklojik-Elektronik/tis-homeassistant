"""Support for TIS binary sensors (motion detection)."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
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
    """Set up TIS binary sensors based on a config entry."""
    from .const import CONF_SUBNET, CONF_DEVICE
    
    # Check if this is a radar sensor device
    # For now, we'll create entities for all devices and let them show as unavailable if no data
    subnet = entry.data.get(CONF_SUBNET, 1)
    device_id = entry.data.get(CONF_DEVICE, 1)
    
    entities = []
    
    # Add radar motion sensor entity
    # It will show as unavailable until radar packets are received
    entities.append(TISRadarMotionSensor(hass, entry, subnet, device_id))

    async_add_entities(entities)


class TISRadarMotionSensor(BinarySensorEntity):
    """Representation of a TIS Radar Motion Sensor (TIS-OS-MMV2-IRE)."""

    _attr_device_class = BinarySensorDeviceClass.MOTION

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        subnet: int,
        device_id: int,
    ) -> None:
        """Initialize the binary sensor."""
        self.hass = hass
        self.entry = entry
        self.subnet = subnet
        self.device_id = device_id
        self.device_key = (subnet, device_id)
        
        self._attr_unique_id = f"{entry.entry_id}_radar_motion_{subnet}_{device_id}"
        self._attr_name = f"{entry.title} Motion"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{subnet}_{device_id}")},
            "name": f"{entry.title} ({subnet}.{device_id})",
            "manufacturer": "TIS",
            "model": "TIS-OS-MMV2-IRE",
        }
        self._is_on = False
        self._radar_data = {}

    async def async_added_to_hass(self) -> None:
        """Register callback when entity is added."""
        # Register callback for radar updates
        entry_data = self.hass.data[DOMAIN][self.entry.entry_id]
        
        async def radar_callback(radar_data: dict):
            """Update entity when new radar data received."""
            self._is_on = radar_data.get("motion_detected", False)
            self._radar_data = radar_data
            self.async_write_ha_state()
        
        entry_data["radar_callbacks"][self.device_key] = radar_callback

    @property
    def is_on(self) -> bool | None:
        """Return true if motion is detected."""
        return self._is_on

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the state attributes."""
        return {
            "state": self._radar_data.get("state", "unknown"),
            "target_count": self._radar_data.get("target_count", 0),
            "motion_distance_cm": self._radar_data.get("motion_distance_cm", 0),
            "stationary_distance_cm": self._radar_data.get("stationary_distance_cm", 0),
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        # Available if we have radar data
        return len(self._radar_data) > 0
