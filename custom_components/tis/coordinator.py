from __future__ import annotations
from datetime import timedelta
import logging
from TISControlProtocol.api import TISApi
from TISControlProtocol.Protocols.udp.ProtocolHandler import TISPacket,TISProtocolHandler
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
_LOGGER=logging.getLogger(__name__)
HANDLER=TISProtocolHandler()
class SensorUpdateCoordinator(DataUpdateCoordinator):
    def __init__(A,hass,api,update_interval,device_id,update_packet):B=device_id;A.api=api;A.device_id=B;A.update_packet=update_packet;super().__init__(hass,_LOGGER,name=f"Sensor Update Coordinator for {B}",update_interval=update_interval)
    async def _async_update_data(A):return await A.api.protocol.sender.send_packet(A.update_packet)