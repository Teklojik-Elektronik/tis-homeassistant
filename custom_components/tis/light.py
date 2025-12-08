from __future__ import annotations
_H='channel_number'
_G='offline_device'
_F='update_response'
_E=True
_D='additional_bytes'
_C=False
_B='feedback_type'
_A=None
import logging
from math import ceil
from typing import Any
from TISControlProtocol.api import TISApi
from TISControlProtocol.BytesHelper import int_to_8_bit_binary
from TISControlProtocol.Protocols.udp.ProtocolHandler import TISPacket,TISProtocolHandler
from homeassistant.components.light import ATTR_BRIGHTNESS,ATTR_RGB_COLOR,ATTR_RGBW_COLOR,ColorMode,LightEntity,LightEntityFeature
from homeassistant.const import STATE_OFF,STATE_ON,STATE_UNKNOWN
from homeassistant.core import Event,HomeAssistant,callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from.import TISConfigEntry
handler=TISProtocolHandler()
async def async_setup_entry(hass,entry,async_add_devices):
    F='gateway';E='is_protected';D='device_id';C=async_add_devices;B='channels';A=entry.runtime_data.api;G=await A.get_entities(platform='dimmer')
    if G:J=[(C,next(iter(A[B][0].values())),A[D],A[E],A[F])for A in G for(C,A)in A.items()];K=[TISLight(tis_api=A,light_name=B,device_id=D,channel_number=C,gateway=E)for(B,C,D,F,E)in J];C(K)
    H=await A.get_entities(platform='rgb')
    if H:L=[(C,next(iter(A[B][0].values())),next(iter(A[B][1].values())),next(iter(A[B][2].values())),A[D],A[E],A[F])for A in H for(C,A)in A.items()];M=[TISRGBLight(tis_api=A,light_name=B,r_channel=C,g_channel=D,b_channel=E,device_id=F,gateway=G)for(B,C,D,E,F,H,G)in L];C(M)
    I=await A.get_entities(platform='rgbw')
    if I:N=[(C,next(iter(A[B][0].values())),next(iter(A[B][1].values())),next(iter(A[B][2].values())),next(iter(A[B][3].values())),A[D],A[E],A[F])for A in I for(C,A)in A.items()];O=[TISRGBWLight(tis_api=A,light_name=B,r_channel=C,g_channel=D,b_channel=E,w_channel=F,device_id=G,gateway=H)for(B,C,D,E,F,G,I,H)in N];C(O)
class TISLight(LightEntity):
    def __init__(A,tis_api,gateway,light_name,channel_number,device_id):A.api=tis_api;A.gateway=gateway;A.device_id=device_id;A.channel_number=int(channel_number);A._attr_name=light_name;A._attr_state=_C;A._attr_brightness=_A;A.listener=_A;A.broadcast_channel=255;A._attr_unique_id=f"{A}_{A}";A.setup_light()
    def setup_light(A):A._attr_supported_color_modes={ColorMode.BRIGHTNESS};A._attr_color_mode=ColorMode.BRIGHTNESS;A._attr_supported_features=LightEntityFeature.TRANSITION;A.generate_light_packet=handler.generate_light_control_packet;A.update_packet=handler.generate_control_update_packet(A)
    async def async_added_to_hass(A):
        @callback
        async def B(event):
            B=event
            if B.event_type==str(A.device_id):
                if B.data[_B]=='control_response':
                    logging.info(f"channel number for light: {A}");C=B.data[_D][2];D=B.data[_H]
                    if int(D)==A.channel_number:A._attr_state=int(C)!=0;A._attr_brightness=int(C/100*255)
                    A.async_write_ha_state()
                elif A.channel_number!=A.broadcast_channel:
                    if B.data[_B]=='binary_feedback':
                        E=ceil(B.data[_D][0]/8);F=alpha__("").join(int_to_8_bit_binary(B.data[_D][A])for A in range(1,E+1))
                        if F[A.channel_number-1]=='0':A._attr_state=_C
                        A.async_write_ha_state()
                    elif B.data[_B]==_F:G=B.data[_D];A._attr_brightness=int(G[A.channel_number]/100*255);A._attr_state=STATE_ON if A._attr_brightness>0 else STATE_OFF
                elif B.data[_B]==_G:A._attr_state=STATE_UNKNOWN
        A.listener=A.hass.bus.async_listen(str(A.device_id),B);C=await A.api.protocol.sender.send_packet(A.update_packet)
    @property
    def brightness(self):return self._attr_brightness
    @property
    def color_mode(self):return self._attr_color_mode
    @property
    def supported_color_modes(self):return self._attr_supported_color_modes
    @property
    def supported_features(self):return self._attr_supported_features
    @property
    def is_on(self):return self._attr_brightness>0 if self._attr_brightness is not _A else _A
    @property
    def name(self):return self._attr_name
    async def async_turn_on(A,**B):
        try:C=B[ATTR_BRIGHTNESS]
        except KeyError:C=255
        D=A.generate_light_packet(A,int(C/255*100));E=await A.api.protocol.sender.send_packet_with_ack(D)
        if E:A._attr_state=_E;A._attr_brightness=B.get(ATTR_BRIGHTNESS,255)
        else:A._attr_state=_A;A._attr_brightness=_A
        A.async_write_ha_state()
    async def async_turn_off(A,**D):
        B=A.generate_light_packet(A,0);C=await A.api.protocol.sender.send_packet_with_ack(B)
        if C:A._attr_brightness=0;A._attr_state=_C
        else:A._attr_state=_A;A._attr_brightness=_A
        A.async_write_ha_state()
