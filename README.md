# CNC Bridge

A complete communication bridge between **Autodesk Fusion 360** and the **Anilam Crusader M** CNC controller, providing:

1. **Fusion 360 Post Processor** — Generates Anilam-dialect G-code directly from CAM toolpaths
2. **Desktop Bridge Application** — Python/PyQt6 app for RS232 serial communication, DNC transfer, and monitoring
3. **ESP32 Hardware Bridge** — Standalone firmware for WiFi-enabled DNC transfer and OLED status display
4. **Reference Library** — 228 searchable entries + 18 scanned document PDFs (472 pages) with embedded viewer

---

## Compatible Controllers

The post processor and desktop app support both Anilam Crusader controller variants:

| Feature | Crusader M (default) | Crusader II |
|---|---|---|
| **Display** | CRT / LCD | LED |
| **Baud Rate** | 4800 (AUX 2787) | 2400 (AUX 2786) |
| **Parity** | Even (AUX 2772) | None (AUX 2770) |
| **Handshake** | XON/XOFF (AUX 2791) | None (AUX 2790) |
| **Data Bits** | 7 (AUX 2767) | 7 (AUX 2767) |
| **Program Memory** | Multiple programs | Single program |
| **G-code Dialect** | RS-274-D | RS-274-D (identical) |
| **G29 Subroutines** | Yes | Yes |
| **M1000/M2000** | Yes | Yes |
| **Canned Cycles** | G81–G89, G75–G79 | G81–G89, G75–G79 |

To select your controller in Fusion 360: set the `controllerModel` property to `crusader-m` or `crusader-ii`.

---

## Downloads

### Ready-to-Use Installers (v1.0)

