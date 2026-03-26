/**
 * CNC Bridge Firmware — Serial Bridge Implementation
 *
 * Bidirectional RS232 bridge between host PC and Anilam Crusader M.
 * Supports transparent passthrough and line-by-line DNC drip-feed
 * with XON/XOFF flow control.
 */

#include "serial_bridge.h"

// ─── Constructor ────────────────────────────────────────────
SerialBridge::SerialBridge()
    : _anilamSerial(ANILAM_UART),
      _state(BridgeState::IDLE),
      _xoffActive(false),
      _lastXoffTime(0),
      _programData(nullptr),
      _programLength(0),
      _sendPos(0),
      _lineLen(0),
      _rxLen(0),
      _lastCharTime(0),
      _lastLineTime(0)
{
    memset(_lineBuffer, 0, sizeof(_lineBuffer));
    memset(_rxBuffer, 0, sizeof(_rxBuffer));
}

// ─── Initialisation ─────────────────────────────────────────
void SerialBridge::begin() {
    // Configure UART1 for Anilam: 9600 baud, 7E2
    _anilamSerial.begin(ANILAM_BAUD, ANILAM_PARITY, ANILAM_RX_PIN, ANILAM_TX_PIN);
    _anilamSerial.setRxBufferSize(RX_RING_SIZE);

    // LED pins
    pinMode(LED_TX_PIN, OUTPUT);
    pinMode(LED_RX_PIN, OUTPUT);
    pinMode(LED_ERROR_PIN, OUTPUT);
    digitalWrite(LED_TX_PIN, LOW);
    digitalWrite(LED_RX_PIN, LOW);
    digitalWrite(LED_ERROR_PIN, LOW);

    Serial.println("[BRIDGE] Serial bridge initialised");
    Serial.printf("[BRIDGE] Anilam UART: %d baud, 7E1, pins TX=%d RX=%d\n",
                  ANILAM_BAUD, ANILAM_TX_PIN, ANILAM_RX_PIN);
}

// ─── Main update loop ───────────────────────────────────────
void SerialBridge::update() {
    switch (_state) {
        case BridgeState::PASSTHROUGH:
            processPassthrough();
            break;
        case BridgeState::DNC_SENDING:
            processDNCSend();
            break;
        case BridgeState::DNC_RECEIVING:
            processDNCReceive();
            break;
        case BridgeState::PAUSED:
            // Still read from Anilam to catch XON
            while (_anilamSerial.available()) {
                uint8_t b = _anilamSerial.read();
                handleFlowControl(b);
                if (b != XON_CHAR && b != XOFF_CHAR) {
                    Serial.write(b);
                    _stats.bytesReceived++;
                }
            }
            break;
        default:
            break;
    }
}

// ─── Passthrough mode ───────────────────────────────────────
void SerialBridge::startPassthrough() {
    _state = BridgeState::PASSTHROUGH;
    _stats.reset();
    _xoffActive = false;
    Serial.println("[BRIDGE] Passthrough mode started");
}

void SerialBridge::processPassthrough() {
    // Host → Anilam
    while (Serial.available() && !_xoffActive) {
        uint8_t b = Serial.read();
        _anilamSerial.write(b);
        _stats.bytesSent++;
        blinkTxLed();
        delayMicroseconds(INTER_CHAR_DELAY_US);
    }

    // Anilam → Host
    while (_anilamSerial.available()) {
        uint8_t b = _anilamSerial.read();
        handleFlowControl(b);
        if (b != XON_CHAR && b != XOFF_CHAR) {
            Serial.write(b);
            _stats.bytesReceived++;
            blinkRxLed();
        }
    }
}

// ─── DNC Send (drip-feed to Anilam) ────────────────────────
void SerialBridge::startDNCSend(const char* programData, size_t length) {
    _programData   = programData;
    _programLength = length;
    _sendPos       = 0;
    _lineLen       = 0;
    _xoffActive    = false;
    _state         = BridgeState::DNC_SENDING;
    _stats.reset();
    Serial.printf("[BRIDGE] DNC send started: %u bytes\n", length);
}

void SerialBridge::processDNCSend() {
    // Don't send if flow-controlled
    if (_xoffActive) {
        // Still read incoming data for XON
        while (_anilamSerial.available()) {
            uint8_t b = _anilamSerial.read();
            handleFlowControl(b);
            if (b != XON_CHAR && b != XOFF_CHAR) {
                Serial.write(b);
                _stats.bytesReceived++;
            }
        }
        return;
    }

    // Respect inter-line delay
    if (millis() - _lastLineTime < INTER_LINE_DELAY_MS) {
        return;
    }

    // Extract and send next line
    if (extractNextLine()) {
        sendLineToAnilam(_lineBuffer);
        _stats.linesSent++;
        _stats.updateElapsed();
        _lastLineTime = millis();

        // Report progress to host
        float pct = getProgress();
        Serial.printf("[DNC] Line %u sent (%.1f%%)\n", _stats.linesSent, pct);

    } else {
        // Transfer complete
        _state = BridgeState::IDLE;
        _stats.updateElapsed();
        Serial.printf("[BRIDGE] DNC send complete: %u lines, %u bytes, %lu ms\n",
                      _stats.linesSent, _stats.bytesSent, _stats.elapsed);
    }

    // Always read Anilam responses
    while (_anilamSerial.available()) {
        uint8_t b = _anilamSerial.read();
        handleFlowControl(b);
        if (b != XON_CHAR && b != XOFF_CHAR) {
            Serial.write(b);
            _stats.bytesReceived++;
        }
    }
}

