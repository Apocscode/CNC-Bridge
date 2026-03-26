# CNC Bridge — Session Log

Development history and changelog for the CNC Bridge project.

---

## Session 1 — Project Genesis
**Date:** March 2026

### Created
- **Fusion 360 Post Processor** (`anilam-crusader-m.cps`)
  - RS-274 G-code output for Anilam Crusader M controller
  - G29 subroutine calls, T10xx tool numbering, V-variable drilling cycles
  - M1000/M2000 look-ahead, feed/RPM clamping, `%` delimiters for DNC
  - Arc format: IJ incremental or R (configurable)
- **Desktop Bridge App** (PyQt6)
  - `serial_manager.py` — RS232 serial communication with XON/XOFF flow control
  - `dnc_sender.py` — DNC drip-feed engine with progress tracking
  - `gcode_parser.py` — G-code parser and Anilam-specific validator
  - `main_window.py` — Dark-themed monitoring dashboard with tabs:
    Connection, Monitor, Transfer, Serial Terminal, G-Code Viewer
  - `main.py` — App entry point with system tray support
- **ESP32-S3 Firmware** (PlatformIO)
  - `serial_bridge.cpp/h` — RS232 bridge via MAX3232
  - `web_server.cpp/h` — WiFi REST API + web dashboard
  - `config.h` — Pin mapping and serial defaults
  - `main.cpp` — Firmware entry point
- **Test programs** — `test-pattern.nc` sample G-code
- **README.md** — Full project documentation

### Configured
- Supermax-30 mill AUX settings applied across all components:
  - AUX 2758 = ASCII (2758)
  - AUX 2767 = 7-bit data
  - AUX 2787 = 4800 baud
  - AUX 2791 = XON/XOFF flow control
  - AUX 2701 = RS-274 format

---

## Session 2 — Reference Library
**Date:** March 2026

### Created
- **Reference Library** (`reference_library.py`)
  - 203 searchable entries across 24 categories
  - Complete AUX code database with descriptions, syntax, examples, warnings
  - All G-codes, M-codes, V-variables documented
  - RS-232 settings, programming reference, subroutines, drilling cycles
  - Servo setup procedures, CRT alignment guides, wiring info, parts reference
  - Full-text search with relevance scoring and category filtering
- **Library Panel UI** (`library_panel.py`)
  - Searchable interface with instant filtering (200ms debounce)
  - Category dropdown filter (24 categories)
  - Results tree with color-coded entries
  - Rich HTML detail view with syntax highlighting
  - Integrated as "Reference Library" tab in dashboard
  - F1 keyboard shortcut, Help menu entry

