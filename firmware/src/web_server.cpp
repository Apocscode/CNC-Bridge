/**
 * CNC Bridge Firmware — Web Server Implementation
 *
 * WiFi AP mode with REST API for remote DNC operations.
 */

#include "web_server.h"

// Static buffer for uploaded program data
static char uploadBuffer[64 * 1024];  // 64 KB max program
static size_t uploadSize = 0;

// ─── Constructor ────────────────────────────────────────────
BridgeWebServer::BridgeWebServer(SerialBridge& bridge)
    : _bridge(bridge),
      _server(WEB_SERVER_PORT),
      _active(false)
{}

// ─── Initialisation ─────────────────────────────────────────
void BridgeWebServer::begin() {
    // Start WiFi in AP mode
    WiFi.mode(WIFI_AP);
    WiFi.softAP(WIFI_AP_SSID, WIFI_AP_PASSWORD, WIFI_AP_CHANNEL);

    Serial.printf("[WIFI] AP started: SSID=%s  IP=%s\n",
                  WIFI_AP_SSID, WiFi.softAPIP().toString().c_str());

    setupRoutes();
    _server.begin();
    _active = true;

    Serial.printf("[WEB] Server started on port %d\n", WEB_SERVER_PORT);
}

// ─── Route setup ────────────────────────────────────────────
void BridgeWebServer::setupRoutes() {
    // Serve embedded dashboard
    _server.on("/", HTTP_GET, [](AsyncWebServerRequest* request) {
        request->send(200, "text/html", R"rawliteral(
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <title>CNC Bridge</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', sans-serif; background: #1e1e1e; color: #d4d4d4; }
        .header { background: #007acc; color: #fff; padding: 12px 20px; }
        .header h1 { font-size: 18px; font-weight: 500; }
        .container { padding: 20px; max-width: 800px; margin: 0 auto; }
        .card { background: #252526; border: 1px solid #3c3c3c; border-radius: 6px;
                padding: 16px; margin-bottom: 16px; }
        .card h2 { font-size: 14px; color: #007acc; margin-bottom: 10px; text-transform: uppercase; }
        .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }
        .stat { text-align: center; }
        .stat .value { font-size: 24px; font-weight: bold; color: #4ec9b0; }
        .stat .label { font-size: 11px; color: #808080; margin-top: 4px; }
        .status-badge { display: inline-block; padding: 4px 12px; border-radius: 12px;
                        font-size: 12px; font-weight: bold; }
        .status-idle { background: #3c3c3c; color: #808080; }
        .status-active { background: #1b4332; color: #4ec9b0; }
        .status-paused { background: #4a3000; color: #dcdcaa; }
        .status-error { background: #4a0000; color: #f48771; }
        .btn { border: none; padding: 8px 20px; border-radius: 4px; cursor: pointer;
               font-size: 13px; margin: 4px; color: #fff; }
        .btn-primary { background: #007acc; }
        .btn-warning { background: #d19a00; }
        .btn-danger { background: #cc3333; }
        .btn-success { background: #16825d; }
        .btn:hover { opacity: 0.85; }
        .controls { margin-top: 12px; }
        #upload-form input[type=file] { margin: 8px 0; }
        .progress { background: #3c3c3c; border-radius: 4px; height: 20px; margin: 8px 0; }
        .progress-bar { background: #007acc; height: 100%; border-radius: 4px;
                        transition: width 0.3s; min-width: 0; }
    </style>
</head>
<body>
    <div class="header"><h1>CNC Bridge — Anilam Crusader M</h1></div>
    <div class="container">
        <div class="card">
            <h2>Status</h2>
            <p>State: <span id="state" class="status-badge status-idle">IDLE</span>
               <span id="flow" style="margin-left:12px;font-size:12px"></span></p>
            <div class="stat-grid" style="margin-top:12px">
                <div class="stat"><div class="value" id="bytesSent">0</div><div class="label">Bytes Sent</div></div>
                <div class="stat"><div class="value" id="bytesRecv">0</div><div class="label">Bytes Received</div></div>
                <div class="stat"><div class="value" id="linesSent">0</div><div class="label">Lines Sent</div></div>
                <div class="stat"><div class="value" id="elapsed">0s</div><div class="label">Elapsed</div></div>
            </div>
            <div class="progress"><div class="progress-bar" id="progressBar" style="width:0%"></div></div>
        </div>

        <div class="card">
            <h2>Controls</h2>
            <div class="controls">
                <button class="btn btn-primary" onclick="api('passthrough')">Passthrough</button>
                <button class="btn btn-warning" onclick="api('pause')">Pause</button>
                <button class="btn btn-success" onclick="api('resume')">Resume</button>
                <button class="btn btn-danger"  onclick="api('abort')">Abort</button>
            </div>
        </div>

        <div class="card">
            <h2>Upload G-Code</h2>
            <form id="upload-form">
                <input type="file" id="file-input" accept=".nc,.tap,.gcode,.txt">
                <button type="submit" class="btn btn-primary">Send to Anilam</button>
            </form>
        </div>
    </div>

    <script>
        async function api(cmd) {
            await fetch('/api/' + cmd, { method: 'POST' });
        }

        async function refresh() {
            try {
                const r = await fetch('/api/status');
                const d = await r.json();
                document.getElementById('state').textContent = d.state;
                document.getElementById('state').className =
                    'status-badge status-' + (d.state === 'IDLE' ? 'idle' :
                    d.state === 'PAUSED' ? 'paused' : d.state === 'ERROR' ? 'error' : 'active');
                document.getElementById('bytesSent').textContent = d.bytesSent;
                document.getElementById('bytesRecv').textContent = d.bytesReceived;
                document.getElementById('linesSent').textContent = d.linesSent;
                document.getElementById('elapsed').textContent = (d.elapsed / 1000).toFixed(1) + 's';
                document.getElementById('flow').textContent = d.xoff ? '⏸ XOFF' : '';
                document.getElementById('progressBar').style.width = d.progress + '%';
            } catch (e) {}
        }

        document.getElementById('upload-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const file = document.getElementById('file-input').files[0];
            if (!file) return;
            const form = new FormData();
            form.append('file', file);
            await fetch('/api/upload', { method: 'POST', body: form });
        });

        setInterval(refresh, 500);
        refresh();
    </script>
</body>
</html>
)rawliteral");
    });

    // REST API endpoints
    _server.on("/api/status", HTTP_GET,
        [this](AsyncWebServerRequest* req) { handleStatus(req); });

    _server.on("/api/passthrough", HTTP_POST,
        [this](AsyncWebServerRequest* req) { handleStartPassthrough(req); });

    _server.on("/api/pause", HTTP_POST,
        [this](AsyncWebServerRequest* req) { handlePause(req); });

    _server.on("/api/resume", HTTP_POST,
        [this](AsyncWebServerRequest* req) { handleResume(req); });

    _server.on("/api/abort", HTTP_POST,
        [this](AsyncWebServerRequest* req) { handleAbort(req); });

    // File upload (multipart)
    _server.on("/api/upload", HTTP_POST,
        [this](AsyncWebServerRequest* req) {
            // After upload completes, start DNC send
            _bridge.startDNCSend(uploadBuffer, uploadSize);
            req->send(200, "application/json", "{\"ok\":true}");
        },
        [this](AsyncWebServerRequest* req, const String& filename,
               size_t index, uint8_t* data, size_t len, bool final) {
            handleUpload(req, filename, index, data, len, final);
        }
    );

    _server.onNotFound([this](AsyncWebServerRequest* req) { handleNotFound(req); });
}

// ─── API handlers ───────────────────────────────────────────
void BridgeWebServer::handleStatus(AsyncWebServerRequest* request) {
    request->send(200, "application/json", buildStatusJson());
}

void BridgeWebServer::handleStartPassthrough(AsyncWebServerRequest* request) {
    _bridge.startPassthrough();
    request->send(200, "application/json", "{\"ok\":true}");
}

void BridgeWebServer::handlePause(AsyncWebServerRequest* request) {
    _bridge.pause();
    request->send(200, "application/json", "{\"ok\":true}");
}

void BridgeWebServer::handleResume(AsyncWebServerRequest* request) {
    _bridge.resume();
    request->send(200, "application/json", "{\"ok\":true}");
}

void BridgeWebServer::handleAbort(AsyncWebServerRequest* request) {
    _bridge.abort();
    request->send(200, "application/json", "{\"ok\":true}");
}

void BridgeWebServer::handleUpload(AsyncWebServerRequest* request,
                                    const String& filename, size_t index,
                                    uint8_t* data, size_t len, bool final) {
    if (index == 0) {
        Serial.printf("[WEB] Upload started: %s\n", filename.c_str());
        uploadSize = 0;
    }

    // Copy into buffer
    if (uploadSize + len < sizeof(uploadBuffer)) {
        memcpy(uploadBuffer + uploadSize, data, len);
        uploadSize += len;
    }

    if (final) {
        uploadBuffer[uploadSize] = '\0';
        Serial.printf("[WEB] Upload complete: %s (%u bytes)\n",
                      filename.c_str(), uploadSize);
    }
}

void BridgeWebServer::handleNotFound(AsyncWebServerRequest* request) {
    request->send(404, "text/plain", "Not Found");
}

// ─── Helpers ────────────────────────────────────────────────
String BridgeWebServer::buildStatusJson() {
    StaticJsonDocument<512> doc;
    const TransferStats& s = _bridge.getStats();

    doc["state"]         = _bridge.getStateString();
    doc["progress"]      = _bridge.getProgress();
    doc["xoff"]          = _bridge.isXoffActive();
    doc["bytesSent"]     = s.bytesSent;
    doc["bytesReceived"] = s.bytesReceived;
    doc["linesSent"]     = s.linesSent;
    doc["linesReceived"] = s.linesReceived;
    doc["errors"]        = s.errors;
    doc["flowPauses"]    = s.flowPauses;
    doc["elapsed"]       = s.elapsed;

    String json;
    serializeJson(doc, json);
    return json;
}

void BridgeWebServer::update() {
    // AsyncWebServer handles requests in callbacks;
    // this is reserved for periodic tasks if needed.
}

String BridgeWebServer::getIPAddress() const {
    return WiFi.softAPIP().toString();
}
