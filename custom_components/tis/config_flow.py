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


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TIS Control."""

    VERSION = 1
    
    def __init__(self):
        """Initialize."""
        self._discovered_devices = {}
    
    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return TISOptionsFlowHandler(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle initial step - get gateway IP and port."""
        errors = {}
        
        if user_input is not None:
            # Validate and create entry
            return self.async_create_entry(
                title="TIS Akıllı Ev Sistemi",
                data={
                    "gateway_ip": user_input["gateway_ip"],
                    "udp_port": user_input.get("udp_port", 6000),
                    "configured": True,
                },
            )
        
        # Show form to get gateway IP and port
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required("gateway_ip", default="192.168.1.200"): str,
                vol.Optional("udp_port", default=6000): int,
            }),
            errors=errors,
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
        """Manage the options - allow changing gateway IP and port."""
        if user_input is not None:
            # Update config entry data
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    "gateway_ip": user_input["gateway_ip"],
                    "udp_port": user_input.get("udp_port", 6000),
                }
            )
            return self.async_create_entry(title="", data={})
        
        # Show form with current values
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(
                    "gateway_ip", 
                    default=self.config_entry.data.get("gateway_ip", "192.168.1.200")
                ): str,
                vol.Optional(
                    "udp_port", 
                    default=self.config_entry.data.get("udp_port", 6000)
                ): int,
            }),
        )