class TISRGBLight(LightEntity):
    def __init__(A,tis_api,gateway,device_id,r_channel,g_channel,b_channel,light_name):A.api=tis_api;A.gateway=gateway;A.device_id=device_id;A.r_channel=int(r_channel);A.g_channel=int(g_channel);A.b_channel=int(b_channel);A.rgb_value_flags=[0,0,0];A._attr_name=light_name;A._attr_state=_A;A._attr_rgb_color=_A;A._attr_brightness=_A;A.listener=_A;A._attr_unique_id=f"{A}_{A}_{A}_{A}";A.default_color=0,0,0;A.setup_light()
    def setup_light(A):A._attr_supported_color_modes={ColorMode.RGB};A._attr_color_mode=ColorMode.RGB;A.generate_rgb_packets=handler.generate_rgb_light_control_packet;A.update_packet=handler.generate_control_update_packet(A)
    async def async_added_to_hass(A):
        @callback
        async def B(event):
            C=event
            if C.event_type==str(A.device_id):
                if C.data[_B]==_F:
                    D=C.data[_D];B=C.data[_H]
                    if A._attr_rgb_color is _A:A._attr_rgb_color=[0,0,0]
                    if B==A.r_channel:A._attr_rgb_color[0]=int(D[B]/100*255)
                    elif B==A.g_channel:A._attr_rgb_color[1]=int(D[B]/100*255)
                    elif B==A.b_channel:A._attr_rgb_color[2]=int(D[B]/100*255)
                    A._attr_state=bool(A.r_channel or A.g_channel or A.b_channel)
                elif C.data[_B]==_G:A._attr_state=STATE_UNKNOWN
        A.listener=A.hass.bus.async_listen(str(A.device_id),B)
        for C in range(5):
            if A._attr_rgb_color is _A:D=await A.api.protocol.sender.send_packet(A.update_packet)
        if A._attr_rgb_color is _A:A._attr_state=STATE_UNKNOWN;A._attr_rgb_color=0,0,0
    @property
    def color_mode(self):return self._attr_color_mode
    @property
    def brightness(self):return self._attr_brightness
    @property
    def rgb_color(self):return self._attr_rgb_color
    @property
    def supported_color_modes(self):return self._attr_supported_color_modes
    @property
    def is_on(self):return self._attr_state
    @property
    def name(self):return self._attr_name
    async def async_turn_on(A,**G):
        try:
            B=G.get(ATTR_RGB_COLOR,_A);C=G.get(ATTR_BRIGHTNESS,_A);logging.info(f"color: {B}");logging.info(f"brightness: {C}")
            if B is not _A:B=tuple([int(A/255*100)for A in B]);D,E,F=A.generate_rgb_packets(A,B);await A.api.protocol.sender.send_packet(D);await A.api.protocol.sender.send_packet(E);await A.api.protocol.sender.send_packet(F);A._attr_state=_E;B=tuple([int(A/100*255)for A in B]);A._attr_rgb_color=B;A.default_color=B;logging.info(f"new default color: {B}")
            elif C is not _A:C=max(1,min(255,C));C/=255;B=A.default_color or(0,0,0);logging.info(f"default color: {B}");B=tuple([int(C*A*100/255)for A in B]);D,E,F=A.generate_rgb_packets(A,B);await A.api.protocol.sender.send_packet(D);await A.api.protocol.sender.send_packet(E);await A.api.protocol.sender.send_packet(F);logging.info(f"brightened color: {B}")
            else:logging.info('Neither color nor brightness provided, using default color.');B=A.default_color or(0,0,0);A._attr_state=_E if A.default_color and A.default_color!=(0,0,0)else _C;A._attr_rgb_color=B;B=tuple([int(A*100/255)for A in B]);D,E,F=A.generate_rgb_packets(A,B);await A.api.protocol.sender.send_packet(D);await A.api.protocol.sender.send_packet(E);await A.api.protocol.sender.send_packet(F)
        except KeyError as H:logging.error(f"error turning on light: {H}")
        A.async_write_ha_state()
    async def async_turn_off(A,**B):logging.info('turning off');logging.info(f"kwargs: {B}");C,D,E=A.generate_rgb_packets(A,(0,0,0));await A.api.protocol.sender.send_packet(D);await A.api.protocol.sender.send_packet(C);await A.api.protocol.sender.send_packet(E);A._attr_state=_C;A._attr_rgb_color=0,0,0;A.async_write_ha_state()
