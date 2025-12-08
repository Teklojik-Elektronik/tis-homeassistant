from __future__ import annotations
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity,DataUpdateCoordinator
class BaseSensorEntity(CoordinatorEntity):
    def __init__(A,coordinator,name,device_id):B=coordinator;super().__init__(B);A.coordinator=B;A._attr_name=name;A._state=None;A._device_id=device_id
    async def async_added_to_hass(A):await super().async_added_to_hass();A.async_on_remove(A.coordinator.async_add_listener(A._handle_coordinator_update))
    @callback
    def _handle_coordinator_update(self):A=self;A._update_state(A.coordinator.data);A.async_write_ha_state()
    def _update_state(A,data):raise NotImplementedError
    @property
    def should_poll(self):return False
    @property
    def state(self):return self._state