### Source Material Processed
- Extracted text from ~12 Anilam PDFs with extractable content
- Cataloged AUX codes, G-codes, M-codes, procedures from documentation
- PDF directory: `F:\anilam\Anilam crusader m\` (36 files)

---

## Session 3 — Scanned PDF Integration
**Date:** March 2026

### Created
- **PDF Page Viewer** (`pdf_viewer.py`)
  - Embedded viewer using PyMuPDF (fitz) to render scanned PDF pages as images
  - Page navigation: first/prev/next/last buttons
  - Zoom controls: 50%–400% via dropdown and scroll wheel
  - Mouse drag-to-pan with grab hand cursor (open/closed hand states)
  - Default 200% zoom (144 DPI) for scanned document clarity

### Updated
- **Reference Library** — expanded to 221 entries, 25 categories
  - Added `DOCUMENTS` category ("Scanned Documents")
  - Added `pdf_file` and `pdf_pages` fields to `ReferenceEntry` dataclass
  - 18 scanned PDF document entries (472 total pages):

    | Code | Document | Pages |
    |------|----------|-------|
    | DOC PROGRAMMING | Crusader M 3X Programming Manual | 220 |
    | DOC SUPERMAX MANUAL | Supermax YCM-16VS Machine Manual | 50 |
    | DOC COMPUTRON DATA | Computron CRT Data Sheets | 31 |
    | DOC CONSOLE WIRING | Console Wiring Diagrams | 26 |
    | DOC RS232 MANUAL | RS-232 Manual Crusader II | 24 |
    | DOC GCODE-RS232 | G-Code & RS-232 Specification | 22 |
    | DOC RS232-FORMAT | RS-232 Format Specification | 22 |
    | DOC ADVANCED | Advanced Programming Manual | 22 |
    | DOC QUANTUM SCALE | Quantum Scale Installation | 17 |
    | DOC M-FUNCTIONS | M-Functions Reference | 11 |
    | DOC AUX SCANNED | AUX Codes (Scanned) | 8 |
    | DOC MCODES-AUX | M-Codes & AUX Supplement | 8 |
    | DOC SERVO PC801 | Servo Diagrams PC801 | 3 |
    | DOC CRT ALIGNMENT | CRT Alignment Procedures | 2 |
    | DOC DNC | DNC Communication Guide | 2 |
    | DOC DNC DRIP | DNC Drip Feed Procedure | 2 |
    | DOC SERVO WIRING 1 | Servo Drive Wiring Diagram 1 | 1 |
    | DOC SERVO WIRING 2 | Servo Drive Wiring Diagram 2 | 1 |

- **Library Panel** — integrated PDF viewer
  - Stacked widget: text detail view ↔ PDF page viewer
  - "View Document" / "Back to Details" button bar
  - 📄 icon prefix on document entries in results tree
  - Welcome page shows document count and page total
  - `DOCUMENTS` category color (#42a5f5) added

### Downloaded
- `CrusaderM_Docs_All.zip` (43.3 MB) from ijohnsen.com
  - Extracted: all 24 files were duplicates of existing collection
- `Supermax_YCM-16VS_Manual.pdf` (19.1 MB, 50 pages) from ijohnsen.com
  - New document — added to library as DOC SUPERMAX MANUAL

### Git Repository
- Initialized Git repo at `F:\CNC Bridge`
- Created `.gitignore` (Python, PlatformIO, IDE, OS files)
- Initial commit: 27 files, 8,208 lines
- Published to GitHub: **https://github.com/Apocscode/CNC-Bridge** (public)

### Release v1.0
- Built standalone Windows `.exe` with PyInstaller (no Python needed on target)
- Created 3 distributable ZIP packages:
  - `CNC-Bridge-Desktop-v1.0.zip` (53 MB) — standalone app, extract & run
  - `CNC-Bridge-PostProcessor-v1.0.zip` (<1 MB) — Fusion 360 `.cps` file
  - `CNC-Bridge-Source-v1.0.zip` (<1 MB) — full source code
- Published GitHub Release v1.0 with all ZIPs as downloadable assets
- Updated README with direct download links to release assets

---

## Current State Summary

| Component | Status | Details |
|-----------|--------|---------|
| Post Processor | ✅ Complete | `anilam-crusader-m.cps` — Fusion 360 → Anilam RS-274 |
| Desktop App | ✅ Complete | PyQt6 dashboard, serial manager, DNC sender, G-code parser |
| Reference Library | ✅ Complete | 221 entries, 25 categories, full-text search |
| PDF Viewer | ✅ Complete | 18 documents, 472 pages, zoom + drag-to-pan |
| ESP32 Firmware | ✅ Complete | Serial bridge, web server, WiFi AP mode |
| Git/GitHub | ✅ Complete | Apocscode/CNC-Bridge (public) |

### File Inventory (27 tracked files)
```
.gitignore
README.md
SESSION_LOG.md
bridge-app/requirements.txt
bridge-app/run.bat
bridge-app/extract_pdfs.py
bridge-app/test_library.py
bridge-app/src/__init__.py
bridge-app/src/main.py
bridge-app/src/core/__init__.py
bridge-app/src/core/serial_manager.py
bridge-app/src/core/dnc_sender.py
bridge-app/src/core/gcode_parser.py
bridge-app/src/core/reference_library.py
bridge-app/src/ui/__init__.py
bridge-app/src/ui/main_window.py
bridge-app/src/ui/library_panel.py
bridge-app/src/ui/pdf_viewer.py
bridge-app/src/utils/__init__.py
firmware/platformio.ini
firmware/src/config.h
firmware/src/main.cpp
firmware/src/serial_bridge.cpp
firmware/src/serial_bridge.h
firmware/src/web_server.cpp
firmware/src/web_server.h
post-processor/anilam-crusader-m.cps
post-processor/test-programs/test-pattern.nc
```

### Machine Configuration (Supermax-30 / Anilam Crusader M)
| AUX Code | Setting | Value |
|----------|---------|-------|
| 2758 | Character set | ASCII |
| 2767 | Data bits | 7-bit |
| 2787 | Baud rate | 4800 |
| 2791 | Flow control | XON/XOFF |
| 2701 | G-code format | RS-274 |
