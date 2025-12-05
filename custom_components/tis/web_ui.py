"""TIS Web UI Manager."""
import logging
import json
from aiohttp import web
from homeassistant import config_entries
from .discovery import discover_tis_devices
from .const import DOMAIN, CONF_HOST, CONF_SUBNET, CONF_DEVICE

_LOGGER = logging.getLogger(__name__)

class TISWebUI:
    """Web UI for TIS Control."""

    def __init__(self, hass):
        """Initialize."""
        self.hass = hass
        self.app = web.Application()
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/api/scan', self.handle_scan)
        self.app.router.add_post('/api/add', self.handle_add)
        self.runner = None
        self.site = None

    async def start(self):
        """Start the web server."""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            # Port 8888 kullanıyoruz (Çakışma olmaması için)
            self.site = web.TCPSite(self.runner, '0.0.0.0', 8888)
            await self.site.start()
            _LOGGER.info("TIS Web UI started on port 8888")
        except Exception as e:
            _LOGGER.error(f"Failed to start TIS Web UI: {e}")

    async def stop(self):
        """Stop the web server."""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

    async def handle_index(self, request):
        """Serve the HTML page."""
        html = """
        <!DOCTYPE html>
        <html lang="tr">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>TIS Cihaz Yöneticisi</title>
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; background-color: #f5f5f5; }
                .container { max-width: 1000px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                h1 { color: #333; border-bottom: 2px solid #03a9f4; padding-bottom: 10px; }
                table { border-collapse: collapse; width: 100%; margin-top: 20px; }
                th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
                th { background-color: #03a9f4; color: white; }
                tr:nth-child(even) { background-color: #f9f9f9; }
                tr:hover { background-color: #f1f1f1; }
                button { padding: 12px 24px; background: #4CAF50; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; transition: background 0.3s; }
                button:hover { background: #45a049; }
                button:disabled { background: #ccc; cursor: not-allowed; }
                .status { margin-top: 15px; font-weight: bold; color: #666; }
                .badge { padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; }
                .badge-blue { background: #e3f2fd; color: #1976d2; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🏠 TIS Akıllı Ev Yöneticisi</h1>
                <p>Ağınızdaki TIS cihazlarını taramak ve listelemek için aşağıdaki butona basın.</p>
                
                <button id="scanBtn" onclick="scan()">🔍 Ağı Tara (Scan Network)</button>
                <div id="status" class="status">Hazır</div>
                
                <table id="devices">
                    <thead>
                        <tr>
                            <th>Cihaz Adı</th>
                            <th>IP Adresi</th>
                            <th>Subnet ID</th>
                            <th>Device ID</th>
                            <th>Tip (Type)</th>
                            <th>İşlem</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr><td colspan="6" style="text-align:center">Henüz tarama yapılmadı...</td></tr>
                    </tbody>
                </table>
            </div>

            <script>
                async function scan() {
                    const btn = document.getElementById('scanBtn');
                    const status = document.getElementById('status');
                    const tbody = document.querySelector('#devices tbody');
                    
                    btn.disabled = true;
                    btn.innerText = "Taranıyor...";
                    status.innerText = "Ağ taranıyor, lütfen bekleyin (30sn)...";
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center">⏳ Taranıyor...</td></tr>';
                    
                    try {
                        const response = await fetch('/api/scan');
                        const devices = await response.json();
                        
                        tbody.innerHTML = '';
                        status.innerText = `Tarama Tamamlandı: ${devices.length} cihaz bulundu.`;
                        
                        if (devices.length === 0) {
                            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center">❌ Hiç cihaz bulunamadı.</td></tr>';
                        }
                        
                        devices.forEach(dev => {
                            const row = `<tr>
                                <td><strong>${dev.name}</strong></td>
                                <td><span class="badge badge-blue">${dev.host}</span></td>
                                <td>${dev.subnet}</td>
                                <td>${dev.device}</td>
                                <td>${dev.device_type_hex} (${dev.model_name})</td>
                                <td>
                                    <button onclick="addDevice('${dev.subnet}', '${dev.device}', '${dev.model_name}', ${dev.channels})" style="padding: 5px 10px; font-size: 14px;">
                                        Ekle
                                    </button>
                                </td>
                            </tr>`;
                            tbody.innerHTML += row;
                        });
                    } catch (e) {
                        status.innerText = "Hata oluştu: " + e;
                        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:red">Hata: ${e}</td></tr>`;
                    } finally {
                        btn.disabled = false;
                        btn.innerText = "🔍 Ağı Tara (Scan Network)";
                    }
                }

                async function addDevice(subnet, deviceId, modelName, channels) {
                    if (!confirm(`Cihazı eklemek istiyor musunuz?\nSubnet: ${subnet}\nDevice ID: ${deviceId}`)) {
                        return;
                    }

                    try {
                        const response = await fetch('/api/add', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                            },
                            body: JSON.stringify({
                                subnet: subnet,
                                device_id: deviceId,
                                model_name: modelName,
                                channels: channels
                            })
                        });
                        
                        const result = await response.json();
                        if (result.success) {
                            alert('Cihaz başarıyla eklendi!');
                        } else {
                            alert('Hata: ' + result.message);
                        }
                    } catch (err) {
                        alert('Hata: ' + err.message);
                    }
                }
            </script>
        </body>
        </html>
        """
        return web.Response(text=html, content_type='text/html')

    async def handle_scan(self, request):
        """Handle scan request."""
        devices = await discover_tis_devices(self.hass)
        # Convert dict to list for JSON
        dev_list = list(devices.values())
        return web.json_response(dev_list)

    async def handle_add(self, request):
        """Handle add device request."""
        try:
            data = await request.json()
            subnet = data.get('subnet')
            device_id = data.get('device_id')
            model_name = data.get('model_name')
            channels = data.get('channels')

            if not all([subnet, device_id]):
                return web.json_response({'success': False, 'message': 'Eksik parametreler'}, status=400)

            # Check if device already exists
            existing_entries = self.hass.config_entries.async_entries(DOMAIN)
            for entry in existing_entries:
                if entry.data.get(CONF_SUBNET) == subnet and entry.data.get(CONF_DEVICE) == device_id:
                    return web.json_response({'success': False, 'message': 'Cihaz zaten ekli'})

            # Create config entry
            self.hass.async_create_task(
                self.hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": config_entries.SOURCE_IMPORT},
                    data={
                        CONF_HOST: "0.0.0.0", # Dummy host, not used for UDP
                        CONF_SUBNET: int(subnet),
                        CONF_DEVICE: int(device_id),
                        "model_name": model_name,
                        "channels": channels
                    }
                )
            )

            return web.json_response({'success': True})
        except Exception as e:
            _LOGGER.error(f"Error adding device: {e}")
            return web.json_response({'success': False, 'message': str(e)}, status=500)
