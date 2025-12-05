#!/usr/bin/env python3
"""
TIS full UDP parser (UDP 6000).
Parses TIS packets after AA AA header, verifies CRC and prints
human-readable interpretation for known opcodes (based on TIS protocol doc).
Source doc: TIS protocol (uploaded). :contentReference[oaicite:1]{index=1}
"""

import socket
from typing import Tuple

UDP_PORT = 6000
BUFFER_SIZE = 4096

# ---- CRC16 (TIS: using CRC_TAB algorithm from doc) ----
CRC_TAB = [
0x0000,0x1021,0x2042,0x3063,0x4084,0x50a5,0x60c6,0x70e7,0x8108,0x9129,0xa14a,0xb16b,0xc18c,0xd1ad,0xe1ce,0xf1ef,
0x1231,0x0210,0x3273,0x2252,0x52b5,0x4294,0x72f7,0x62d6,0x9339,0x8318,0xb37b,0xa35a,0xd3bd,0xc39c,0xf3ff,0xe3de,
0x2462,0x3443,0x0420,0x1401,0x64e6,0x74c7,0x44a4,0x5485,0xa56a,0xb54b,0x8528,0x9509,0xe5ee,0xf5cf,0xc5ac,0xd58d,
0x3653,0x2672,0x1611,0x0630,0x76d7,0x66f6,0x5695,0x46b4,0xb75b,0xa77a,0x9719,0x8738,0xf7df,0xe7fe,0xd79d,0xc7bc,
0x48c4,0x58e5,0x6886,0x78a7,0x0840,0x1861,0x2802,0x3823,0xc9cc,0xd9ed,0xe98e,0xf9af,0x8948,0x9969,0xa90a,0xb92b,
0x5af5,0x4ad4,0x7ab7,0x6a96,0x1a71,0x0a50,0x3a33,0x2a12,0xdbfd,0xcbdc,0xfbbf,0xeb9e,0x9b79,0x8b58,0xbb3b,0xab1a,
0x6ca6,0x7c87,0x4ce4,0x5cc5,0x2c22,0x3c03,0x0c60,0x1c41,0xedae,0xfd8f,0xcdec,0xddcd,0xad2a,0xbd0b,0x8d68,0x9d49,
0x7e97,0x6eb6,0x5ed5,0x4ef4,0x3e13,0x2e32,0x1e51,0x0e70,0xff9f,0xefbe,0xdfdd,0xcffc,0xbf1b,0xaf3a,0x9f59,0x8f78,
0x9188,0x81a9,0xb1ca,0xa1eb,0xd10c,0xc12d,0xf14e,0xe16f,0x1080,0x00a1,0x30c2,0x20e3,0x5004,0x4025,0x7046,0x6067,
0x83b9,0x9398,0xa3fb,0xb3da,0xc33d,0xd31c,0xe37f,0xf35e,0x02b1,0x1290,0x22f3,0x32d2,0x4235,0x5214,0x6277,0x7256,
0xb5ea,0xa5cb,0x95a8,0x8589,0xf56e,0xe54f,0xd52c,0xc50d,0x34e2,0x24c3,0x14a0,0x0481,0x7466,0x6447,0x5424,0x4405,
0xa7db,0xb7fa,0x8799,0x97b8,0xe75f,0xf77e,0xc71d,0xd73c,0x26d3,0x36f2,0x0691,0x16b0,0x6657,0x7676,0x4615,0x5634,
0xd94c,0xc96d,0xf90e,0xe92f,0x99c8,0x89e9,0xb98a,0xa9ab,0x5844,0x4865,0x7806,0x6827,0x18c0,0x08e1,0x3882,0x28a3,
0xcb7d,0xdb5c,0xeb3f,0xfb1e,0x8bf9,0x9bd8,0xabbb,0xbb9a,0x4a75,0x5a54,0x6a37,0x7a16,0x0af1,0x1ad0,0x2ab3,0x3a92,
0xfd2e,0xed0f,0xdd6c,0xcd4d,0xbdaa,0xad8b,0x9de8,0x8dc9,0x7c26,0x6c07,0x5c64,0x4c45,0x3ca2,0x2c83,0x1ce0,0x0cc1,
0xef1f,0xff3e,0xcf5d,0xdf7c,0xaf9b,0xbfba,0x8fd9,0x9ff8,0x6e17,0x7e36,0x4e55,0x5e74,0x2e93,0x3eb2,0x0ed1,0x1ef0
]

