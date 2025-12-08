from homeassistant.core import HomeAssistant  # type: ignore
import logging


class PacketDispatcher:
    def __init__(self, hass: HomeAssistant, OPERATIONS_DICT: dict):
        self.hass = hass
        self.operations_dict = OPERATIONS_DICT

    async def dispatch_packet(self, info):
        try:
            packet_handler = self.operations_dict.get(
                tuple(info["operation_code"]), "unknown operation"
            )
            if packet_handler != "unknown operation":
                logging.info(f"📨 Dispatching to handler: {packet_handler.__name__} for OpCode 0x{info['operation_code'][0]:02X}{info['operation_code'][1]:02X}")
                await packet_handler(self.hass, info)
            else:
                logging.warning(f"❌ Unknown operation code: 0x{info['operation_code'][0]:02X}{info['operation_code'][1]:02X}")
        except Exception as e:
            logging.error(f"💥 Error dispatching packet: {e}, OpCode: {info.get('operation_code', 'unknown')}")
