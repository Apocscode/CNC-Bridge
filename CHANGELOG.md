# Changelog

All notable changes to CNC Bridge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [3.0.0] — 2026-03-27

### Added
- **Macro Recorder** — Record, play, and edit keystroke macros for repetitive editing tasks (persists in `config/macros.json`)
- **Program Library** — Tag, search, and organize saved G-code programs with metadata (description, tags, date)
- **Comment Translator** — Auto-translate G-code comments between English, Spanish, and French (200+ machining terms)
- **Dark / Light Theme** — VS Code-inspired dark theme (default) with one-click toggle via View → Theme
- **Touch-Screen Mode** — Enlarged buttons, spacing, and fonts for shop-floor touchscreen PCs via View → Touch Mode
- **Backplotter Speed Control** — Adjustable playback speed (100% / 75% / 50% / 25% / 10% / 5%) with explicit timer interval map
- **Tool Library — Import from Code** — Parse tool comments and T10xx table blocks from G-code files
- **Tool Library — Save / Load** — Export and import tool libraries as JSON files with Replace or Merge mode
- **File Diff — Preview on Load** — Shows both files immediately when loaded, before running diff compare
- **Validation Color-Coding** — G-code Viewer highlights error lines red and warning lines yellow in the code display
- **Validation Output Highlighting** — `[ERROR]` and `[WARN]` rows in the validation summary pane are color-coded
- **Test Programs** — Two multi-operation test programs: `test_part_v1.txt` (Rev A, 8 tools, 510 lines), `test_part_v2.txt` (Rev B, 9 tools, 552 lines)
- **Screenshot Capture Script** — `capture_screenshots.py` auto-loads test data and captures all dashboard screenshots

### Changed
- Version bumped to 3.0.0
- Backplotter animation uses timer-interval approach (15ms–800ms) instead of step-size for smoother speed control
- Tool Library panel expanded with Import from Code, Save to File, Load from File buttons
- File Diff panel shows loaded file content immediately without requiring Compare click
- README updated with v3.0 features, project structure tree, and fresh screenshots
- All documentation updated (quickstart, troubleshooting, quick-reference-card)

---

## [2.1.0] — 2026-03-26

### Added
- **Recent Files Menu** — File → Recent Files submenu shows last 10 opened files, auto-updates on open
- **Drag-and-Drop** — Drop G-code files anywhere on the window to load them into the active tab
- **Audible Transfer Alerts** — Success beeps on transfer complete, warning beeps on transfer error
- **Send to Controller from Editor** — "▶ Send to Controller" button on Editor toolbar sends current buffer directly
- **N-Line Renumber** — Edit → Renumber N-lines adds/renumbers N10, N20, N30... sequence numbers
- **Inline Validation Markers** — Editor "Validate" button highlights error lines with colored wavy underlines
- **Estimated Cycle Time** — Validation shows estimated machining time and travel distance in the editor toolbar
- **Auto-Reconnect** — Automatically retries serial connection every 5 seconds after unexpected disconnect
- **Feed-Rate Heat Map** — Backplotter checkbox colors toolpath by feed rate (blue=slow → red=fast)
- **Toolpath Animation** — Play/Pause/Step controls and scrubber slider to animate toolpath drawing with tool position cursor
- **Export Backplot** — Save backplot as PNG image or PDF document with full rendering
- **G-code Snippet Templates** — Insert menu with 8 Anilam-specific templates (header, footer, tool change, drilling, etc.)
- **Connection Test / Handshake** — Connection → Test Connection runs 8-step diagnostic: port check, signal lines, DTR/RTS toggle, buffer clear, XON send, CR echo, data write
- **Send-Receive-Verify** — Transfer → Send-Receive-Verify sends a file, receives it back, compares for integrity with pass/fail report
- **Error Logging System** — Rotating file loggers: `logs/cnc_bridge.log` (all events, 5MB×5) and `logs/errors.log` (errors only, 2MB×3) with console output
- **Connection Tester Module** — New `src/core/connection_tester.py` with full test suite and formatted report
- **Error Logger Module** — New `src/core/error_logger.py` with `setup_logging()` and `get_logger()`