def calc_crc(data: bytes) -> int:
    """CRC calculation following doc: iterate over data bytes using CRC_TAB."""
    crc = 0
    for b in data:
        dat = (crc >> 8) & 0xFF
        crc = ((crc << 8) & 0xFFFF) ^ CRC_TAB[dat ^ b]
    return crc & 0xFFFF

# ---- Helpers to pretty print addresses and bytes ----
def ip_from_header(data: bytes) -> str:
    return ".".join(str(b) for b in data[:4])

def hexstr(b: bytes) -> str:
    return " ".join(f"{x:02X}" for x in b)

# ---- Parsers for specific operation groups (based on uploaded doc) ----
def parse_lighting(opcode: int, pkt: bytes) -> str:
    # A-1 Scene control 0x0002 / response 0x0003
    if opcode == 0x0002:
        # additional: [area, scene]
        if len(pkt) >= 11+2:
            area = pkt[9]
            scene = pkt[10]
            return f"Scene Control: Area={area}, Scene={scene}"
        return "Scene Control (short)"
    if opcode == 0x0003:
        # response: area, scene, max channel, channel states...
        # doc: additional length varies; we show basic fields if present
        if len(pkt) >= 14:
            area = pkt[9]; scene = pkt[10]; max_ch = pkt[11]
            return f"Scene Feedback: Area={area}, Scene={scene}, MaxCh={max_ch}"
        return "Scene Feedback"
    # Single channel control 0x0031 / response 0x0032
    if opcode == 0x0031:
        if len(pkt) >= 15:
            ch = pkt[9]; level = pkt[10]; time_h = pkt[11]; time_l = pkt[12]
            ramp = (time_h<<8) | time_l
            return f"Single Channel Control: CH={ch}, Level={level}%, Ramp={ramp}s"
        return "Single Channel Control (short)"
    if opcode == 0x0032:
        # response: current channel, flag success/fail, result %, qty channels, status bitmap...
        if len(pkt) >= 13:
            ch = pkt[9]; flag = pkt[10]
            status_flag = "Success" if flag == 0xF8 else ("Fail" if flag==0xF5 else f"0x{flag:02X}")
            # try extract value if exists
            value = pkt[11] if len(pkt) > 11 else None
            s = f"Single Channel Feedback: CH={ch}, Flag={status_flag}"
            if value is not None:
                s += f", Value={value}"
            return s
        return "Single Channel Feedback"
    if opcode == 0x001A:
        # sequence control
        if len(pkt) >= 11+2:
            area = pkt[9]; seq = pkt[10]
            return f"Sequence Control: Area={area}, Seq={seq}"
        return "Sequence Control"
    if opcode == 0x001B:
        return "Sequence Response"
    if opcode == 0x0033:
        return "Read Status of Channels (request)"
    if opcode == 0x0034:
        # response: qty channels + each status
        if len(pkt) >= 12:
            qty = pkt[9]
            vals = pkt[10:10+qty]
            vals_str = ", ".join(str(v) for v in vals)
            return f"Channels Status: QTY={qty} Values=[{vals_str}]"
        return "Channels Status (short)"
    return None

def parse_curtain(opcode:int, pkt:bytes) -> str:
    if opcode == 0xE3E0:
        if len(pkt)>=11:
            no = pkt[9]; typ = pkt[10]; typ_s = {0:"Stop",1:"Open",2:"Close"}.get(typ,str(typ))
            return f"Curtain Control: No={no}, Type={typ_s}"
        return "Curtain Control (short)"
    if opcode == 0xE3E1:
        return "Curtain Response"
    if opcode == 0xE3E2:
        return "Curtain Read Status (request)"
    if opcode == 0xE3E3:
        if len(pkt)>=12:
            no = pkt[9]; typ = pkt[10]; return f"Curtain Status: No={no}, Type={typ}"
        return "Curtain Status"
    return None

def parse_universal(opcode:int,pkt:bytes)->str:
    if opcode == 0xE01C:
        if len(pkt)>=11:
            sw = pkt[9]; ct = pkt[10]; return f"Universal Switch Control: No={sw}, Type={'ON' if ct==0xFF else ('OFF' if ct==0 else ct)}"
        return "Universal Switch Control"
    if opcode == 0xE01D:
        return "Universal Switch Response"
    return None

