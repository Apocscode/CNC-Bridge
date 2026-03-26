/**
 * CNC Bridge Firmware — Web Server Module
 *
 * Provides a WiFi-based web interface for wireless DNC transfer
 * and status monitoring.  Runs an async HTTP server with REST API
 * endpoints and a simple HTML dashboard served from SPIFFS/SD.
 */

#ifndef WEB_SERVER_H
#define WEB_SERVER_H

#include <Arduino.h>
#include <WiFi.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoJson.h>
#include "config.h"
#include "serial_bridge.h"

class BridgeWebServer {
public:
    BridgeWebServer(SerialBridge& bridge);

    /** Start WiFi AP and web server. */
    void begin();

    /** Call from loop() for housekeeping. */
    void update();

    /** Check if WiFi is active. */
    bool isActive() const { return _active; }

    /** Get the AP IP address. */
    String getIPAddress() const;

private:
    SerialBridge&    _bridge;
    AsyncWebServer   _server;
    bool             _active;

    // ── Route handlers ──
    void setupRoutes();
    void handleStatus(AsyncWebServerRequest* request);
    void handleStartPassthrough(AsyncWebServerRequest* request);
    void handlePause(AsyncWebServerRequest* request);
    void handleResume(AsyncWebServerRequest* request);
    void handleAbort(AsyncWebServerRequest* request);
    void handleUpload(AsyncWebServerRequest* request,
                      const String& filename, size_t index,
                      uint8_t* data, size_t len, bool final);
    void handleNotFound(AsyncWebServerRequest* request);

    // ── Helpers ──
    String buildStatusJson();
};

#endif // WEB_SERVER_H
