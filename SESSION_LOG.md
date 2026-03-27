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

## Session 4 — RS232 Cable Docs & Community
**Date:** March 2026

### Created
- **RS232 custom cable documentation** — full pinout tables for DB-25→DB-9 and DB-25→DB-25, handshake loopback explanation, "why standard cables fail" section
- **Dashboard screenshots** for README — G-code Viewer, Serial Terminal, Reference Library
- **Practical Machinist forum post** (`docs/practical-machinist-post.txt`) — community introduction post with project overview

### Updated
- **README.md** — added disclaimer, comparison notes vs Autodesk Conversational post, MIT license section, cable wiring tables
- **LICENSE** — MIT License file created

---

## Session 5 — v2.0 Feature Expansion
**Date:** March 2026

### Created (9 Software Features)
- **G-code Editor** (`gcode_editor.py`) — Full editor with syntax highlighting, line numbers, current line highlight, find/replace (Ctrl+F), undo/redo
- **2D Backplotter** (`backplotter.py`) — Visual toolpath preview with rapid/feed/arc/drill color coding, pan, zoom, grid overlay, coordinate display
- **Tool Library Manager** (`tool_library.py`) — Persistent tool database, add/edit/delete, T10xx table generation, clipboard copy
- **File Diff Tool** (`file_diff.py`) — Side-by-side G-code comparison with synchronized scrolling and color-coded diff highlighting
- **Settings Persistence** (`settings.py`) — JSON-based settings for window geometry, serial config, last tab, recent files
- **Connection Profiles** — Save/load named RS232 configurations, ships with Crusader M and Crusader II defaults
- **Serial Traffic Logger** (`traffic_logger.py`) — Auto-logs all TX/RX data to timestamped session files in `logs/serial/`
- **Program Backup Vault** (`backup_vault.py`) — Auto-archives every sent/received program with metadata manifest in `backups/`
- **Auto-Update Checker** (`update_checker.py`) — Checks GitHub Releases API on startup, notifies when new version available

