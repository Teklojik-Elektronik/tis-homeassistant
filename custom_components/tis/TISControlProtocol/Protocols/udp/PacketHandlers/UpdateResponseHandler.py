from homeassistant.core import HomeAssistant  # type: ignore
import logging


async def handle_update_response(hass: HomeAssistant, info: dict):
    # remove auxilary bytes which represents number of scenarios
    channels_number = info["additional_bytes"][0]
    event_data = {
        "device_id": info["device_id"],
        "subnet": info["device_id"][0],
        "device": info["device_id"][1],
        "feedback_type": "update_response",
        "additional_bytes": info["additional_bytes"],
        "channel_number": channels_number,
    }
    try:
        # Fire standard Home Assistant event
        hass.bus.async_fire("tis_update_response", event_data)
        # Keep device-specific event for backward compatibility
        hass.bus.async_fire(str(info["device_id"]), event_data)
    except Exception as e:
        logging.error(f"error in firing event: {e}")
