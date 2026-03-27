# Quick Start Guide

Get CNC Bridge running and send your first program to the Anilam Crusader M in 5 minutes.

---

## Step 1: Install

### Option A: Standalone .exe (Recommended)
1. Download `CNC-Bridge-Desktop-v3.0.zip` from [GitHub Releases](https://github.com/Apocscode/CNC-Bridge/releases)
2. Extract to any folder (e.g., `C:\CNC-Bridge`)
3. Run `CNC-Bridge.exe`

### Option B: From Source
```bash
cd bridge-app
pip install -r requirements.txt
python -m src.main
```

---

## Step 2: Connect the Cable

You need a **custom RS232 cable** — standard cables will NOT work.

1. Connect the DB-25 Male end to the controller (DB-25 Female port on the back of the machine)
2. Bridge pins 4, 5, 6, 8, and 20 together on the DB-25 connector with a short jumper (handshake loopback)
3. Connect the DB-9 Female end to your USB-to-serial adapter
4. Plug the USB adapter into your PC

> See [docs/troubleshooting.md](troubleshooting.md) for full cable pinout and wiring details.

---

## Step 3: Select Connection Profile

1. In the **Connection** panel (left sidebar), select a profile:
   - **Crusader M (Default)** — 4800 baud, 7E2, XON/XOFF
   - **Crusader II** — 2400 baud, 7N1, No flow control
2. Click **⟳ Refresh** to find your COM port
3. Select your COM port from the dropdown
4. Click **Connect** — the status indicator should turn green

---

## Step 4: Load a G-code File

### From Fusion 360
1. Install the post processor: copy `post-processor/anilam-crusader-m.cps` to your Fusion 360 Posts folder
2. In Fusion 360: Manufacturing → Post Process → select "Anilam Crusader M"
3. Save the .nc file

### In CNC Bridge
1. **G-code Viewer tab**: Click "Open File" → select your .nc file
2. Click **Validate** to check for errors
3. **Backplotter tab**: Click "Open G-code" → select the same file to see a visual preview

---

## Step 5: Send to Controller

1. On the controller: Press `LOAD` → select `RS232` (or `DNC`) mode
2. In CNC Bridge, go to the **DNC Transfer** panel (right sidebar):
   - Click **Load File** → select your .nc file
   - Select mode: **Upload** (sends entire program) or **Drip Feed** (line-by-line)
   - Click **▶ Send**
3. Watch the progress bar and monitor panel
4. On completion, the controller will show the program in memory

---

## Step 6: Verify and Run

1. On the controller, review the loaded program
2. Set your Part Zero / work offset (G92)
3. Run in single-block mode first (cycle start with single block on)
4. Once verified, run at full speed

---

## Tips

- **Always verify G-code** before sending — use the Validator and Backplotter
- **Drag and drop** G-code files onto the window to load them instantly
- **Use Connection → Test Connection** before your first transfer to verify cable and handshake
- **Use Transfer → Send-Receive-Verify** to confirm transfer integrity (sends, receives back, compares)
- **Inline validation** — click Validate in the Editor to see wavy underline markers on error lines
- **Validation color-coding** — error lines are highlighted red and warnings yellow in the Viewer
- **Toolpath animation** — use Play/Pause/Step in the Backplotter to step through cuts
- **Playback speed** — use the Speed dropdown (100% / 75% / 50% / 25% / 10% / 5%) to slow down the animation
- **Feed-rate heat map** — toggle Heat Map in the Backplotter to color toolpath by feed rate
- **Export backplot** — save your toolpath as PNG or PDF for documentation
- **Insert → Snippets** — 8 Anilam-specific G-code templates (header, footer, tool change, drilling, etc.)
- **Use the Tool Library** (Tool Library tab) to manage your tools and generate T10xx table blocks
- **Import from Code** — click "Import from Code" in the Tool Library to parse tools from a G-code file
- **Save / Load Tool Libraries** — export and import tool sets as JSON files
- **Macro Recorder** — record keystroke macros for repetitive edits (View → Macro Recorder)
- **Program Library** — tag, search, and organize your saved programs
- **Comment Translator** — auto-translate G-code comments between English, Spanish, and French
- **Dark / Light Theme** — toggle between VS Code dark and light themes (View → Theme)
- **Touch-Screen Mode** — enable enlarged buttons for shop-floor touchscreens (View → Touch Mode)
- **Serial traffic is logged** automatically in `logs/serial/` — useful for debugging
- **Error logs** are saved in `logs/cnc_bridge.log` and `logs/errors.log` (rotating file loggers)
- **Programs are backed up** automatically in `backups/` — you'll never lose a program
- **Settings are saved** between sessions — your COM port, baud rate, and window position are remembered
- **Auto-reconnect** — if the serial connection drops, CNC Bridge retries every 5 seconds
- Press **F1** to open the Reference Library — 228 searchable entries covering every code and setting
- Press **Ctrl+F** in the Editor tab to find/replace text

---

## Controller AUX Settings (Crusader M)

Ensure these AUX codes match on your controller:

| AUX Code | Setting | Value |
|----------|---------|-------|
| 2701 | Format | RS-274 |
| 2758 | Character Set | ASCII |
| 2767 | Data Bits | 7 |
| 2787 | Baud Rate | 4800 |
| 2791 | Flow Control | XON/XOFF |

If your AUX settings differ, create a custom Connection Profile in CNC Bridge to match.
