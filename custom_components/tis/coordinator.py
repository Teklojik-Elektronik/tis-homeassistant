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
from .tis_protocol import TISPacket, TISUDPClient

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


class SensorUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching TIS sensor data."""

    def __init__(
        self,
        hass: HomeAssistant,
        gateway_ip: str,
        udp_port: int,
        update_interval: timedelta,
        device_id: tuple,
        update_packet: TISPacket,
    ) -> None:
        """Initialize the sensor coordinator."""
        self.gateway_ip = gateway_ip
        self.udp_port = udp_port
        self.device_id = device_id
        self.update_packet = update_packet
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"Sensor Update Coordinator for {device_id}",
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """Fetch data from TIS device."""
        try:
            client = TISUDPClient(self.gateway_ip, self.udp_port)
            await client.async_connect(bind=False)
            
            # Get local IP for SMARTCLOUD header
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(('8.8.8.8', 80))
                local_ip = s.getsockname()[0]
            finally:
                s.close()
            
            ip_bytes = bytes([int(x) for x in local_ip.split('.')])
            tis_data = self.update_packet.build()
            full_packet = ip_bytes + b'SMARTCLOUD' + tis_data
            
            client.send_to(full_packet, self.gateway_ip)
            client.close()
            
            return True
        except Exception as e:
            _LOGGER.error(f"Error updating sensor data: {e}")
            return None
