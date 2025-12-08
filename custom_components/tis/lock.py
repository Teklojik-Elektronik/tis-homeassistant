"""Support for TIS lock entities (Admin Lock)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Default password (should be changed by user)
DEFAULT_PASSWORD = "1234"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TIS lock entities from config entry."""
    # Get password from entry data or use default
    password = entry.data.get("admin_lock_password", DEFAULT_PASSWORD)
    
    # Create Admin Lock entity
    admin_lock = TISAdminLock("Admin Lock", password, hass)
    async_add_entities([admin_lock])


class TISAdminLock(LockEntity):
    """Representation of TIS Admin Lock."""
    
    def __init__(
        self,
        name: str,
        password: str,
        hass: HomeAssistant,
    ) -> None:
        """Initialize admin lock."""
        self._attr_name = name
        self._attr_unique_id = f"tis_admin_lock"
        self._attr_is_locked = True  # Start locked by default
        self._password = password
        self._attr_changed_by = None
        self._attr_code_format = r".*"  # Accept any code format
        self._timeout = 60  # Auto-lock timeout in seconds
        self._auto_lock_task = None
        self.hass = hass
        
        _LOGGER.info(f"🔒 Admin Lock initialized (default password: {DEFAULT_PASSWORD})")
    
    @property
    def name(self) -> str:
        """Return the name of the lock."""
        return self._attr_name
    
    @property
    def is_locked(self) -> bool:
        """Return true if lock is locked."""
        return self._attr_is_locked
    
    @property
    def code_format(self) -> str:
        """Return the code format."""
        return self._attr_code_format
    
    @property
    def changed_by(self) -> str | None:
        """Return who last changed the lock."""
        return self._attr_changed_by
    
    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        code = kwargs.get("code")
        
        # Check password
        if code and code == self._password:
            self._attr_is_locked = True
            self._attr_changed_by = "user"
            self.async_write_ha_state()
            
            # Fire event to notify other platforms (especially SELECT)
            self.hass.bus.async_fire("admin_lock", {"locked": True})
            
            _LOGGER.info(f"🔒 Admin Lock: LOCKED")
        else:
            _LOGGER.error("🔒 Admin Lock: Invalid password for lock")
            raise ValueError("Invalid password")
    
    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        code = kwargs.get("code")
        
        # Check password
        if code and code == self._password:
            self._attr_is_locked = False
            self._attr_changed_by = "user"
            self.async_write_ha_state()
            
            # Fire event to notify other platforms (especially SELECT)
            self.hass.bus.async_fire("admin_lock", {"locked": False})
            
            # Cancel previous auto-lock task if exists
            if self._auto_lock_task and not self._auto_lock_task.done():
                self._auto_lock_task.cancel()
            
            # Start auto-lock timer
            self._auto_lock_task = asyncio.create_task(self._auto_lock())
            
            _LOGGER.info(f"🔓 Admin Lock: UNLOCKED (auto-lock in {self._timeout}s)")
        else:
            _LOGGER.error("🔒 Admin Lock: Invalid password for unlock")
            raise ValueError("Invalid password")
    
    async def _auto_lock(self) -> None:
        """Automatically lock after timeout."""
        try:
            await asyncio.sleep(self._timeout)
            await self.async_lock(code=self._password)
            _LOGGER.info(f"🔒 Admin Lock: AUTO-LOCKED after {self._timeout}s")
        except asyncio.CancelledError:
            _LOGGER.debug("Auto-lock timer cancelled")
    
    async def async_open(self, **kwargs: Any) -> None:
        """Open the lock (same as unlock)."""
        await self.async_unlock(**kwargs)
