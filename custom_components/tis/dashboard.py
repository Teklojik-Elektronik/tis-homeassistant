"""TIS Dashboard Setup - Sidebar Panel to Web UI."""
import os
import logging
from ruamel.yaml import YAML

_LOGGER = logging.getLogger(__name__)

def setup_dashboard(hass):
    """Setup the TIS sidebar panel pointing to Web UI."""
    try:
        base_dir = hass.config.config_dir
        config_path = os.path.join(base_dir, "configuration.yaml")
        
        # Initialize YAML
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=2, offset=0)
        
        # Check if file exists
        if not os.path.exists(config_path):
            _LOGGER.error("configuration.yaml not found at: %s", config_path)
            return False

        # Read configuration.yaml
        with open(config_path, "r", encoding='utf-8') as f:
            config = yaml.load(f) or {}

        # Add panel config if missing
        if "panel_iframe" not in config:
            config["panel_iframe"] = {}
        
        # TIS Configuration panel - points to Web UI (port 8888)
        if "tis_configuration" not in config["panel_iframe"]:
            _LOGGER.info("Adding TIS Configuration panel to sidebar")
            config["panel_iframe"]["tis_configuration"] = {
                "title": "TIS Configuration",
                "icon": "mdi:chip",
                "url": "http://homeassistant.local:8888",
                "require_admin": False
            }
            
            # Save configuration.yaml
            with open(config_path, "w", encoding='utf-8') as f:
                yaml.dump(config, f)
            
            _LOGGER.info("✓ TIS Configuration panel successfully added to configuration.yaml")
            return True
        else:
            _LOGGER.debug("TIS Configuration panel already exists in configuration.yaml")
            return True
                
    except PermissionError as e:
        _LOGGER.error("Permission denied writing to configuration.yaml: %s", e)
        return False
    except Exception as e:
        _LOGGER.error("Failed to setup TIS sidebar panel: %s", e)
        return False