class TISRGBWLight(LightEntity):
    def __init__(A,tis_api,gateway,device_id,r_channel,g_channel,b_channel,w_channel,light_name):A.api=tis_api;A.gateway=gateway;A.device_id=device_id;A.r_channel=int(r_channel);A.g_channel=int(g_channel);A.b_channel=int(b_channel);A.w_channel=int(w_channel);A._attr_name=light_name;A._attr_state=_A;A._attr_brightness=_A;A._attr_rgbw_color=_A;A.rgbw_value_flags=[0,0,0,0];A.listener=_A;A._attr_unique_id=f"{A}_{A}_{A}_{A}_{A}";A.default_color=0,0,0,0;A.setup_light()
    def setup_light(A):A._attr_supported_color_modes={ColorMode.RGBW};A._attr_color_mode=ColorMode.RGBW;A._attr_supported_features=LightEntityFeature.TRANSITION;A.generate_rgbw_packets=handler.generate_rgbw_light_control_packet;A.update_packet=handler.generate_control_update_packet(A)
    async def async_added_to_hass(A):
        @callback
        async def B(event):
            B=event
            if B.event_type==str(A.device_id):
                if B.data[_B]==_F:logging.info(f"RGBW event data: {B}");C=B.data[_D];D=C[A.r_channel]/100*255;E=C[A.g_channel]/100*255;F=C[A.b_channel]/100*255;G=C[A.w_channel]/100*255;A._attr_rgbw_color=D,E,F,G;A._attr_state=bool(D or E or F or G)
                elif B.data[_B]==_G:A._attr_state=STATE_UNKNOWN
        A.listener=A.hass.bus.async_listen(str(A.device_id),B)
        for C in range(5):
            if A._attr_rgbw_color is _A:D=await A.api.protocol.sender.send_packet(A.update_packet)
        if A._attr_rgbw_color is _A:A._attr_state=STATE_UNKNOWN;A._attr_rgbw_color=0,0,0,0
    @property
    def brightness(self):return self._attr_brightness
    @property
    def color_mode(self):return self._attr_color_mode
    @property
    def rgbw_color(self):return self._attr_rgbw_color
    @property
    def supported_color_modes(self):return self._attr_supported_color_modes
    @property
    def supported_features(self):return self._attr_supported_features
    @property
    def is_on(self):return self._attr_state
    @property
    def name(self):return self._attr_name
    async def async_turn_on(A,**D):
        try:
            B=D.get(ATTR_RGBW_COLOR,_A);C=D.get(ATTR_BRIGHTNESS,_A);logging.warning(f"kwargs: {D}")
            if B is not _A:B=tuple([int(A/255*100)for A in B]);E,F,G,H=A.generate_rgbw_packets(A,B);logging.info(f"color (percent): {B}");await A.api.protocol.sender.send_packet(E);await A.api.protocol.sender.send_packet(F);await A.api.protocol.sender.send_packet(G);await A.api.protocol.sender.send_packet(H);A._attr_state=_E;B=tuple([int(A/100*255)for A in B]);A._attr_rgbw_color=B;A.default_color=B
            elif C is not _A:C=max(1,min(255,C));logging.warning(f"brightness: {C}, self._attr_brightness: {A}");A._attr_brightness=C;C/=255;B=A.default_color or(0,0,0,0);logging.info(f"default color: {B}");B=tuple([int(C*A*100/255)for A in B]);E,F,G,H=A.generate_rgbw_packets(A,B);await A.api.protocol.sender.send_packet(E);await A.api.protocol.sender.send_packet(F);await A.api.protocol.sender.send_packet(G);await A.api.protocol.sender.send_packet(H);A._attr_state=_E;B=tuple([int(A/100*255)for A in B]);A._attr_rgbw_color=B
        except KeyError as I:logging.error(f"error turning on light: {I}")
        A.async_write_ha_state()
    async def async_turn_off(A,**F):B,C,D,E=A.generate_rgbw_packets(A,(0,0,0,0));await A.api.protocol.sender.send_packet(B);await A.api.protocol.sender.send_packet(C);await A.api.protocol.sender.send_packet(D);await A.api.protocol.sender.send_packet(E);A._attr_state=_C;A._attr_rgbw_color=0,0,0,0;A.async_write_ha_state()