def parse_ac(opcode:int,pkt:bytes)->str:
    # D family (thermostat) many opcodes; implement main ones
    if opcode == 0xE120: return "Read Temperature Unit (request)"
    if opcode == 0xE121:
        if len(pkt)>=11:
            unit = pkt[9]; return f"Temperature Unit Response: {('Celsius' if unit==0 else 'Fahrenheit' if unit==1 else unit)}"
        return "Temperature Unit Response"
    if opcode == 0xE124: return "Read AC Fan Speed/Mode (request)"
    if opcode == 0xE125:
        return "AC Fan Speed/Mode Response (detailed fields - see doc)"
    if opcode == 0x1900: return "Read AC temp range (request)"
    if opcode == 0x1901: return "AC temp range response (detailed fields)"
    if opcode == 0xE0EC: return "Read AC params (request)"
    if opcode == 0xE0ED: return "AC params response (detailed fields)"
    if opcode == 0xE0EE: return "Modify AC params (request)"
    if opcode == 0xE0EF: return "Modify AC params response"
    if opcode == 0xE3D8: return "Panel control command"
    if opcode == 0xE3D9: return "Panel control response"
    if opcode == 0xE3DA: return "Read Panel control status (request)"
    if opcode == 0xE3DB: return "Read Panel control status (response)"
    return None

def parse_security(opcode:int,pkt:bytes)->str:
    if opcode == 0x0104:
        if len(pkt)>=11:
            zone = pkt[9]; mode = pkt[10]; return f"Security Arm/Disarm: Zone={zone}, Mode={mode}"
        return "Security Arm/Disarm"
    if opcode == 0x0105:
        return "Security Response"
    return None

def parse_sensors(opcode:int,pkt:bytes)->str:
    if opcode == 0xDB00: return "10F Sensor Read (request)"
    if opcode == 0xDB01:
        if len(pkt)>=17:
            # doc says 8 bytes: dry1,dry2,lux,motion,flagA,flagB,delayH,delayL
            vals = pkt[9:17]
            return f"10F Sensor Resp: dry1={vals[0]}, dry2={vals[1]}, lux={vals[2]}, motion={vals[3]}, flagA={vals[4]}, flagB={vals[5]}, delay={(vals[6]<<8)|vals[7]}"
        return "10F Sensor Resp"
    if opcode == 0xDC00: return "Temp Read (request)"
    if opcode == 0xDC01:
        if len(pkt)>=17:
            unit = pkt[9]; temp = pkt[10]; return f"Temp Resp: Unit={'C' if unit==0 else 'F'}, Temp={temp}"
        return "Temp Resp"
    if opcode == 0x02CA:
        return "10F Auto Broadcast (energy servant) (see doc for fields)"
    if opcode == 0x012C: return "Read digital inputs (request)"
    if opcode == 0x012D: return "Digital inputs response (see doc)"
    if opcode == 0xDC22: return "Auto broadcast digital inputs"
    return None

def parse_audio(opcode:int,pkt:bytes)->str:
    if opcode == 0x0222: return "Audio: Read Source En/Disable (request)"
    if opcode == 0x0223: return "Audio: Read Response (flags)"
    if opcode == 0x0224: return "Audio: Write Source (request)"
    if opcode == 0x0225: return "Audio: Write Response"
    if opcode == 0xE140: return "Audio Read Radio Station Name (request)"
    if opcode == 0xE141: return "Audio Read Radio Station Name (response)"
    if opcode == 0xE142: return "Audio Write Radio Station Name (request)"
    if opcode == 0xE143: return "Audio Write Radio Station Name (response)"
    if opcode == 0x02E0: return "Audio: Read How Many Album/Song (request)"
    if opcode == 0x02E1: return "Audio: Read How Many (response)"
    if opcode == 0x02E2: return "Audio: Read Album/Song name (request)"
    if opcode == 0x02E3: return "Audio: Read Album/Song name (response)"
    if opcode == 0x0218: return "Audio Control (matrix)"
    if opcode == 0x0219: return "Audio Control Response"
    return None

def parse_energy(opcode:int,pkt:bytes)->str:
    if opcode == 0x2010: return "Energy Meter Request"
    if opcode == 0x2011: return "Energy Meter Response (see doc for fields)"
    return None

