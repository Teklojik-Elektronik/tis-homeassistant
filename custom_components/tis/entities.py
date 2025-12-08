"""Base entities for TIS integration."""
from __future__ import annotations

from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity, DataUpdateCoordinator


class BaseSensorEntity(CoordinatorEntity):
    """Base class for TIS sensor entities with coordinator support."""

    def __init__(self, coordinator: DataUpdateCoordinator, name: str, device_id: tuple) -> None:
        """Initialize the base sensor entity."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._attr_name = name
        self._state = None
        self._device_id = device_id

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self.coordinator.async_add_listener(self._handle_coordinator_update)
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self._update_state(self.coordinator.data)
        self.async_write_ha_state()

    def _update_state(self, data) -> None:
        """Update state from coordinator data - to be implemented by subclasses."""
        raise NotImplementedError

    @property
    def should_poll(self) -> bool:
        """No polling needed with coordinator."""
        return False

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state
