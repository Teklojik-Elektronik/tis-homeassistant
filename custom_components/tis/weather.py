from __future__ import annotations
from datetime import timedelta
import logging
from TISControlProtocol.api import TISApi,TISPacket
from TISControlProtocol.Protocols.udp.ProtocolHandler import TISProtocolHandler
from homeassistant.components.weather import ATTR_CONDITION_CLOUDY,ATTR_CONDITION_EXCEPTIONAL,ATTR_CONDITION_FOG,ATTR_CONDITION_HAIL,ATTR_CONDITION_LIGHTNING,ATTR_CONDITION_LIGHTNING_RAINY,ATTR_CONDITION_PARTLYCLOUDY,ATTR_CONDITION_POURING,ATTR_CONDITION_RAINY,ATTR_CONDITION_SNOWY,ATTR_CONDITION_SNOWY_RAINY,ATTR_CONDITION_SUNNY,ATTR_CONDITION_WINDY,ATTR_CONDITION_WINDY_VARIANT,ATTR_FORECAST_CONDITION,ATTR_FORECAST_NATIVE_PRECIPITATION,ATTR_FORECAST_NATIVE_TEMP,ATTR_FORECAST_NATIVE_TEMP_LOW,ATTR_FORECAST_NATIVE_WIND_SPEED,ATTR_FORECAST_TIME,ATTR_FORECAST_WIND_BEARING,Forecast,UnitOfTemperature,WeatherEntity,WeatherEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import MATCH_ALL,CONF_LATITUDE,CONF_LONGITUDE,CONF_NAME,Platform,UnitOfLength,UnitOfPrecipitationDepth,UnitOfPressure,UnitOfSpeed,UnitOfTemperature
from homeassistant.core import Event,HomeAssistant,callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from.import TISConfigEntry
handler=TISProtocolHandler()
async def async_setup_entry(hass,entry,async_add_devices):A=entry.runtime_data.api;B=[TISWeatherStation(api=A,device_id=[1,254],gateway='192.168.1.4')];async_add_devices(B,update_before_add=True)
class TISWeatherStation(WeatherEntity):
    def __init__(A,api,device_id,gateway):A.api=api;A.device_id=device_id;A.gateway=gateway;A.update_packet=handler.generate_weather_update_packet(A);A.listener=None;A._attr_unit_of_measurement=UnitOfTemperature.CELSIUS;A._attr_update_interval=timedelta(seconds=10);async_track_time_interval(A.api.hass,A.async_update,A._attr_update_interval)
    async def async_added_to_hass(A):
        @callback
        def B(event):
            B=event
            if B.event_type==str(A.device_id):
                if B.data['feedback_type']=='weather_feedback':A._attr_uv_index=float(B.data['uv']);A._attr_native_temperature=B.data['temperature'];logging.info(f"event data {B}")
            A.schedule_update_ha_state()
        A.listener=A.hass.bus.async_listen(MATCH_ALL,B)
    async def async_will_remove_from_hass(A):A.listener=None
    async def async_update(A,*B,**C):await A.api.protocol.sender.send_packet(A.update_packet)
    @property
    def name(self):return 'TIS Weather Station'
    @property
    def wind_bearing(self):return self._attr_wind_bearing
    @property
    def native_temperature(self):return self._attr_native_temperature
    @property
    def native_temperature_unit(self):return UnitOfTemperature.CELSIUS
    @property
    def humidity(self):return self._attr_humidity
    @property
    def native_wind_speed(self):return self._attr_native_wind_speed
    @property
    def native_wind_gust_speed(self):return self._attr_native_wind_gust_speed
    @property
    def uv_index(self):return self._attr_uv_index
    @property
    def condition(self):return self._attr_condition