# ---- Master dispatcher ----
def dispatch_packet(tis_pkt: bytes) -> str:
    # tis_pkt starts at length byte (first byte = LEN)
    if len(tis_pkt) < 11:
        return f"Too short TIS packet: {hexstr(tis_pkt)}"

    length = tis_pkt[0]
    if length != len(tis_pkt):
        return f"Length mismatch: LEN={length} / actual={len(tis_pkt)}  RAW={hexstr(tis_pkt)}"

    # core header fields
    src_subnet = tis_pkt[1]; src_device = tis_pkt[2]
    src_type = (tis_pkt[3]<<8)|tis_pkt[4]  # note: doc places device type in SN 4-5; careful with indexing variations
    # But per doc layout earlier: [len][src subnet][src dev][src dev type hi][src dev type lo][op hi][op lo]...
    # We'll extract op accordingly:
    op_hi = tis_pkt[5]; op_lo = tis_pkt[6]
    opcode = (op_hi<<8)|op_lo
    tgt_subnet = tis_pkt[7]; tgt_device = tis_pkt[8]

    # CRC
    crc_recv = (tis_pkt[-2]<<8) | tis_pkt[-1]
    crc_calc = calc_crc(tis_pkt[:-2])
    crc_ok = (crc_recv == crc_calc)

    out = []
    out.append(f"TIS Packet: {hexstr(tis_pkt)}")
    out.append(f"  From: {src_subnet}.{src_device}  To: {tgt_subnet}.{tgt_device}")
    out.append(f"  OpCode: 0x{opcode:04X}  CRC: {'OK' if crc_ok else f'BAD (calc {crc_calc:04X})'}")

    # chain through parsers (lighting, curtain, universal, AC, security, sensors, audio, energy)
    handlers = [
        parse_lighting, parse_curtain, parse_universal, parse_ac,
        parse_security, parse_sensors, parse_audio, parse_energy
    ]
    for h in handlers:
        try:
            res = h(opcode, tis_pkt)
            if res:
                out.append("  -> " + res)
                break
        except Exception as e:
            out.append(f"  -> Parser {h._name_} error: {e}")
            break
    else:
        out.append("  -> (Unknown opcode - raw payload shown)")

    return "\n".join(out)

# ---- UDP listener and main loop ----
def send_discovery(sock):
    """Sends discovery packets (OpCode 0xF003) to wake up/find devices."""
    print("🔍 Sending Discovery Broadcasts (OpCode 0xF003)...")
    
    # Construct Discovery Packet
    # Data: SN3(1) SN4(254) Type(FFFE) Op(F003) Tgt(255.255)
    # 01 FE FF FE F0 03 FF FF
    payload = bytearray([0x01, 0xFE, 0xFF, 0xFE, 0xF0, 0x03, 0xFF, 0xFF])
    length = 1 + len(payload) + 2 # Len byte + payload + CRC
    
    # CRC on (Length + Payload)
    crc_data = bytearray([length]) + payload
    crc = calc_crc(crc_data)
    
    # Full Packet: AA AA + Length + Payload + CRC
    packet = bytearray([0xAA, 0xAA, length]) + payload + bytearray([(crc >> 8) & 0xFF, crc & 0xFF])
    
    # Send 10 times with 1s interval
    import time
    for i in range(10):
        try:
            sock.sendto(packet, ('255.255.255.255', UDP_PORT))
            print(f"  -> Broadcast {i+1}/10 sent.")
            time.sleep(1.0)
        except Exception as e:
            print(f"  -> Broadcast failed: {e}")
            
    print("✅ Discovery broadcasts finished. Listening for responses...\n")

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
    except:
        pass
        
    sock.bind(('', UDP_PORT))
    
    # Run discovery at startup
    send_discovery(sock)
    
    print(f"📡 Listening UDP {UDP_PORT} - TIS parser started (detailed).")
    while True:
        data, addr = sock.recvfrom(BUFFER_SIZE)
        # show source ip prefix and SMARTCLOUD header if present
        if len(data) < 16:
            print(f"[{addr}] SHORT UDP: {hexstr(data)}")
            continue
        # optionally print sender IP from header
        try:
            src_ip = ip_from_header(data)
        except Exception:
            src_ip = addr[0]
        # find AA AA
        if b'\xAA\xAA' not in data:
            # some UDP packets may include only TIS payload; handle gracefully
            print(f"[{addr}] No AA AA: {hexstr(data)}")
            continue
        tis_payload = data.split(b'\xAA\xAA',1)[1]
        # dispatch
        result = dispatch_packet(tis_payload)
        print(f"\n[{addr}] {src_ip} ->\n{result}\n")

if __name__ == "__main__":
    main()