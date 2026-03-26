/**
 * CNC Bridge Firmware — Serial Bridge Module
 *
 * Manages bidirectional RS232 communication between the host PC
 * and the Anilam Crusader M controller through the MAX3232 level
 * shifter.  Handles XON/XOFF flow control, character timing, and
 * line-based DNC drip-feed mode.
 */

#ifndef SERIAL_BRIDGE_H
#define SERIAL_BRIDGE_H

#include <Arduino.h>
#include "config.h"

// ─── Transfer state machine ────────────────────────────────
enum class BridgeState : uint8_t {
    IDLE,            // No transfer in progress
    PASSTHROUGH,     // Transparent byte-level relay
    DNC_SENDING,     // Drip-feeding G-code to Anilam
    DNC_RECEIVING,   // Downloading program from Anilam
    PAUSED,          // Transfer paused (XOFF received or manual)
    ERROR            // Recoverable error state
};

// ─── Transfer statistics ────────────────────────────────────
struct TransferStats {
    uint32_t bytesSent      = 0;
    uint32_t bytesReceived  = 0;
    uint32_t linesSent      = 0;
    uint32_t linesReceived  = 0;
    uint32_t errors         = 0;
    uint32_t flowPauses     = 0;  // Times XOFF was received
    unsigned long startTime = 0;
    unsigned long elapsed   = 0;

    void reset() {
        bytesSent = bytesReceived = linesSent = linesReceived = 0;
        errors = flowPauses = 0;
        startTime = millis();
        elapsed = 0;
    }

    void updateElapsed() { elapsed = millis() - startTime; }
};

// ─── SerialBridge class ─────────────────────────────────────
class SerialBridge {
public:
    SerialBridge();

    /** Initialise UART1 with Anilam settings. */
    void begin();

    /** Call from loop() — processes buffered data. */
    void update();

    // ── Mode control ──
    void startPassthrough();
    void startDNCSend(const char* programData, size_t length);
    void startDNCReceive();
    void pause();
    void resume();
    void abort();

    // ── Direct write ──
    void sendToAnilam(const uint8_t* data, size_t len);
    void sendLineToAnilam(const char* line);
    void sendToHost(const uint8_t* data, size_t len);

    // ── Status ──
    BridgeState       getState()  const { return _state; }
    const char*       getStateString() const;
    const TransferStats& getStats() const { return _stats; }
    bool              isXoffActive() const { return _xoffActive; }
    float             getProgress() const;

private:
    HardwareSerial    _anilamSerial;
    BridgeState       _state;
    TransferStats     _stats;

    // Flow control
    bool              _xoffActive;
    unsigned long     _lastXoffTime;

    // DNC send state
    const char*       _programData;
    size_t            _programLength;
    size_t            _sendPos;
    char              _lineBuffer[LINE_BUFFER_SIZE];
    size_t            _lineLen;

    // Receive buffer
    char              _rxBuffer[LINE_BUFFER_SIZE];
    size_t            _rxLen;

    // Timing
    unsigned long     _lastCharTime;
    unsigned long     _lastLineTime;

    // ── Internal ──
    void processPassthrough();
    void processDNCSend();
    void processDNCReceive();
    bool extractNextLine();
    void handleFlowControl(uint8_t byte);
    void blinkTxLed();
    void blinkRxLed();
};

#endif // SERIAL_BRIDGE_H
