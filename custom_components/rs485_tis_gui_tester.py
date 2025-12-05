 #!/usr/bin/env python3
"""
RS485 TIS GUI Test Aracı
Operation code'ları manuel olarak test etmek için GUI arayüz
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import serial
import socket
import threading
import time
from datetime import datetime

def hexstr(data: bytes) -> str:
    """Bytes'ı hex string'e çevirir"""
    return " ".join(f"{x:02X}" for x in data)

def hex_to_bytes(hex_string: str) -> bytes:
    """Hex string'i bytes'a çevirir"""
    hex_string = hex_string.replace(" ", "").replace(",", "")
    if len(hex_string) % 2 != 0:
        hex_string = "0" + hex_string
    return bytes.fromhex(hex_string)

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_broadcast_address():
    """Get the broadcast address for the local network"""
    try:
        import ipaddress
        local_ip = get_local_ip()
        # Assume /24 network (common for home networks)
        network = ipaddress.IPv4Network(f"{local_ip}/24", strict=False)
        return str(network.broadcast_address)
    except:
        return "255.255.255.255"
# TIS Device Type Lookup Tablosu - Gerçek Model İsimleri
DEVICE_TYPES = {
    0x8022: "TIS-HEALTH-CM",           # TIS Health Sensor
    0x80BA: "TIS-OS-MMV2-IRE",        # TIS Radar Sensor With IRE
    0x802B: "RCU-24R20Z",             # Room Control Unit 20 In 24 Out
    0x807A: "TIS-ZIG-PORT",           # TIS Zigbee Home Automation Converter
    0x2332: "LUNA-TFT-43",            # LUNA TFT TOUCH SCREEN 4.3
    0x0076: "TIS-4DI-IN",             # 4 Zone Dry Contact DIGITAL INPUT
    0x3301: "TIS-M3-MOTOR",           # TIS M3 Motor Module
    0xFFFE: "Light Dimmer (Generic)",
    0x0000: "Control Panel (Generic)"
}

def get_device_type_name(device_type: int) -> str:
    """Device type'ın açıklamasını getir"""
    return DEVICE_TYPES.get(device_type, f"Unknown (0x{device_type:04X})")


# CRC Lookup Table
CRC_TABLE = [
    0x0000, 0x1021, 0x2042, 0x3063, 0x4084, 0x50a5, 0x60c6, 0x70e7,
    0x8108, 0x9129, 0xa14a, 0xb16b, 0xc18c, 0xd1ad, 0xe1ce, 0xf1ef,
    0x1231, 0x0210, 0x3273, 0x2252, 0x52b5, 0x4294, 0x72f7, 0x62d6,
    0x9339, 0x8318, 0xb37b, 0xa35a, 0xd3bd, 0xc39c, 0xf3ff, 0xe3de,
    0x2462, 0x3443, 0x0420, 0x1401, 0x64e6, 0x74c7, 0x44a4, 0x5485,
    0xa56a, 0xb54b, 0x8528, 0x9509, 0xe5ee, 0xf5cf, 0xc5ac, 0xd58d,
    0x3653, 0x2672, 0x1611, 0x0630, 0x76d7, 0x66f6, 0x5695, 0x46b4,
    0xb75b, 0xa77a, 0x9719, 0x8738, 0xf7df, 0xe7fe, 0xd79d, 0xc7bc,
    0x48c4, 0x58e5, 0x6886, 0x78a7, 0x0840, 0x1861, 0x2802, 0x3823,
    0xc9cc, 0xd9ed, 0xe98e, 0xf9af, 0x8948, 0x9969, 0xa90a, 0xb92b,
    0x5af5, 0x4ad4, 0x7ab7, 0x6a96, 0x1a71, 0x0a50, 0x3a33, 0x2a12,
    0xdbfd, 0xcbdc, 0xfbbf, 0xeb9e, 0x9b79, 0x8b58, 0xbb3b, 0xab1a,
    0x6ca6, 0x7c87, 0x4ce4, 0x5cc5, 0x2c22, 0x3c03, 0x0c60, 0x1c41,
    0xedae, 0xfd8f, 0xcdec, 0xddcd, 0xad2a, 0xbd0b, 0x8d68, 0x9d49,
    0x7e97, 0x6eb6, 0x5ed5, 0x4ef4, 0x3e13, 0x2e32, 0x1e51, 0x0e70,
    0xff9f, 0xefbe, 0xdfdd, 0xcffc, 0xbf1b, 0xaf3a, 0x9f59, 0x8f78,
    0x9188, 0x81a9, 0xb1ca, 0xa1eb, 0xd10c, 0xc12d, 0xf14e, 0xe16f,
    0x1080, 0x00a1, 0x30c2, 0x20e3, 0x5004, 0x4025, 0x7046, 0x6067,
    0x83b9, 0x9398, 0xa3fb, 0xb3da, 0xc33d, 0xd31c, 0xe37f, 0xf35e,
    0x02b1, 0x1290, 0x22f3, 0x32d2, 0x4235, 0x5214, 0x6277, 0x7256,
    0xb5ea, 0xa5cb, 0x95a8, 0x8589, 0xf56e, 0xe54f, 0xd52c, 0xc50d,
    0x34e2, 0x24c3, 0x14a0, 0x0481, 0x7466, 0x6447, 0x5424, 0x4405,
    0xa7db, 0xb7fa, 0x8799, 0x97b8, 0xe75f, 0xf77e, 0xc71d, 0xd73c,
    0x26d3, 0x36f2, 0x0691, 0x16b0, 0x6657, 0x7676, 0x4615, 0x5634,
    0xd94c, 0xc96d, 0xf90e, 0xe92f, 0x99c8, 0x89e9, 0xb98a, 0xa9ab,
    0x5844, 0x4865, 0x7806, 0x6827, 0x18c0, 0x08e1, 0x3882, 0x28a3,
    0xcb7d, 0xdb5c, 0xeb3f, 0xfb1e, 0x8bf9, 0x9bd8, 0xabbb, 0xbb9a,
    0x4a75, 0x5a54, 0x6a37, 0x7a16, 0x0af1, 0x1ad0, 0x2ab3, 0x3a92,
    0xfd2e, 0xed0f, 0xdd6c, 0xcd4d, 0xbdaa, 0xad8b, 0x9de8, 0x8dc9,
    0x7c26, 0x6c07, 0x5c64, 0x4c45, 0x3ca2, 0x2c83, 0x1ce0, 0x0cc1,
    0xef1f, 0xff3e, 0xcf5d, 0xdf7c, 0xaf9b, 0xbfba, 0x8fd9, 0x9ff8,
    0x6e17, 0x7e36, 0x4e55, 0x5e74, 0x2e93, 0x3eb2, 0x0ed1, 0x1ef0
]

def calculate_crc(data: bytes) -> int:
    """TIS CRC hesaplaması - ESKİ YÖNTEMİ (YANLIŞ)"""
    crc = 0
    for byte in data:
        tbl_idx = ((crc >> 8) ^ byte) & 0xFF
        crc = ((crc << 8) ^ CRC_TABLE[tbl_idx]) & 0xFFFF
    return crc

def pack_crc_c_style(data: list) -> int:
    """
    TIS dokümantasyonundaki Pack_crc C fonksiyonunun EXACT kopyası:
    GERÇEK PAKETLERLE %100 DOĞRULANDI!
    
    void Pack_crc(unchar *ptr, unchar len)
    {
        unint crc;
        unchar dat;
        crc=0;
        while(len--!=0)
        {
            dat=crc>>8;
            crc<<=8;
            crc^=CRC_TAB[dat^*ptr];
            ptr++;
        }
        *ptr=crc>>8;
        ptr++;
        *ptr=crc;
    }
    """
    crc = 0  # unint crc; crc=0;
    
    # while(len--!=0) - Python equivalent
    for byte in data:
        dat = (crc >> 8) & 0xFF  # dat=crc>>8; - high byte
        crc = (crc << 8) & 0xFFFF  # crc<<=8; - shift left, keep 16-bit
        crc ^= CRC_TABLE[dat ^ byte]  # crc^=CRC_TAB[dat^*ptr];
        # ptr++; - handled by for loop
    
    return crc

