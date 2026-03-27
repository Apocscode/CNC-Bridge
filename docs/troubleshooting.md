# Troubleshooting Guide

Common issues when using CNC Bridge with the Anilam Crusader M / Crusader II controller.

---

## RS232 Connection Issues

### "No COM Ports Found"

**Symptoms:** Port dropdown is empty after clicking refresh.

**Causes & Solutions:**
1. **USB-to-serial adapter not installed** — Install the driver for your adapter (FTDI, Prolific PL2303, CH340, etc.). Check Device Manager for "Ports (COM & LPT)".
2. **Cable not plugged in** — Plug in the USB adapter, then click ⟳ Refresh.
3. **Wrong USB port** — Try a different USB port. Some USB 3.0 ports have issues with serial adapters.

### "Connection Failed"

**Symptoms:** Clicking Connect shows "Could not connect to COMx".

**Causes & Solutions:**
1. **Port in use** — Another program (PuTTY, HyperTerminal, another CNC Bridge instance) has the port open. Close it.
2. **Wrong COM port** — Unplug the adapter, refresh ports, note which one disappears. That's your port.
3. **Adapter hardware failure** — Try a different USB-to-serial adapter.

### "Connected But No Response from Controller"

**Symptoms:** Connected (green LED) but no data appears in the Serial Terminal.

**Causes & Solutions:**
1. **Wrong baud rate** — The Crusader M defaults to **4800 baud** (AUX 2787). The Crusader II defaults to **2400 baud**. Use the correct Connection Profile.
2. **Wrong cable wiring** — Standard RS232 cables **will not work**. You need a custom cable with handshake loopback. See the Cable section below.
3. **Controller not in DNC mode** — On the controller, press `LOAD` then select `RS232` (or `DNC`) mode.
4. **Wrong parity/data bits** — Crusader M requires **7 data bits, Even parity, 2 stop bits**. Crusader II requires **7 data bits, No parity, 1 stop bit**.
5. **Flow control mismatch** — Crusader M requires **XON/XOFF**. Crusader II uses **None**.

### "Garbled Characters / Gibberish"

**Symptoms:** You receive data but it's unreadable characters like `□ÿ±³`.

**Causes & Solutions:**
1. **Wrong baud rate** — Most common cause. Each wrong baud rate produces a different pattern of garbage. Try 4800, 2400, 9600.
2. **Wrong data bits or parity** — If you're at 8N1 and the controller is 7E2, you'll get garbled data.
3. **Electrical noise** — Long RS232 cables (>50 feet) can pick up EMI from spindle motors. Use shielded cable.
4. **Wrong cable** — Null-modem cables swap TX/RX. If you need straight-through, don't use null-modem (and vice versa).

### "Data Starts Then Stops (XOFF Hang)"

**Symptoms:** Transfer starts, sends a few lines, then freezes. Monitor shows "XOFF (Busy)".

**Causes & Solutions:**
1. **Controller buffer full** — The Crusader M has a small receive buffer (~256 bytes). This is normal for XON/XOFF — the controller sends XOFF when full and XON when ready. Wait for it.
2. **XON not received** — Check that TX and RX lines are both wired correctly. If the PC can't receive the XON character (0x11), transfer stalls.
3. **Handshake lines not looped** — The custom cable must bridge pins 4,5,6,8,20 on the controller's DB-25 connector. Without this, the controller may not assert RTS/CTS and some adapters won't transmit.
4. **Wrong flow control setting** — Make sure CNC Bridge is set to XON/XOFF, not RTS/CTS or None.

---

## RS232 Cable Issues

### The Standard Cable Problem

A standard RS232 cable **will not work** with the Anilam Crusader M or II. The controller requires specific handshake lines to be looped back. Without the loopback, the controller will not communicate.

### Verified Working Cable Pinout

**DB-25 (Controller) → DB-9 (PC)**

| Signal   | DB-25 Pin | DB-9 Pin | Direction       |
|----------|-----------|----------|-----------------|
| TX Data  | 2         | 2 (RX)   | Controller → PC |
| RX Data  | 3         | 3 (TX)   | PC → Controller |
| Ground   | 7         | 5        | Common          |

**Handshake Loopback on DB-25 (Controller Side):**
Bridge these 5 pins together with a short jumper wire:
- Pin 4 (RTS)
- Pin 5 (CTS)
- Pin 6 (DSR)
- Pin 8 (DCD)
- Pin 20 (DTR)

