"""Config flow for TIS Control integration - UDP Based."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_SUBNET, CONF_DEVICE
from .api import TISDevice
from .discovery import discover_tis_devices

_LOGGER = logging.getLogger(__name__)


class TISConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TIS Control."""

    VERSION = 1
    
    def __init__(self):
        """Initialize."""
        self._discovered_devices = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle initial step - create entry and redirect to web UI."""
        if user_input is not None or self._async_current_entries():
            # Already configured or user confirmed
            return self.async_abort(reason="already_configured")
        
        # Create a single entry for TIS system (no per-device config)
        return self.async_create_entry(
            title="TIS Akıllı Ev Sistemi",
            data={
                "configured": True,
                "web_ui_port": 8888,
            },
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user()