### Created (6 Documentation Items)
- **CHANGELOG.md** — Keep a Changelog format version history
- **CONTRIBUTING.md** — Contribution guidelines
- **docs/troubleshooting.md** — RS232 debugging guide
- **docs/quickstart.md** — First-run walkthrough
- **docs/quick-reference-card.md** — Printable cheat sheet
- **docs/wiring/** — RS232 cable and ESP32 wiring diagrams (SVG)

### Created (3 Engineering Items)
- **tests/** — 58 unit tests (pytest) for GCodeParser, GCodeValidator, SerialConfig, AppSettings, TrafficLogger, BackupVault
- **.github/workflows/ci.yml** — GitHub Actions CI (lint + test)
- **installer/cnc-bridge.iss** — Inno Setup Windows installer script

### Updated
- **main_window.py** — Expanded from 5 tabs to 7 tabs, added Edit/View/Tools/Help menus
- **README.md** — v2.0 feature section, updated project structure, updated feature list
- Version bumped to 2.0 — committed as bb4192e

---

## Session 6 — v2.1 Advanced Features
**Date:** March 2026

### Created
- **Connection Tester** (`connection_tester.py`) — 8-step COM port handshake/connectivity verification:
  1. Port open test
  2. Signal line check (DSR/CTS)
  3. DTR toggle test
  4. RTS toggle test
  5. Buffer clear
  6. XON send test
  7. CR echo test
  8. Data write verification
  - `HandshakeReport` with `to_text()` formatter, `TestStep` dataclass with PASS/FAIL/WARN/SKIP results
- **Error Logger** (`error_logger.py`) — Centralized rotating file log system:
  - `logs/cnc_bridge.log` — RotatingFileHandler, 5MB × 5 backups, DEBUG level
  - `logs/errors.log` — RotatingFileHandler, 2MB × 3 backups, ERROR only
  - Console handler at INFO level
  - `setup_logging()` and `get_logger(name)` helpers

### Added (17 Features)
- **Recent Files Menu** — File → Recent Files submenu, last 10 files, auto-updates
- **Drag-and-Drop** — Drop `.nc`/`.tap`/`.gcode` files onto the window to load
- **Audible Transfer Alerts** — `winsound.Beep` on transfer success (ascending) and error (3× warning)
- **Send to Controller from Editor** — Green "▶ Send to Controller" button on Editor toolbar
- **N-Line Renumber** — Edit → Renumber N-lines (strips existing, adds N10/N20/N30...)
- **Inline Validation Markers** — Validate button applies colored wavy underlines (red=error, yellow=warning) with tooltips
- **Estimated Cycle Time** — Yellow label in editor toolbar shows machining time and travel distance
- **Auto-Reconnect** — 5-second retry timer on unexpected serial disconnect
- **Feed-Rate Heat Map** — Backplotter checkbox colors toolpath by feed rate (blue→green→yellow→red gradient)
- **Toolpath Animation** — Play/Pause/Step controls and scrubber slider with tool position crosshair cursor
- **Export Backplot** — Save backplot as PNG image or PDF document (via QPdfWriter)
- **G-code Snippet Templates** — Insert menu with 8 Anilam-specific templates (header, footer, tool change, G81 drill, G83 peck, subroutine, safe start, coolant)
- **Connection Test / Handshake** — Connection → Test Connection runs 8-step diagnostic with colorized report
- **Send-Receive-Verify** — Transfer → Send-Receive-Verify: sends file, receives back, compares character-by-character, loads diff on failure
- **Error Logging System** — Rotating file loggers with console output
- **Connection Tester Module** — `src/core/connection_tester.py`
- **Error Logger Module** — `src/core/error_logger.py`

### Updated
- **main_window.py** — ~370 lines added: new menus (Insert, Connection→Test, Transfer→Send-Receive-Verify, Edit→Renumber), drag-drop handlers, auto-reconnect timer, connection tester integration, audible alerts, recent files, snippet insertion
- **gcode_editor.py** — ~100 lines added: Validate button, Send to Controller button, inline ExtraSelections, cycle time label
- **backplotter.py** — ~300 lines added: heat map toggle, animation controls bar (Play/Pause/Step/Slider), export PNG/PDF, `_feed_to_color()`, `render_to_image()`
- **file_diff.py** — Added `_load_texts()` method for programmatic diff loading
- **main.py** — Upgraded from `logging.basicConfig` to `setup_logging()` from error_logger
- **update_checker.py** — Version bumped to 2.1.0
- **CHANGELOG.md** — v2.1.0 section with 17 Added + 6 Changed items
- **.gitignore** — Added `logs/`, `bridge-app/config/`, `bridge-app/backups/` exclusions
- **About dialog** — Updated to v2.1 with full feature list

### Screenshots Updated
- Captured all 7 tabs + main dashboard screenshot (2576×1056 each)
- New screenshots: `dashboard-gcode-editor.png`, `dashboard-backplotter.png`, `dashboard-tool-library.png`, `dashboard-file-diff.png`
- Updated: `dashboard-gcode-viewer.png`, `dashboard-serial-terminal.png`, `dashboard-reference-library.png`, `dashboard-main.png`

### Git
- Committed as 317081b: "v2.1: +17 features"
- Pushed to origin/master

---

## Session 7 — v3.0 Feature Expansion
**Date:** March 2026

### Created (5 Core Features)
- **Macro Recorder** (`macro_recorder.py`) — Record, play, and edit keystroke macros for repetitive editing tasks. Macros persist in `config/macros.json`
- **Program Library** (`program_library.py`) — Tag, search, and organize saved G-code programs with metadata (description, tags, date, file path)
- **Comment Translator** (`comment_translator.py`) — Auto-translate G-code comments between English, Spanish, and French using a built-in machining dictionary (200+ terms)
- **Dark / Light Theme** — VS Code-inspired dark theme (default) with one-click toggle to light mode via View → Theme
- **Touch-Screen Mode** — Enlarged buttons, spacing, and font sizes for shop-floor touchscreen PCs via View → Touch Mode

### Git
- Committed as d203ed5: "v3.0: macro recorder, program library, comment translator, dark/light theme, touch mode"
- Pushed to origin/master

---

## Session 8 — Test Programs, Backplotter Polish, Documentation
**Date:** March 2026

### Created
- **Test Programs** (`bridge-app/test_programs/`)
  - `test_part_v1.txt` — Rev A, 8 tools, 510 lines — multi-operation machining program (face mill, drill, tap, contour, pocket, chamfer, bore, engrave)
  - `test_part_v2.txt` — Rev B, 9 tools, 552 lines — adds thread mill op, modified feeds/speeds, deeper pocket, extra drill holes
- **Screenshot Capture Script** (`bridge-app/capture_screenshots.py`) — Auto-loads test data into all 7 tabs and captures 8 dashboard screenshots to `docs/images/`

### Added (8 Features)
- **Backplotter Speed Control** — Adjustable playback speed dropdown (100% / 75% / 50% / 25% / 10% / 5%) with explicit timer interval map (15ms–800ms) and step scaling for smooth animation
- **Tool Library — Import from Code** — "Import from Code" button parses tool comments `( T1 — 0.500 4FL END MILL )` and T10xx table blocks `T1001 X0.5000 Z3.2500` from G-code files
- **Tool Library — Save / Load** — Export tool libraries as JSON files, import with Replace or Merge mode
- **File Diff — Preview on Load** — Shows both files immediately when loaded (before running diff compare)
- **Validation Color-Coding** — G-code Viewer highlights error lines red and warning lines yellow in the code display
- **Validation Output Highlighting** — `[ERROR]` and `[WARN]` rows in the validation summary pane are color-coded red/yellow
- **Diff shows files on load** — `_show_plain_text()` renders loaded files without diff markers for immediate preview
- **Speed control fix** — Replaced step-size approach (clamped to 1) with timer-interval approach; then improved with explicit interval map for dramatic speed differences

### Updated (Documentation)
- **README.md** — Added v3.0 features section (11 items), renamed v2.1 section, updated project structure tree with new files (`macro_recorder.py`, `program_library.py`, `comment_translator.py`, `test_programs/`, `capture_screenshots.py`), updated Features bullet list with 9 new entries
- **docs/quickstart.md** — Version bump to v3.0 download link, added 9 new tips (speed control, import from code, save/load tools, macro recorder, program library, comment translator, theme, touch mode, validation colors)
- **docs/troubleshooting.md** — Added 6 new troubleshooting sections (Theme Not Changing, Tool Library Import from Code, Tool Library Save/Load, Backplotter Speed Control, Macro Recorder Not Recording, Touch-Screen Mode)
- **docs/quick-reference-card.md** — Added v3.0 Features Quick Reference table (10 entries), version bump to v3.0

### Screenshots Updated
- Captured 8 fresh dashboard screenshots with test program data loaded:
  - `dashboard-gcode-viewer.png` (96KB) — with validation color-coding
  - `dashboard-gcode-editor.png` (133KB) — with test code loaded
  - `dashboard-backplotter.png` (152KB) — with toolpath rendered
  - `dashboard-serial-terminal.png` (50KB) — empty terminal
  - `dashboard-tool-library.png` (62KB) — with 8 tools imported from code
  - `dashboard-file-diff.png` (110KB) — v1 vs v2 comparison
  - `dashboard-reference-library.png` (181KB) — searchable library
  - `dashboard-main.png` (96KB) — overview/viewer tab

### Git
- Feature commits: 24c78af, e4eea00, 2353e18, 909f9b5, e33310b
- Documentation commit: f2df1e8
- Pushed to origin/master

---

## Current State Summary

| Component | Status | Version | Details |
|-----------|--------|---------|---------|
| Post Processor | ✅ Complete | 1.0 | `anilam-crusader-m.cps` — Fusion 360 → Anilam RS-274 |
| Desktop App | ✅ Complete | 3.0 | PyQt6 dashboard, 7 tabs, dark/light theme, touch mode |
| Reference Library | ✅ Complete | — | 228 entries, 25 categories, full-text search |
| PDF Viewer | ✅ Complete | — | 18 documents, 472 pages, zoom + drag-to-pan |
| ESP32 Firmware | ✅ Complete | 1.0 | Serial bridge, web server, WiFi AP mode |
| Macro Recorder | ✅ Complete | 3.0 | Record/play/edit keystroke macros |
| Program Library | ✅ Complete | 3.0 | Tag, search, organize G-code programs |
| Comment Translator | ✅ Complete | 3.0 | EN/ES/FR auto-translation (200+ terms) |
| Connection Tester | ✅ Complete | 2.1 | 8-step handshake/diagnostic test |
| Error Logging | ✅ Complete | 2.1 | Rotating file logs + console output |
| Test Programs | ✅ Complete | — | 2 multi-op programs (510 + 552 lines) |
| Git/GitHub | ✅ Complete | — | Apocscode/CNC-Bridge (public) |

### Machine Configuration (Supermax-30 / Anilam Crusader M)
| AUX Code | Setting | Value |
|----------|---------|-------|
| 2758 | Character set | ASCII |
| 2767 | Data bits | 7-bit |
| 2787 | Baud rate | 4800 |
| 2791 | Flow control | XON/XOFF |
| 2701 | G-code format | RS-274 |