### Connector Gender
- **Controller port**: DB-25 **Female** (on the back of the machine)
- **Cable machine end**: DB-25 **Male**
- **Cable PC end**: DB-9 **Female** (plugs into USB-to-serial adapter's DB-9 Male)

---

## DNC Transfer Issues

### "Transfer Complete But Controller Shows Error"

**Causes & Solutions:**
1. **Missing % delimiters** — Anilam expects `%` at the start and end of the program for DNC. Ensure the post processor has "Add % signs" enabled.
2. **Unsupported G-code** — Run the Validator (G-code Viewer → Validate button) to check for unsupported codes. The Crusader M only accepts RS-274-D dialect.
3. **Line too long** — Anilam has a ~256 character line limit. Break up long tool table blocks.
4. **Wrong line endings** — Anilam expects CR+LF (`\r\n`). CNC Bridge handles this automatically.

### "Program Runs But Cuts in Wrong Location"

1. **Wrong work offset** — Set G92 or the controller's Part Zero before running.
2. **Inch vs. Metric mismatch** — Ensure G70 (inch) or G71 (metric) is in the program header.
3. **Absolute vs. Incremental** — Ensure G90 (absolute) is set. G91 (incremental) will offset moves from the current position.

### "Drip Feed Pauses at Each Line"

This is normal behavior for drip feed mode. The controller executes one block at a time and requests the next line via XON. For continuous operation, use Upload mode instead.

---

## Application Issues

### "App Won't Start / Import Error"

```
ModuleNotFoundError: No module named 'PyQt6'
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Or use the standalone `.exe` from the GitHub Releases page — it includes all dependencies.

### "PDF Viewer Shows Blank / Can't Load PDFs"

The PDF viewer requires PyMuPDF (`fitz`). Install it:
```bash
pip install PyMuPDF
```

Also ensure your Anilam PDF files are in the configured directory (`F:\anilam\Anilam crusader m\` by default).

### "Settings Not Saving"

Settings are stored in `bridge-app/config/settings.json`. Ensure the `config/` directory is writable. If running from a read-only location, copy the bridge-app folder to a writable directory.

### "Theme Not Changing"

If changing between dark and light theme doesn't take effect:
1. Go to **View → Theme** and toggle the theme
2. The theme change is applied immediately — no restart needed
3. If the theme reverts on restart, check that `config/settings.json` is writable

### "Tool Library Import from Code Finds No Tools"

The Import from Code feature looks for two patterns:
1. **Tool comments**: `( T1 — 0.500 4FL END MILL )` — requires a T-number followed by dash/em-dash and description
2. **T10xx table blocks**: `T1001 X0.5000 Z3.2500` — standard Anilam tool table format

If no tools are found:
- Ensure your G-code uses standard Anilam tool comment format
- Check that tool comments use `T` followed by a number
- The Import dialog will report how many tools were parsed

### "Tool Library Save/Load Not Working"

- **Save to File** exports tools as a `.json` file — check that the target directory is writable
- **Load from File** imports a previously saved `.json` file — you can choose Replace (clear existing) or Merge (add new)
- If merge produces duplicates, tools are matched by tool number

### "Backplotter Speed Control Has No Effect"

- Speed control only affects animated playback (Play button), not static rendering
- If the program is very short (<50 lines), speed differences may be subtle at higher speeds
- Try 5% or 10% speed for clearly visible slow playback
- Speed changes take effect immediately during active playback

### "Macro Recorder Not Recording"

- Macros record editor keystrokes only — they do not record mouse actions or menu clicks
- Start recording before making edits, then stop when done
- Saved macros persist in `config/macros.json`

---

## Theming & Display Issues

### Touch-Screen Mode

If controls are too small on your shop-floor touchscreen:
1. Go to **View → Touch Mode** to enable enlarged buttons and controls
2. Touch mode increases button size, spacing, and font size for easier touch interaction
3. The setting persists between sessions

---

## Connection Testing (v2.1+)

### Using the Connection Test
Go to **Connection → Test Connection** to run an 8-step diagnostic:

1. **Port Open** — Can the COM port be opened?
2. **Signal Lines** — Are DSR and CTS asserted?
3. **DTR Toggle** — Does toggling DTR work?
4. **RTS Toggle** — Does toggling RTS work?
5. **Buffer Clear** — Can buffers be flushed?
6. **XON Send** — Can XON (0x11) be written?
7. **CR Echo** — Does the controller echo a carriage return?
8. **Data Write** — Can a test string be written?

If steps 1–6 pass but 7–8 fail, your cable is correct but the controller isn't in RS232/DNC mode.

### Send-Receive-Verify
Go to **Transfer → Send-Receive-Verify** for a round-trip integrity check:
1. Sends a file to the controller
2. Receives the program back
3. Compares character-by-character
4. Opens the File Diff tab if mismatches are found

---

## Getting Help

1. Check the **Reference Library** (F1 key) — 228 searchable entries covering every G-code, M-code, AUX code, and RS232 setting.
2. Run **Connection → Test Connection** for an 8-step COM port diagnostic.
3. Check serial traffic logs in `logs/serial/` for raw TX/RX data.
4. Check error logs in `logs/cnc_bridge.log` and `logs/errors.log` for application-level issues.
5. Post on [Practical Machinist](https://www.practicalmachinist.com/) in the CNC forum.
6. Open a [GitHub Issue](https://github.com/Apocscode/CNC-Bridge/issues).
