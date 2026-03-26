/**
 * CNC Bridge Firmware — Configuration
 *
 * Pin assignments, serial settings, and defaults for the
 * ESP32-S3 ↔ Anilam Crusader M bridge.
 */

#ifndef CONFIG_H
#define CONFIG_H

// ─── Firmware version ──────────────────────────────────────
#define FW_VERSION "1.0.0"
#define FW_NAME   "CNC Bridge"

// ─── Anilam RS232 Serial (UART1 → MAX3232) ─────────────────
#define ANILAM_UART      1         // HardwareSerial index
#define ANILAM_TX_PIN    17        // GPIO → MAX3232 T1IN
#define ANILAM_RX_PIN    18        // GPIO ← MAX3232 R1OUT
#define ANILAM_BAUD      4800       // AUX 2787 — 4800 baud
#define ANILAM_DATA_BITS 7         // AUX 2767 — 7-bit ASCII (AUX 2758)
#define ANILAM_PARITY    SERIAL_7E1 // 7 data, Even parity, 1 stop
#define ANILAM_STOP_BITS 1

// XON/XOFF software flow control
#define XON_CHAR   0x11  // DC1
#define XOFF_CHAR  0x13  // DC3

// ─── Host Serial (USB-CDC or UART0) ────────────────────────
#define HOST_BAUD  115200
// USB-CDC is enabled via build flag ARDUINO_USB_CDC_ON_BOOT

// ─── SD Card (SPI) ─────────────────────────────────────────
#define SD_CS_PIN   5
#define SD_MOSI_PIN 11
#define SD_MISO_PIN 13
#define SD_SCK_PIN  12
#define SD_ENABLED  true

// ─── OLED Display (I2C — SSD1306 128×64) ───────────────────
#define OLED_WIDTH   128
#define OLED_HEIGHT  64
#define OLED_ADDR    0x3C
#define OLED_SDA_PIN 8
#define OLED_SCL_PIN 9
#define OLED_ENABLED true

// ─── Status LEDs ────────────────────────────────────────────
#define LED_STATUS_PIN  2   // On-board LED (blue)
#define LED_TX_PIN      38  // Activity LED — transmitting
#define LED_RX_PIN      39  // Activity LED — receiving
#define LED_ERROR_PIN   40  // Error LED (red)

// ─── WiFi Access Point (fallback) ──────────────────────────
#define WIFI_AP_SSID     "CNC-Bridge"
#define WIFI_AP_PASSWORD "cncbridge"
#define WIFI_AP_CHANNEL  1
#define WEB_SERVER_PORT  80

// ─── Timing ─────────────────────────────────────────────────
#define INTER_CHAR_DELAY_US  500   // µs between chars to Anilam
#define INTER_LINE_DELAY_MS  50    // ms between lines (drip feed)
#define DISPLAY_REFRESH_MS   250   // OLED update interval
#define HEARTBEAT_INTERVAL   1000  // ms between heartbeat blinks

// ─── Buffer sizes ───────────────────────────────────────────
#define LINE_BUFFER_SIZE  256   // Max G-code line length
#define FILE_BUFFER_SIZE  4096  // SD card read buffer
#define RX_RING_SIZE      2048  // Receive ring buffer

// ─── Program storage ────────────────────────────────────────
#define MAX_PROGRAMS     100    // Max programs on SD
#define PROGRAM_DIR      "/programs"

#endif // CONFIG_H
