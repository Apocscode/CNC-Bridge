/**
 * CNC Bridge Firmware — Main Entry Point
 *
 * ESP32-S3 based serial bridge between a host PC and the
 * Anilam Crusader M CNC controller.
 *
 * Modes of operation:
 *   1. USB passthrough — transparent RS232 relay via USB-CDC
 *   2. DNC drip-feed  — line-by-line program transfer
 *   3. WiFi AP        — wireless web-based DNC + monitoring
 *   4. SD standalone  — send programs from SD card (no PC)
 *
 * Hardware:
 *   ESP32-S3 DevKitC-1
 *   MAX3232 RS232 transceiver on UART1
 *   SSD1306 128×64 OLED on I2C
 *   SD card module on SPI
 */

#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <SD.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

#include "config.h"
#include "serial_bridge.h"
#include "web_server.h"

// ─── Global objects ─────────────────────────────────────────
SerialBridge    bridge;
BridgeWebServer webServer(bridge);
Adafruit_SSD1306 display(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);

bool sdReady   = false;
bool oledReady = false;

unsigned long lastDisplayUpdate = 0;
unsigned long lastHeartbeat     = 0;
bool heartbeatState             = false;

// Forward declarations
void initDisplay();
void initSDCard();
void updateDisplay();
void processHostCommands();

// ─── Setup ──────────────────────────────────────────────────
void setup() {
    // USB-CDC serial to host PC
    Serial.begin(HOST_BAUD);
    delay(500);

    Serial.println();
    Serial.println("╔══════════════════════════════════════╗");
    Serial.println("║        CNC Bridge v" FW_VERSION "            ║");
    Serial.println("║   Anilam Crusader M Serial Bridge    ║");
    Serial.println("╚══════════════════════════════════════╝");
    Serial.println();

    // Status LED
    pinMode(LED_STATUS_PIN, OUTPUT);
    digitalWrite(LED_STATUS_PIN, HIGH);

    // Initialise I2C for OLED
    Wire.begin(OLED_SDA_PIN, OLED_SCL_PIN);
    initDisplay();

    // Initialise SPI + SD
    initSDCard();

    // Initialise Anilam serial bridge
    bridge.begin();

    // Start WiFi web server
    webServer.begin();

    // Default to passthrough mode
    bridge.startPassthrough();

    Serial.println("[MAIN] Initialisation complete");
    Serial.println("[MAIN] Type 'help' for commands");
    Serial.println();
}

// ─── Loop ───────────────────────────────────────────────────
void loop() {
    // Process serial bridge data
    bridge.update();

    // Process web server
    webServer.update();

    // Process host text commands (when not in passthrough)
    processHostCommands();

    // Update OLED display periodically
    if (oledReady && millis() - lastDisplayUpdate > DISPLAY_REFRESH_MS) {
        updateDisplay();
        lastDisplayUpdate = millis();

        // Turn off activity LEDs (they get turned on by TX/RX events)
        digitalWrite(LED_TX_PIN, LOW);
        digitalWrite(LED_RX_PIN, LOW);
    }

    // Heartbeat
    if (millis() - lastHeartbeat > HEARTBEAT_INTERVAL) {
        heartbeatState = !heartbeatState;
        digitalWrite(LED_STATUS_PIN, heartbeatState ? HIGH : LOW);
        lastHeartbeat = millis();
    }
}

// ─── OLED Display ───────────────────────────────────────────
void initDisplay() {
#if OLED_ENABLED
    if (display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
        oledReady = true;
        display.clearDisplay();
        display.setTextSize(1);
        display.setTextColor(SSD1306_WHITE);
        display.setCursor(0, 0);
        display.println("CNC Bridge v" FW_VERSION);
        display.println("Anilam Crusader M");
        display.println();
        display.println("Initialising...");
        display.display();
        Serial.println("[OLED] Display ready");
    } else {
        Serial.println("[OLED] Display not found");
    }
#endif
}

void updateDisplay() {
    if (!oledReady) return;

    const TransferStats& stats = bridge.getStats();

    display.clearDisplay();
    display.setCursor(0, 0);
    display.setTextSize(1);

    // Line 1: State
    display.printf("State: %s", bridge.getStateString());
    if (bridge.isXoffActive()) {
        display.print(" [XOFF]");
    }
    display.println();

    // Line 2: Progress (if sending)
    if (bridge.getState() == BridgeState::DNC_SENDING) {
        float pct = bridge.getProgress();
        display.printf("Progress: %.1f%%\n", pct);

        // Mini progress bar
        int barWidth = (int)(pct / 100.0f * (OLED_WIDTH - 4));
        display.drawRect(0, 20, OLED_WIDTH, 6, SSD1306_WHITE);
        display.fillRect(2, 22, barWidth, 2, SSD1306_WHITE);
        display.setCursor(0, 28);
    }

    // Stats
    display.printf("TX: %lu B  %lu ln\n", stats.bytesSent, stats.linesSent);
    display.printf("RX: %lu B  %lu ln\n", stats.bytesReceived, stats.linesReceived);

    // Elapsed time
    unsigned long sec = stats.elapsed / 1000;
    display.printf("Time: %lu:%02lu\n", sec / 60, sec % 60);

    // WiFi info
    if (webServer.isActive()) {
        display.printf("WiFi: %s\n", webServer.getIPAddress().c_str());
    }

    // SD card
    display.printf("SD: %s\n", sdReady ? "OK" : "---");

    display.display();
}

