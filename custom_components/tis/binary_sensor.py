from __future__ import annotations
import logging
_A=None
from TISControlProtocol.api import TISApi
from homeassistant.components.binary_sensor import STATE_OFF,STATE_ON,BinarySensorEntity
from homeassistant.const import MATCH_ALL
from homeassistant.core import Event,HomeAssistant,callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from.import TISConfigEntry
async def async_setup_entry(hass,entry,async_add_entities):
    A=entry.runtime_data.api;B=await A.get_entities(platform='binary_sensor')
    if B and len(B) > 0:
        C=[(C,next(iter(A['channels'][0].values())),A['device_id'],A['gateway'],A['is_protected'])for B in B for(C,A)in B.items()]
        D=[TISBinarySensor(tis_api=A,sensor_name=B,channel_number=C,device_id=D,gateway=E)for(B,C,D,E,F)in C]
        async_add_entities(D)
    else:
        logging.info("No binary sensors found in configuration")
        async_add_entities([])
class TISBinarySensor(BinarySensorEntity):
    def __init__(A,tis_api,sensor_name,channel_number,device_id,gateway):A._api=tis_api;A._name=sensor_name;A._device_id=device_id;A._channel_number=int(channel_number);A._listener=_A;A._attr_state=_A;A._attr_is_on=_A;A._attr_device_class='motion',;A._gateway=gateway;A._attr_unique_id=f"{A}_{A}"
    async def async_added_to_hass(A):
        @callback
        async def B(event):
            E=False;D='feedback_type';C=True;B=event
            if B.event_type==str(A._device_id):
                if B.data[D]=='auto_binary_feedback':
                    F=B.data['channels_values'][A._channel_number-1]
                    if int(F)==1:A._attr_is_on=C;A._attr_state=STATE_ON
                    else:A._attr_is_on=E;A._attr_state=STATE_OFF
                elif B.data[D]=='realtime_feedback':
                    if B.data['channel_number']==A._channel_number:
                        G=int(B.data['additional_bytes'][1])
                        if G==100:A._attr_is_on=C;A._attr_state=STATE_ON
                        else:A._attr_is_on=E;A._attr_state=STATE_OFF
            await A.async_update_ha_state(C)
        A._listener=A.hass.bus.async_listen(MATCH_ALL,B)
    async def async_will_remove_from_hass(A):A._listener();A._listener=_A
    @property
    def name(self):return self._name
    @property
    def is_on(self):return self._attr_is_on