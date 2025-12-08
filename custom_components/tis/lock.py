from __future__ import annotations
_G='locked'
_F='admin_lock'
_E='Invalid password'
_D='user'
_C=True
_B='code'
_A=False
from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from.const import DOMAIN
from TISControlProtocol.api import TISApi
import asyncio,logging
async def async_setup_entry(hass,entry,async_add_devices):
    B=entry.runtime_data.api;A=await B.get_entities(platform='lock_module')
    if A is None:logging.error('No lock module found in the configuration');return
    else:async_add_devices([TISControlLock('Admin Lock',A['password'])])
class TISControlLock(LockEntity):
    def __init__(A,name,password):A._attr_name=name;A.unique_id=f"lock_{A}";A._attr_is_locked=_C;A._attr_password=password;A._attr_changed_by=None;A._attr_code_format='.*';A._attr_is_locking=_A;A._attr_is_unlocking=_A;A._attr_is_opening=_A;A._attr_is_open=_A;A._attr_timeout=60
    @property
    def name(self):return self._attr_name
    @property
    def is_locked(self):return self._attr_is_locked
    async def async_lock(A,**B):
        if _B in B and B[_B]==A._attr_password:A._attr_is_locked=_C;A._attr_changed_by=_D;A.hass.bus.async_fire(str(_F),{_G:_C})
        else:raise ValueError(_E)
    async def async_unlock(A,**B):
        if _B in B and B[_B]==A._attr_password:
            A._attr_is_locked=_A;A._attr_changed_by=_D;A.hass.bus.async_fire(str(_F),{_G:_A})
            if hasattr(A,'_auto_lock_task')and A._auto_lock_task:A._auto_lock_task.cancel()
            A._auto_lock_task=asyncio.create_task(A.auto_lock())
        else:raise ValueError(_E)
    async def auto_lock(A):await asyncio.sleep(A._attr_timeout);await A.async_lock(code=A._attr_password)
    async def async_open(A,**B):
        if _B in B and B[_B]==A._attr_password:A._attr_is_open=_C;A._attr_changed_by=_D
        else:raise ValueError(_E)