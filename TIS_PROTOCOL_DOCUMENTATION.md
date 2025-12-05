# TIS Protocol & Database Documentation

**Generated:** 2025-12-05  
**Source:** tis.db3 (TIS DevSearch Configuration Database)  
**Purpose:** Complete reference for TIS Home Automation Protocol implementation

---

## Table of Contents

1. [Protocol OpCodes](#protocol-opcodes)
2. [Packet Structure](#packet-structure)
3. [Device Types](#device-types)
4. [Channel Configurations](#channel-configurations)
5. [Important Findings](#important-findings)

---

## Protocol OpCodes

### Discovered OpCodes (from TIS DevSearch packet analysis)

| OpCode | Direction | Description | Additional Data |
|--------|-----------|-------------|-----------------|
| `0x0031` | → Device | Channel control command | `[channel, 0x00, brightness, ...]` |
| `0x0032` | ← Device | Channel feedback/status | `[channel, 0xF8, brightness, ...]` |
| `0x0033` | → Device | Multi-channel status query | Empty (requests all channels) |
| `0x0034` | ← Device | Multi-channel status response | 24 bytes (one per channel) |
| `0xF00E` | → Device | Channel name query | `[channel_number]` |
| `0xF00F` | ← Device | Channel name response | `[channel, ...UTF-8 name bytes...]` |
| `0xEFFD` | → Device | Device info query | Variable |
| `0xEFFE` | ← Device | Device info response | Variable |
| `0xF00A` | → Device | Unknown function query | Variable |
| `0xF00B` | ← Device | Unknown function response | Variable |
| `0xF012` | → Device | Unknown function query | Variable |
| `0xF013` | ← Device | Unknown function response | Variable |

### Brightness Encoding

- **Range:** 0-248 (raw value)
- **Conversion:** `brightness_pct = (raw_value / 248.0) * 100`
- **States:**
  - `0` = OFF
  - `1-248` = ON with brightness level (0.4% - 100%)

### OpCode 0x0032 (Feedback) Packet Structure

```
additional_data[0] = Channel number (0-23)
additional_data[1] = 0xF8 (max brightness constant, always 248)
additional_data[2] = Actual brightness (0-248)
additional_data[3+] = Reserved/unused
```

**Important:** Index 2 contains the actual brightness, NOT index 1!

### OpCode 0x0034 (Multi-Channel Status) Packet Structure

```
additional_data[0]  = CH0 brightness (0-248)
additional_data[1]  = CH1 brightness (0-248)
...
additional_data[23] = CH23 brightness (0-248)
```

Total: 24 bytes, one per channel

### OpCode 0xF00F (Channel Name) Packet Structure

```
additional_data[0] = Channel number (0-23)
additional_data[1+] = UTF-8 encoded channel name (max 20 bytes)
```

**Examples:**
- `[0, 0x42, 0x69, 0x6C, 0x69, 0x6E, 0x6D, 0x69, 0x79, 0x6F, 0x72]` = CH0: "Bilinmiyor"
- `[5, 0x4B, 0x4F, 0x52, 0x49, 0x44, 0x4F, 0x52]` = CH5: "KORIDOR"
- `[12, 0x4C, 0x41, 0x56, 0x41, 0x42, 0x4F]` = CH12: "LAVABO"

**Note:** UTF-8 encoding supports Turkish characters (İ, Ğ, Ş, Ç, Ö, Ü)

---

## Packet Structure

### Full UDP Packet Format

```
[PC IP (4 bytes)] + "SMARTCLOUD" (10 bytes) + [TIS Packet]
```

### TIS Packet Structure

| Field | Size | Description |
|-------|------|-------------|
| `src_subnet` | 1 byte | Source subnet ID (0-255) |
| `src_device` | 1 byte | Source device ID (0-255) |
| `src_type` | 2 bytes | Source device type code |
| `tgt_subnet` | 1 byte | Target subnet ID (0-255) |
| `tgt_device` | 1 byte | Target device ID (0-255) |
| `op_code` | 2 bytes | Operation code (see table above) |
| `additional_data_length` | 1 byte | Length of additional data |
| `additional_data` | Variable | Command/response data |

**Total Header Size:** 9 bytes (before additional_data)

### Example Packet (Turn ON CH5 at 50% brightness)

```
Source: Subnet 1, Device 254 (Controller)
Target: Subnet 1, Device 10 (RCU-24R20Z)
OpCode: 0x0031 (Control)
Additional Data: [0x05, 0x00, 0x7C] (CH5, reserved, brightness=124)
```

Raw bytes:
```
01 FE FF FE 01 0A 00 31 03 05 00 7C
│  │  │  │  │  │  │  │  │  │  │  └─ Brightness (124 = ~50%)
│  │  │  │  │  │  │  │  │  │  └──── Reserved (0x00)
│  │  │  │  │  │  │  │  │  └─────── Channel (5)
│  │  │  │  │  │  │  │  └────────── Data length (3)
│  │  │  │  │  │  │  └───────────── OpCode (0x0031)
│  │  │  │  │  └──────────────────── Target device (10)
│  │  │  │  └─────────────────────── Target subnet (1)
│  │  └────────────────────────────── Source type (0xFFFE)
│  └───────────────────────────────── Source device (254)
└──────────────────────────────────── Source subnet (1)
```

---

## Device Types

### Gateway/Bridge

| Type | Model | Description |
|------|-------|-------------|
| 186 | Unknown | TIS Gateway/Bridge |

### Multi-Channel Relay Modules

| Type | Model | Channels | Description |
|------|-------|----------|-------------|
| 214 | Unknown | 24 | RCU-24R20Z (OLD type code) |
| **32811** | **RCU-24R20Z** | **24** | **24 channel relay (CURRENT)** |
| 32813 | RCU-20R20Z-IP | 20 | 20 channel relay with IP |
| 7098 | RCU-8OUT-8IN | 8 | Room controller (8 out, 8 in) |
| 424 | RLY-4CH-10A | 4 | 4 channel 10A relay |
| 428 | RLY-8CH-16A | 8 | 8 channel 16A relay |
| 440 | VLC-12CH-10A | 12 | 12 channel valve/lighting controller |

### Dimmer Modules

| Type | Model | Channels | Description |
|------|-------|----------|-------------|
| 600 | DIM-6CH-2A | 6 | 6 channel 2A dimmer |
| 601 | DIM-4CH-3A | 4 | 4 channel 3A dimmer |
| 602 | DIM-2CH-6A | 2 | 2 channel 6A dimmer |
| 7090 | TIS-DIM-4CH-1A | 4 | 4 channel 1A dimmer |
| 7092 | DIM-TE-2CH-3A | 2 | TE 2 channel 3A dimmer |
| 7094 | DIM-TE-4CH-1.5A | 4 | TE 4 channel 1.5A dimmer |
| 33056 | DIM-TE-8CH-1A | 8 | TE 8 channel 1A dimmer |

### DALI Controllers

| Type | Model | Channels | Description |
|------|-------|----------|-------------|
| 7080 | DALI-64 | 64 | DALI 64 channel controller |
| 7081 | DALI-PRO-64 | 64 | DALI PRO 64 channel controller |

### Control Panels (MARS Series)

| Type | Model | Buttons | Description |
|------|-------|---------|-------------|
| 7040 | MRS-4G | 4 | MARS 4 button panel |
| 7050 | MRS-8G | 8 | MARS 8 button panel |
| 7060 | MRS-12G | 12 | MARS 12 button panel |
| 7070 | MRS-AC10G | 10 | MARS AC thermostat 10 buttons |

### Other Device Types

| Type | Model | Description |
|------|-------|-------------|
| 32 | TIS-DMX-48 | DMX 48 channel controller |
| 118 | TIS-4DI-IN | 4 zone digital input |
| 119 | HVAC6-3A-T | HVAC/VAV air condition module |
| 133 | TIS-PIR-CM | Ceiling PIR sensor |
| 306 | TIS-IR-CUR | IR emitter with current sensor |
| 309 | ES-10F-CM | 10 functions sensor |
| 426 | VLC-6CH-3A | Valve/lighting controller 6CH 3A |
| 1108 | TIS-AUT-TMR | Automation timer module |
| 3049 | TIS-SEC-SM | Security module |

**Total Device Types in Database:** 191

---

## Channel Configurations

### Devices with Channel Mapping

| Type | Model | Channel Count |
|------|-------|---------------|
| 32 | TIS-DMX-48 | 48 |
| 424 | RLY-4CH-10A | 4 |
| 426 | VLC-6CH-3A | 6 |
| 428 | RLY-8CH-16A | 8 |
| 440 | VLC-12CH-10A | 12 |
| 600 | DIM-6CH-2A | 6 |
| 601 | DIM-4CH-3A | 4 |
| 602 | DIM-2CH-6A | 2 |
| 7080 | DALI-64 | 64 |
| 7081 | DALI-PRO-64 | 64 |
| 7090 | TIS-DIM-4CH-1A | 4 |
| 7092 | DIM-TE-2CH-3A | 2 |
| 7094 | DIM-TE-4CH-1.5A | 4 |
| 7098 | RCU-8OUT-8IN | 8 |
| 7099 | RLY-6CH-0-10V | 6 |
| 32798 | ADS-BUS-1D | 1 |
| **32811** | **RCU-24R20Z** | **24** |
| 32813 | RCU-20R20Z-IP | 20 |
| 32816 | DIM-W06CH10A-TE | 6 |
| 32817 | DIM-W12CH10A-TE | 12 |
| 32827 | ADS-3R-BUS | 3 |
| 32832 | ADS-1D-1Z | 1 |
| 32833 | ADS-2R-2Z | 2 |
| 32835 | VEN-4S-4R-HC | 4 |
| 32844 | VEN-2S-2R-HC | 2 |
| 32846 | ADS-4CH-0-10V | 4 |
| 32847 | ADS-3R-3Z | 3 |
| 32849 | AIR-SOCKET-S | 1 |
| 32850 | VEN-1D-UV | 1 |
| 32851 | VEN-3S-3R-HC | 3 |
| 33056 | DIM-TE-8CH-1A | 8 |

**Total Configured Devices:** 31

---

## Important Findings

### 1. RCU-24R20Z Type Code Change

**Discovery:** RCU-24R20Z has TWO type codes in the database:
- **Old Code:** 214 (no model name in db)
- **New Code:** 32811 (with model name "RCU-24R20Z")

**Recommendation:** Use type code **32811** for device detection, but handle both codes for backward compatibility.

### 2. Brightness Parsing Bug

**Issue:** Original implementation read `additional_data[1]` which always contains `0xF8` (248), causing 248% brightness display.

**Solution:** Read `additional_data[2]` for actual brightness value (0-248).

**Affected OpCodes:** 0x0032 (feedback)

### 3. Multi-Channel Query Protocol

**Discovery:** TIS DevSearch uses OpCode 0x0033/0x0034 to query all channels at once, instead of querying each channel individually.

**Benefits:**
- Single request gets status of all 24 channels
- Reduces network traffic
- Faster device state refresh

### 4. Channel Name Support

**Discovery:** OpCode 0xF00E/0xF00F retrieves channel names stored in device memory.

**Usage:**
- Send 0xF00E with channel number
- Receive 0xF00F with UTF-8 encoded name
- Maximum 20 bytes for name
- Supports Turkish characters

**Examples from real device:**
- "Bilinmiyor" (Unknown)
- "KORIDOR TEKLİ" (Single corridor)
- "LAVABO" (Bathroom sink)
- "MUTFAK" (Kitchen)

### 5. Network Configuration

**From Database:**
- Host IP: 192.168.2.124 (TIS DevSearch PC)
- Filtered Subnet: 1 (only shows subnet 1 devices)
- Gateway: Subnet 0, Device 0, Type 186

### 6. Project Structure

**Room Definitions:**
- Living Room
- Kitchen
- Master Room
- Kids Room
- Bath Room
- homepage (default)

**Scene Definitions:**
- 24 scenes configured
- All on Subnet 210, Device 210, Area 1
- Named Scene-01 through Scene-24

### 7. Packet Header Format

**Discovery:** Full UDP packets include:
1. PC IP address (4 bytes) - sender's IP
2. "SMARTCLOUD" text (10 bytes) - protocol identifier
3. TIS packet data (variable) - actual command/response

**Example:**
```
[C0 A8 02 7C] + "SMARTCLOUD" + [01 FE FF FE 01 0A 00 31 03 05 00 7C]
│              │                │
PC IP          Protocol ID      TIS Packet
192.168.2.124
```

---

## Implementation Notes

### For Home Assistant Integration

1. **Device Discovery:**
   - Listen for broadcasts on UDP port 6000
   - Look for packets with "SMARTCLOUD" header
   - Parse device type from `src_type` field
   - Use type code 32811 to identify RCU-24R20Z

2. **Initial State Query:**
   - Send OpCode 0x0033 to get all channel states
   - Send OpCode 0xF00E for each channel to get names
   - Process 0x0034 response (24 bytes)
   - Process 0xF00F responses (UTF-8 names)

3. **Real-Time Feedback:**
   - Listen for OpCode 0x0032 packets
   - Parse brightness from `additional_data[2]`
   - Convert 0-248 to 0-100%
   - Update entity state immediately

4. **Channel Control:**
   - Send OpCode 0x0031 with channel and brightness
   - Format: `[channel, 0x00, brightness_raw]`
   - Gateway IP from configuration
   - Source: Subnet 1, Device 254

### For TIS Addon

1. **Debug Tool:**
   - Decode OpCode 0xF00F as UTF-8 text
   - Show channel names in debug output
   - Display all 24 channels from 0x0034 response
   - Color-code packet types

2. **Device List:**
   - Use `TIS_DATABASE_ANALYSIS.json` for type mapping
   - Show model name from database
   - Display channel count for multi-channel devices
   - Indicate if device has channel name support

---

## Database Tables Reference

### Key Tables

1. **tbl_map_type** (191 rows)
   - Maps device type codes to model names
   - Contains descriptions for each device type

2. **tbl_channel** (31 rows)
   - Maps device types to channel counts
   - Defines which devices are multi-channel

3. **tbl_project_network** (1 row)
   - Gateway configuration
   - Server IP and domain settings

4. **tbl_project_room** (6 rows)
   - Room definitions
   - Display types and icons

5. **tbl_project_scene** (24 rows)
   - Scene configurations
   - Subnet, device, area, scene number mappings

---

## Future Research Needed

### Unknown OpCodes

- **0xF00A/0xF00B:** Unknown function
- **0xF012/0xF013:** Unknown function
- **0xEFFD/0xEFFE:** Device info format unknown

### Missing Documentation

- Scene activation protocol
- Security system commands
- HVAC/thermostat control
- Audio system commands
- Sensor data format
- PIR sensor events

---

## Revision History

- **2025-12-05:** Initial documentation
  - Analyzed tis.db3 database
  - Documented 191 device types
  - Documented 31 channel configurations
  - Reverse-engineered OpCode 0xF00F (channel names)
  - Reverse-engineered OpCode 0x0034 (multi-channel status)

---

**Generated by:** TIS Protocol Analysis Tool  
**Source Files:**
- `tis.db3` (TIS DevSearch database)
- `TIS_DATABASE_ANALYSIS.json` (exported data)
- Packet captures from TIS DevSearch network traffic

**Related Projects:**
- [TIS Home Assistant Integration](https://github.com/Teklojik-Elektronik/tis-homeassistant)
- [TIS Addon](https://github.com/Teklojik-Elektronik/tis_addon)
