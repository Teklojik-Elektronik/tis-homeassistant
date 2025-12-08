from __future__ import annotations
_G='channel_number'
_F='control_response'
_E='additional_bytes'
_D='feedback_type'
_C=False
_B=True
_A=None
import logging
from math import ceil
from typing import Any
import json
from homeassistant.helpers.event import async_track_time_interval
from collections.abc import Callable
from datetime import timedelta
from TISControlProtocol.api import TISApi
from TISControlProtocol.BytesHelper import int_to_8_bit_binary
from TISControlProtocol.Protocols.udp.ProtocolHandler import TISPacket,TISProtocolHandler
from homeassistant.components.cover import ATTR_POSITION,CoverDeviceClass,CoverEntity,CoverEntityFeature
from homeassistant.const import STATE_CLOSING,STATE_OPENING,STATE_UNKNOWN,Platform
from homeassistant.core import Event,HomeAssistant,callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from.import TISConfigEntry
handler=TISProtocolHandler()
POLLING_INTERVAL=timedelta(seconds=60)
async def async_setup_entry(hass,entry,async_add_devices):
    I='gateway';H='device_id';E=async_add_devices;D='channels';A=entry.runtime_data.api;F=await A.get_entities(platform='motor');G=await A.get_entities(platform='shutter')
    if F:B=[(B,next(iter(A[D][0].values())),A[H],A[I],A['settings'])for A in F for(B,A)in A.items()];C=[TISCoverWPos(tis_api=A,cover_name=B,channel_number=C,device_id=D,gateway=E,settings=F)for(B,C,D,E,F)in B];E(C,update_before_add=_B)
    if G:B=[(B,next(iter(A[D][0].values())),next(iter(A[D][1].values())),A[H],A[I])for A in G for(B,A)in A.items()];C=[TISCoverNoPos(tis_api=A,cover_name=B,up_channel_number=C,down_channel_number=D,device_id=E,gateway=F)for(B,C,D,E,F)in B];E(C,update_before_add=_B)
class TISCoverWPos(CoverEntity):
    def __init__(A,tis_api,gateway,cover_name,channel_number,device_id,settings):
        B=settings
        if B:B=json.loads(B);A.exchange_command=B['exchange_command']
        else:A.exchange_command='0'
        A.api=tis_api;A.gateway=gateway;A.device_id=device_id;A.channel_number=int(channel_number);A._attr_name=cover_name;A._attr_is_closed=_A;A._attr_current_cover_position=_A;A._attr_device_class=CoverDeviceClass.SHUTTER;A._attr_unique_id=f"{A}_{A}";A.listener=_A;A.update_packet=handler.generate_control_update_packet(A);A.generate_cover_packet=handler.generate_light_control_packet;A._update_task_unsub=_A
    def _start_polling(A):
        if not A._update_task_unsub:logging.info(f"Starting state polling for {A}");A._update_task_unsub=async_track_time_interval(A.hass,A._async_poll_for_state,POLLING_INTERVAL)
    def _stop_polling(A):
        if A._update_task_unsub:logging.info(f"Stopping state polling for {A}");A._update_task_unsub();A._update_task_unsub=_A
    async def _async_poll_for_state(A,now=_A):logging.info(f"Polling for state of {A}");await A.api.protocol.sender.send_packet(A.update_packet)
    async def async_added_to_hass(A):
        A._start_polling()
        @callback
        async def B(event):
            C=event
            if C.event_type==str(A.device_id):
                if C.data[_D]==_F:
                    logging.info(f"channel number for cover: {A}");D=C.data[_E][2];E=C.data[_G]
                    if int(E)==A.channel_number:
                        B=D
                        if A.exchange_command=='1':B=100-B
                        A._attr_is_closed=B<20;A._attr_current_cover_position=B
                    A.async_write_ha_state()
                elif C.data[_D]=='update_response':
                    F=C.data[_E];B=F[A.channel_number]
                    if A.exchange_command=='1':B=100-B
                    A._attr_current_cover_position=B;A._attr_is_closed=A._attr_current_cover_position<20;A._attr_state=STATE_CLOSING if A._attr_is_closed else STATE_OPENING;A._stop_polling()
                elif C.data[_D]=='offline_device':A._attr_state=STATE_UNKNOWN;A._start_polling();A._attr_is_closed=_A;A._attr_current_cover_position=_A
            await A.async_update_ha_state(_B)
        A.listener=A.hass.bus.async_listen(str(A.device_id),B);C=await A.api.protocol.sender.send_packet(A.update_packet)
    def _convert_position(B,position):
        A=position
        if B.exchange_command=='1':return 100-A
        return A
    @property
    def name(self):return self._attr_name
    @property
    def is_closed(self):return self._attr_is_closed
    @property
    def supported_features(self):return CoverEntityFeature.SET_POSITION
    @property
    def current_cover_position(self):return self._attr_current_cover_position
    @property
    def unique_id(self):return self._attr_unique_id
    async def async_open_cover(A,**E):
        B=A._convert_position(100);C=A.generate_cover_packet(A,B);D=await A.api.protocol.sender.send_packet_with_ack(C)
        if D:A._attr_is_closed=_C;A._attr_current_cover_position=100;A._stop_polling()
        else:A._start_polling();A._attr_is_closed=_A;A._attr_current_cover_position=_A
        A.async_write_ha_state()
    async def async_close_cover(A,**E):
        B=A._convert_position(0);C=A.generate_cover_packet(A,B);D=await A.api.protocol.sender.send_packet_with_ack(C)
        if D:A._attr_is_closed=_B;A._attr_current_cover_position=0;A._stop_polling()
        else:A._attr_is_closed=_A;A._attr_current_cover_position=_A;A._start_polling()
        A.async_write_ha_state()
    async def async_set_cover_position(A,**D):
        C=D[ATTR_POSITION];B=A._convert_position(C);E=A.generate_cover_packet(A,B);F=await A.api.protocol.sender.send_packet_with_ack(E)
        if F:A._attr_is_closed=B<=20 if A.exchange_command=='0'else B>=80;A._attr_current_cover_position=C;A._stop_polling()
        else:A._attr_is_closed=_A;A._attr_current_cover_position=_A;A._start_polling()
        A.async_write_ha_state()
