from __future__ import annotations
_D='device_id'
_C='vacation'
_B='disarm'
_A=None
from homeassistant.components.select import SelectEntity
from TISControlProtocol.api import TISApi
from homeassistant.const import MATCH_ALL,STATE_UNAVAILABLE
from homeassistant.core import callback,Event,HomeAssistant
from TISControlProtocol.Protocols.udp.ProtocolHandler import TISPacket,TISProtocolHandler
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from.import TISConfigEntry
import logging
SECURITY_OPTIONS={_C:1,'away':2,'night':3,_B:6}
SECURITY_FEEDBACK_OPTIONS={1:_C,2:'away',3:'night',6:_B}
handler=TISProtocolHandler()
async def async_setup_entry(hass,entry,async_add_devices):
    A=entry.runtime_data.api;B=await A.get_entities(platform='security')
    if B:C=[(C,next(iter(A['channels'][0].values())),A[_D],A['gateway'])for B in B for(C,A)in B.items()];D=[TISSecurity(api=A,name=B,options=list(SECURITY_OPTIONS.keys()),initial_option=_B,channel_number=C,device_id=D,gateway=E)for(B,C,D,E)in C];async_add_devices(D)
protocol_handler=TISProtocolHandler()
class TISSecurity(SelectEntity):
    def __init__(A,api,name,options,initial_option,channel_number,device_id,gateway):A._name=name;A.api=api;A.unique_id=f"select_{A}";A._attr_options=options;A._attr_current_option=A._state=initial_option;A._attr_icon='mdi:shield';A._attr_is_protected=True;A._attr_read_only=True;A._listener=_A;A.channel_number=int(channel_number);A.device_id=device_id;A.gateway=gateway;A.update_packet=protocol_handler.generate_update_security_packet(A)
    async def async_added_to_hass(A):
        @callback
        async def B(event):
            E='feedback_type';B=event
            if B.event_type=='admin_lock':
                logging.info(f"admin lock event: {B}")
                if B.data.get('locked'):A.protect()
                else:A.unprotect()
            if B.data.get(E)=='security_feedback'or B.data.get(E)=='security_update':
                logging.info(f"security feedback event: {B}")
                if A.channel_number==B.data['channel_number']and A.device_id==B.data[_D]:
                    C=B.data['mode']
                    if C in SECURITY_FEEDBACK_OPTIONS:D=SECURITY_FEEDBACK_OPTIONS[C];logging.info(f"mode: {C}, option: {D}");A._state=A._attr_current_option=D
            A.async_write_ha_state()
        A._listener=A.hass.bus.async_listen(MATCH_ALL,B);await A.api.protocol.sender.send_packet(A.update_packet);logging.info(f"update packet sent: {A}");logging.info(f"listener added: {A}")
    @property
    def name(self):return self._name
    @property
    def options(self):return self._attr_options
    @property
    def current_option(self):return self._attr_current_option if self._attr_current_option in SECURITY_FEEDBACK_OPTIONS.values()else _A
    def protect(A):A._attr_read_only=True
    def unprotect(A):A._attr_read_only=False
    async def async_select_option(A,option):
        B=option
        if A._attr_is_protected:
            if A._attr_read_only:A._state=A._attr_current_option=STATE_UNAVAILABLE;logging.error('resetting state to last known state');await A.api.protocol.sender.send_packet(A.update_packet);A.async_write_ha_state();raise ValueError('The security module is protected and read only')
            else:
                logging.info(f"setting security mode to {B}");C=SECURITY_OPTIONS.get(B,_A)
                if C:
                    logging.info(f"mode: {C}");D=handler.generate_control_security_packet(A,C);E=await A.api.protocol.sender.send_packet_with_ack(D);logging.info(f"control_packet: {D}");logging.info(f"ack: {E}")
                    if E:logging.info(f"setting state to {B}");A._state=A._attr_current_option=B;A.async_write_ha_state()
                    else:logging.warning(f"Failed to set security mode to {B}");A._state=A._attr_current_option=_A;A.async_write_ha_state()
        if B not in A._attr_options:raise ValueError(f"Invalid option: {B} (possible options: {A})")