// ─── DNC Receive (download from Anilam) ─────────────────────
void SerialBridge::startDNCReceive() {
    _state  = BridgeState::DNC_RECEIVING;
    _rxLen  = 0;
    _stats.reset();
    Serial.println("[BRIDGE] DNC receive started — waiting for data from Anilam");
}

void SerialBridge::processDNCReceive() {
    while (_anilamSerial.available()) {
        uint8_t b = _anilamSerial.read();
        handleFlowControl(b);

        if (b == XON_CHAR || b == XOFF_CHAR) continue;

        _stats.bytesReceived++;
        blinkRxLed();

        // Forward to host
        Serial.write(b);

        // Accumulate lines for counting
        if (b == '\n' || b == '\r') {
            if (_rxLen > 0) {
                _stats.linesReceived++;
                _rxLen = 0;
            }
        } else if (_rxLen < LINE_BUFFER_SIZE - 1) {
            _rxBuffer[_rxLen++] = (char)b;
        }
    }
}

// ─── Control ────────────────────────────────────────────────
void SerialBridge::pause() {
    if (_state == BridgeState::DNC_SENDING || _state == BridgeState::PASSTHROUGH) {
        _state = BridgeState::PAUSED;
        Serial.println("[BRIDGE] Paused");
    }
}

void SerialBridge::resume() {
    if (_state == BridgeState::PAUSED) {
        _state = (_programData != nullptr && _sendPos < _programLength)
                 ? BridgeState::DNC_SENDING : BridgeState::PASSTHROUGH;
        Serial.println("[BRIDGE] Resumed");
    }
}

void SerialBridge::abort() {
    _state = BridgeState::IDLE;
    _programData   = nullptr;
    _programLength = 0;
    _sendPos       = 0;
    _xoffActive    = false;
    _stats.updateElapsed();
    Serial.println("[BRIDGE] Aborted");
}

// ─── Direct send helpers ────────────────────────────────────
void SerialBridge::sendToAnilam(const uint8_t* data, size_t len) {
    for (size_t i = 0; i < len; i++) {
        // Wait if flow-controlled
        unsigned long timeout = millis() + 5000;
        while (_xoffActive && millis() < timeout) {
            if (_anilamSerial.available()) {
                uint8_t b = _anilamSerial.read();
                handleFlowControl(b);
            }
            delay(1);
        }
        _anilamSerial.write(data[i]);
        _stats.bytesSent++;
        delayMicroseconds(INTER_CHAR_DELAY_US);
    }
    blinkTxLed();
}

void SerialBridge::sendLineToAnilam(const char* line) {
    size_t len = strlen(line);
    sendToAnilam((const uint8_t*)line, len);

    // Send CR+LF line ending (Anilam expects CR or CR+LF)
    uint8_t crlf[] = {'\r', '\n'};
    sendToAnilam(crlf, 2);
}

void SerialBridge::sendToHost(const uint8_t* data, size_t len) {
    Serial.write(data, len);
}

// ─── Status ─────────────────────────────────────────────────
const char* SerialBridge::getStateString() const {
    switch (_state) {
        case BridgeState::IDLE:          return "IDLE";
        case BridgeState::PASSTHROUGH:   return "PASSTHROUGH";
        case BridgeState::DNC_SENDING:   return "DNC_SEND";
        case BridgeState::DNC_RECEIVING: return "DNC_RECV";
        case BridgeState::PAUSED:        return "PAUSED";
        case BridgeState::ERROR:         return "ERROR";
        default:                         return "UNKNOWN";
    }
}

float SerialBridge::getProgress() const {
    if (_programLength == 0) return 0.0f;
    return (float)_sendPos / (float)_programLength * 100.0f;
}

// ─── Internal helpers ───────────────────────────────────────
bool SerialBridge::extractNextLine() {
    if (_sendPos >= _programLength) return false;

    _lineLen = 0;
    while (_sendPos < _programLength && _lineLen < LINE_BUFFER_SIZE - 1) {
        char c = _programData[_sendPos++];
        if (c == '\n') break;
        if (c == '\r') continue;  // Skip CR, we add our own
        _lineBuffer[_lineLen++] = c;
    }
    _lineBuffer[_lineLen] = '\0';
    return _lineLen > 0 || _sendPos < _programLength;
}

void SerialBridge::handleFlowControl(uint8_t byte) {
    if (byte == XOFF_CHAR) {
        _xoffActive = true;
        _lastXoffTime = millis();
        _stats.flowPauses++;
        Serial.println("[FLOW] XOFF received — pausing output");
    } else if (byte == XON_CHAR) {
        _xoffActive = false;
        Serial.printf("[FLOW] XON received — resuming (paused %lu ms)\n",
                      millis() - _lastXoffTime);
    }
}

void SerialBridge::blinkTxLed() {
    digitalWrite(LED_TX_PIN, HIGH);
    // LED will be turned off in the display refresh cycle
}

void SerialBridge::blinkRxLed() {
    digitalWrite(LED_RX_PIN, HIGH);
}