class TISCoverNoPos(CoverEntity):
    def __init__(A,tis_api,gateway,cover_name,up_channel_number,down_channel_number,device_id):A.api=tis_api;A.gateway=gateway;A.device_id=device_id;A.up_channel_number=int(up_channel_number);A.down_channel_number=int(down_channel_number);A._attr_name=cover_name;A._attr_unique_id=f"{A}_{A}_{A}";A.channel_number=A.up_channel_number;A._attr_is_closed=_C;A._attr_device_class=CoverDeviceClass.WINDOW;A.last_state=STATE_OPENING;A.listener=_A
    async def async_added_to_hass(A):
        @callback
        async def B(event):
            B=event
            if B.event_type==str(A.device_id):
                if B.data[_D]==_F:
                    C=B.data[_E][2];D=B.data[_G]
                    if int(D)==A.up_channel_number:
                        if C!=0:A._attr_is_closed=_C;A.last_state=STATE_OPENING;A._attr_state=STATE_OPENING;logging.info(f"up channel value: {C} 'opening'")
                    elif int(D)==A.down_channel_number:
                        if C!=0:A._attr_is_closed=_B;A._attr_state=STATE_CLOSING;A.last_state=STATE_CLOSING;logging.info(f"down channel value: {C} 'closing'")
                    else:logging.info(f"channel number: {D} 'stopping'");A._attr_state=A.last_state;A._attr_is_closed=_C if A.last_state==STATE_OPENING else _B
            await A.async_update_ha_state(_B);A.schedule_update_ha_state()
        A.listener=A.hass.bus.async_listen(str(A.device_id),B)
    @property
    def name(self):return self._attr_name
    @property
    def is_closed(self):
        if self._attr_is_closed==_B:return _B
        elif self._attr_is_closed==_C:return _C
        else:return
    @property
    def supported_features(self):return CoverEntityFeature.OPEN|CoverEntityFeature.STOP|CoverEntityFeature.CLOSE
    @property
    def unique_id(self):return self._attr_unique_id
    async def async_open_cover(A,**D):
        B,E=handler.generate_no_pos_cover_packet(A,'open');C=await A.api.protocol.sender.send_packet_with_ack(B)
        if C:logging.info("up packet sent 'opening'");A._attr_is_closed=_C;A._attr_state=STATE_OPENING;A.last_state=STATE_OPENING
        else:logging.info("up packet not sent 'None'");A._attr_is_closed=_A;A._attr_state=_A
        A.async_write_ha_state()
    async def async_close_cover(A,**D):
        E,B=handler.generate_no_pos_cover_packet(A,'close');C=await A.api.protocol.sender.send_packet_with_ack(B)
        if C:logging.info("down packet sent 'closing'");A._attr_is_closed=_B;A._attr_state=STATE_CLOSING;A.last_state=STATE_CLOSING
        else:logging.info("down packet not sent 'None'");A._attr_is_closed=_A;A._attr_state=_A
        A.async_write_ha_state()
    async def async_stop_cover(A,**E):
        C,D=handler.generate_no_pos_cover_packet(A,'stop')
        if A._attr_is_closed:
            B=await A.api.protocol.sender.send_packet_with_ack(D)
            if B:logging.info("down packet sent 'stopping'");A._attr_state=A.last_state;A._attr_is_closed=_C if A.last_state==STATE_OPENING else _B
            else:logging.info("down packet not sent 'stopping'");A._attr_state=_A;A._attr_is_closed=_A
        elif not A._attr_is_closed:
            B=await A.api.protocol.sender.send_packet_with_ack(C)
            if B:logging.info("up packet sent 'stopping'");A._attr_state=A.last_state;A._attr_is_closed=_C if A.last_state==STATE_OPENING else _B
            else:logging.info("up packet not sent 'stopping'");A._attr_state=_A;A._attr_is_closed=_A
        A.async_write_ha_state()