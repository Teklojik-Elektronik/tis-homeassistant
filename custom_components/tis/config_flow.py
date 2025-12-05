"""Config flow for TIS Control integration - UDP Based."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class TISConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TIS Control."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return TISOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle initial step - create entry and redirect to web UI."""
        # Check if already configured
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        
        if user_input is not None:
            # User confirmed, create entry
            return self.async_create_entry(
                title="TIS Akıllı Ev Sistemi",
                data={
                    "configured": True,
                    "gateway_ip": "192.168.1.200",
                    "udp_port": 6000,
                },
            )
        
        # Show confirmation form
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({}),
            description_placeholders={
                "info": "TIS Akıllı Ev Sistemi entegrasyonu yüklenecek. Cihazları TIS Addon web arayüzünden ekleyebilirsiniz."
            }
        )

    async def async_step_import(self, import_data: dict[str, Any]) -> FlowResult:
        """Handle import from configuration.yaml."""
        return await self.async_step_user()


class TISOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle TIS options (allows device/entity removal)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options - mainly for UI purposes."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
            description_placeholders={
                "info": "TIS cihazları TIS Addon web arayüzünden yönetilir. Entity'leri silmek için cihaz sayfasından entity'yi seçip sağ üst köşedeki ayarlar menüsünü kullanın."
            }
        )

