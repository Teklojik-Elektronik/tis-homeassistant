"""TIS Control Integration for Home Assistant - Works with TIS Addon."""
from __future__ import annotations

import asyncio
import logging
import json
import os
import socket
from pathlib import Path

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr

from .const import DOMAIN
from .tis_protocol import TISPacket, TISUDPClient

_LOGGER = logging.getLogger(__name__)

# All supported platforms
PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.LIGHT,
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
    Platform.CLIMATE,  # AC/HVAC control + Floor Heating ✅
    Platform.COVER,    # Curtain/Blind control ✅
    Platform.FAN,      # Fan speed control ✅
    Platform.BUTTON,   # Universal Switch ✅
    Platform.LOCK,     # Admin Lock ✅
    Platform.SELECT,   # Security Mode ✅
    Platform.WEATHER,  # Weather Station ✅
]
DEVICES_FILE = "/config/tis_devices.json"


def load_devices_from_file() -> dict:
    """Load devices from JSON file."""
    if os.path.exists(DEVICES_FILE):
        try:
            with open(DEVICES_FILE, 'r') as f:
                devices = json.load(f)
            _LOGGER.debug(f"Loaded {len(devices)} devices from {DEVICES_FILE}")
            return devices
        except Exception as e:
            _LOGGER.error(f"Failed to load devices: {e}")
            return {}
    return {}


