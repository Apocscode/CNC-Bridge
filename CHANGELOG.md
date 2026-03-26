# Changelog

All notable changes to CNC Bridge will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
