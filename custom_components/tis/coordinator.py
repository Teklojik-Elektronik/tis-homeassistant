"""Data update coordinator for TIS devices."""
from __future__ import annotations

from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TISDevice
from .const import DOMAIN, UPDATE_INTERVAL, CONF_SUBNET, CONF_DEVICE

_LOGGER = logging.getLogger(__name__)


class TISDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching TIS data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        self.device = TISDevice(
            entry.data[CONF_HOST],
            entry.data.get(CONF_SUBNET, 1),
            entry.data.get(CONF_DEVICE, 1),
        )
        self.entry = entry

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from TIS device."""
        try:
            if not self.device._connected:
                await self.device.async_connect()

            status = await self.device.async_get_status()
            sensors = await self.device.async_get_sensors()

            return {
                "status": status,
                "sensors": sensors,
                "host": self.device.host,
            }
        except Exception as err:
            _LOGGER.error("Error updating TIS device data: %s", err)
            raise UpdateFailed(f"Error communicating with device: {err}") from err
