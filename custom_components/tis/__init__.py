"""TIS Integration - Decoded from original."""
from __future__ import annotations
import logging
import os
import sys
import json
import io
from attr import dataclass
import aiofiles
import ruamel.yaml

# CRITICAL: Remove system TISControlProtocol from path to force local version
import sys
_to_remove = [p for p in sys.path if 'site-packages' in p or 'dist-packages' in p]
for p in _to_remove:
    if p in sys.modules:
        # Clear cached imports
        mods_to_clear = [k for k in sys.modules.keys() if k.startswith('TISControlProtocol')]
        for mod in mods_to_clear:
            del sys.modules[mod]

# Force use of local TISControlProtocol
_COMPONENT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _COMPONENT_DIR)

from TISControlProtocol.api import TISApi
from TISControlProtocol.Protocols.udp.ProtocolHandler import TISProtocolHandler

# Verify we're using local version
logging.info(f"✅ Using TISControlProtocol from: {TISApi.__module__}")

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DEVICES_DICT, DOMAIN
from . import tis_configuration_dashboard


@dataclass
class TISData:
    """Runtime data for TIS integration."""
    api: TISApi


PLATFORMS = [
    Platform.LIGHT,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.SWITCH,
    Platform.COVER,
    Platform.CLIMATE,
    Platform.SELECT,
    Platform.LOCK,
    Platform.FAN,
    Platform.BUTTON,
]

type TISConfigEntry = ConfigEntry[TISData]

protocol_handler = TISProtocolHandler()


async def async_setup_entry(hass: HomeAssistant, entry: TISConfigEntry) -> bool:
    """Set up TIS integration."""
    # Create dashboard
    tis_configuration_dashboard.create()
    
    # Configure HTTP settings in configuration.yaml
    current_dir = os.path.dirname(__file__)
    base_dir = os.path.abspath(os.path.join(current_dir, "../../"))
    config_path = os.path.join(base_dir, "configuration.yaml")
    
    yaml = ruamel.yaml.YAML()
    async with aiofiles.open(config_path, "r") as f:
        contents = await f.read()
    
    config_data = await hass.async_add_executor_job(yaml.load, contents)
    
    http_settings = {
        "use_x_forwarded_for": True,
        "trusted_proxies": ["172.30.33.0/24"]
    }
    
    if "http" not in config_data or config_data["http"] != http_settings:
        logging.warning("Adding HTTP configuration to configuration.yaml")
        config_data["http"] = http_settings
        buffer = io.StringIO()
        await hass.async_add_executor_job(yaml.dump, config_data, buffer)
        async with aiofiles.open(config_path, "w") as f:
            await f.write(buffer.getvalue())
    else:
        logging.info("HTTP configuration already exists in configuration.yaml")
    
    # Read version from manifest
    try:
        async with aiofiles.open("/config/custom_components/tis_control/manifest.json", "r") as f:
            contents = await f.read()
            data = json.loads(contents)
            version = data["version"]
    except Exception as e:
        logging.warning(f"couldn't read the version error: {e}")
        version = "0.0.0"
    
    # Create TISApi instance
    tis_api = TISApi(
        port=int(entry.data["port"]),
        hass=hass,
        domain=DOMAIN,
        devices_dict=DEVICES_DICT,
        display_logo="./custom_components/tis_control/images/logo.png",
        version=version
    )
    
    entry.runtime_data = TISData(api=tis_api)
    hass.data.setdefault(DOMAIN, {"supported_platforms": PLATFORMS})
    
    # Connect to TIS
    try:
        await tis_api.connect()
    except ConnectionError as e:
        logging.error("error connecting to TIS api %s", e)
        return False
    
    # Setup platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TISConfigEntry) -> bool:
    """Unload TIS integration."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        return unload_ok
    return False