// ─── SD Card ────────────────────────────────────────────────
void initSDCard() {
#if SD_ENABLED
    SPI.begin(SD_SCK_PIN, SD_MISO_PIN, SD_MOSI_PIN, SD_CS_PIN);
    if (SD.begin(SD_CS_PIN)) {
        sdReady = true;
        // Create programs directory if needed
        if (!SD.exists(PROGRAM_DIR)) {
            SD.mkdir(PROGRAM_DIR);
        }
        Serial.printf("[SD] Card ready: %llu MB\n",
                      SD.totalBytes() / (1024 * 1024));
    } else {
        Serial.println("[SD] Card not found");
    }
#endif
}

// ─── Host command processor ─────────────────────────────────
// Simple text commands over USB for testing and control
static char cmdBuffer[256];
static size_t cmdLen = 0;

void processHostCommands() {
    // Only process commands while IDLE (not in passthrough)
    if (bridge.getState() == BridgeState::PASSTHROUGH) return;

    while (Serial.available()) {
        char c = Serial.read();
        if (c == '\n' || c == '\r') {
            if (cmdLen == 0) continue;
            cmdBuffer[cmdLen] = '\0';
            String cmd = String(cmdBuffer).trim();
            cmd.toLowerCase();
            cmdLen = 0;

            if (cmd == "help") {
                Serial.println("Commands:");
                Serial.println("  status       — Show bridge status");
                Serial.println("  passthrough  — Start transparent relay");
                Serial.println("  pause        — Pause current transfer");
                Serial.println("  resume       — Resume transfer");
                Serial.println("  abort        — Abort transfer");
                Serial.println("  receive      — Start DNC download from Anilam");
                Serial.println("  list         — List programs on SD card");
                Serial.println("  send <file>  — Send SD file to Anilam");
                Serial.println("  wifi         — Show WiFi info");
                Serial.println("  reboot       — Restart ESP32");
            }
            else if (cmd == "status") {
                const TransferStats& s = bridge.getStats();
                Serial.printf("State: %s\n", bridge.getStateString());
                Serial.printf("XOFF:  %s\n", bridge.isXoffActive() ? "YES" : "no");
                Serial.printf("TX:    %lu bytes, %lu lines\n", s.bytesSent, s.linesSent);
                Serial.printf("RX:    %lu bytes, %lu lines\n", s.bytesReceived, s.linesReceived);
                Serial.printf("Errors: %lu  Flow pauses: %lu\n", s.errors, s.flowPauses);
            }
            else if (cmd == "passthrough") {
                bridge.startPassthrough();
            }
            else if (cmd == "pause") {
                bridge.pause();
            }
            else if (cmd == "resume") {
                bridge.resume();
            }
            else if (cmd == "abort") {
                bridge.abort();
            }
            else if (cmd == "receive") {
                bridge.startDNCReceive();
            }
            else if (cmd == "wifi") {
                Serial.printf("SSID: %s\n", WIFI_AP_SSID);
                Serial.printf("IP:   %s\n", webServer.getIPAddress().c_str());
                Serial.printf("Port: %d\n", WEB_SERVER_PORT);
            }
            else if (cmd == "list") {
                if (sdReady) {
                    File dir = SD.open(PROGRAM_DIR);
                    if (dir) {
                        Serial.println("Programs on SD:");
                        File f = dir.openNextFile();
                        while (f) {
                            Serial.printf("  %-24s %8u bytes\n", f.name(), f.size());
                            f = dir.openNextFile();
                        }
                        dir.close();
                    }
                } else {
                    Serial.println("SD card not available");
                }
            }
            else if (cmd.startsWith("send ")) {
                String filename = cmd.substring(5);
                filename.trim();
                String path = String(PROGRAM_DIR) + "/" + filename;
                if (sdReady && SD.exists(path)) {
                    File f = SD.open(path, FILE_READ);
                    if (f) {
                        size_t sz = f.size();
                        if (sz < sizeof(cmdBuffer) * 256) {  // Reasonable limit
                            // Use web server's upload buffer
                            extern char uploadBuffer[];
                            extern size_t uploadSize;
                            uploadSize = f.read((uint8_t*)uploadBuffer, sz);
                            uploadBuffer[uploadSize] = '\0';
                            f.close();
                            bridge.startDNCSend(uploadBuffer, uploadSize);
                        } else {
                            Serial.println("File too large for buffer");
                            f.close();
                        }
                    }
                } else {
                    Serial.printf("File not found: %s\n", path.c_str());
                }
            }
            else if (cmd == "reboot") {
                Serial.println("Rebooting...");
                delay(500);
                ESP.restart();
            }
            else {
                Serial.printf("Unknown command: %s (type 'help')\n", cmdBuffer);
            }
        }
        else if (cmdLen < sizeof(cmdBuffer) - 1) {
            cmdBuffer[cmdLen++] = c;
        }
    }
}