### Changed
- Version bumped to 2.1.0
- About dialog updated with all new features
- Logging system upgraded from basic `logging.basicConfig` to rotating file handlers
- Backplotter now has animation controls bar below toolbar
- Editor toolbar expanded with Validate, Send to Controller, and cycle time display
- Menu bar expanded with Insert menu and Edit → Renumber N-lines

---

## [2.0.0] — 2026-03-26

### Added
- **G-code Editor** — Full-featured editor with syntax highlighting, line numbers, current line highlight, find/replace, undo/redo
- **Toolpath Backplotter** — 2D visual preview of G-code toolpaths with pan/zoom, grid overlay, coordinate display, and color-coded moves (rapids/linear/arc/drill)
- **Tool Library Manager** — Persistent tool database with add/edit/delete, T10xx table generation, and clipboard copy
- **File Diff Tool** — Side-by-side G-code comparison with synchronized scrolling and diff highlighting (added/removed/changed)
- **Settings Persistence** — Window geometry, serial settings, last-used tab, and recent files remembered across sessions
- **Connection Profiles** — Save and load named RS232 configurations (ships with Crusader M and Crusader II defaults)
- **Serial Traffic Logger** — Auto-logs all TX/RX data to timestamped files in `logs/serial/`
- **Program Backup Vault** — Auto-archives every program sent/received with metadata in `backups/`
- **Auto-Update Checker** — Checks GitHub Releases API on startup, notifies when a new version is available
- **Edit menu** with Find/Replace (Ctrl+F)
- **View menu** for quick tab switching
- **Tools menu** with Compare Files and Backplot Current File
- **Help → Check for Updates** menu item
- Unsaved changes prompt on editor close
- File → New / Save / Save As for the editor
- Backplot button to visualize current viewer/editor content

### Changed
- Version bumped to 2.0
- About dialog updated with full feature list
- Ctrl+O now opens file into whichever tab is active (Viewer, Editor, or Backplotter)
- Tab count increased from 3 to 7

### Documentation
- Added `CHANGELOG.md` (this file)
- Added `CONTRIBUTING.md` with contribution guidelines
- Added `docs/troubleshooting.md` — RS232 debugging guide
- Added `docs/quickstart.md` — first-run walkthrough
- Added `docs/quick-reference-card.md` — printable cheat sheet
- Added `docs/wiring/` — RS232 cable and ESP32 wiring diagrams (SVG)

### Engineering
- Added `tests/` directory with pytest unit tests for GCodeParser, GCodeValidator, SerialConfig, and settings
- Added `.github/workflows/ci.yml` for GitHub Actions CI (lint + test)
- Added `installer/cnc-bridge.iss` for Inno Setup Windows installer

---

## [1.0.0] — 2026-03-25

### Added
- Initial release
- Fusion 360 post processor for Anilam Crusader M (RS-274-D ISO G-code)
- Post processor Crusader II compatibility mode (`controllerProfiles`)
- PyQt6 desktop application with dark theme
- G-code Viewer with validation
- Serial Terminal (direct TX/RX)
- Reference Library (228 entries, 30 categories, full-text search)
- Embedded PDF viewer for scanned Anilam documentation (18 docs, 472 pages)
- Connection Panel (COM port, baud, data bits, parity, stop bits, flow control)
- Controller Monitor (signal LEDs, flow control, transfer stats)
- DNC Transfer Panel (upload, drip feed, pause/resume/abort, progress)
- DNC Sender engine with XON/XOFF flow control
- G-code parser and validator for Anilam dialect
- ESP32-S3 firmware (USB passthrough, DNC drip feed, WiFi AP, SD standalone)
- RS232 custom cable documentation with pinout tables
- GitHub Release with 4 downloadable assets
- PyInstaller standalone .exe build
- MIT License and safety disclaimer
