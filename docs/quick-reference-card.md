# CNC Bridge — Quick Reference Card

> Print this page and keep it at your workstation.

---

## RS232 Connection Settings

### Crusader M (Default)
| Parameter | Value |
|-----------|-------|
| Baud Rate | 4800 |
| Data Bits | 7 |
| Parity | Even |
| Stop Bits | 2 |
| Flow Ctrl | XON/XOFF |

### Crusader II
| Parameter | Value |
|-----------|-------|
| Baud Rate | 2400 |
| Data Bits | 7 |
| Parity | None |
| Stop Bits | 1 |
| Flow Ctrl | None |

---

## RS232 Cable Pinout (DB-25M → DB-9F)

```
DB-25 Male (Controller)     DB-9 Female (PC Adapter)
─────────────────────────   ────────────────────────
Pin 2  (TX Data)     ────→  Pin 2 (RX Data)
Pin 3  (RX Data)     ←────  Pin 3 (TX Data)
Pin 7  (Signal GND)  ─────  Pin 5 (Signal GND)
Pin 1  (Shield GND)  ─────  Pin 5 (Signal GND)

Pins 4, 5, 6, 8, 20  → Jumper together on DB-25 side
```

---

## Common G-Codes (Anilam Crusader M)

### Motion
| Code | Description |
|------|-------------|
| G00 | Rapid Positioning |
| G01 | Linear Interpolation (feed) |
| G02 | Circular CW |
| G03 | Circular CCW |
| G04 | Dwell (P = seconds) |

### Coordinate
| Code | Description |
|------|-------------|
| G28 | Return to Reference |
| G90 | Absolute Mode |
| G91 | Incremental Mode |
| G92 | Set Work Coordinate |

### Canned Cycles
| Code | Description |
|------|-------------|
| G81 | Drill Cycle |
| G82 | Spot Drill / Counterbore |
| G83 | Peck Drill |
| G84 | Tapping Cycle |
| G85 | Boring Cycle |
| G80 | Cancel Canned Cycle |

### Compensation
| Code | Description |
|------|-------------|
| G40 | Cancel Cutter Comp |
| G41 | Cutter Comp Left |
| G42 | Cutter Comp Right |
| G43 | Tool Length Comp + |
| G44 | Tool Length Comp − |
| G49 | Cancel Tool Length Comp |

---

## Common M-Codes

| Code | Description |
|------|-------------|
| M00 | Program Stop |
| M01 | Optional Stop |
| M02 | Program End |
| M03 | Spindle CW |
| M04 | Spindle CCW |
| M05 | Spindle Stop |
| M06 | Tool Change |
| M08 | Coolant On |
| M09 | Coolant Off |
| M30 | Program End & Rewind |
| M98 | Subprogram Call |
| M99 | Subprogram Return |

---

## Controller AUX Codes

| AUX | Setting | Typical Value |
|-----|---------|---------------|
| 2701 | Format | RS-274 |
| 2758 | Character Set | ASCII |
| 2767 | Data Bits | 7 |
| 2787 | Baud Rate | 4800 |
| 2791 | Flow Control | XON/XOFF |
| 100 | X Axis Direction | +/− |
| 101 | Y Axis Direction | +/− |
| 102 | Z Axis Direction | +/− |
| 103 | Spindle Direction | +/− |

---

## Keyboard Shortcuts (CNC Bridge App)

| Shortcut | Action |
|----------|--------|
| Ctrl+O | Open File |
| Ctrl+N | New File (Editor) |
| Ctrl+S | Save File (Editor) |
| Ctrl+F | Find / Replace |
| Ctrl+Z | Undo |
| Ctrl+Y | Redo |
| Ctrl+1–7 | Switch Tabs |
| F1 | Reference Library |

---

## Transfer Checklist

- [ ] Cable connected (DB-25 ↔ DB-9 via USB-Serial adapter)
- [ ] COM port selected and showing green
- [ ] Controller in RS232 / LOAD / DNC mode
- [ ] G-code validated (no errors)
- [ ] Backplot reviewed for correct paths
- [ ] Correct transfer mode selected (Upload vs Drip Feed)
- [ ] Part zero set on controller (G92)

---

## Troubleshooting Quick Fixes

| Problem | Fix |
|---------|-----|
| No COM port | Check USB adapter → Device Manager |
| Can't connect | Check cable wiring, verify AUX settings |
| Garbled text | Wrong baud rate or parity |
| Transfer hangs | Flow control mismatch (XON/XOFF) |
| Missing lines | Check handshake jumpers on DB-25 |

---

*CNC Bridge v2.0 — © 2025 Apocscode — MIT License*
