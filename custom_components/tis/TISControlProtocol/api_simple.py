"""Simplified TIS API for Home Assistant Integration"""
from __future__ import annotations

import socket
import logging
from typing import Optional

from homeassistant.core import HomeAssistant

from .Protocols import setup_udp_protocol
from .Protocols.udp.ProtocolHandler import TISProtocolHandler, TISPacket
from .Protocols.udp.PacketProtocol import PacketProtocol

_LOGGER = logging.getLogger(__name__)


class TISApi:
    """Simplified TIS API class for protocol communication only."""

    def __init__(
        self,
        port: int,
        hass: HomeAssistant,
        domain: str,
        host: str = "0.0.0.0",
    ):
        """Initialize the API class."""
        self.host = host
        self.port = port
        self.protocol: Optional[PacketProtocol] = None
        self.transport = None
        self.hass = hass
        self.domain = domain
        self.sock: Optional[socket.socket] = None
        self.protocol_handler = TISProtocolHandler()

    async def connect(self):
        """Connect to the TIS API and setup UDP protocol."""
        self.loop = self.hass.loop
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        try:
            await self._setup_udp_protocol()
            await self._initialize_hass_data()
            _LOGGER.info(f"✅ TIS API connected: {self.host}:{self.port}")
        except Exception as e:
            _LOGGER.error(f"❌ Error during TIS API connection setup: {e}")
            raise ConnectionError(f"Failed to connect to TIS API: {e}")

    async def _setup_udp_protocol(self):
        """Setup the UDP protocol."""
        try:
            self.transport, self.protocol = await setup_udp_protocol(
                self.sock,
                self.loop,
                self.host,
                self.port,
                self.hass,
            )
            _LOGGER.info("UDP protocol initialized successfully")
        except Exception as e:
            _LOGGER.error(f"Error connecting to TIS API: {e}")
            raise ConnectionError(f"UDP protocol setup failed: {e}")

    async def _initialize_hass_data(self):
        """Initialize Home Assistant data."""
        if self.domain not in self.hass.data:
            self.hass.data[self.domain] = {}
        
        self.hass.data[self.domain]["discovered_devices"] = []
        self.hass.data[self.domain]["api"] = self
        _LOGGER.debug("Home Assistant data initialized")

    async def disconnect(self):
        """Disconnect from the TIS API."""
        try:
            if self.transport:
                self.transport.close()
            if self.sock:
                self.sock.close()
            _LOGGER.info("TIS API disconnected")
        except Exception as e:
            _LOGGER.error(f"Error during disconnect: {e}")

    def get_protocol_handler(self) -> TISProtocolHandler:
        """Get the protocol handler instance."""
        return self.protocol_handler

    def get_packet_protocol(self) -> Optional[PacketProtocol]:
        """Get the packet protocol instance."""
        return self.protocol
