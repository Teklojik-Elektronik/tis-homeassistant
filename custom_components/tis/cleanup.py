"""TIS Cleanup - Remove sidebar panel when integration is removed."""
import os
import logging
from ruamel.yaml import YAML

_LOGGER = logging.getLogger(__name__)

def remove_dashboard(hass):
    """Remove TIS sidebar panel from configuration.yaml."""
    try:
        base_dir = hass.config.config_dir
        config_path = os.path.join(base_dir, "configuration.yaml")
        
        # Initialize YAML
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=2, offset=0)
        
        # Read configuration.yaml
        if not os.path.exists(config_path):
            _LOGGER.warning("configuration.yaml not found at: %s", config_path)
            return False

        with open(config_path, "r", encoding='utf-8') as f:
            config = yaml.load(f) or {}

        # Remove panel if it exists
        if "panel_iframe" in config and "tis_configuration" in config["panel_iframe"]:
            _LOGGER.info("Removing TIS Configuration panel from sidebar")
            del config["panel_iframe"]["tis_configuration"]
            
            # If panel_iframe is now empty, remove it
            if not config["panel_iframe"]:
                del config["panel_iframe"]
            
            # Save configuration.yaml
            with open(config_path, "w", encoding='utf-8') as f:
                yaml.dump(config, f)
            
            _LOGGER.info("✓ TIS Configuration panel successfully removed from configuration.yaml")
            return True
        else:
            _LOGGER.debug("TIS Configuration panel not found in configuration.yaml")
            return True
                
    except PermissionError as e:
        _LOGGER.error("Permission denied writing to configuration.yaml: %s", e)
        return False
    except Exception as e:
        _LOGGER.error("Failed to remove TIS sidebar panel: %s", e)
        return False
