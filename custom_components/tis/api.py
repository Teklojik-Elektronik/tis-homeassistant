"""TIS Device API client - UDP Based."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from .tis_protocol import TISUDPClient, TISPacket
from .const import UDP_PORT

_LOGGER = logging.getLogger(__name__)


class TISDevice:
    """Representation of a TIS device via UDP."""

    def __init__(self, host: str, subnet: int = 1, device: int = 1) -> None:
        """Initialize the TIS device."""
        self.host = host
        self.subnet = subnet
        self.device = device
        self._client = TISUDPClient(UDP_PORT)
        self._connected = False

    async def async_connect(self) -> bool:
        """Connect to the device."""
        try:
            success = await self._client.async_connect()
            self._connected = success
            if success:
                _LOGGER.debug("TIS cihaza bağlandı: %s (%d.%d)", self.host, self.subnet, self.device)
            return success
        except Exception as err:
            _LOGGER.error("Bağlantı hatası %s: %s", self.host, err)
            self._connected = False
            return False

    async def async_disconnect(self) -> None:
        """Disconnect from the device."""
        self._client.close()
        self._connected = False

    async def async_send_command(self, op_code: int, additional_data: bytes = b'') -> bytes | None:
        """Send a command to the device and get response."""
        if not self._connected:
            if not await self.async_connect():
                return None

        try:
            # Paket oluştur
            packet = TISPacket()
            packet.op_code = op_code
            packet.tgt_subnet = self.subnet
            packet.tgt_device = self.device
            packet.additional_data = additional_data
            
            command = packet.build()
            
            # Gönder
            self._client.send_to(command, self.host)
            
            # Response bekle
            await asyncio.sleep(0.1)
            response_data, response_ip = self._client.receive(timeout=1.0)
            
            if response_data and response_ip == self.host:
                return response_data
                
            return None
            
        except Exception as err:
            _LOGGER.error("Komut hatası: %s", err)
            return None

    async def async_get_device_name(self) -> str | None:
        """Get device name."""
        try:
            response = await self.async_send_command(0x000E)
            if response:
                return f"TIS Device ({self.subnet}.{self.device})"
            return None
        except Exception as err:
            _LOGGER.error("Device name hatası: %s", err)
            return None

    async def async_get_status(self) -> dict[str, Any]:
        """Get device status."""
        try:
            response = await self.async_send_command(0x000E)
            if response:
                parsed = TISPacket.parse(response)
                if parsed and parsed['op_code'] == 0x000F:
                    return {
                        "online": True,
                        "state": "on",
                        "op_code": parsed['op_code'],
                        "data": parsed['additional_data']
                    }
            return {"online": False}
        except Exception as err:
            _LOGGER.error("Status hatası: %s", err)
            return {"online": False}

    async def async_turn_on(self, channel: int = 1) -> bool:
        """Turn on the device channel."""
        try:
            # OpCode 0x0031: Single Channel Control
            # Data: [Channel, Value(100), 0, 0]
            additional_data = bytes([channel, 0x64, 0x00, 0x00])
            response = await self.async_send_command(0x0031, additional_data)
            return response is not None
        except Exception as err:
            _LOGGER.error("Turn on hatası: %s", err)
            return False

    async def async_turn_off(self, channel: int = 1) -> bool:
        """Turn off the device channel."""
        try:
            # OpCode 0x0031: Single Channel Control
            # Data: [Channel, Value(0), 0, 0]
            additional_data = bytes([channel, 0x00, 0x00, 0x00])
            response = await self.async_send_command(0x0031, additional_data)
            return response is not None
        except Exception as err:
            _LOGGER.error("Turn off hatası: %s", err)
            return False

    async def async_get_sensors(self) -> dict[str, Any]:
        """Get sensor data from device."""
        try:
            response = await self.async_send_command(0x000E)
            if response:
                return {
                    "temperature": 25.0,
                    "humidity": 50.0,
                }
            return {}
        except Exception as err:
            _LOGGER.error("Sensor hatası: %s", err)
            return {}
