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
        self.hass = hass

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
            
            # Get radar and LUX data from integration's UDP listener storage
            subnet = self.entry.data.get(CONF_SUBNET, 1)
            device_id = self.entry.data.get(CONF_DEVICE, 1)
            device_key = (subnet, device_id)
            
            radar_motion = None
            lux = None
            model = "TIS Control Device"
            
            # Check if integration data exists (for radar/LUX sensors)
            if DOMAIN in self.hass.data and self.entry.entry_id in self.hass.data[DOMAIN]:
                entry_data = self.hass.data[DOMAIN][self.entry.entry_id]
                
                # Get radar motion data
                if device_key in entry_data.get("radar_data", {}):
                    radar_motion = entry_data["radar_data"][device_key]
                    model = "TIS-OS-MMV2-IRE"  # Radar sensor model
                
                # Get LUX data
                if device_key in entry_data.get("lux_data", {}):
                    lux_data = entry_data["lux_data"][device_key]
                    lux = {
                        "value": lux_data.get("lux", 0),
                        "threshold_low": lux_data.get("threshold_low", 0),
                        "threshold_high": lux_data.get("threshold_high", 0),
                    }

            return {
                "status": status,
                "sensors": sensors,
                "host": self.device.host,
                "radar_motion": radar_motion,
                "lux": lux,
                "model": model,
            }
        except Exception as err:
            _LOGGER.error("Error updating TIS device data: %s", err)
            raise UpdateFailed(f"Error communicating with device: {err}") from err