class TISGUITester:
    def __init__(self):
        self.serial_port = None
        self.udp_socket = None
        self.connection_mode = "RS485"  # RS485 or UDP
        self.is_connected = False
        self.monitoring = False
        
        # Network scanning
        self.scanning = False
        self.scan_thread = None
        self.discovered_devices = {}
        
        # GUI setup
        self.setup_gui()
        
        # Threading
        self.monitor_thread = None
        
        # Paket İzleme için değişkenler
        self.packet_pairs = []  # [(query_packet, response_packet, timestamp), ...]
        self.pending_queries = {}  # {op_code: (packet_data, timestamp), ...}
        
    def setup_gui(self):
        """GUI'yi oluştur - Mouse ile genişletilebilir log paneli"""
        self.root = tk.Tk()
        self.root.title("RS485 TIS GUI Test Aracı")
        self.root.geometry("1200x900")
        # Mouse ile genişletilebilir hale getir
        self.root.resizable(True, True)
        self.root.minsize(800, 600)
       
        
        # Bağlantı frame'i (üstte sabit)
        self.setup_connection_frame()
        
        # Ana container - PanedWindow ile bölünebilir alan
        self.main_paned = tk.PanedWindow(self.root, orient=tk.VERTICAL, sashrelief=tk.RAISED)
        self.main_paned.pack(fill="both", expand=True, padx=10, pady=5)
       
        
        # Üst panel - Tab notebook
        self.top_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.top_frame, minsize=300)
        
        
        self.notebook = ttk.Notebook(self.top_frame)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
      
        
        # Tab'ları oluştur
        self.setup_send_tab()
        self.setup_packet_monitor_tab()
        self.setup_scan_tab()
        self.setup_opcode_tab()
        self.setup_brute_force_tab()
        
        # Alt panel - Monitor frame (Mouse ile genişletilebilir)
        self.bottom_frame = ttk.Frame(self.main_paned)
        self.main_paned.add(self.bottom_frame, minsize=200)
        
        # Monitor frame'ini alt panele yerleştir
        self.setup_monitor_frame_in_paned()
        
        
        
    def setup_connection_frame(self):
        """Bağlantı frame'i"""
        conn_frame = ttk.LabelFrame(self.root, text="Bağlantı Ayarları", padding=10)
        conn_frame.pack(fill="x", padx=10, pady=5)
        
        # Use a frame for the top row controls to keep them aligned
        top_row = ttk.Frame(conn_frame)
        top_row.pack(fill="x", expand=True)
        
        # Connection Mode Selection
        ttk.Label(top_row, text="Mod:").pack(side="left", padx=(0, 5))
        self.mode_var = tk.StringVar(value="RS485")
        mode_combo = ttk.Combobox(top_row, textvariable=self.mode_var, width=10, state="readonly")
        mode_combo['values'] = ['RS485', 'UDP']
        mode_combo.pack(side="left", padx=5)
        mode_combo.bind("<<ComboboxSelected>>", self.on_mode_change)
        
        # RS485 Widgets Frame
        self.rs485_frame = ttk.Frame(top_row)
        self.rs485_frame.pack(side="left", padx=10)
        
        # Port
        ttk.Label(self.rs485_frame, text="Port:").pack(side="left", padx=(10, 0))
        self.port_var = tk.StringVar(value="COM11")
        port_combo = ttk.Combobox(self.rs485_frame, textvariable=self.port_var, width=10)
        port_combo['values'] = [f'COM{i}' for i in range(1, 21)]
        port_combo.pack(side="left", padx=5)
        
        # Baudrate
        ttk.Label(self.rs485_frame, text="Baud:").pack(side="left", padx=(10, 0))
        self.baudrate_var = tk.StringVar(value="9600")
        baudrate_combo = ttk.Combobox(self.rs485_frame, textvariable=self.baudrate_var, width=8)
        baudrate_combo['values'] = ['9600', '19200', '38400', '57600', '115200']
        baudrate_combo.pack(side="left", padx=5)
        
        # Parity
        ttk.Label(self.rs485_frame, text="Parity:").pack(side="left", padx=(10, 0))
        self.parity_var = tk.StringVar(value="EVEN")
        parity_combo = ttk.Combobox(self.rs485_frame, textvariable=self.parity_var, width=8)
        parity_combo['values'] = ['NONE', 'EVEN', 'ODD']
        parity_combo.pack(side="left", padx=5)
        
        # UDP Widgets Frame (Initially Hidden)
        self.udp_frame = ttk.Frame(top_row)
        # Don't pack initially
        
        ttk.Label(self.udp_frame, text="Local IP:").pack(side="left", padx=(10, 0))
        self.local_ip_var = tk.StringVar(value=get_local_ip())
        ttk.Entry(self.udp_frame, textvariable=self.local_ip_var, width=15, state="readonly").pack(side="left", padx=5)
        
        ttk.Label(self.udp_frame, text="Port:").pack(side="left", padx=(10, 0))
        self.udp_port_var = tk.StringVar(value="6000")
        ttk.Entry(self.udp_frame, textvariable=self.udp_port_var, width=6).pack(side="left", padx=5)

        # Status (Right aligned)
        self.status_var = tk.StringVar(value="Bağlı Değil")
        ttk.Label(top_row, textvariable=self.status_var, foreground="red").pack(side="right", padx=10)

        # Connect button (Right aligned)
        self.connect_btn = ttk.Button(top_row, text="Bağlan", command=self.toggle_connection)
        self.connect_btn.pack(side="right", padx=20)
        
    def on_mode_change(self, event=None):
        mode = self.mode_var.get()
        self.connection_mode = mode
        if mode == "RS485":
            self.udp_frame.pack_forget()
            self.rs485_frame.pack(side="left", padx=10)
        else:
            self.rs485_frame.pack_forget()
            self.udp_frame.pack(side="left", padx=10)
            self.local_ip_var.set(get_local_ip())
        
    def setup_send_tab(self):
        """Paket gönder tab'ı"""
        self.send_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.send_tab, text="Paket Gönder")
        
        # Paket gönderme frame'i
        send_frame = ttk.LabelFrame(self.send_tab, text="TIS Paket Gönder", padding=10)
        send_frame.pack(fill="x", padx=10, pady=5)
        
        # İlk satır - Start Code ve Length
        row1 = ttk.Frame(send_frame)
        row1.pack(fill="x", pady=2)
        
        ttk.Label(row1, text="Start Code:").pack(side="left")
        self.start_code_var = tk.StringVar(value="AA AA")
        start_code_combo = ttk.Combobox(row1, textvariable=self.start_code_var, width=8)
        start_code_combo['values'] = ['AA AA', 'BB BB', 'CC CC']
        start_code_combo.pack(side="left", padx=5)
        
        ttk.Label(row1, text="Length:").pack(side="left", padx=(20,5))
        self.length_var = tk.StringVar(value="Auto")
        ttk.Entry(row1, textvariable=self.length_var, width=8, state="readonly").pack(side="left", padx=5)
        
        # İkinci satır - Source
        row2 = ttk.Frame(send_frame)
        row2.pack(fill="x", pady=2)
        
        ttk.Label(row2, text="Source:").pack(side="left")
        self.src_subnet_var = tk.StringVar(value="1")
        ttk.Entry(row2, textvariable=self.src_subnet_var, width=5).pack(side="left", padx=2)
        ttk.Label(row2, text=".").pack(side="left")
        self.src_device_var = tk.StringVar(value="254")
        ttk.Entry(row2, textvariable=self.src_device_var, width=5).pack(side="left", padx=2)
        
        ttk.Label(row2, text="Type:").pack(side="left", padx=(10,5))
        self.src_type_var = tk.StringVar(value="FFFE")
        ttk.Entry(row2, textvariable=self.src_type_var, width=8).pack(side="left", padx=5)
        
        # Üçüncü satır - Operation Code
        row3 = ttk.Frame(send_frame)
        row3.pack(fill="x", pady=2)
        
        ttk.Label(row3, text="Op Code:").pack(side="left")
        self.op_code_var = tk.StringVar(value="0031")
        op_code_combo = ttk.Combobox(row3, textvariable=self.op_code_var, width=8)
        op_code_combo['values'] = ['0031', '0032', '0002', '0003', '000E', '000F', 'E0F9', 'DA44']
        op_code_combo.pack(side="left", padx=5)
        
        ttk.Label(row3, text="Target:").pack(side="left", padx=(20,5))
        self.tgt_subnet_var = tk.StringVar(value="1")
        ttk.Entry(row3, textvariable=self.tgt_subnet_var, width=5).pack(side="left", padx=2)
        ttk.Label(row3, text=".").pack(side="left")
        self.tgt_device_var = tk.StringVar(value="1")
        ttk.Entry(row3, textvariable=self.tgt_device_var, width=5).pack(side="left", padx=2)
        
        # Dördüncü satır - Additional Data
        row4 = ttk.Frame(send_frame)
        row4.pack(fill="x", pady=2)
        
        ttk.Label(row4, text="Additional Data (Hex):").pack(side="left")
        self.additional_data_var = tk.StringVar(value="0F 64 00 00")
        ttk.Entry(row4, textvariable=self.additional_data_var, width=40).pack(side="left", padx=5)
        
        # Beşinci satır - CRC ve Gönder
        row5 = ttk.Frame(send_frame)
        row5.pack(fill="x", pady=5)
        
        ttk.Label(row5, text="CRC:").pack(side="left")
        self.crc_var = tk.StringVar(value="Auto")
        ttk.Entry(row5, textvariable=self.crc_var, width=8, state="readonly").pack(side="left", padx=5)
        
        ttk.Button(row5, text="Paketi Oluştur", command=self.build_packet).pack(side="left", padx=20)
        ttk.Button(row5, text="Gönder", command=self.send_packet).pack(side="left", padx=5)
        
        # Altıncı satır - Oluşturulan paket
        row6 = ttk.Frame(send_frame)
        row6.pack(fill="x", pady=2)
        
        ttk.Label(row6, text="Tam Paket:").pack(side="left")
        self.full_packet_var = tk.StringVar()
        ttk.Entry(row6, textvariable=self.full_packet_var, width=70, state="readonly").pack(side="left", padx=5)
    
    def setup_packet_monitor_tab(self):
        """Paket İzleme tab'ı - Sorgu ve Response çiftlerini göster"""
        self.packet_monitor_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.packet_monitor_tab, text="Paket İzleme")
        
        # Kontrol frame'i
        control_frame = ttk.LabelFrame(self.packet_monitor_tab, text="Paket İzleme Kontrolleri", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Kontrol butonları
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill="x", pady=5)
        
        self.packet_monitor_btn = ttk.Button(btn_frame, text="📡 Paket İzlemeyi Başlat", command=self.toggle_packet_monitoring)
        self.packet_monitor_btn.pack(side="left", padx=5)
        
        ttk.Button(btn_frame, text="🗑️ Listeyi Temizle", command=self.clear_packet_monitor).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="💾 Dışa Aktar", command=self.export_packet_pairs).pack(side="left", padx=5)
        
        # Filtre kontrolleri
        filter_frame = ttk.Frame(control_frame)
        filter_frame.pack(fill="x", pady=5)
        
        ttk.Label(filter_frame, text="Op Code Filtresi:").pack(side="left")
        self.packet_filter_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.packet_filter_var, width=10).pack(side="left", padx=5)
        ttk.Button(filter_frame, text="Filtrele", command=self.apply_packet_filter).pack(side="left", padx=5)
        ttk.Button(filter_frame, text="Temizle", command=self.clear_packet_filter).pack(side="left", padx=5)
        
        # İstatistik bilgileri
        stats_frame = ttk.Frame(control_frame)
        stats_frame.pack(fill="x", pady=5)
        
        self.packet_stats_var = tk.StringVar(value="Toplam Çift: 0 | Bekleyen Sorgu: 0")
        ttk.Label(stats_frame, textvariable=self.packet_stats_var).pack(side="left")
        
        # Ana paket listesi frame'i
        packets_frame = ttk.LabelFrame(self.packet_monitor_tab, text="Sorgu-Response Paket Çiftleri", padding=10)
        packets_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Paket çiftleri treeview
        packet_columns = ("Zaman", "Sorgu Op", "Sorgu Kaynak", "Sorgu Hedef", "Sorgu Data",
                         "Response Op", "Response Kaynak", "Response Data", "Süre (ms)", "Durum")
        self.packet_pairs_tree = ttk.Treeview(packets_frame, columns=packet_columns, show="headings", height=15)
        
        # Sütun başlıkları
        self.packet_pairs_tree.heading("Zaman", text="Zaman")
        self.packet_pairs_tree.heading("Sorgu Op", text="Sorgu Op")
        self.packet_pairs_tree.heading("Sorgu Kaynak", text="Sorgu Kaynak")
        self.packet_pairs_tree.heading("Sorgu Hedef", text="Sorgu Hedef")
        self.packet_pairs_tree.heading("Sorgu Data", text="Sorgu Data")
        self.packet_pairs_tree.heading("Response Op", text="Response Op")
        self.packet_pairs_tree.heading("Response Kaynak", text="Response Kaynak")
        self.packet_pairs_tree.heading("Response Data", text="Response Data")
        self.packet_pairs_tree.heading("Süre (ms)", text="Süre (ms)")
        self.packet_pairs_tree.heading("Durum", text="Durum")
        
        # Sütun genişlikleri
        self.packet_pairs_tree.column("Zaman", width=80)
        self.packet_pairs_tree.column("Sorgu Op", width=80)
        self.packet_pairs_tree.column("Sorgu Kaynak", width=80)
        self.packet_pairs_tree.column("Sorgu Hedef", width=80)
        self.packet_pairs_tree.column("Sorgu Data", width=120)
        self.packet_pairs_tree.column("Response Op", width=80)
        self.packet_pairs_tree.column("Response Kaynak", width=80)
        self.packet_pairs_tree.column("Response Data", width=120)
        self.packet_pairs_tree.column("Süre (ms)", width=70)
        self.packet_pairs_tree.column("Durum", width=80)
        
        # Scrollbar
        packet_scroll = ttk.Scrollbar(packets_frame, orient="vertical", command=self.packet_pairs_tree.yview)
        self.packet_pairs_tree.configure(yscrollcommand=packet_scroll.set)
        
        # Pack
        self.packet_pairs_tree.pack(side="left", fill="both", expand=True)
        packet_scroll.pack(side="right", fill="y")
        
        # Paket izleme değişkenleri
        self.packet_monitoring_active = False
        
    def setup_scan_tab(self):
        """Ağ tarama tab'ı"""
        scan_tab = ttk.Frame(self.notebook)
        self.notebook.add(scan_tab, text="Ağ Tarama")
        
        # Tarama kontrolleri
        control_frame = ttk.LabelFrame(scan_tab, text="Tarama Kontrolleri", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Tarama parametreleri
        param_frame = ttk.Frame(control_frame)
        param_frame.pack(fill="x", pady=5)
        
        ttk.Label(param_frame, text="Subnet ID:").pack(side="left")
        self.scan_subnet_var = tk.StringVar(value="1")
        ttk.Entry(param_frame, textvariable=self.scan_subnet_var, width=5).pack(side="left", padx=5)
        
        ttk.Label(param_frame, text="Device Aralığı:").pack(side="left", padx=(20,5))
        self.scan_start_var = tk.StringVar(value="1")
        ttk.Entry(param_frame, textvariable=self.scan_start_var, width=5).pack(side="left", padx=2)
        ttk.Label(param_frame, text="-").pack(side="left")
        self.scan_end_var = tk.StringVar(value="254")
        ttk.Entry(param_frame, textvariable=self.scan_end_var, width=5).pack(side="left", padx=2)
        
        ttk.Label(param_frame, text="Timeout (ms):").pack(side="left", padx=(20,5))
        self.scan_timeout_var = tk.StringVar(value="500")
        ttk.Entry(param_frame, textvariable=self.scan_timeout_var, width=8).pack(side="left", padx=5)
        
        # Tarama butonları
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill="x", pady=5)
        
        self.scan_btn = ttk.Button(btn_frame, text="Ağı Tara", command=self.start_network_scan)
        self.scan_btn.pack(side="left", padx=5)
        
        ttk.Button(btn_frame, text="Taramayı Durdur", command=self.stop_network_scan).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Listeyi Temizle", command=self.clear_device_list).pack(side="left", padx=5)
        
        # Tarama durumu
        self.scan_status_var = tk.StringVar(value="Hazır")
        ttk.Label(btn_frame, textvariable=self.scan_status_var).pack(side="left", padx=20)
        
        # Bulunan cihazlar listesi
        devices_frame = ttk.LabelFrame(scan_tab, text="Bulunan TIS Cihazları", padding=10)
        devices_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Treeview oluştur - TIS yazılımına benzer format
        columns = ("Adres", "Model", "Comment", "Description", "Device Type", "Status", "Son Görülme")
        self.device_tree = ttk.Treeview(devices_frame, columns=columns, show="headings", height=15)
        
        # Sütun başlıkları - TIS yazılımı format
        self.device_tree.heading("Adres", text="Adres")
        self.device_tree.heading("Model", text="Model")
        self.device_tree.heading("Comment", text="Comment")
        self.device_tree.heading("Description", text="Description")
        self.device_tree.heading("Device Type", text="Device Type")
        self.device_tree.heading("Status", text="Status")
        self.device_tree.heading("Son Görülme", text="Son Görülme")
        
        # Sütun genişlikleri - optimize edilmiş
        self.device_tree.column("Adres", width=70)
        self.device_tree.column("Model", width=130)
        self.device_tree.column("Comment", width=100)
        self.device_tree.column("Description", width=180)
        self.device_tree.column("Device Type", width=80)
        self.device_tree.column("Status", width=70)
        self.device_tree.column("Son Görülme", width=100)
        
        # Pack treeview and scrollbar
        self.device_tree.pack(side="left", fill="both", expand=True)
        
        # Scrollbar
        tree_scroll = ttk.Scrollbar(devices_frame, orient="vertical", command=self.device_tree.yview)
        self.device_tree.configure(yscrollcommand=tree_scroll.set)
        tree_scroll.pack(side="right", fill="y")
    def setup_opcode_tab(self):
        """Operation Code Analiz tabı"""
        opcode_tab = ttk.Frame(self.notebook)
        self.notebook.add(opcode_tab, text="Operation Code Analiz")
        
        # Op Code tracking kontrolleri
        control_frame = ttk.LabelFrame(opcode_tab, text="Operation Code İzleme", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Control buttons - İlk satır
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill="x", pady=5)
        
        self.snapshot_btn = ttk.Button(btn_frame, text="📸 Snapshot Al", command=self.take_snapshot)
        self.snapshot_btn.pack(side="left", padx=5)
        
        self.analyze_btn = ttk.Button(btn_frame, text="🔍 Analiz Et", command=self.analyze_changes, state="disabled")
        self.analyze_btn.pack(side="left", padx=5)
        
        ttk.Button(btn_frame, text="🗑️ Temizle", command=self.clear_opcode_data).pack(side="left", padx=5)
        
        # Discovery buttons - İkinci satır
        discovery_frame = ttk.Frame(control_frame)
        discovery_frame.pack(fill="x", pady=5)
        
        self.opcode_discovery_btn = ttk.Button(discovery_frame, text="🔎 Op Code Discovery", command=self.start_opcode_discovery)
        self.opcode_discovery_btn.pack(side="left", padx=5)
        
        self.smart_discovery_btn = ttk.Button(discovery_frame, text="🧠 Smart Discovery", command=self.start_smart_discovery)
        self.smart_discovery_btn.pack(side="left", padx=5)
        
        self.brute_force_btn = ttk.Button(discovery_frame, text="⚡ Brute Force", command=self.start_brute_force_discovery)
        self.brute_force_btn.pack(side="left", padx=5)
        
        ttk.Button(discovery_frame, text="📋 Op Code Database", command=self.show_opcode_database).pack(side="left", padx=5)
        
        # Status
        self.opcode_status_var = tk.StringVar(value="Op Code İzleme Hazır")
        ttk.Label(discovery_frame, textvariable=self.opcode_status_var).pack(side="left", padx=20)
        
        # Current Operation Codes frame
        current_frame = ttk.LabelFrame(opcode_tab, text="Anlık Operation Code'lar", padding=10)
        current_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Current Op Codes treeview
        current_columns = ("Adres", "Op Code", "Hex Değer", "Açıklama", "Data", "Zaman")
        self.current_opcodes_tree = ttk.Treeview(current_frame, columns=current_columns, show="headings", height=8)
        
        # Sütun başlıkları
        self.current_opcodes_tree.heading("Adres", text="Cihaz Adresi")
        self.current_opcodes_tree.heading("Op Code", text="Op Code")
        self.current_opcodes_tree.heading("Hex Değer", text="Hex Değer")
        self.current_opcodes_tree.heading("Açıklama", text="Açıklama")
        self.current_opcodes_tree.heading("Data", text="Additional Data")
        self.current_opcodes_tree.heading("Zaman", text="Zaman")
        
        # Sütun genişlikleri
        self.current_opcodes_tree.column("Adres", width=80)
        self.current_opcodes_tree.column("Op Code", width=80)
        self.current_opcodes_tree.column("Hex Değer", width=80)
        self.current_opcodes_tree.column("Açıklama", width=150)
        self.current_opcodes_tree.column("Data", width=200)
        self.current_opcodes_tree.column("Zaman", width=100)
        
        # Scrollbar for current
        current_scroll = ttk.Scrollbar(current_frame, orient="vertical", command=self.current_opcodes_tree.yview)
        self.current_opcodes_tree.configure(yscrollcommand=current_scroll.set)
        
        # Pack current
        self.current_opcodes_tree.pack(side="left", fill="both", expand=True)
        current_scroll.pack(side="right", fill="y")
        
        # Changes Analysis frame
        changes_frame = ttk.LabelFrame(opcode_tab, text="Değişiklik Analizi (Eski vs Yeni)", padding=10)
        changes_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Changes treeview
        changes_columns = ("Adres", "Op Code", "Eski Değer", "Yeni Değer", "Eski Data", "Yeni Data", "Değişiklik Zamanı")
        self.changes_tree = ttk.Treeview(changes_frame, columns=changes_columns, show="headings", height=8)
        
        # Sütun başlıkları
        self.changes_tree.heading("Adres", text="Cihaz")
        self.changes_tree.heading("Op Code", text="Op Code")
        self.changes_tree.heading("Eski Değer", text="Eski Hex")
        self.changes_tree.heading("Yeni Değer", text="Yeni Hex")
        self.changes_tree.heading("Eski Data", text="Eski Data")
        self.changes_tree.heading("Yeni Data", text="Yeni Data")
        self.changes_tree.heading("Değişiklik Zamanı", text="Zaman")
        
        # Sütun genişlikleri
        self.changes_tree.column("Adres", width=70)
        self.changes_tree.column("Op Code", width=70)
        self.changes_tree.column("Eski Değer", width=80)
        self.changes_tree.column("Yeni Değer", width=80)
        self.changes_tree.column("Eski Data", width=150)
        self.changes_tree.column("Yeni Data", width=150)
        self.changes_tree.column("Değişiklik Zamanı", width=100)
        
        # Scrollbar for changes
        changes_scroll = ttk.Scrollbar(changes_frame, orient="vertical", command=self.changes_tree.yview)
        self.changes_tree.configure(yscrollcommand=changes_scroll.set)
        
        # Pack changes
        self.changes_tree.pack(side="left", fill="both", expand=True)
        changes_scroll.pack(side="right", fill="y")
        
        # Op Code tracking variables
        self.current_opcodes = {}  # {address: {op_code: (hex_val, data, timestamp)}}
        self.snapshot_opcodes = {}  # Snapshot verileri
        self.discovered_opcodes = {}  # Tüm tespit edilen operation code'lar
        self.opcode_discovery_active = False
        self.brute_force_discovery = False
        self.current_brute_force_code = 0x0000
        
        # Genişletilmiş Operation Code Database
        self.opcode_descriptions = {
            # Discovery & System
            0x000E: "Discovery Request",
            0xF003: "Old Discovery Request (deprecated)",
            0xF004: "Discovery Response",
            0xF005: "Network Status Request",
            0xF006: "Network Status Response",
            
            # Device Status & Control
            0x000E: "Status Request",
            0x000F: "Device Status Report",
            0x0010: "Device Configuration Request",
            0x0011: "Device Configuration Response",
            
            # Channel Control
            0x0031: "Single Channel Control",
            0x0032: "Multi Channel Control",
            0x0033: "Channel Status Request",
            0x0034: "Channel Status Report",
            0x0035: "Channel Configuration",
            
            # Scene Management
            0x0002: "Scene Control",
            0x0003: "Scene Status Request",
            0x0004: "Scene Status Response",
            0x0005: "Scene Configuration",
            
            # System Commands
            0xDA44: "System Status Broadcast",
            0xDA45: "System Status Response",
            0xEFFF: "System Command",
            0xE000: "Emergency Command",
            0xE001: "Emergency Response",
            
            # Time & Schedule
            0x0020: "Time Sync Request",
            0x0021: "Time Sync Response",
            0x0022: "Schedule Command",
            0x0023: "Schedule Status",
            
            # Security & Access
            0x0040: "Access Control Request",
            0x0041: "Access Control Response",
            0x0042: "Security Status",
            
            # Energy Management
            0x0050: "Energy Status Request",
            0x0051: "Energy Status Response",
            0x0052: "Power Control Command",
            
            # LUNA TFT Specific
            0x1945: "LUNA Display Control",
            0xE0ED: "LUNA Status Broadcast",
            0x1900: "LUNA Command Range Start",
            0xE000: "LUNA Status Range Start",
            
            # Device Type Specific Commands
            0x8000: "TIS Health Sensor Command",
            0x8001: "TIS Radar Sensor Command",
            0x8002: "RCU Control Command",
            0x8003: "Zigbee Gateway Command"
        }

    def setup_brute_force_tab(self):
        """Brute Force Discovery tabı"""
        brute_force_tab = ttk.Frame(self.notebook)
        self.notebook.add(brute_force_tab, text="🔍 Brute Force Discovery")
        
        # Brute Force kontrolleri
        control_frame = ttk.LabelFrame(brute_force_tab, text="Brute Force Discovery Kontrolleri", padding=10)
        control_frame.pack(fill="x", padx=10, pady=5)
        
        # Parametreler frame'i - İlk satır
        params_frame1 = ttk.Frame(control_frame)
        params_frame1.pack(fill="x", pady=2)
        
        # Op Code aralığı
        ttk.Label(params_frame1, text="Op Code Aralığı:").pack(side="left")
        self.bf_start_var = tk.StringVar(value="0000")
        ttk.Entry(params_frame1, textvariable=self.bf_start_var, width=8).pack(side="left", padx=5)
        ttk.Label(params_frame1, text=" - ").pack(side="left")
        self.bf_end_var = tk.StringVar(value="FFFF")
        ttk.Entry(params_frame1, textvariable=self.bf_end_var, width=8).pack(side="left", padx=5)
        
        # Hedef cihaz
        ttk.Label(params_frame1, text="Hedef Cihaz:").pack(side="left", padx=(20,5))
        self.bf_target_subnet_var = tk.StringVar(value="1")
        ttk.Entry(params_frame1, textvariable=self.bf_target_subnet_var, width=5).pack(side="left", padx=2)
        ttk.Label(params_frame1, text=".").pack(side="left")
        self.bf_target_device_var = tk.StringVar(value="1")
        ttk.Entry(params_frame1, textvariable=self.bf_target_device_var, width=5).pack(side="left", padx=2)
        
        # İkinci satır parametreler
        params_frame2 = ttk.Frame(control_frame)
        params_frame2.pack(fill="x", pady=2)
        
        # Delay settings
        ttk.Label(params_frame2, text="Packet Delay (ms):").pack(side="left")
        self.bf_delay_var = tk.StringVar(value="50")
        ttk.Entry(params_frame2, textvariable=self.bf_delay_var, width=8).pack(side="left", padx=5)
        
        ttk.Label(params_frame2, text="Batch Size:").pack(side="left", padx=(20,5))
        self.bf_batch_var = tk.StringVar(value="100")
        ttk.Entry(params_frame2, textvariable=self.bf_batch_var, width=8).pack(side="left", padx=5)
        
        # Auto Target checkbox
        self.bf_auto_target_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(params_frame2, text="Auto Target (İlk bulunan cihaz)", variable=self.bf_auto_target_var).pack(side="left", padx=20)
        
        # Butonlar frame'i
        buttons_frame = ttk.Frame(control_frame)
        buttons_frame.pack(fill="x", pady=5)
        
        self.bf_start_btn = ttk.Button(buttons_frame, text="🚀 Brute Force Başlat", command=self.start_advanced_brute_force)
        self.bf_start_btn.pack(side="left", padx=5)
        
        self.bf_stop_btn = ttk.Button(buttons_frame, text="⏹️ Durdur", command=self.stop_brute_force, state="disabled")
        self.bf_stop_btn.pack(side="left", padx=5)
        
        self.bf_pause_btn = ttk.Button(buttons_frame, text="⏸️ Duraklat", command=self.pause_brute_force, state="disabled")
        self.bf_pause_btn.pack(side="left", padx=5)
        
        ttk.Button(buttons_frame, text="📊 İstatistik", command=self.show_bf_statistics).pack(side="left", padx=5)
        
        # Status ve Progress
        status_frame = ttk.Frame(control_frame)
        status_frame.pack(fill="x", pady=5)
        
        self.bf_status_var = tk.StringVar(value="Hazır")
        ttk.Label(status_frame, textvariable=self.bf_status_var).pack(side="left")
        
        # Progress bar
        self.bf_progress = ttk.Progressbar(status_frame, length=300, mode='determinate')
        self.bf_progress.pack(side="left", padx=20)
        
        self.bf_progress_label = tk.StringVar(value="0%")
        ttk.Label(status_frame, textvariable=self.bf_progress_label).pack(side="left", padx=5)
        
        # Sonuçlar frame'i
        results_frame = ttk.LabelFrame(brute_force_tab, text="Brute Force Discovery Sonuçları", padding=10)
        results_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Results treeview
        bf_columns = ("Op Code", "Hex", "Response", "Cihaz", "Response Op", "Data", "Tespit Zamanı", "Durum")
        self.bf_results_tree = ttk.Treeview(results_frame, columns=bf_columns, show="headings", height=15)
        
        # Sütun başlıkları
        self.bf_results_tree.heading("Op Code", text="Test Op Code")
        self.bf_results_tree.heading("Hex", text="Hex")
        self.bf_results_tree.heading("Response", text="Response Var")
        self.bf_results_tree.heading("Cihaz", text="Response Cihaz")
        self.bf_results_tree.heading("Response Op", text="Response Op Code")
        self.bf_results_tree.heading("Data", text="Response Data")
        self.bf_results_tree.heading("Tespit Zamanı", text="Zaman")
        self.bf_results_tree.heading("Durum", text="Durum")
        
        # Sütun genişlikleri
        self.bf_results_tree.column("Op Code", width=80)
        self.bf_results_tree.column("Hex", width=60)
        self.bf_results_tree.column("Response", width=80)
        self.bf_results_tree.column("Cihaz", width=80)
        self.bf_results_tree.column("Response Op", width=100)
        self.bf_results_tree.column("Data", width=150)
        self.bf_results_tree.column("Tespit Zamanı", width=80)
        self.bf_results_tree.column("Durum", width=80)
        
        # Scrollbar
        bf_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.bf_results_tree.yview)
        self.bf_results_tree.configure(yscrollcommand=bf_scroll.set)
        
        # Pack
        self.bf_results_tree.pack(side="left", fill="both", expand=True)
        bf_scroll.pack(side="right", fill="y")
        
        # Brute Force variables
        self.bf_active = False
        self.bf_paused = False
        self.bf_current_op = 0x0000
        self.bf_discovered_responses = {}
        self.bf_stats = {
            'total_sent': 0,
            'responses_received': 0,
            'unique_opcodes': 0,
            'start_time': None
        }

    def take_snapshot(self):
        """Mevcut operation code'ların snapshot'ını al"""
        try:
            import copy
            self.snapshot_opcodes = copy.deepcopy(self.current_opcodes)
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            snapshot_count = len(self.snapshot_opcodes)
            self.opcode_status_var.set(f"📸 Snapshot alındı: {snapshot_count} cihaz, {timestamp}")
            self.log_message(f"📸 Op Code Snapshot: {snapshot_count} cihazın durumu kaydedildi")
            
            # Snapshot sonrası analiz butonu aktif et
            self.analyze_btn.config(state="normal")
            
        except Exception as e:
            self.log_message(f"❌ Snapshot hatası: {e}")
    
    def analyze_changes(self):
        """Snapshot ile şu anki durumu karşılaştır"""
        try:
            changes_found = 0
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Changes tree'yi temizle
            for item in self.changes_tree.get_children():
                self.changes_tree.delete(item)
            
            # Her cihaz için karşılaştır
            for address in self.current_opcodes:
                current_device = self.current_opcodes[address]
                snapshot_device = self.snapshot_opcodes.get(address, {})
                
                for op_code in current_device:
                    current_entry = current_device[op_code]
                    snapshot_entry = snapshot_device.get(op_code)
                    
                    if snapshot_entry is None:
                        # Yeni operation code
                        self.changes_tree.insert("", "end", values=(
                            address,
                            f"0x{op_code:04X}",
                            "YENİ",
                            f"0x{current_entry[0]:04X}",
                            "-",
                            hexstr(current_entry[1]),
                            timestamp
                        ))
                        changes_found += 1
                        
                    elif current_entry[0] != snapshot_entry[0] or current_entry[1] != snapshot_entry[1]:
                        # Değişiklik var
                        self.changes_tree.insert("", "end", values=(
                            address,
                            f"0x{op_code:04X}",
                            f"0x{snapshot_entry[0]:04X}",
                            f"0x{current_entry[0]:04X}",
                            hexstr(snapshot_entry[1]),
                            hexstr(current_entry[1]),
                            timestamp
                        ))
                        changes_found += 1
            
            # Snapshot'da olan ama şimdi olmayan op code'ları da kontrol et
            for address in self.snapshot_opcodes:
                if address not in self.current_opcodes:
                    continue
                    
                snapshot_device = self.snapshot_opcodes[address]
                current_device = self.current_opcodes.get(address, {})
                
                for op_code in snapshot_device:
                    if op_code not in current_device:
                        # Silinen operation code
                        snapshot_entry = snapshot_device[op_code]
                        self.changes_tree.insert("", "end", values=(
                            address,
                            f"0x{op_code:04X}",
                            f"0x{snapshot_entry[0]:04X}",
                            "SİLİNDİ",
                            hexstr(snapshot_entry[1]),
                            "-",
                            timestamp
                        ))
                        changes_found += 1
            
            self.opcode_status_var.set(f"🔍 Analiz tamamlandı: {changes_found} değişiklik bulundu")
            self.log_message(f"🔍 Op Code Analiz: {changes_found} değişiklik tespit edildi")
            
        except Exception as e:
            self.log_message(f"❌ Analiz hatası: {e}")
    
    def clear_opcode_data(self):
        """Operation code verilerini temizle"""
        try:
            # Tüm verileri temizle
            self.current_opcodes.clear()
            self.snapshot_opcodes.clear()
            
            # Tree'leri temizle
            for item in self.current_opcodes_tree.get_children():
                self.current_opcodes_tree.delete(item)
            for item in self.changes_tree.get_children():
                self.changes_tree.delete(item)
            
            self.opcode_status_var.set("🗑️ Veriler temizlendi")
            self.analyze_btn.config(state="disabled")
            
            self.log_message("🗑️ Op Code verileri temizlendi")
            
        except Exception as e:
            self.log_message(f"❌ Temizleme hatası: {e}")
    
    def update_current_opcodes(self, parsed_packet: dict):
        """Gelen paketten operation code'ları güncelle"""
        try:
            address = f"{parsed_packet['src_subnet']}.{parsed_packet['src_device']}"
            op_code = parsed_packet['op_code']
            additional_data = parsed_packet.get('additional_data', b'')
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # DEBUG LOG
            self.log_message(f"🔧 Op Code Update: {address} - 0x{op_code:04X} - {hexstr(additional_data)}")
            
            # Current opcodes dictionary'e ekle
            if address not in self.current_opcodes:
                self.current_opcodes[address] = {}
                
            self.current_opcodes[address][op_code] = (op_code, additional_data, timestamp)
            
            # Tree'yi güncelle (Thread-safe)
            self.root.after(0, self._update_opcode_tree, address, op_code, additional_data, timestamp)
            
        except Exception as e:
            self.log_message(f"❌ Op Code güncelleme hatası: {e}")
    
    def _update_opcode_tree(self, address: str, op_code: int, additional_data: bytes, timestamp: str):
        """Thread-safe: Op Code tree'yi güncelle"""
        try:
            # DEBUG LOG
            self.log_message(f"🔧 Tree Update: {address} - 0x{op_code:04X}")
            
            # current_opcodes_tree var mı kontrol et
            if not hasattr(self, 'current_opcodes_tree'):
                self.log_message(f"❌ current_opcodes_tree mevcut değil!")
                return
                
            # Mevcut girdiyi bul ve güncelle
            found = False
            for item in self.current_opcodes_tree.get_children():
                values = self.current_opcodes_tree.item(item, "values")
                if values and len(values) > 0 and values[0] == address and values[1] == f"0x{op_code:04X}":
                    # Güncelle
                    description = self.opcode_descriptions.get(op_code, "Unknown")
                    new_values = (
                        address,
                        f"0x{op_code:04X}",
                        f"0x{op_code:04X}",
                        description,
                        hexstr(additional_data),
                        timestamp
                    )
                    self.current_opcodes_tree.item(item, values=new_values)
                    found = True
                    self.log_message(f"✅ Op Code güncellendi: {address}")
                    break
            
            if not found:
                # Yeni girdi ekle
                description = self.opcode_descriptions.get(op_code, "Unknown")
                values = (
                    address,
                    f"0x{op_code:04X}",
                    f"0x{op_code:04X}",
                    description,
                    hexstr(additional_data),
                    timestamp
                )
                self.current_opcodes_tree.insert("", "end", values=values)
                self.log_message(f"➕ Yeni Op Code eklendi: {address}")
                
        except Exception as e:
            self.log_message(f"❌ Op Code Tree güncelleme hatası: {e}")
            import traceback
            self.log_message(f"❌ Traceback: {traceback.format_exc()}")

    def setup_monitor_frame_in_paned(self):
        """İzleme frame'i - PanedWindow içinde mouse ile genişletilebilir"""
       
        monitor_frame = ttk.LabelFrame(self.bottom_frame, text="RS485 İzleme", padding=5)
        monitor_frame.pack(fill="both", expand=True)
       
        
        # Kontrol butonları
        btn_frame = ttk.Frame(monitor_frame)
        btn_frame.pack(fill="x", pady=(0,5))
        
        self.monitor_btn = ttk.Button(btn_frame, text="İzlemeyi Başlat", command=self.toggle_monitoring)
        self.monitor_btn.pack(side="left")
        
        ttk.Button(btn_frame, text="Temizle", command=self.clear_monitor).pack(side="left", padx=10)
        
      
        
        # Log alanı - Sabit boyut kısıtlamaları KALDIRILDI
      
        self.log_text = scrolledtext.ScrolledText(monitor_frame)  # Hiç boyut parametresi yok!
        self.log_text.pack(fill="both", expand=True, padx=2, pady=2)
       
        
        # Mouse ile resize için ek ayarlar
        self.log_text.configure(wrap=tk.WORD)
       
        
        # Hazır komutlar frame'i (send tab içinde)
        self.setup_presets_frame(self.send_tab)
    
    def setup_presets_frame(self, parent):
        """Hazır komutlar frame'i"""
        presets_frame = ttk.LabelFrame(parent, text="Hızlı Komutlar", padding=10)
        presets_frame.pack(fill="x", padx=10, pady=5)
        
        # Preset butonları
        btn_frame = ttk.Frame(presets_frame)
        btn_frame.pack(fill="x")
        
        presets = [
            ("Light ON (0x64)", "0031", "02 64 00 00"),
            ("Light OFF (0x00)", "0031", "02 00 00 00"),
            ("Scene 1", "0002", "01 01"),
            ("Scene 2", "0002", "01 02"),
            ("Status Request", "000E", "")
        ]
        
        for i, (name, op_code, data) in enumerate(presets):
            btn = ttk.Button(btn_frame, text=name, 
                           command=lambda oc=op_code, d=data: self.load_preset(oc, d))
            btn.pack(side="left", padx=5)
    
    def load_preset(self, op_code: str, data: str):
        """Hazır komutu yükle"""
        self.op_code_var.set(op_code)
        self.additional_data_var.set(data)
        self.build_packet()
    
    def toggle_connection(self):
        """Bağlantıyı aç/kapat"""
        if not self.is_connected:
            try:
                if self.connection_mode == "RS485":
                    parity_map = {
                        'NONE': serial.PARITY_NONE,
                        'EVEN': serial.PARITY_EVEN, 
                        'ODD': serial.PARITY_ODD
                    }
                    
                    self.serial_port = serial.Serial(
                        port=self.port_var.get(),
                        baudrate=int(self.baudrate_var.get()),
                        parity=parity_map[self.parity_var.get()],
                        stopbits=serial.STOPBITS_ONE,
                        bytesize=serial.EIGHTBITS,
                        timeout=0.1
                    )
                    self.log_message(f"✅ {self.port_var.get()} portuna bağlanıldı (RS485)")
                else:
                    # UDP Connection - Enhanced for broadcast receive
                    self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    
                    # CRITICAL: Socket options for receiving broadcasts
                    self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    
                    # Windows-specific: Allow address reuse
                    try:
                        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                    except AttributeError:
                        pass  # SO_REUSEPORT not available on Windows
                    
                    # CRITICAL: Enable broadcast transmission AND reception
                    self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    
                    # Large receive buffer for RPi4-like performance
                    try:
                        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
                        self.log_message("📊 UDP Receive Buffer: 4MB")
                    except:
                        pass
                    
                    port = int(self.udp_port_var.get())
                    
                    # Bind to all interfaces (0.0.0.0) to receive broadcasts
                    self.udp_socket.bind(('0.0.0.0', port))
                    self.udp_socket.settimeout(0.1) # Non-blocking read for thread
                    
                    local_ip = get_local_ip()
                    self.log_message(f"✅ UDP Port {port} dinleniyor (Bind: 0.0.0.0)")
                    self.log_message(f"📍 Local IP: {local_ip}")
                    self.log_message(f"📡 Broadcast enabled: Ağdaki tüm cihazlardan paket alınabilir")

                self.is_connected = True
                self.connect_btn.config(text="Bağlantıyı Kes")
                self.status_var.set("Bağlandı")
                
            except Exception as e:
                messagebox.showerror("Bağlantı Hatası", f"Bağlantı hatası: {e}")
        else:
            if self.serial_port:
                self.serial_port.close()
                self.serial_port = None
            if self.udp_socket:
                self.udp_socket.close()
                self.udp_socket = None
                
            self.is_connected = False
            self.connect_btn.config(text="Bağlan")  
            self.status_var.set("Bağlı Değil")
            self.log_message("❌ Bağlantı kapatıldı")
    
    def build_packet(self):
        """TIS paketini oluştur - DEBUG versiyon"""
        try:
            # Debug log başlat
            debug_info = []
            debug_info.append("🔧 PAKET OLUŞTURULUYOR...")
            
            # Start Code
            start_bytes = hex_to_bytes(self.start_code_var.get())
            debug_info.append(f"📌 Start Code: {hexstr(start_bytes)}")
            
            # Source
            src_subnet = int(self.src_subnet_var.get())
            src_device = int(self.src_device_var.get())
            src_type_str = self.src_type_var.get()
            debug_info.append(f"🔍 Source Type String: '{src_type_str}'")
            src_type = int(src_type_str, 16)
            debug_info.append(f"📍 Source: {src_subnet}.{src_device} Type:0x{src_type:04X}")
            
            # Operation Code
            op_code = int(self.op_code_var.get(), 16)
            debug_info.append(f"⚡ Operation Code: 0x{op_code:04X}")
            
            # Target
            tgt_subnet = int(self.tgt_subnet_var.get())
            tgt_device = int(self.tgt_device_var.get())
            debug_info.append(f"🎯 Target: {tgt_subnet}.{tgt_device}")
            
            # Additional Data
            additional_data = b''
            additional_data_str = self.additional_data_var.get().strip()
            debug_info.append(f"🔍 Additional Data String: '{additional_data_str}'")
            if additional_data_str:
                additional_data = hex_to_bytes(additional_data_str)
            debug_info.append(f"📝 Additional Data: {hexstr(additional_data)} ({len(additional_data)} bytes)")
            
            # Data package (TIS protokolü: SN 2-10 arası)
            # SN2=Length, SN3=src_subnet, SN4=src_device, SN5-6=src_type
            # SN7-8=op_code, SN9=tgt_subnet, SN10=tgt_device, SN11-N=additional, CRC
            data_package = bytearray()
            data_package.append(src_subnet)          # SN 3
            data_package.append(src_device)          # SN 4
            data_package.extend([(src_type >> 8) & 0xFF, src_type & 0xFF])  # SN 5-6
            data_package.extend([(op_code >> 8) & 0xFF, op_code & 0xFF])    # SN 7-8
            data_package.append(tgt_subnet)          # SN 9
            data_package.append(tgt_device)          # SN 10
            data_package.extend(additional_data)     # SN 11-N
            
            debug_info.append(f"📦 Data Package: {hexstr(data_package)} ({len(data_package)} bytes)")
            
            # Length hesapla (TIS protokol: Length kendisi + data package + CRC)
            # TIS DOKÜMANTASYONVer:3.1 "From SN 2 to 10, it's not included SN 1"
            # SN2=Length field kendisi, SN3-10=data package, +2 CRC
            length = 1 + len(data_package) + 2  # +1 length kendisi, +2 CRC
            debug_info.append(f"📏 Length: {length} (Data:{len(data_package)} + CRC:2)")
            
            # CRC hesapla - CANLI ANALİZ SONUCU: packet[2:-2] yöntemi
            # Yani: Length + Data Package (Start Code hariç, CRC hariç)
            crc_data = bytes([length]) + bytes(data_package)
            crc = pack_crc_c_style(list(crc_data))  # Doğru C-style CRC
            debug_info.append(f"🔐 CRC Data: {hexstr(crc_data)}")
            debug_info.append(f"🔐 CRC: 0x{crc:04X} (H:{(crc>>8)&0xFF:02X} L:{crc&0xFF:02X})")
            debug_info.append(f"✅ TIS DOKÜMANTASYONU C KODU İLE %100 DOĞRULANMIş!")
            
            # Tam paket oluştur
            full_packet = start_bytes + bytes([length]) + bytes(data_package) + bytes([(crc >> 8) & 0xFF, crc & 0xFF])
            
            debug_info.append(f"✅ TAM PAKET: {hexstr(full_packet)} ({len(full_packet)} bytes)")
            debug_info.append("=" * 50)
            
            # Debug log'ları göster
            for info in debug_info:
                self.log_message(info)
            
            # GUI'yi güncelle
            self.length_var.set(str(length))
            self.crc_var.set(f"{crc:04X}")
            self.full_packet_var.set(hexstr(full_packet))
            
            self.current_packet = full_packet
            
        except Exception as e:
            error_msg = f"Paket oluşturulamadı: {e}"
            messagebox.showerror("Paket Hatası", error_msg)
            self.log_message(f"❌ HATA: {error_msg}")
    
    def send_packet(self):
        """Paketi gönder"""
        if not self.is_connected:
            messagebox.showwarning("Bağlantı", "Önce Bağlanın!")
            return
            
        if not hasattr(self, 'current_packet'):
            self.build_packet()
        
        try:
            if self.connection_mode == "RS485":
                self.serial_port.write(self.current_packet)
            else:
                # UDP Broadcast - SMARTCLOUD header ekle
                local_ip = get_local_ip()
                ip_bytes = bytes([int(x) for x in local_ip.split('.')])
                smartcloud_header = b'SMARTCLOUD'
                udp_packet = ip_bytes + smartcloud_header + self.current_packet
                self.udp_socket.sendto(udp_packet, ('255.255.255.255', 6000))
                
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.log_message(f"📤 GÖNDER [{timestamp}]: {hexstr(self.current_packet)}")
            
            # Paket izleme için giden paketi işle
            if hasattr(self, 'current_packet'):
                parsed_outgoing = self.parse_received_packet(self.current_packet)
                if parsed_outgoing:
                    self.process_packet_for_monitoring(parsed_outgoing, is_outgoing=True)
            
        except Exception as e:
            messagebox.showerror("Gönderme Hatası", f"Paket gönderilemedi: {e}")
    
    def toggle_monitoring(self):
        """İzlemeyi başlat/durdur"""
        if not self.monitoring:
            if not self.is_connected:
                messagebox.showwarning("Bağlantı", "Önce Bağlanın!")
                return
            
            self.monitoring = True
            self.monitor_btn.config(text="İzlemeyi Durdur")
            self.monitor_thread = threading.Thread(target=self.monitor_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            self.log_message("🔍 İzleme başlatıldı...")
            
        else:
            self.monitoring = False
            self.monitor_btn.config(text="İzlemeyi Başlat")
            self.log_message("⏹️ İzleme durduruldu")
    
    def monitor_loop(self):
        """İzleme thread'i (RS485 ve UDP)"""
        buffer = b''
        
        while self.monitoring and self.is_connected:
            try:
                new_data = b''
                if self.connection_mode == "RS485":
                    if self.serial_port and self.serial_port.in_waiting > 0:
                        new_data = self.serial_port.read(self.serial_port.in_waiting)
                else:
                    # UDP
                    try:
                        data, addr = self.udp_socket.recvfrom(8192)
                        
                        # Gateway'den gelen paketler SMARTCLOUD header ile gelir
                        # Format: [4 byte IP][SMARTCLOUD][TIS paket(ler)i...]
                        offset = 0
                        if data.startswith(b'SMARTCLOUD'):
                            offset = 10  # "SMARTCLOUD" = 10 byte
                            self.root.after(0, lambda sz=len(data): self.log_message(f"📡 UDP from {addr[0]}:{addr[1]} ({sz} bytes) 🔧 SMARTCLOUD header (10 byte atlandı)"))
                            if len(data) > 60:  # Büyük paketlerin içeriğini göster
                                self.root.after(0, lambda d=data: self.log_message(f"   📦 TIS Data ({len(data)-10} bytes): {hexstr(d[10:110])}{'...' if len(d) > 110 else ''}"))
                        elif len(data) > 14 and data[4:14] == b'SMARTCLOUD':
                            offset = 14  # 4 byte IP + 10 byte "SMARTCLOUD"
                            gateway_ip = '.'.join(str(b) for b in data[0:4])
                            self.root.after(0, lambda gw=gateway_ip, sz=len(data): self.log_message(f"📡 UDP from {addr[0]}:{addr[1]} ({sz} bytes) 🔧 Gateway header: IP={gw} ({offset} byte atlandı)"))
                            if len(data) > 64:  # Büyük paketlerin içeriğini göster (174 byte gibi)
                                self.root.after(0, lambda d=data, off=offset: self.log_message(f"   📦 TIS Data ({len(d)-off} bytes): {hexstr(d[off:off+100])}{'...' if len(d) > off+100 else ''}"))
                        else:
                            # Normal paket
                            if len(data) > 50:
                                self.root.after(0, lambda sz=len(data): self.log_message(f"📡 UDP from {addr[0]}:{addr[1]} ({sz} bytes) ⚠️ BÜYÜK PAKET"))
                                self.root.after(0, lambda d=data: self.log_message(f"   RAW: {hexstr(d[:100])}{'...' if len(d) > 100 else ''}"))
                            else:
                                self.root.after(0, lambda: self.log_message(f"📡 UDP from {addr[0]}:{addr[1]} ({len(data)} bytes)"))
                        
                        # TIS paketini extract et
                        new_data = data[offset:] if offset > 0 else data
                        
                    except socket.timeout:
                        pass
                    except Exception as e:
                        if self.monitoring:
                            self.root.after(0, lambda: self.log_message(f"⚠️ UDP error: {e}"))
                        pass

                if new_data:
                    buffer += new_data
                    
                    # Paket işleme - basit ama etkili approach
                    # Kısa aralıklarla buffer'da tam paketler ara
                    if len(buffer) >= 13:
                        VALID_START_CODES = [(0xAA, 0xAA), (0xBB, 0xBB), (0xCC, 0xCC)]
                        
                        packet_found = False
                        for i in range(len(buffer) - 2):
                            for byte1, byte2 in VALID_START_CODES:
                                if buffer[i] == byte1 and buffer[i + 1] == byte2:
                                    
                                    if i + 2 < len(buffer):
                                        length = buffer[i + 2]
                                        total_size = length + 2  # length + start_code
                                        
                                        # Length limiti: minimum 11, maximum 200 (discovery response'lar 158 byte olabilir)
                                        if 11 <= length <= 200 and i + total_size <= len(buffer):
                                            packet = buffer[i:i + total_size]
                                            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                            
                                            # Parse packet
                                            parsed = self.parse_received_packet(packet)
                                            self.log_message(f"📥 ALINDI [{timestamp}]: {hexstr(packet)}")
                                            if parsed:
                                                self.log_message(f"   📋 Op: 0x{parsed['op_code']:04X} | {parsed['src_subnet']}.{parsed['src_device']}→{parsed['tgt_subnet']}.{parsed['tgt_device']} | Data: {hexstr(parsed['additional_data'])}")
                                                
                                                # Operation Code Tracking - Her gelen paketi kaydet
                                                self.update_current_opcodes(parsed)
                                                
                                                # Paket izleme için gelen paketi işle
                                                self.process_packet_for_monitoring(parsed, is_outgoing=False)
                                                
                                                # PASIF DİNLEME: Ağdaki HER cihazı topla (sadece discovery değil)
                                                # Kendi paketlerimizi filtrele (1.254 = PC)
                                                address = f"{parsed['src_subnet']}.{parsed['src_device']}"
                                                if address != "1.254" and self.scanning:
                                                    device_name = ""
                                                    
                                                    # 000F response'dan device name extract et
                                                    if parsed['op_code'] == 0x000F:
                                                        device_name = self.extract_device_name(parsed['additional_data'])
                                                        if device_name:
                                                            self.log_message(f"   🏷️ Device Name: '{device_name}'")
                                                    
                                                    self.log_message(f"   ➕ Cihaz: {address} Type=0x{parsed['src_type']:04X} Op=0x{parsed['op_code']:04X}")
                                                    self.add_discovered_device(address, 0, parsed['src_type'], parsed['op_code'], device_name)
                                            
                                            buffer = buffer[i + total_size:]
                                            packet_found = True
                                            break
                            if packet_found:
                                break
                        
                        if not packet_found:
                            buffer = buffer[1:]  # İlk byte'ı at
                        
                        if len(buffer) > 1000:  # Buffer overflow koruması
                            buffer = buffer[500:]
                
                time.sleep(0.01)
                
            except Exception as e:
                if self.monitoring:
                    self.log_message(f"❌ İzleme hatası: {e}")
                break
    
    def start_network_scan(self):
        """TIS ağ taramasını başlat"""
        if not self.is_connected:
            messagebox.showwarning("Bağlantı", "Önce RS485'e bağlanın!")
            return
            
        if self.scanning:
            messagebox.showinfo("Tarama", "Tarama zaten devam ediyor!")
            return
        
        # Monitoring otomatik başlat (response'ları yakalamak için)
        if not self.monitoring:
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self.monitor_loop)
            self.monitor_thread.daemon = True
            self.monitor_thread.start()
            self.monitor_btn.config(text="İzlemeyi Durdur")
            self.log_message("🔍 İzleme başlatıldı...")
            
        self.scanning = True
        self.scan_btn.config(state="disabled")
        self.scan_status_var.set("Tarama başlıyor...")
        
        # Tarama thread'ini başlat
        self.scan_thread = threading.Thread(target=self.network_scan_worker)
        self.scan_thread.daemon = True
        self.scan_thread.start()
        
        self.log_message("🔍 TIS ağ taraması başlatıldı")
    
    def stop_network_scan(self):
        """Ağ taramasını durdur"""
        self.scanning = False
        self.scan_btn.config(state="normal")
        self.scan_status_var.set("Tarama durduruldu")
        self.log_message("⏹️ Tarama durduruldu")
    
    def clear_device_list(self):
        """Cihaz listesini temizle"""
        self.device_tree.delete(*self.device_tree.get_children())
        self.discovered_devices.clear()
        self.log_message("🗑️ Cihaz listesi temizlendi")
    
    def network_scan_worker(self):
        """Ağ tarama worker thread'i - TISControlProtocol stratejisi"""
        try:
            subnet = int(self.scan_subnet_var.get())
            start_device = int(self.scan_start_var.get())
            end_device = int(self.scan_end_var.get())
            
            # TISControlProtocol YANLIŞ kullanıyor! Gerçek: 0xF003 (TIS DevSearch kullanır)
            discovery_op = 0xF003  # Discovery Request (Response: 0xF004)
            retry_count = 10
            retry_interval = 1.5  # saniye
            
            self.log_message(f"📡 Tarama başlıyor: {subnet}.{start_device}-{end_device}")
            self.log_message(f"🔍 Strateji: 0x{discovery_op:04X} paketini {retry_count} kez gönder")
            self.log_message(f"📊 Pasif dinleme: Ağdaki TÜM trafikten cihaz topla")
            
            # Discovery paketini 10 kez tekrarla
            for i in range(retry_count):
                if not self.scanning:
                    break
                    
                self.log_message(f"🔎 Discovery {i+1}/{retry_count}...")
                self.send_discovery_broadcast(discovery_op)
                
                # Her broadcast sonrası dinle
                time.sleep(retry_interval)
                
                # Progress güncelle
                progress = ((i + 1) / retry_count) * 100
                self.scan_status_var.set(f"Tarama: {i+1}/{retry_count} (%{progress:.0f})")
            
            if self.scanning:
                # Final dinleme - Ağdaki tüm trafiği topla
                self.log_message("⏳ Final: Ağdaki tüm trafiği topluyorum (10 saniye)...")
                time.sleep(10.0)
                
                device_count = len(self.discovered_devices)
                self.scan_status_var.set(f"Tamamlandı - {device_count} cihaz")
                self.log_message(f"✅ Tarama tamamlandı - {device_count} cihaz bulundu")
                
                # Bulunan cihazları listele
                for addr, info in self.discovered_devices.items():
                    self.log_message(f"   📌 {addr}: {info.get('model', 'Unknown')}")
            
        except Exception as e:
            self.log_message(f"❌ Tarama hatası: {e}")
            self.scan_status_var.set("Tarama hatası")
        finally:
            self.scanning = False
            self.scan_btn.config(state="normal")
    
    def send_discovery_broadcast(self, op_code: int):
        """Discovery broadcast paketi gönder"""
        try:
            # Broadcast packet oluştur (255.255 target)
            subnet = int(self.scan_subnet_var.get())
            
            # Source bilgileri
            src_subnet = subnet
            src_device = 254  # Scanner device ID
            src_type = 0x0000  # Control panel type
            
            # Target: Broadcast (255.255 - TIS DevSearch format)
            tgt_subnet = 255
            tgt_device = 255  # TIS DevSearch uses 255.255
            
            # Additional data (genellikle boş)
            additional_data = b''
            
            # Data package oluştur (TIS DevSearch format: 0xF003 → 255.255)
            data_package = bytearray()
            data_package.append(1)                    # Source subnet
            data_package.append(254)                  # Source device
            data_package.extend([0xFF, 0xFE])        # Source type
            data_package.extend([(op_code >> 8) & 0xFF, op_code & 0xFF])  # Operation code
            data_package.append(255)                  # Target subnet (broadcast)
            data_package.append(255)                  # Target device (broadcast)
            data_package.extend(additional_data)
            
            # Length ve CRC hesapla
            length = 1 + len(data_package) + 2
            crc_data = bytes([length]) + bytes(data_package)
            crc = pack_crc_c_style(list(crc_data))
            
            # Tam paket oluştur
            start_code = 0xAAAA
            full_packet = (
                bytes([(start_code >> 8) & 0xFF, start_code & 0xFF]) +
                bytes([length]) +
                bytes(data_package) +
                bytes([(crc >> 8) & 0xFF, crc & 0xFF])
            )
            
            # Paket gönder
            if self.is_connected:
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                
                if self.connection_mode == "RS485":
                    self.serial_port.write(full_packet)
                    self.log_message(f"📤 Discovery [{timestamp}] Op:0x{op_code:04X} → 255.255 (RS485): {hexstr(full_packet)}")
                else:
                    # UDP Broadcast - SMARTCLOUD header ekle (TISControlProtocol format)
                    # Aktif network interface IP'sini otomatik tespit et (Ethernet/WiFi)
                    local_ip = get_local_ip()
                    ip_bytes = bytes([int(x) for x in local_ip.split('.')])
                    smartcloud_header = b'SMARTCLOUD'
                    udp_packet = ip_bytes + smartcloud_header + full_packet
                    self.log_message(f"📍 Aktif Network IP: {local_ip} (Otomatik tespit)")
                    
                    # Çoklu broadcast strateji
                    broadcast_addresses = [
                        ('255.255.255.255', 6000),  # Global broadcast
                        (get_broadcast_address(), 6000),  # Network-specific broadcast
                    ]
                    
                    success_count = 0
                    for addr, port in broadcast_addresses:
                        try:
                            bytes_sent = self.udp_socket.sendto(udp_packet, (addr, port))
                            if bytes_sent == len(udp_packet):
                                success_count += 1
                                self.log_message(f"✅ UDP Broadcast → {addr}:{port} ({bytes_sent} bytes gönderildi, SMARTCLOUD header dahil)")
                            else:
                                self.log_message(f"⚠️ UDP Broadcast → {addr}:{port} (Kısmi: {bytes_sent}/{len(udp_packet)} bytes)")
                        except Exception as e:
                            self.log_message(f"❌ UDP Broadcast → {addr}:{port} HATA: {e}")
                    
                    if success_count > 0:
                        self.log_message(f"📤 Discovery [{timestamp}] Op:0x{op_code:04X}: {hexstr(full_packet)}")
                    else:
                        self.log_message(f"❌ Hiçbir broadcast başarısız oldu!")
            else:
                self.log_message("⚠️ Bağlantı yok - paket gönderilemedi")
            
        except Exception as e:
            import traceback
            self.log_message(f"❌ Discovery broadcast hatası: {e}")
            self.log_message(f"🔍 Traceback: {traceback.format_exc()}")
            
    def extract_device_name(self, additional_data: bytes) -> str:
        """000F response'dan device name'i extract et"""
        try:
            if not additional_data or len(additional_data) == 0:
                return ""
            
            # Null byte'a kadar oku (UTF-8 string)
            null_pos = additional_data.find(0)
            if null_pos == -1:
                # Null byte bulunamadı, tüm data'yı kullan
                name_bytes = additional_data
            else:
                name_bytes = additional_data[:null_pos]
            
            if len(name_bytes) == 0:
                return ""
                
            # UTF-8 decode et
            device_name = name_bytes.decode('utf-8', errors='ignore').strip()
            
            # Debug log
            if device_name:
                self.log_message(f"   🏷️ Name bytes: {hexstr(name_bytes)} → '{device_name}'")
                
            return device_name
            
        except Exception as e:
            self.log_message(f"❌ Device name extract hatası: {e}")
            return ""

            # Gönder
            self.serial_port.write(full_packet)
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            self.log_message(f"📤 Discovery [{timestamp}] Op:0x{op_code:04X} → 255.255: {hexstr(full_packet)}")
            
        except Exception as e:
            self.log_message(f"❌ Discovery broadcast hatası: {e}")
    
    def add_discovered_device(self, address: str, device_type: int, src_type: int, op_code: int, device_name: str = ""):
        """Bulunan cihazı listeye ekle - TIS formatında"""
        try:
            # TIS yazılımına benzer format
            model = get_device_type_name(src_type)           # Model sütunu
            comment = device_name if device_name.strip() else ""  # Comment sütunu (cihaz adı)
            
            # Description mapping - TIS yazılımından
            description_map = {
                0x8022: "TIS Health Sensor",
                0x80BA: "TIS Radar Sensor With IRE",
                0x802B: "Room Control Unit 20 In 24 Out",
                0x807A: "TIS Zigbee Home Automation Converter",
                0x2332: "LUNA TFT TOUCH SCREEN 4.3",
                0x0076: "4 Zone Dry Contact DIGITAL INPUT"
            }
            description = description_map.get(src_type, f"Unknown Device (0x{src_type:04X})")
            type_hex = f"0x{src_type:04X}"
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            if address not in self.discovered_devices:
                # Yeni cihaz
                self.discovered_devices[address] = {
                    'type': src_type,
                    'model': model,
                    'comment': comment,
                    'description': description,
                    'last_seen': timestamp,
                    'responses': [op_code]
                }
                
                # Treeview'e ekle (Thread-safe GUI update)
                self.root.after(0, self._add_device_to_tree, address, model, comment, description, type_hex, timestamp)
                self.log_message(f"🎯 Yeni cihaz bulundu: {address} - {model}")
                
            else:
                # Mevcut cihazı güncelle
                device = self.discovered_devices[address]
                device['last_seen'] = timestamp
                device['model'] = model
                device['description'] = description
                
                # Comment güncelleme (000F response'dan gelirse)
                if device_name and device_name.strip():
                    device['comment'] = device_name
                    comment = device_name
                else:
                    comment = device.get('comment', '')
                    
                if op_code not in device['responses']:
                    device['responses'].append(op_code)
                
                # Treeview'de güncelle (Thread-safe GUI update)
                self.root.after(0, self._update_device_in_tree, address, model, comment, description, type_hex, timestamp)
                
                self.log_message(f"🔄 Cihaz güncellendi: {address} - {model}")
                
        except Exception as e:
            self.log_message(f"❌ Cihaz ekleme hatası: {e}")

    def _add_device_to_tree(self, address: str, model: str, comment: str, description: str, type_hex: str, timestamp: str):
        """Thread-safe: Cihazı treeview'e ekle - TIS formatında"""
        try:
            # TIS yazılımı format: (Adres, Model, Comment, Description, Device Type, Status, Son Görülme)
            values = (address, model, comment, description, type_hex, "Online", timestamp)
            self.device_tree.insert("", "end", values=values)
        except Exception as e:
            self.log_message(f"❌ Treeview ekleme hatası: {e}")

    def _update_device_in_tree(self, address: str, model: str, comment: str, description: str, type_hex: str, timestamp: str):
        """Thread-safe: Cihazı treeview'de güncelle - TIS formatında"""
        try:
            # Mevcut cihazı bul ve güncelle
            for item in self.device_tree.get_children():
                values = self.device_tree.item(item, "values")
                if values and len(values) > 0 and values[0] == address:
                    new_values = (address, model, comment, description, type_hex, "Online", timestamp)
                    self.device_tree.item(item, values=new_values)
                    break
        except Exception as e:
            self.log_message(f"❌ Treeview güncelleme hatası: {e}")

    def is_discovery_response(self, parsed: dict) -> bool:
        """Bu paket bir discovery response mu?"""
        if not parsed:
            return False
            
        # Discovery response operation codes
        discovery_responses = [0xF004, 0x000F, 0xDA45, 0xDA44, 0x0002]  # Response codes
        
        return parsed['op_code'] in discovery_responses

    def parse_received_packet(self, packet: bytes):
        """Alınan paketi parse et"""
        try:
            if len(packet) < 13:
                return None
                
            parsed = {
                'start_code': (packet[0] << 8) | packet[1],
                'length': packet[2],
                'src_subnet': packet[3],
                'src_device': packet[4],
                'src_type': (packet[5] << 8) | packet[6],
                'op_code': (packet[7] << 8) | packet[8],
                'tgt_subnet': packet[9],
                'tgt_device': packet[10],
                'additional_data': b'',
                'crc': (packet[-2] << 8) | packet[-1]
            }
            
            # Additional data
            if parsed['length'] > 11:
                additional_start = 11
                crc_start = parsed['length'] + 2 - 2
                if additional_start < crc_start:
                    parsed['additional_data'] = packet[additional_start:crc_start]
            
            return parsed
            
        except:
            return None
    
    def log_message(self, message: str):
        """Log mesajı ekle"""
        def update_log():
            self.log_text.insert(tk.END, message + "\n")
            self.log_text.see(tk.END)
        
        self.root.after(0, update_log)
    
    def clear_monitor(self):
        """İzleme alanını temizle"""
        self.log_text.delete(1.0, tk.END)
    
    def run(self):
        """GUI'yi çalıştır"""
        self.root.mainloop()
        
        # Cleanup
        if self.is_connected and self.serial_port:
            self.serial_port.close()

    def start_opcode_discovery(self):
        """Pasif Op Code discovery - mevcut trafiği analiz et"""
        try:
            self.opcode_discovery_active = True
            self.opcode_status_var.set("🔎 Op Code Discovery aktif - trafik analiz ediliyor...")
            self.log_message("🔎 Operation Code Discovery başlatıldı - mevcut trafik analiz ediliyor")
            
            # Monitoring otomatik başlat
            if not self.monitoring:
                self.toggle_monitoring()
                
        except Exception as e:
            self.log_message(f"❌ Op Code Discovery hatası: {e}")

    def start_smart_discovery(self):
        """Akıllı Op Code discovery - bilinen cihazlara test paketleri gönder"""
        try:
            if not self.is_connected:
                messagebox.showwarning("Bağlantı", "Önce RS485'e bağlanın!")
                return
                
            self.opcode_status_var.set("🧠 Smart Discovery başlıyor...")
            self.log_message("🧠 Smart Op Code Discovery başlatıldı")
            
            # Bilinen cihazlara test op code'ları gönder
            test_opcodes = [
                0x000E, 0x000F, 0x0031, 0x0032, 0x0033, 0x0034, 0x0035,
                0x0002, 0x0003, 0x0004, 0x0005,
                0x0020, 0x0021, 0x0022, 0x0023,
                0x0040, 0x0041, 0x0042,
                0x0050, 0x0051, 0x0052,
                0xF003, 0xF004, 0xF005, 0xF006,
                0xDA44, 0xDA45, 0xEFFF, 0xE000, 0xE001
            ]
            
            # Thread'de çalıştır
            discovery_thread = threading.Thread(
                target=self.smart_discovery_worker,
                args=(test_opcodes,)
            )
            discovery_thread.daemon = True
            discovery_thread.start()
            
        except Exception as e:
            self.log_message(f"❌ Smart Discovery hatası: {e}")

    def smart_discovery_worker(self, test_opcodes):
        """Smart Discovery worker thread"""
        try:
            for i, op_code in enumerate(test_opcodes):
                if not self.is_connected:
                    break
                    
                self.log_message(f"🧠 Test Op Code: 0x{op_code:04X}")
                
                # Her tespit edilen cihaza gönder
                for address in list(self.discovered_devices.keys()):
                    if not self.is_connected:
                        break
                        
                    parts = address.split('.')
                    if len(parts) == 2:
                        subnet = int(parts[0])
                        device = int(parts[1])
                        
                        # Test paketi gönder
                        self.send_test_opcode(op_code, subnet, device)
                        time.sleep(0.1)  # Kısa beklem
                
                # Progress güncelle
                progress = ((i + 1) / len(test_opcodes)) * 100
                self.opcode_status_var.set(f"🧠 Smart Discovery: %{progress:.1f}")
                
                time.sleep(0.5)  # Op code'lar arası beklem
                
            self.opcode_status_var.set(f"✅ Smart Discovery tamamlandı")
            self.log_message("✅ Smart Op Code Discovery tamamlandı")
            
        except Exception as e:
            self.log_message(f"❌ Smart Discovery worker hatası: {e}")

    def start_brute_force_discovery(self):
        """Brute Force Op Code discovery - tüm op code'ları sistematik test et"""
        try:
            if not self.is_connected:
                messagebox.showwarning("Bağlantı", "Önce RS485'e bağlanın!")
                return
                
            if not self.discovered_devices:
                messagebox.showwarning("Hedef Yok", "Önce ağ taraması yapın ve hedef cihazları bulun!")
                return
                
            # Kullanıcıdan onay al
            result = messagebox.askyesno(
                "Brute Force Discovery",
                "Bu işlem tüm operation code'ları (0x0000-0xFFFF) test edecek.\n"
                "Çok uzun sürebilir ve ağda trafik yoğunluğu yaratır.\n"
                "Devam etmek istiyor musunuz?"
            )
            
            if not result:
                return
                
            self.brute_force_discovery = True
            self.current_brute_force_code = 0x0000
            self.opcode_status_var.set("⚡ Brute Force Discovery başlıyor...")
            self.log_message("⚡ Brute Force Op Code Discovery başlatıldı (0x0000-0xFFFF)")
            
            # Thread'de çalıştır
            brute_thread = threading.Thread(target=self.brute_force_worker)
            brute_thread.daemon = True
            brute_thread.start()
            
        except Exception as e:
            self.log_message(f"❌ Brute Force Discovery hatası: {e}")

    def brute_force_worker(self):
        """Brute Force Discovery worker thread"""
        try:
            total_codes = 0xFFFF
            
            for op_code in range(0x0000, 0xFFFF + 1):
                if not self.brute_force_discovery or not self.is_connected:
                    break
                    
                self.current_brute_force_code = op_code
                
                # İlk tespit edilen cihaza gönder
                if self.discovered_devices:
                    first_address = next(iter(self.discovered_devices.keys()))
                    parts = first_address.split('.')
                    if len(parts) == 2:
                        subnet = int(parts[0])
                        device = int(parts[1])
                        
                        # Test paketi gönder
                        self.send_test_opcode(op_code, subnet, device)
                        time.sleep(0.01)  # Çok kısa beklem
                
                # Progress güncelle (her 100 op code'da bir)
                if op_code % 100 == 0:
                    progress = (op_code / total_codes) * 100
                    self.opcode_status_var.set(f"⚡ Brute Force: 0x{op_code:04X} (%{progress:.1f})")
                    
                # Throttling - çok hızlı gönderme
                if op_code % 1000 == 0:
                    time.sleep(0.1)  # Her 1000 op code'da kısa mola
                    
            self.brute_force_discovery = False
            self.opcode_status_var.set(f"✅ Brute Force Discovery tamamlandı")
            self.log_message("✅ Brute Force Op Code Discovery tamamlandı")
            
        except Exception as e:
            self.log_message(f"❌ Brute Force Discovery worker hatası: {e}")
            self.brute_force_discovery = False

    def send_test_opcode(self, op_code, target_subnet, target_device):
        """Test için Op Code paketi gönder"""
        try:
            # Test paketi oluştur
            src_subnet = 1
            src_device = 254
            src_type = 0xFFFE
            
            # Data package oluştur
            data_package = bytearray()
            data_package.append(src_subnet)
            data_package.append(src_device)
            data_package.extend([(src_type >> 8) & 0xFF, src_type & 0xFF])
            data_package.extend([(op_code >> 8) & 0xFF, op_code & 0xFF])
            data_package.append(target_subnet)
            data_package.append(target_device)
            # Boş additional data
            
            # Length ve CRC hesapla
            length = 1 + len(data_package) + 2
            crc_data = bytes([length]) + bytes(data_package)
            crc = pack_crc_c_style(list(crc_data))
            
            # Tam paket oluştur
            start_code = 0xAAAA
            full_packet = (
                bytes([(start_code >> 8) & 0xFF, start_code & 0xFF]) +
                bytes([length]) +
                bytes(data_package) +
                bytes([(crc >> 8) & 0xFF, crc & 0xFF])
            )
            
            # Paket gönder
            if self.serial_port and self.is_connected:
                self.serial_port.write(full_packet)
                
        except Exception as e:
            self.log_message(f"❌ Test Op Code gönderim hatası: {e}")

    def show_opcode_database(self):
        """Op Code veritabanını göster"""
        try:
            # Yeni pencere oluştur
            db_window = tk.Toplevel(self.root)
            db_window.title("TIS Operation Code Database")
            db_window.geometry("900x600")
            
            # Treeview oluştur
            columns = ("Op Code", "Hex", "Açıklama", "Kategori", "Tespit Edildi")
            db_tree = ttk.Treeview(db_window, columns=columns, show="headings", height=20)
            
            # Sütun başlıkları
            db_tree.heading("Op Code", text="Op Code")
            db_tree.heading("Hex", text="Hex Değer")
            db_tree.heading("Açıklama", text="Açıklama")
            db_tree.heading("Kategori", text="Kategori")
            db_tree.heading("Tespit Edildi", text="Tespit Edildi")
            
            # Sütun genişlikleri
            db_tree.column("Op Code", width=80)
            db_tree.column("Hex", width=80)
            db_tree.column("Açıklama", width=300)
            db_tree.column("Kategori", width=120)
            db_tree.column("Tespit Edildi", width=100)
            
            # Kategoriler
            categories = {
                "Discovery & System": [0xF003, 0xF004, 0xF005, 0xF006],
                "Device Status": [0x000E, 0x000F, 0x0010, 0x0011],
                "Channel Control": [0x0031, 0x0032, 0x0033, 0x0034, 0x0035],
                "Scene Management": [0x0002, 0x0003, 0x0004, 0x0005],
                "System Commands": [0xDA44, 0xDA45, 0xEFFF, 0xE000, 0xE001],
                "Time & Schedule": [0x0020, 0x0021, 0x0022, 0x0023],
                "Security & Access": [0x0040, 0x0041, 0x0042],
                "Energy Management": [0x0050, 0x0051, 0x0052],
                "LUNA TFT": [0x1945, 0xE0ED, 0x1900],
                "Device Specific": [0x8000, 0x8001, 0x8002, 0x8003]
            }
            
            # Veritabanını doldur
            for category, op_codes in categories.items():
                for op_code in op_codes:
                    description = self.opcode_descriptions.get(op_code, "Unknown")
                    
                    # Tespit edildi mi kontrol et
                    detected = "❌ Hayır"
                    for device_opcodes in self.current_opcodes.values():
                        if op_code in device_opcodes:
                            detected = "✅ Evet"
                            break
                            
                    db_tree.insert("", "end", values=(
                        f"0x{op_code:04X}",
                        f"{op_code}",
                        description,
                        category,
                        detected
                    ))
            
            # Scrollbar
            db_scroll = ttk.Scrollbar(db_window, orient="vertical", command=db_tree.yview)
            db_tree.configure(yscrollcommand=db_scroll.set)
            
            # Pack
            db_tree.pack(side="left", fill="both", expand=True)
            db_scroll.pack(side="right", fill="y")
            
            # İstatistik bilgileri
            stats_frame = ttk.Frame(db_window)
            stats_frame.pack(fill="x", padx=10, pady=5)
            
            total_known = len(self.opcode_descriptions)
            detected_count = len([op for device_ops in self.current_opcodes.values() for op in device_ops.keys()])
            
            ttk.Label(stats_frame, text=f"Bilinen Op Code'lar: {total_known}").pack(side="left")
            ttk.Label(stats_frame, text=f"Tespit Edilen: {detected_count}").pack(side="left", padx=20)
            
        except Exception as e:
            self.log_message(f"❌ Op Code database gösterim hatası: {e}")

    def start_advanced_brute_force(self):
        """Gelişmiş Brute Force Discovery başlat"""
        try:
            if not self.is_connected:
                messagebox.showwarning("Bağlantı", "Önce RS485'e bağlanın!")
                return
                
            # Auto target kontrolü
            if self.bf_auto_target_var.get():
                if not self.discovered_devices:
                    messagebox.showwarning("Hedef Yok", "Auto Target seçili ama bulunan cihaz yok! Önce ağ taraması yapın.")
                    return
                    
            # Parametreleri al ve doğrula
            try:
                start_op = int(self.bf_start_var.get(), 16)
                end_op = int(self.bf_end_var.get(), 16)
                target_subnet = int(self.bf_target_subnet_var.get())
                target_device = int(self.bf_target_device_var.get())
                delay_ms = int(self.bf_delay_var.get())
                batch_size = int(self.bf_batch_var.get())
                
                if start_op > end_op:
                    messagebox.showerror("Hata", "Başlangıç Op Code bitiş Op Code'dan büyük olamaz!")
                    return
                    
            except ValueError as e:
                messagebox.showerror("Parametre Hatası", f"Geçersiz parametre: {e}")
                return
                
            # Monitoring başlat
            if not self.monitoring:
                self.toggle_monitoring()
                
            # Brute Force başlat
            self.bf_active = True
            self.bf_paused = False
            self.bf_current_op = start_op
            self.bf_stats = {
                'total_sent': 0,
                'responses_received': 0,
                'unique_opcodes': 0,
                'start_time': time.time()
            }
            
            # Buton durumları güncelle
            self.bf_start_btn.config(state="disabled")
            self.bf_stop_btn.config(state="normal")
            self.bf_pause_btn.config(state="normal")
            
            self.bf_status_var.set(f"🚀 Brute Force aktif: 0x{start_op:04X} - 0x{end_op:04X}")
            self.log_message(f"🚀 Gelişmiş Brute Force Discovery başlatıldı: 0x{start_op:04X} - 0x{end_op:04X}")
            
            # Worker thread başlat
            bf_thread = threading.Thread(
                target=self.advanced_brute_force_worker,
                args=(start_op, end_op, target_subnet, target_device, delay_ms, batch_size)
            )
            bf_thread.daemon = True
            bf_thread.start()
            
        except Exception as e:
            self.log_message(f"❌ Brute Force başlatma hatası: {e}")

    def stop_brute_force(self):
        """Brute Force Discovery durdur"""
        self.bf_active = False
        self.bf_paused = False
        
        # Buton durumları
        self.bf_start_btn.config(state="normal")
        self.bf_stop_btn.config(state="disabled")
        self.bf_pause_btn.config(state="disabled")
        
        self.bf_status_var.set("⏹️ Brute Force durduruldu")
        self.log_message("⏹️ Brute Force Discovery durduruldu")

    def pause_brute_force(self):
        """Brute Force Discovery duraklat/devam et"""
        if self.bf_paused:
            self.bf_paused = False
            self.bf_pause_btn.config(text="⏸️ Duraklat")
            self.bf_status_var.set("▶️ Brute Force devam ediyor")
            self.log_message("▶️ Brute Force Discovery devam ediyor")
        else:
            self.bf_paused = True
            self.bf_pause_btn.config(text="▶️ Devam Et")
            self.bf_status_var.set("⏸️ Brute Force duraklatıldı")
            self.log_message("⏸️ Brute Force Discovery duraklatıldı")

    def advanced_brute_force_worker(self, start_op, end_op, target_subnet, target_device, delay_ms, batch_size):
        """Gelişmiş Brute Force Discovery worker"""
        try:
            total_ops = end_op - start_op + 1
            sent_count = 0
            
            self.log_message(f"📊 Toplam test edilecek Op Code: {total_ops}")
            
            for op_code in range(start_op, end_op + 1):
                # Durdurma kontrolleri
                if not self.bf_active:
                    break
                    
                while self.bf_paused and self.bf_active:
                    time.sleep(0.1)
                    
                if not self.bf_active:
                    break
                    
                self.bf_current_op = op_code
                
                # Auto target kontrolü
                if self.bf_auto_target_var.get() and self.discovered_devices:
                    first_address = next(iter(self.discovered_devices.keys()))
                    parts = first_address.split('.')
                    if len(parts) == 2:
                        target_subnet = int(parts[0])
                        target_device = int(parts[1])
                        
                # Test paketi gönder ve response bekle
                before_responses = set()
                for addr, device_ops in self.current_opcodes.items():
                    for op_code_resp in device_ops.keys():
                        before_responses.add(f"{addr}_{op_code_resp}")
                        
                self.send_test_opcode(op_code, target_subnet, target_device)
                sent_count += 1
                self.bf_stats['total_sent'] = sent_count
                
                # Response kontrolü (kısa süre bekle)
                time.sleep(delay_ms / 1000.0)
                
                # Yeni response'ları kontrol et
                after_responses = set()
                for addr, device_ops in self.current_opcodes.items():
                    for op_code_resp in device_ops.keys():
                        after_responses.add(f"{addr}_{op_code_resp}")
                        
                new_responses = after_responses - before_responses
                if new_responses:
                    self.bf_stats['responses_received'] += len(new_responses)
                    for resp in new_responses:
                        addr, resp_op_str = resp.split('_', 1)
                        resp_op = int(resp_op_str)
                        self.check_bf_response(op_code, target_subnet, target_device, addr, resp_op)
                
                # Progress güncelle
                if sent_count % 10 == 0 or op_code == end_op:
                    progress = (sent_count / total_ops) * 100
                    self.bf_progress['value'] = progress
                    self.bf_progress_label.set(f"{progress:.1f}%")
                    
                    elapsed = time.time() - self.bf_stats['start_time']
                    rate = sent_count / elapsed if elapsed > 0 else 0
                    self.bf_status_var.set(f"🔍 Op: 0x{op_code:04X} | Gönderilen: {sent_count} | Hız: {rate:.1f}/s")
                
                # Batch kontrolü - her batch'te kısa mola
                if sent_count % batch_size == 0:
                    time.sleep(0.1)
                    
            # Tamamlandı
            if self.bf_active:
                elapsed = time.time() - self.bf_stats['start_time']
                self.bf_status_var.set(f"✅ Tamamlandı! {sent_count} Op Code test edildi ({elapsed:.1f}s)")
                self.log_message(f"✅ Brute Force Discovery tamamlandı: {sent_count} test, {self.bf_stats['responses_received']} response")
                
                # Final istatistik
                self.show_bf_statistics()
                
            self.stop_brute_force()  # Butonları resetle
            
        except Exception as e:
            self.log_message(f"❌ Brute Force worker hatası: {e}")
            self.stop_brute_force()

    def check_bf_response(self, sent_op_code, target_subnet, target_device, response_address, response_op):
        """Brute Force response kontrolü ve kayıt"""
        try:
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Bu response yeni mi?
            key = f"{sent_op_code:04X}_{response_address}_{response_op:04X}"
            if key not in self.bf_discovered_responses:
                self.bf_discovered_responses[key] = True
                
                # Response data'yı al
                data = b''
                if response_address in self.current_opcodes and response_op in self.current_opcodes[response_address]:
                    data = self.current_opcodes[response_address][response_op][1]
                
                # Results tree'ye ekle
                description = self.opcode_descriptions.get(response_op, "Unknown")
                status = "✅ Response" if response_op != sent_op_code else "🔄 Echo"
                
                self.root.after(0, self._add_bf_result,
                    sent_op_code, response_op, response_address, hexstr(data), timestamp, status)
                
                self.log_message(f"🎯 BF Response: Test=0x{sent_op_code:04X} → Response=0x{response_op:04X} from {response_address}")
                        
        except Exception as e:
            self.log_message(f"❌ BF response check hatası: {e}")

    def _add_bf_result(self, sent_op, response_op, address, data, timestamp, status):
        """Thread-safe: BF sonucunu treeview'e ekle"""
        try:
            values = (
                f"0x{sent_op:04X}",
                f"{sent_op}",
                "✅ Evet" if status == "✅ Response" else "🔄 Echo",
                address,
                f"0x{response_op:04X}",
                data,
                timestamp,
                status
            )
            self.bf_results_tree.insert("", "end", values=values)
            
        except Exception as e:
            self.log_message(f"❌ BF result ekleme hatası: {e}")

    def show_bf_statistics(self):
        """Brute Force istatistikleri göster"""
        try:
            elapsed = time.time() - self.bf_stats['start_time'] if self.bf_stats['start_time'] else 0
            
            stats_window = tk.Toplevel(self.root)
            stats_window.title("Brute Force Discovery İstatistikleri")
            stats_window.geometry("500x400")
            
            stats_text = scrolledtext.ScrolledText(stats_window, width=60, height=20)
            stats_text.pack(fill="both", expand=True, padx=10, pady=10)
            
            # İstatistikler
            stats_content = f"""
📊 BRUTE FORCE DISCOVERY İSTATİSTİKLERİ
{'='*50}

⏱️ Toplam Süre: {elapsed:.1f} saniye
📤 Gönderilen Paket: {self.bf_stats['total_sent']}
📥 Alınan Response: {self.bf_stats['responses_received']}
🎯 Başarı Oranı: {(self.bf_stats['responses_received']/self.bf_stats['total_sent']*100) if self.bf_stats['total_sent'] > 0 else 0:.2f}%
🚀 Gönderim Hızı: {self.bf_stats['total_sent']/elapsed if elapsed > 0 else 0:.1f} paket/saniye

📋 BULUNAN OPERATION CODE'LAR:
{'-'*50}
"""
            
            # Unique op code'ları listele
            unique_responses = set()
            for key in self.bf_discovered_responses.keys():
                parts = key.split('_')
                if len(parts) >= 3:
                    response_op_hex = parts[2]
                    response_op = int(response_op_hex, 16)
                    unique_responses.add(response_op)
            
            for op_code in sorted(unique_responses):
                description = self.opcode_descriptions.get(op_code, "Unknown")
                stats_content += f"• 0x{op_code:04X}: {description}\n"
                
            stats_content += f"\n📈 Toplam Unique Op Code: {len(unique_responses)}"
            
            stats_text.insert(tk.END, stats_content)
            stats_text.config(state=tk.DISABLED)
            
        except Exception as e:
            self.log_message(f"❌ İstatistik gösterme hatası: {e}")

    def toggle_packet_monitoring(self):
        """Paket izlemeyi başlat/durdur"""
        if not self.packet_monitoring_active:
            # Monitoring otomatik başlat
            if not self.monitoring:
                self.toggle_monitoring()
            
            self.packet_monitoring_active = True
            self.packet_monitor_btn.config(text="⏹️ Paket İzlemeyi Durdur")
            self.log_message("📡 Paket İzleme başlatıldı - Sorgu-Response çiftleri kaydediliyor")
        else:
            self.packet_monitoring_active = False
            self.packet_monitor_btn.config(text="📡 Paket İzlemeyi Başlat")
            self.log_message("⏹️ Paket İzleme durduruldu")

    def clear_packet_monitor(self):
        """Paket izleme listesini temizle"""
        self.packet_pairs.clear()
        self.pending_queries.clear()
        
        # Tree'yi temizle
        for item in self.packet_pairs_tree.get_children():
            self.packet_pairs_tree.delete(item)
        
        self.update_packet_stats()
        self.log_message("🗑️ Paket İzleme listesi temizlendi")

    def apply_packet_filter(self):
        """Paket filtresini uygula"""
        filter_text = self.packet_filter_var.get().strip()
        if not filter_text:
            return
        
        try:
            # Op code filtresi
            if filter_text.startswith("0x"):
                filter_op = int(filter_text, 16)
            else:
                filter_op = int(filter_text, 16) if filter_text.isdigit() else None
            
            # Tree'yi temizle ve filtrelenmiş sonuçları göster
            for item in self.packet_pairs_tree.get_children():
                self.packet_pairs_tree.delete(item)
            
            for query_packet, response_packet, timestamp, duration in self.packet_pairs:
                if filter_op is None or query_packet['op_code'] == filter_op or (response_packet and response_packet['op_code'] == filter_op):
                    self._add_packet_pair_to_tree(query_packet, response_packet, timestamp, duration)
            
            self.log_message(f"🔍 Paket filtresi uygulandı: {filter_text}")
            
        except ValueError:
            messagebox.showerror("Filtre Hatası", "Geçersiz Op Code formatı!")

    def clear_packet_filter(self):
        """Paket filtresini temizle"""
        self.packet_filter_var.set("")
        
        # Tüm paketleri yeniden göster
        for item in self.packet_pairs_tree.get_children():
            self.packet_pairs_tree.delete(item)
        
        for query_packet, response_packet, timestamp, duration in self.packet_pairs:
            self._add_packet_pair_to_tree(query_packet, response_packet, timestamp, duration)

    def export_packet_pairs(self):
        """Paket çiftlerini CSV'ye aktar"""
        try:
            from tkinter import filedialog
            import csv
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Paket Çiftlerini Kaydet"
            )
            
            if filename:
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Header
                    writer.writerow([
                        "Zaman", "Sorgu_Op", "Sorgu_Kaynak", "Sorgu_Hedef", "Sorgu_Data",
                        "Response_Op", "Response_Kaynak", "Response_Data", "Süre_ms", "Durum"
                    ])
                    
                    # Data
                    for query_packet, response_packet, timestamp, duration in self.packet_pairs:
                        query_src = f"{query_packet['src_subnet']}.{query_packet['src_device']}"
                        query_tgt = f"{query_packet['tgt_subnet']}.{query_packet['tgt_device']}"
                        query_data = hexstr(query_packet['additional_data'])
                        
                        if response_packet:
                            resp_src = f"{response_packet['src_subnet']}.{response_packet['src_device']}"
                            resp_data = hexstr(response_packet['additional_data'])
                            status = "✅ Eşleşti"
                        else:
                            resp_src = "-"
                            resp_data = "-"
                            status = "⏳ Bekliyor"
                        
                        writer.writerow([
                            timestamp,
                            f"0x{query_packet['op_code']:04X}",
                            query_src,
                            query_tgt,
                            query_data,
                            f"0x{response_packet['op_code']:04X}" if response_packet else "-",
                            resp_src,
                            resp_data,
                            f"{duration:.1f}" if duration else "-",
                            status
                        ])
                
                self.log_message(f"💾 Paket çiftleri dışa aktarıldı: {filename}")
                messagebox.showinfo("Dışa Aktarma", f"Paket çiftleri başarıyla kaydedildi:\n{filename}")
                
        except Exception as e:
            self.log_message(f"❌ Dışa aktarma hatası: {e}")
            messagebox.showerror("Hata", f"Dışa aktarma hatası: {e}")

    def update_packet_stats(self):
        """Paket istatistiklerini güncelle"""
        total_pairs = len(self.packet_pairs)
        pending_queries = len(self.pending_queries)
        self.packet_stats_var.set(f"Toplam Çift: {total_pairs} | Bekleyen Sorgu: {pending_queries}")

    def process_packet_for_monitoring(self, parsed_packet: dict, is_outgoing: bool = False):
        """Paket izleme için paketi işle"""
        if not self.packet_monitoring_active:
            return
        
        try:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            op_code = parsed_packet['op_code']
            
            if is_outgoing:
                # Giden paket - sorgu olarak kaydet
                self.pending_queries[op_code] = (parsed_packet, time.time())
                self.log_message(f"📤 Sorgu kaydedildi: 0x{op_code:04X}")
                
            else:
                # Gelen paket - response olarak kontrol et
                response_op = op_code
                
                # Bu response hangi sorguya ait olabilir?
                matched_query = None
                query_timestamp = None
                
                # Basit eşleştirme: aynı op code veya +1 pattern
                for query_op, (query_packet, query_time) in list(self.pending_queries.items()):
                    if (query_op == response_op or
                        query_op + 1 == response_op or
                        self._is_response_pair(query_op, response_op)):
                        
                        matched_query = query_packet
                        query_timestamp = query_time
                        del self.pending_queries[query_op]
                        break
                
                if matched_query:
                    # Eşleşme bulundu
                    duration = (time.time() - query_timestamp) * 1000  # ms
                    self.packet_pairs.append((matched_query, parsed_packet, timestamp, duration))
                    self.root.after(0, self._add_packet_pair_to_tree, matched_query, parsed_packet, timestamp, duration)
                    self.log_message(f"✅ Paket çifti eşleşti: 0x{matched_query['op_code']:04X} → 0x{response_op:04X} ({duration:.1f}ms)")
                else:
                    # Eşleşmeyen response - tek başına kaydet
                    self.packet_pairs.append((parsed_packet, None, timestamp, None))
                    self.root.after(0, self._add_packet_pair_to_tree, parsed_packet, None, timestamp, None)
                    self.log_message(f"❓ Eşleşmeyen response: 0x{response_op:04X}")
            
            # İstatistikleri güncelle
            self.root.after(0, self.update_packet_stats)
            
        except Exception as e:
            self.log_message(f"❌ Paket izleme hatası: {e}")

    def _is_response_pair(self, query_op: int, response_op: int) -> bool:
        """Bu iki op code sorgu-response çifti mi?"""
        # Bilinen sorgu-response çiftleri
        known_pairs = {
            0x000E: 0x000F,  # Status Request → Status Response
            0xF003: 0xF004,  # Discovery Request → Discovery Response
            0xDA44: 0xDA45,  # System Status → System Response
            0x0002: 0x0003,  # Scene Control → Scene Status
            0x0031: 0x0032,  # Single Channel → Multi Channel (bazen)
            0xE3E0: 0xE3E1,  # Curtain Control → Curtain Response
            0xE3E2: 0xE3E3,  # Curtain Status Request → Curtain Status Response
        }
        
        return known_pairs.get(query_op) == response_op

    def _add_packet_pair_to_tree(self, query_packet, response_packet, timestamp, duration):
        """Thread-safe: Paket çiftini tree'ye ekle"""
        try:
            query_src = f"{query_packet['src_subnet']}.{query_packet['src_device']}"
            query_tgt = f"{query_packet['tgt_subnet']}.{query_packet['tgt_device']}"
            query_data = hexstr(query_packet['additional_data'])
            
            if response_packet:
                resp_src = f"{response_packet['src_subnet']}.{response_packet['src_device']}"
                resp_data = hexstr(response_packet['additional_data'])
                status = "✅ Eşleşti"
                duration_str = f"{duration:.1f}" if duration else "-"
                resp_op_str = f"0x{response_packet['op_code']:04X}"
            else:
                resp_src = "-"
                resp_data = "-"
                status = "❓ Tek Response"
                duration_str = "-"
                resp_op_str = "-"
            
            values = (
                timestamp,
                f"0x{query_packet['op_code']:04X}",
                query_src,
                query_tgt,
                query_data,
                resp_op_str,
                resp_src,
                resp_data,
                duration_str,
                status
            )
            
            self.packet_pairs_tree.insert("", "end", values=values)
            
        except Exception as e:
            self.log_message(f"❌ Paket tree ekleme hatası: {e}")

if __name__ == "__main__":
    app = TISGUITester()
    app.run()