def save_devices_to_file(devices: dict) -> None:
    """Save devices to JSON file."""
    try:
        with open(DEVICES_FILE, 'w') as f:
            json.dump(devices, f, indent=2, ensure_ascii=False)
        _LOGGER.debug(f"Saved {len(devices)} devices to {DEVICES_FILE}")
    except Exception as e:
        _LOGGER.error(f"Failed to save devices: {e}")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TIS Control from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    # Load devices from TIS Addon's JSON file
    devices = load_devices_from_file()
    
    if not devices:
        _LOGGER.warning(f"No devices found in {DEVICES_FILE}")
        _LOGGER.info("Add devices via TIS Addon Web UI (http://homeassistant.local:8888)")
    else:
        _LOGGER.info(f"Loaded {len(devices)} TIS devices from addon")
    
    # Store integration data
    hass.data[DOMAIN][entry.entry_id] = {
        "devices": devices,
        "gateway_ip": entry.data.get("gateway_ip", "192.168.1.200"),
        "udp_port": entry.data.get("udp_port", 6000),
        "configured": True,
        "file_watcher_task": None,
        "udp_listener_task": None,
        "update_callbacks": {},  # {(subnet, device, channel): callback_func}
    }
    
    # Forward to platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Start UDP listener for real-time state updates
    async def handle_control_response(parsed: dict, entry_data: dict):
        """Handle single channel control response (0x0032)"""
        if len(parsed['additional_data']) >= 3:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            channel = parsed['additional_data'][0]
            brightness_raw = parsed['additional_data'][2]
            
            brightness = int((brightness_raw / 248.0) * 100)
            is_on = brightness_raw > 0
            
            _LOGGER.info(f"🔦 Control response: {src_subnet}.{src_device} CH{channel} → "
                        f"{'ON' if is_on else 'OFF'} ({brightness}%)")
            
            callback_key = (src_subnet, src_device, channel)
            if callback_key in entry_data["update_callbacks"]:
                await entry_data["update_callbacks"][callback_key](is_on, brightness)
    
    async def handle_update_response(parsed: dict, entry_data: dict):
        """Handle multi-channel status response (0x0034)"""
        if len(parsed['additional_data']) >= 25:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            
            _LOGGER.info(f"Multi-channel status from {src_subnet}.{src_device}")
            
            updated_count = 0
            for channel in range(1, 25):
                brightness_raw = parsed['additional_data'][channel]
                brightness = int((brightness_raw / 248.0) * 100)
                is_on = brightness_raw > 0
                
                callback_key = (src_subnet, src_device, channel)
                if callback_key in entry_data["update_callbacks"]:
                    await entry_data["update_callbacks"][callback_key](is_on, brightness)
                    updated_count += 1
            
            _LOGGER.info(f"Updated {updated_count} channels for {src_subnet}.{src_device}")
    
    async def handle_health_feedback(parsed: dict, entry_data: dict):
        """Handle health sensor feedback (0x2025) - Based on TISControlProtocol"""
        if len(parsed['additional_data']) >= 15:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            # DEBUG: Log first 20 bytes of additional_data
            _LOGGER.info(f"🔍 Additional_data (first 20 bytes): {data[:20].hex(' ').upper()}")
            
            # Parse health sensor data (TISControlProtocol HealthFeedbackHandler format)
            # Parser skips 01 FE (target device), so additional_data starts at 0x14
            # Offsets adjusted based on real packet analysis (2025-12-08)
            try:
                lux = int.from_bytes(data[5:7], 'big')          # [5-6]: Light level (lx)
                noise = int.from_bytes(data[7:9], 'big')        # [7-8]: Noise level (raw value)
                eco2 = int.from_bytes(data[9:11], 'big')        # [9-10]: eCO2 (ppm)
                tvoc = int.from_bytes(data[11:13], 'big')       # [11-12]: TVOC (μg/m³)
                temperature = int(data[13])                     # [13]: Temperature (single byte, °C)
                humidity = int(data[14])                        # [14]: Humidity (%)
                
                # Optional: CO sensor and state flags
                co = 0
                eco2_state = 0
                tvoc_state = 0
                co_state = 0
                
                if len(data) >= 29:
                    co = int.from_bytes(data[27:29], 'big')     # [27-28]: CO level (ppm)
                if len(data) >= 34:
                    eco2_state = int(data[31])                  # [31]: eCO2 state (0-5)
                    tvoc_state = int(data[32])                  # [32]: TVOC state (0-5)
                    co_state = int(data[33])                    # [33]: CO state (0-5)
                
                _LOGGER.info(f"🏥 Health sensor: {src_subnet}.{src_device} → "
                            f"Temp={temperature}°C, Humidity={humidity}%, eCO2={eco2}ppm, "
                            f"TVOC={tvoc}ppb, CO={co}ppm, Lux={lux}lx, Noise={noise}dB")
                
                # Fire event for sensor platform
                hass.bus.async_fire("tis_health_feedback", {
                    "subnet": src_subnet,
                    "device": src_device,
                    "temperature": temperature,
                    "humidity": humidity,
                    "eco2": eco2,
                    "tvoc": tvoc,
                    "co": co,
                    "lux": lux,
                    "noise": noise,
                    "eco2_state": eco2_state,
                    "tvoc_state": tvoc_state,
                    "co_state": co_state
                })
            except Exception as e:
                _LOGGER.error(f"Error parsing health sensor data from {src_subnet}.{src_device}: {e}", exc_info=True)
    
    async def handle_energy_feedback(parsed: dict, entry_data: dict):
        """Handle energy meter feedback (0x2011) - TISControlProtocol with 3-phase support"""
        if len(parsed['additional_data']) >= 2:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            channel = data[0] + 1  # Convert 0-based to 1-based
            sub_operation = data[1]
            
            try:
                if sub_operation == 0xDA:  # Monthly energy
                    if len(data) >= 18:
                        energy = int.from_bytes(data[16:18], 'big')
                        
                        _LOGGER.info(f"⚡ Monthly energy: {src_subnet}.{src_device} CH{channel} → {energy} kWh")
                        
                        hass.bus.async_fire("tis_energy_feedback", {
                            "subnet": src_subnet,
                            "device": src_device,
                            "channel": channel,
                            "feedback_type": "monthly_energy",
                            "energy": energy
                        })
                
                elif sub_operation == 0x65:  # Real-time 3-phase energy (MET-EN-3PH)
                    if len(data) >= 147:
                        import struct
                        
                        def big_endian_to_float(bytes_data):
                            return round(struct.unpack('>f', bytes(bytes_data))[0], 1)
                        
                        energy_data = {
                            "v1": big_endian_to_float(data[3:7]),
                            "v2": big_endian_to_float(data[7:11]),
                            "v3": big_endian_to_float(data[11:15]),
                            "current_p1": big_endian_to_float(data[15:19]),
                            "current_p2": big_endian_to_float(data[19:23]),
                            "current_p3": big_endian_to_float(data[23:27]),
                            "active_p1": big_endian_to_float(data[27:31]),
                            "active_p2": big_endian_to_float(data[31:35]),
                            "active_p3": big_endian_to_float(data[35:39]),
                            "apparent1": big_endian_to_float(data[39:43]),
                            "apparent2": big_endian_to_float(data[43:47]),
                            "apparent3": big_endian_to_float(data[47:51]),
                            "reactive1": big_endian_to_float(data[51:55]),
                            "reactive2": big_endian_to_float(data[55:59]),
                            "reactive3": big_endian_to_float(data[59:63]),
                            "pf1": big_endian_to_float(data[63:67]),
                            "pf2": big_endian_to_float(data[67:71]),
                            "pf3": big_endian_to_float(data[71:75]),
                            "pa1": big_endian_to_float(data[75:79]),
                            "pa2": big_endian_to_float(data[79:83]),
                            "pa3": big_endian_to_float(data[83:87]),
                            "avg_voltage": big_endian_to_float(data[87:91]),
                            "avg_current": big_endian_to_float(data[91:95]),
                            "sum_current": big_endian_to_float(data[95:99]),
                            "total_power": big_endian_to_float(data[107:111]),
                            "total_volt_amps": big_endian_to_float(data[115:119]),
                            "total_var": big_endian_to_float(data[123:127]),
                            "total_pf": big_endian_to_float(data[127:131]),
                            "total_pa": big_endian_to_float(data[135:139]),
                            "frequency": big_endian_to_float(data[143:147]),
                        }
                        
                        _LOGGER.info(f"⚡ 3-Phase energy: {src_subnet}.{src_device} CH{channel} → "
                                    f"V1={energy_data['v1']}V, V2={energy_data['v2']}V, V3={energy_data['v3']}V, "
                                    f"P={energy_data['total_power']}W, Freq={energy_data['frequency']}Hz")
                        
                        hass.bus.async_fire("tis_energy_feedback", {
                            "subnet": src_subnet,
                            "device": src_device,
                            "channel": channel,
                            "feedback_type": "energy_3phase",
                            "energy": energy_data
                        })
                
                else:  # Simple energy format (fallback)
                    if len(data) >= 9:
                        voltage = int.from_bytes(data[2:4], 'big') / 10.0
                        current = int.from_bytes(data[4:6], 'big') / 1000.0
                        power = int.from_bytes(data[6:8], 'big')
                        energy = int.from_bytes(data[8:10], 'big') / 100.0 if len(data) >= 10 else 0
                        
                        _LOGGER.info(f"⚡ Energy meter: {src_subnet}.{src_device} CH{channel} → "
                                    f"V={voltage}V, I={current}A, P={power}W, E={energy}kWh")
                        
                        hass.bus.async_fire("tis_energy_feedback", {
                            "subnet": src_subnet,
                            "device": src_device,
                            "channel": channel,
                            "feedback_type": "energy_simple",
                            "voltage": voltage,
                            "current": current,
                            "power": power,
                            "energy": energy
                        })
            
            except Exception as e:
                _LOGGER.error(f"Error parsing energy data: {e}", exc_info=True)
    
    async def handle_climate_feedback(parsed: dict, entry_data: dict):
        """Handle AC/climate feedback (0xE0EF / 0xE0ED) - TISControlProtocol compatible"""
        if len(parsed['additional_data']) >= 5:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            ac_number = data[1]  # AC number (0-31 for TIS-VRF-AC)
            state = data[2]  # 0=OFF, 1=ON
            cool_temp = data[3]
            mode_and_fan = data[4]
            mode = (mode_and_fan >> 4) & 0x0F  # Upper 4 bits
            fan_speed = mode_and_fan & 0x0F    # Lower 4 bits
            
            # Optional heat and auto temperatures
            heat_temp = data[7] if len(data) > 7 else cool_temp
            auto_temp = data[9] if len(data) > 9 else cool_temp
            
            mode_names = {0: "Cool", 1: "Heat", 2: "Fan", 3: "Auto", 4: "Dry"}
            fan_names = {0: "Auto", 1: "High", 2: "Medium", 3: "Low"}
            
            _LOGGER.info(f"❄️ AC feedback: {src_subnet}.{src_device} AC{ac_number} → "
                        f"{'ON' if state else 'OFF'}, Cool={cool_temp}°C, Heat={heat_temp}°C, "
                        f"Mode={mode_names.get(mode, 'Unknown')}, "
                        f"Fan={fan_names.get(fan_speed, 'Unknown')}")
            
            # Fire event for climate platform
            hass.bus.async_fire("tis_climate_feedback", {
                "subnet": src_subnet,
                "device": src_device,
                "ac_number": ac_number,
                "state": state,
                "cool_temp": cool_temp,
                "heat_temp": heat_temp,
                "auto_temp": auto_temp,
                "mode": mode,
                "fan_speed": fan_speed
            })
    
    async def handle_security_feedback(parsed: dict, entry_data: dict):
        """Handle security status feedback (0x011F / 0x0105) - TISControlProtocol compatible"""
        if len(parsed['additional_data']) >= 2:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            channel = data[0]
            mode = data[1]  # 1=Vacation, 2=Away, 3=Night, 6=Disarm
            
            mode_names = {1: "Vacation", 2: "Away", 3: "Night", 6: "Disarmed"}
            
            _LOGGER.info(f"🔒 Security feedback: {src_subnet}.{src_device} CH{channel} → "
                        f"Mode={mode_names.get(mode, 'Unknown')}")
            
            # Fire event for alarm_control_panel platform
            hass.bus.async_fire("tis_security_feedback", {
                "subnet": src_subnet,
                "device": src_device,
                "channel": channel,
                "mode": mode
            })
    
    async def handle_binary_feedback(parsed: dict, entry_data: dict):
        """Handle binary sensor feedback (0xEFFF) - TISControlProtocol"""
        if len(parsed['additional_data']) >= 1:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            # Remove auxiliary bytes (number of scenarios)
            len_aux = data[0]
            binary_data = data[len_aux + 1:] if len(data) > len_aux else []
            
            _LOGGER.info(f"🚪 Binary sensor feedback: {src_subnet}.{src_device} → "
                        f"{len(binary_data)} states: {binary_data[:10]}...")
            
            # Fire event for binary_sensor platform
            hass.bus.async_fire("tis_binary_feedback", {
                "subnet": src_subnet,
                "device": src_device,
                "binary_states": binary_data
            })
    
    async def handle_auto_binary_feedback(parsed: dict, entry_data: dict):
        """Handle auto binary feedback (0xDC22) - RCU devices - TISControlProtocol"""
        if len(parsed['additional_data']) >= 1:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            _LOGGER.info(f"🔄 Auto binary feedback: {src_subnet}.{src_device} → "
                        f"{len(data)} bytes: {data[:10]}...")
            
            # Fire event for binary_sensor platform
            hass.bus.async_fire("tis_auto_binary_feedback", {
                "subnet": src_subnet,
                "device": src_device,
                "binary_states": data
            })
    
    async def handle_floor_feedback(parsed: dict, entry_data: dict):
        """Handle floor heating feedback (0x1945) - TISControlProtocol"""
        if len(parsed['additional_data']) >= 3:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            # Floor number mapping from TISControlProtocol
            FLOOR_NUMBER_MAP = {0x22: 0, 0x23: 1, 0x24: 2, 0x25: 3}
            
            if data[0] == 0x2E:  # Multi-floor format
                floor_number = data[1] - 1
                sub_operation = data[2]
                operation_value = data[3] if len(data) > 3 else 0
            else:
                floor_number = FLOOR_NUMBER_MAP.get(data[0], 0)
                sub_operation = data[1]
                operation_value = data[2]
            
            _LOGGER.info(f"🔥 Floor heating feedback: {src_subnet}.{src_device} Floor{floor_number} → "
                        f"SubOp=0x{sub_operation:02X}, Value={operation_value}")
            
            # Fire event for climate platform (floor heating)
            hass.bus.async_fire("tis_floor_feedback", {
                "subnet": src_subnet,
                "device": src_device,
                "floor_number": floor_number,
                "sub_operation": sub_operation,
                "operation_value": operation_value
            })
    
    async def handle_climate_binary_feedback(parsed: dict, entry_data: dict):
        """Handle climate binary feedback (0xE3D9) - AC/Floor control - TISControlProtocol"""
        if len(parsed['additional_data']) >= 3:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            # AC/Floor number detection
            AC_NUMBER_MAP = {0x19: 0, 0x1A: 1, 0x1B: 2, 0x1C: 3, 0x1D: 4, 0x1E: 5, 0x1F: 6, 0x20: 7}
            FLOOR_NUMBER_MAP = {0x22: 0, 0x23: 1, 0x24: 2, 0x25: 3}
            
            if data[0] <= 0x18:
                sub_operation = data[0]
                operation_value = data[1]
                feedback_type = "ac_feedback" if data[0] < 0x14 else "floor_feedback"
                number = 0
            elif data[0] == 0x2E:
                number = data[1] - 1
                sub_operation = 0x14 if data[2] == 0x03 else 0x18 if data[2] == 0x04 else data[2]
                operation_value = data[3] if len(data) > 3 else 0
                feedback_type = "floor_feedback"
            else:
                ac_number = AC_NUMBER_MAP.get(data[0])
                floor_number = FLOOR_NUMBER_MAP.get(data[0])
                sub_operation = data[1]
                operation_value = data[2]
                
                if ac_number is not None:
                    feedback_type = "ac_feedback"
                    number = ac_number
                else:
                    feedback_type = "floor_feedback"
                    number = floor_number
            
            _LOGGER.info(f"🌡️ Climate binary feedback: {src_subnet}.{src_device} {feedback_type} #{number} → "
                        f"SubOp=0x{sub_operation:02X}, Value={operation_value}")
            
            hass.bus.async_fire(f"tis_{feedback_type}", {
                "subnet": src_subnet,
                "device": src_device,
                "number": number,
                "sub_operation": sub_operation,
                "operation_value": operation_value
            })
    
    async def handle_realtime_feedback(parsed: dict, entry_data: dict):
        """Handle real-time feedback (0x0031) - TISControlProtocol"""
        src_subnet = parsed['src_subnet']
        src_device = parsed['src_device']
        data = parsed['additional_data']
        
        _LOGGER.debug(f"⚡ Real-time feedback: {src_subnet}.{src_device} → {len(data)} bytes")
        
        # Fire generic event
        hass.bus.async_fire("tis_realtime_feedback", {
            "subnet": src_subnet,
            "device": src_device,
            "data": data
        })
    
    async def handle_luna_temp_feedback(parsed: dict, entry_data: dict):
        """Handle Luna temperature feedback (0xE3E8) - TISControlProtocol"""
        if len(parsed['additional_data']) >= 2:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            temperature = int(data[1])
            
            _LOGGER.info(f"🌡️ Luna temp: {src_subnet}.{src_device} → {temperature}°C")
            
            # Fire event for sensor platform
            hass.bus.async_fire("tis_luna_temp_feedback", {
                "subnet": src_subnet,
                "device": src_device,
                "temperature": temperature
            })
    
    async def handle_weather_feedback(parsed: dict, entry_data: dict):
        """Handle weather station feedback (0x2021) - TISControlProtocol"""
        if len(parsed['additional_data']) >= 10:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            # Parse weather data (byte structure from TISControlProtocol)
            temperature = int(data[0]) if len(data) > 0 else None
            humidity = int(data[1]) if len(data) > 1 else None
            uv_index = float(data[2]) if len(data) > 2 else None
            wind_speed = int(data[3]) if len(data) > 3 else None
            wind_bearing = int(data[4]) if len(data) > 4 else None
            pressure = int(data[5]) if len(data) > 5 else None
            
            _LOGGER.info(f"☁️ Weather: {src_subnet}.{src_device} → "
                        f"Temp={temperature}°C, Humidity={humidity}%, UV={uv_index}")
            
            # Fire event for weather platform
            hass.bus.async_fire("tis_weather_feedback", {
                "subnet": src_subnet,
                "device": src_device,
                "temperature": temperature,
                "humidity": humidity,
                "uv_index": uv_index,
                "wind_speed": wind_speed,
                "wind_bearing": wind_bearing,
                "pressure": pressure,
                "condition": None  # Can be determined from other data
            })
    
    async def handle_floor_binary_feedback(parsed: dict, entry_data: dict):
        """Handle floor heating binary feedback (0x1945) - TISControlProtocol"""
        if len(parsed['additional_data']) >= 6:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            heater_number = data[0]
            state = data[3]
            temperature = data[5]
            
            _LOGGER.info(f"🔥 Floor binary feedback: {src_subnet}.{src_device} Heater{heater_number} → "
                        f"{'ON' if state else 'OFF'}, Temp={temperature}°C")
            
            # Fire event for climate platform
            hass.bus.async_fire("tis_floor_feedback", {
                "subnet": src_subnet,
                "device": src_device,
                "heater_number": heater_number,
                "state": state,
                "temperature": temperature
            })
    
    async def handle_climate_binary_feedback(parsed: dict, entry_data: dict):
        """Handle climate binary feedback (0xE3D9) - Can include AC or Floor heating"""
        if len(parsed['additional_data']) >= 3:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            # Parse based on TISControlProtocol logic
            first_byte = data[0]
            
            # Floor heater number mapping
            floor_number_map = {0x22: 0, 0x23: 1, 0x24: 2, 0x25: 3}
            
            if first_byte in floor_number_map:
                # Floor heating feedback
                heater_number = floor_number_map[first_byte]
                sub_operation = data[1]
                operation_value = data[2]
                
                _LOGGER.info(f"🔥 Floor climate feedback: {src_subnet}.{src_device} Heater{heater_number} → "
                            f"SubOp={sub_operation}, Value={operation_value}")
                
                # Fire event for climate platform
                hass.bus.async_fire("tis_floor_feedback", {
                    "subnet": src_subnet,
                    "device": src_device,
                    "heater_number": heater_number,
                    "sub_operation": sub_operation,
                    "value": operation_value
                })
            else:
                _LOGGER.debug(f"🌡️ Climate binary feedback (not floor): {first_byte:02X}")
    
    async def handle_analog_feedback(parsed: dict, entry_data: dict):
        """Handle analog sensor feedback (0xEF01) - TISControlProtocol"""
        if len(parsed['additional_data']) >= 1:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            channels_num = int(data[0])
            analog_values = list(data[1:channels_num + 1]) if len(data) > channels_num else []
            
            _LOGGER.info(f"📊 Analog sensor: {src_subnet}.{src_device} → {channels_num} channels: {analog_values}")
            
            # Fire event for sensor platform
            hass.bus.async_fire("tis_analog_feedback", {
                "subnet": src_subnet,
                "device": src_device,
                "channels": channels_num,
                "analog_values": analog_values
            })
    
    async def handle_weather_feedback(parsed: dict, entry_data: dict):
        """Handle weather station feedback (0x2021) - TISControlProtocol"""
        if len(parsed['additional_data']) >= 24:
            src_subnet = parsed['src_subnet']
            src_device = parsed['src_device']
            data = parsed['additional_data']
            
            # Wind direction mapping
            wind_direction_map = {
                0x01: "north", 0x02: "north east", 0x04: "east", 0x08: "south east",
                0x10: "south", 0x20: "south west", 0x40: "west", 0x80: "north west"
            }
            
            try:
                import struct
                
                def big_endian_to_float(bytes_data):
                    return struct.unpack('>f', bytes(bytes_data))[0]
                
                wind_direction = wind_direction_map.get(int(data[3]), "unknown")
                temperature = big_endian_to_float(data[4:8])
                humidity = int(data[8])
                wind_speed = big_endian_to_float(data[9:13])
                gust_speed = big_endian_to_float(data[13:17])
                rainfall = int.from_bytes(data[17:19], 'big')
                lighting = big_endian_to_float(data[19:23])
                uv = int(data[23])
                
                _LOGGER.info(f"🌤️ Weather station: {src_subnet}.{src_device} → "
                            f"Temp={temperature:.1f}°C, Humidity={humidity}%, "
                            f"Wind={wind_speed:.1f}m/s {wind_direction}, UV={uv}")
                
                # Fire event for weather sensor platform
                hass.bus.async_fire("tis_weather_feedback", {
                    "subnet": src_subnet,
                    "device": src_device,
                    "wind_direction": wind_direction,
                    "temperature": temperature,
                    "humidity": humidity,
                    "wind_speed": wind_speed,
                    "gust_speed": gust_speed,
                    "rainfall": rainfall,
                    "lighting": lighting,
                    "uv": uv
                })
            except Exception as e:
                _LOGGER.error(f"Error parsing weather data: {e}")
    
    async def handle_discovery_feedback(parsed: dict, entry_data: dict):
        """Handle discovery response (0x000F) - TISControlProtocol"""
        src_subnet = parsed['src_subnet']
        src_device = parsed['src_device']
        data = parsed['additional_data']
        
        _LOGGER.info(f"🔍 Discovery response: {src_subnet}.{src_device} → {len(data)} bytes")
        
        # Fire discovery event
        hass.bus.async_fire("tis_discovery_feedback", {
            "subnet": src_subnet,
            "device": src_device,
            "data": data
        })
    
    async def udp_listener():
        """Listen for TIS UDP packets and update entity states."""
        entry_data = hass.data[DOMAIN][entry.entry_id]
        udp_port = entry_data["udp_port"]
        
        _LOGGER.info(f"Starting TIS UDP listener on port {udp_port}")
        
        # Create UDP socket for receiving broadcasts
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Enable broadcast reception
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except AttributeError:
            pass  # Not all systems support SO_BROADCAST
        
        try:
            # Bind to all interfaces on the UDP port
            sock.bind(('0.0.0.0', udp_port))
            sock.setblocking(False)
            _LOGGER.info(f"✅ Successfully bound UDP socket to 0.0.0.0:{udp_port}")
        except OSError as e:
            _LOGGER.error(f"❌ CRITICAL: Could not bind to port {udp_port}: {e}")
            _LOGGER.error("UDP listener will NOT work! Check if another process is using the port.")
            sock.close()
            sock = None
        
        try:
            while True:
                # Check if socket is available
                if sock is None:
                    _LOGGER.error("UDP socket not available, using polling mode only")
                    await asyncio.sleep(5)
                    # Polling logic will happen in the except block below
                    raise BlockingIOError("No socket available")
                
                try:
                    # Non-blocking receive with timeout
                    data, addr = await asyncio.wait_for(
                        hass.loop.sock_recvfrom(sock, 4096),
                        timeout=3.0
                    )
                    
                    _LOGGER.info(f"📡 UDP packet from {addr}: {len(data)} bytes")
                    _LOGGER.info(f"📦 HEX: {data.hex(' ').upper()}")
                    
                    # Parse packet (skip SMARTCLOUD header if present)
                    if b'SMARTCLOUD' in data:
                        smartcloud_index = data.find(b'SMARTCLOUD')
                        tis_data = data[smartcloud_index + 10:]
                    else:
                        tis_data = data
                    
                    parsed = TISPacket.parse(tis_data)
                    
                    if parsed:
                        src_subnet = parsed['src_subnet']
                        src_device = parsed['src_device']
                        op_code = parsed['op_code']
                        
                        _LOGGER.info(f"✅ Parsed: OpCode 0x{op_code:04X} from {src_subnet}.{src_device}")
                        
                        # OpCode-based dispatch system (TISControlProtocol compatible)
                        try:
                            if op_code == 0x0032:  # Control response
                                await handle_control_response(parsed, entry_data)
                            elif op_code == 0x0034:  # Multi-channel status update
                                await handle_update_response(parsed, entry_data)
                            elif op_code == 0x2025:  # Health sensor feedback (CORRECTED from 0x2024)
                                await handle_health_feedback(parsed, entry_data)
                            elif op_code == 0x2011:  # Energy meter feedback (CORRECTED from 0x2010)
                                await handle_energy_feedback(parsed, entry_data)
                            elif op_code == 0xE0EF:  # AC/climate feedback (CORRECTED from 0xE0EC)
                                await handle_climate_feedback(parsed, entry_data)
                            elif op_code == 0xE0ED:  # AC/climate feedback (alternative)
                                await handle_climate_feedback(parsed, entry_data)
                            elif op_code == 0x011F:  # Security update feedback (CORRECTED from 0x011E)
                                await handle_security_feedback(parsed, entry_data)
                            elif op_code == 0x0105:  # Security control feedback
                                await handle_security_feedback(parsed, entry_data)
                            elif op_code == 0xEFFF:  # Binary sensor feedback
                                await handle_binary_feedback(parsed, entry_data)
                            elif op_code == 0xDC22:  # Auto binary feedback (RCU devices)
                                await handle_auto_binary_feedback(parsed, entry_data)
                            elif op_code == 0x1945:  # Floor heating binary feedback
                                await handle_floor_binary_feedback(parsed, entry_data)
                            elif op_code == 0xE3D9:  # Climate binary feedback (includes floor)
                                await handle_climate_binary_feedback(parsed, entry_data)
                            elif op_code == 0x0031:  # Real-time feedback
                                await handle_realtime_feedback(parsed, entry_data)
                            elif op_code == 0xE3E8:  # Luna temperature feedback
                                await handle_luna_temp_feedback(parsed, entry_data)
                            elif op_code == 0xEF01:  # Analog sensor feedback
                                await handle_analog_feedback(parsed, entry_data)
                            elif op_code == 0x2021:  # Weather station feedback
                                await handle_weather_feedback(parsed, entry_data)
                            elif op_code == 0x000F:  # Discovery response
                                await handle_discovery_feedback(parsed, entry_data)
                            else:
                                _LOGGER.debug(f"Unhandled OpCode: 0x{op_code:04X}")
                        except Exception as e:
                            _LOGGER.error(f"Error in handler for OpCode 0x{op_code:04X}: {e}", exc_info=True)
                
                except asyncio.TimeoutError:
                    # No UDP packet received within timeout, continue listening
                    continue
                    
                except (BlockingIOError, OSError) as e:
                    _LOGGER.debug(f"Socket error (will retry): {e}")
                    await asyncio.sleep(1)
                    continue
                    
                except Exception as e:
                    _LOGGER.error(f"Error processing UDP packet: {e}", exc_info=True)
                    await asyncio.sleep(0.1)
                    
        except asyncio.CancelledError:
            _LOGGER.info("TIS UDP listener stopped")
        finally:
            sock.close()
    
    # Start UDP listener task
    udp_task = hass.loop.create_task(udp_listener())
    hass.data[DOMAIN][entry.entry_id]["udp_listener_task"] = udp_task
    
    # Start file watcher to detect changes in tis_devices.json
    async def watch_devices_file():
        """Watch for changes in devices file and reload integration."""
        last_mtime = 0
        if os.path.exists(DEVICES_FILE):
            last_mtime = os.path.getmtime(DEVICES_FILE)
        
        while True:
            await asyncio.sleep(2)  # Check every 2 seconds
            
            try:
                if os.path.exists(DEVICES_FILE):
                    current_mtime = os.path.getmtime(DEVICES_FILE)
                    if current_mtime != last_mtime:
                        last_mtime = current_mtime
                        _LOGGER.info("Devices file changed, reloading integration...")
                        
                        # Reload the config entry
                        await hass.config_entries.async_reload(entry.entry_id)
            except Exception as e:
                _LOGGER.error(f"Error watching devices file: {e}")
    
    # Start file watcher task
    watcher_task = hass.loop.create_task(watch_devices_file())
    hass.data[DOMAIN][entry.entry_id]["file_watcher_task"] = watcher_task
    
    _LOGGER.info(f"TIS Integration loaded: {len(devices)} devices, UDP listener on port {entry.data.get('udp_port', 6000)}")
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    entry_data = hass.data[DOMAIN].get(entry.entry_id)
    
    # Stop UDP listener
    if entry_data and entry_data.get("udp_listener_task"):
        udp_task = entry_data["udp_listener_task"]
        udp_task.cancel()
        try:
            await udp_task
        except asyncio.CancelledError:
            pass
    
    # Stop file watcher
    if entry_data and entry_data.get("file_watcher_task"):
        watcher_task = entry_data["file_watcher_task"]
        watcher_task.cancel()
        try:
            await watcher_task
        except asyncio.CancelledError:
            pass
    
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOGGER.info("TIS Integration unloaded successfully")
    
    return unload_ok
    
    return unload_ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove a device from integration and JSON file."""
    # Get device identifier
    identifiers = list(device_entry.identifiers)
    if not identifiers:
        return True
    
    domain, unique_id = identifiers[0]
    if domain != DOMAIN:
        return True
    
    try:
        _LOGGER.info(f"Removing TIS device: {unique_id}")
        
        # Load current devices
        devices = load_devices_from_file()
        
        # Remove device from JSON
        if unique_id in devices:
            del devices[unique_id]
            save_devices_to_file(devices)
            _LOGGER.info(f"Removed {unique_id} from devices file")
            
            # Update integration data
            entry_data = hass.data[DOMAIN].get(config_entry.entry_id, {})
            if "devices" in entry_data:
                entry_data["devices"] = devices
        else:
            _LOGGER.warning(f"Device {unique_id} not found in devices file")
        
        return True
    
    except Exception as e:
        _LOGGER.error(f"Error removing device: {e}")
        return False

