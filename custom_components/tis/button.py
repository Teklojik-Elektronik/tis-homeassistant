from __future__ import annotations
from homeassistant.components.button import ButtonEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from TISControlProtocol.api import TISApi
from TISControlProtocol.Protocols.udp.ProtocolHandler import TISProtocolHandler
from homeassistant.core import HomeAssistant
import logging,json
from.import TISConfigEntry,DOMAIN
async def async_setup_entry(hass,config_entry,async_add_entities):
    B=config_entry.runtime_data.api;C=await B.get_entities(platform='universal_switch')
    if C:
        A=[(C,next(iter(A['channels'][0].values())),A['device_id'],A['is_protected'],A['gateway'],A['settings'])for B in C for(C,A)in B.items()]
        try:A=[TISUniversalSwitch(tis_api=B,device_name=A,channel_number=C,device_id=D,gateway=E,universal_type=int(json.loads(F).get('universal_type',0)))for(A,C,D,G,E,F)in A];async_add_entities(A)
        except Exception as D:logging.error(f"error happened creating universal switches error: {D}")
protocol_handler=TISProtocolHandler()
class TISUniversalSwitch(ButtonEntity):
    _attr_has_entity_name=True;_attr_name=None;_attr_should_poll=False
    def __init__(A,tis_api,device_name,channel_number,device_id,gateway,universal_type=0):B=device_name;A._attr_unique_id=f"universal_switch_{B}";A._attr_name=B;A.device_id=device_id;A.gateway=gateway;A.channel_number=channel_number;A.api=tis_api;A.universal_type=int(universal_type*255);A._attr_device_info=DeviceInfo(identifiers={(DOMAIN,A._attr_unique_id)},name=B);A.press_packet=protocol_handler.generate_universal_switch_packet(A);logging.warning(f"press packet: {A}")
    async def async_press(A):return await A.api.protocol.sender.send_packet(A.press_packet)