| Download | Size | Description | Requirements |
|----------|------|-------------|--------------|
| [📥 **CNC-Bridge-Desktop-v1.0.zip**](https://github.com/Apocscode/CNC-Bridge/releases/download/v1.0/CNC-Bridge-Desktop-v1.0.zip) | 53 MB | Standalone desktop app — just extract & run `CNC-Bridge.exe` | Windows 10/11 (no Python needed) |
| [📥 **CNC-Bridge-PostProcessor-v1.0.zip**](https://github.com/Apocscode/CNC-Bridge/releases/download/v1.0/CNC-Bridge-PostProcessor-v1.0.zip) | <1 MB | Fusion 360 post processor (`.cps` file) | Autodesk Fusion 360 |
| [📥 **Anilam-Crusader-M-Documentation.zip**](https://github.com/Apocscode/CNC-Bridge/releases/download/v1.0/Anilam-Crusader-M-Documentation.zip) | 63 MB | Complete Anilam Crusader M documentation library (32 files — manuals, wiring diagrams, specs, CRT guides) | Any PDF viewer |
| [📥 **CNC-Bridge-Source-v1.0.zip**](https://github.com/Apocscode/CNC-Bridge/releases/download/v1.0/CNC-Bridge-Source-v1.0.zip) | <1 MB | Full source code (all components) | Python 3.10+, PlatformIO |

👉 **[All releases](https://github.com/Apocscode/CNC-Bridge/releases)**

### Install Desktop App (no Python required)
1. Download **CNC-Bridge-Desktop-v1.0.zip** above
2. Extract to any folder
3. Run `CNC-Bridge.exe`

### Install Post Processor in Fusion 360
1. Download **CNC-Bridge-PostProcessor-v1.0.zip** above
2. Extract the `.cps` file
3. In Fusion 360: **Manufacture → Post Process → Setup → Import** → select `anilam-crusader-m.cps`

### Developer Install (from source)
```bash
git clone https://github.com/Apocscode/CNC-Bridge.git
cd CNC-Bridge/bridge-app
pip install -r requirements.txt
python -m src.main
```

### Browse Source
| Component | Link | Description |
|-----------|------|-------------|
| Desktop App | [bridge-app/](bridge-app/) | PyQt6 dashboard — serial manager, DNC sender, reference library |
| Post Processor | [anilam-crusader-m.cps](post-processor/anilam-crusader-m.cps) | Fusion 360 post processor for Anilam Crusader M |
| ESP32 Firmware | [firmware/](firmware/) | PlatformIO project for ESP32-S3 hardware bridge |
| Session Log | [SESSION_LOG.md](SESSION_LOG.md) | Full development history and changelog |

### Anilam Documentation Library Contents
The **Anilam-Crusader-M-Documentation.zip** contains 32 deduplicated files (PDFs, diagrams, specs):

| Document | Pages | Content |
|----------|-------|---------|
| Crusader M 3X Programming Manual (70000135) | 220 | Complete programming reference |
| Supermax YCM-16VS Machine Manual | 50 | Mill mechanical manual — spindle, gibs, lubrication, electrical |
| Computron CRT Data | 31 | CRT monitor data sheets and specs |
| Console Wiring Diagrams | 26 | Full console wiring schematics |
| RS-232 Manual (Crusader II) | 24 | Serial communication manual |
| G-Code & RS-232 Format Spec | 22 | G-code format and RS-232 protocol specification |
| Advanced Programming | 22 | Advanced programming techniques |
| Quantum Scale Installation (70000036) | 17 | Linear scale/encoder installation |
| M-Functions Reference (70000169) | 11 | M-code function reference |
| AUX Codes (scanned) | 8 | Scanned AUX code pages |
| DNC Communication Guide | 2 | DNC setup and transfer |
| CRT Alignment | 2 | CRT display alignment procedures |
| Servo Drive Wiring Diagrams (×2) | 1 ea. | Wiring diagrams for servo drives |
| Servo Diagrams PC801 | 3 | PC801-style servo board diagrams |
| Westamp Drive Card Adjustment (mill + lathe) | — | Signal adjustment for Westamp drives |
| Balance M/G | — | Servo balance procedures |
| Parts Lists (×3) | — | Crusader II/M/G parts catalogs |
| CRT References (Audiotronics, Computron, New) | — | CRT monitor technical references |
| Heads/Encoders/Ballscrews | — | Mechanical component reference |
| Servo Turn-On Procedure | — | Initial servo startup |
| Rapid Speed Programming (70000249) | — | How to program rapid speed |
| D-A Dipswitches (image) | — | DIP switch settings photo |
| Anilam Series M UPE config | — | Controller configuration file |
| Bushing Bore | — | Bushing bore reference |

---

## Project Structure

```
CNC Bridge/
├── post-processor/               # Fusion 360 post processor
│   ├── anilam-crusader-m.cps     # Main post processor file
│   └── test-programs/            # Sample G-code programs
│       └── test-pattern.nc
│
├── bridge-app/                   # Python desktop application
│   ├── requirements.txt
│   ├── run.bat                   # Quick-start launcher
│   └── src/
│       ├── main.py               # App entry point
│       ├── core/
│       │   ├── serial_manager.py # RS232 serial communication
│       │   ├── dnc_sender.py     # DNC drip-feed engine
│       │   ├── gcode_parser.py   # G-code parser & validator
│       │   └── reference_library.py # 221-entry searchable reference DB
│       ├── ui/
│       │   ├── main_window.py    # PyQt6 monitoring dashboard
│       │   ├── library_panel.py  # Searchable reference library UI
│       │   └── pdf_viewer.py     # Embedded PDF page viewer
│       └── utils/
│
├── firmware/                     # ESP32-S3 firmware
│   ├── platformio.ini            # PlatformIO config
│   └── src/
│       ├── config.h              # Pin/serial configuration
│       ├── main.cpp              # Firmware entry point
│       ├── serial_bridge.h       # Bridge module header
│       ├── serial_bridge.cpp     # RS232 bridge implementation
│       ├── web_server.h          # WiFi web server header
│       └── web_server.cpp        # REST API + web dashboard
│
├── SESSION_LOG.md                # Development history & changelog
└── README.md
```

## Quick Start — Desktop App

### Prerequisites
- Python 3.10+
- USB-to-RS232 adapter (or ESP32 bridge hardware)

### Install & Run
```bash
cd bridge-app
pip install -r requirements.txt
python -m src.main
```

Or on Windows, just double-click `run.bat`.

### Features
- **Connection Panel** — Select COM port, configure baud/parity/flow control (defaults to Anilam 9600/7E2/XON-XOFF)
- **Monitor Panel** — Real-time transfer statistics, signal line status, flow control indicators
- **Transfer Panel** — Upload/download G-code, DNC drip-feed with progress tracking
- **Serial Terminal** — Raw send/receive for debugging
- **G-Code Viewer** — Syntax-highlighted viewer with Anilam-specific validation

---

## Post Processor — Fusion 360

### Installation
1. In Fusion 360, go to **Manufacture → Post Process**
2. Click **Setup** next to the post processor selector
3. Click **Import** and select `post-processor/anilam-crusader-m.cps`

### Anilam-Specific Features
- **Controller selection** — `controllerModel` property: `crusader-m` (default) or `crusader-ii`
- G29 subroutine calls (S#/C#/E)
- T10xx tool numbering with X(diameter)/Z(length) format
- V-variable drilling cycles (V20–V24)
- M1000/M2000 look-ahead mode control
- Feed clamping to 500 IPM, RPM clamping to 10000
- `%` program delimiters for DNC compatibility
- Configurable arc format (IJ incremental or R)
- Auto-generated RS232 setup comments matching selected controller

---

## ESP32 Hardware Bridge

### Hardware Required
| Component | Purpose |
|---|---|
| ESP32-S3 DevKitC‑1 | Main controller |
| MAX3232 module | RS232 level shifting |
| DB‑25 male connector | Anilam RS232 port |
| SSD1306 OLED 128×64 | Status display |
| SD card module | Program storage |

### Wiring
| ESP32 Pin | Connection |
|---|---|
| GPIO 17 | MAX3232 T1IN (TX to Anilam) |
| GPIO 18 | MAX3232 R1OUT (RX from Anilam) |
| GPIO 8/9 | I2C SDA/SCL (OLED) |
| GPIO 5/11/12/13 | SPI CS/MOSI/SCK/MISO (SD) |

### Build & Flash (PlatformIO)
```bash
cd firmware
pio run --target upload
pio device monitor
```

### WiFi Interface
Connect to **CNC-Bridge** WiFi network (password: `cncbridge`), then open `http://192.168.4.1` in a browser for the web dashboard.

### Serial Commands (USB)
```
help         — List commands
status       — Show bridge status
passthrough  — Transparent RS232 relay
pause/resume — Control active transfer
send <file>  — Send file from SD card
list         — List SD card programs
```

---

## Anilam Crusader M — RS232 Specs

| Parameter | Value |
|---|---|
| Baud Rate | 9600 |
| Data Bits | 7 |
| Parity | Even |
| Stop Bits | 2 |
| Flow Control | XON/XOFF (DC1/DC3) |
| Connector | DB-25 |
| Program Delimiters | `%` start/end |

> **Note:** The Anilam RS232 port is designed for program transfer (upload/download/DNC drip-feed). It does not support real-time position queries or status polling. The monitoring dashboard tracks transfer-level metrics.

---

## License

This project is provided for personal/educational use for interfacing with Anilam Crusader M CNC controllers.

---

## Session Log

See [SESSION_LOG.md](SESSION_LOG.md) for the full development history, changelog, and current state summary.
