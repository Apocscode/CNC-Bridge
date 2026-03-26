"""
CNC Bridge — Anilam Crusader M Reference Library

Comprehensive searchable reference database containing:
  - All AUX codes with explanations, categories, and usage suggestions
  - All M-codes (standard + Anilam-specific)
  - All G-codes with syntax and examples
  - RS232/DNC serial communication reference
  - V-variable system documentation
  - Programming reference (subroutines, drilling cycles, etc.)
  - Servo setup and maintenance procedures
  - Hardware parts reference
  - CRT alignment guides
  - Wiring and diagnostic information

Source: Anilam Crusader M documentation library (PDFs + technical notes)
"""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


class EntryCategory(Enum):
    AUX_CODES = "AUX Codes"
    AUX_MIRROR = "AUX — Mirror & Scale"
    AUX_CONTOURING = "AUX — Contouring & Look-Ahead"
    AUX_LIMITS = "AUX — Limits & Backlash"
    AUX_HOMING = "AUX — Homing & Zero Crossing"
    AUX_THREADING = "AUX — Threading & Lathe"
    AUX_AXIS_SWAP = "AUX — Axis Swap & Retract"
    AUX_FEED_RAPID = "AUX — Feed & Rapid Override"
    AUX_PROGRAM = "AUX — Program Mode"
    AUX_SIMULATION = "AUX — Simulation & Diagnostics"
    AUX_LOOP = "AUX — Loop Control"
    AUX_STEPPING = "AUX — Single Step Mode"
    AUX_DRIFT = "AUX — Drift & Gain"
    AUX_RS232 = "AUX — RS-232 Communication"
    AUX_MATH = "AUX — Math & Variables"
    AUX_ADVANCED = "AUX — Advanced / Mold"
    G_CODES = "G-Codes"
    M_CODES = "M-Codes"
    V_VARIABLES = "V-Variables"
    RS232_SETTINGS = "RS-232 / DNC"
    PROGRAMMING = "Programming Reference"
    SUBROUTINES = "Subroutines (G29)"
    DRILLING = "Drilling Cycles"
    SERVO_SETUP = "Servo Setup & Maintenance"
    CRT_ALIGNMENT = "CRT Alignment"
    WIRING = "Wiring & Hardware"
    PARTS = "Service Parts"
    DOCUMENTS = "Scanned Documents"
    GENERAL = "General Reference"


@dataclass
class ReferenceEntry:
    """A single searchable reference entry."""
    code: str                              # e.g. "AUX 2787", "G01", "M03"
    title: str                             # Short title
    category: EntryCategory                # Category for filtering
    description: str                       # Full explanation
    syntax: str = ""                       # Usage syntax if applicable
    example: str = ""                      # Code example
    when_to_use: str = ""                  # Practical guidance
    related: List[str] = field(default_factory=list)  # Related code references
    warning: str = ""                      # Safety or caution notes
    source: str = ""                       # Source document
    tags: List[str] = field(default_factory=list)     # Extra search keywords
    pdf_file: str = ""                      # PDF filename for scanned doc viewer
    pdf_pages: int = 0                      # Number of pages in attached PDF

    def matches(self, query: str) -> bool:
        """Check if this entry matches a search query (case-insensitive)."""
        q = query.lower()
        searchable = " ".join([
            self.code, self.title, self.category.value,
            self.description, self.syntax, self.example,
            self.when_to_use, self.warning, self.source,
            " ".join(self.related), " ".join(self.tags),
        ]).lower()
        # Support multi-word search — all terms must match
        terms = q.split()
        return all(term in searchable for term in terms)

    def match_score(self, query: str) -> int:
        """Return relevance score (higher = better match)."""
        q = query.lower()
        score = 0
        if q in self.code.lower():
            score += 100
        if q in self.title.lower():
            score += 50
        if q in self.category.value.lower():
            score += 20
        if q in self.description.lower():
            score += 10
        for tag in self.tags:
            if q in tag.lower():
                score += 15
        return score


def build_library() -> List[ReferenceEntry]:
    """Build the complete Anilam Crusader M reference library."""
    entries = []

    # ═══════════════════════════════════════════════════════════
    # AUX CODES — Mirror & Scale
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="AUX 100", title="Mirror X Axis",
            category=EntryCategory.AUX_MIRROR,
            description="Mirrors (reflects) all programmed X-axis moves. Positive X becomes negative and vice versa. Useful for cutting mirror-image parts.",
            when_to_use="When you need to cut the same part mirrored left-to-right. Common for making left/right hand pairs of parts.",
            related=["AUX 200", "AUX 300", "AUX 800"],
            tags=["mirror", "reflect", "flip", "x axis"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 200", title="Mirror Y Axis",
            category=EntryCategory.AUX_MIRROR,
            description="Mirrors all programmed Y-axis moves.",
            when_to_use="When you need to cut the same part mirrored front-to-back.",
            related=["AUX 100", "AUX 300", "AUX 800"],
            tags=["mirror", "reflect", "flip", "y axis"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 300", title="Mirror X & Y Axes",
            category=EntryCategory.AUX_MIRROR,
            description="Mirrors both X and Y axis moves simultaneously. Effectively rotates the part 180 degrees.",
            when_to_use="When you need a 180° rotated copy of a part profile.",
            related=["AUX 100", "AUX 200", "AUX 800"],
            tags=["mirror", "reflect", "rotate", "both axes"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 400", title="Mirror Z Axis",
            category=EntryCategory.AUX_MIRROR,
            description="Mirrors all programmed Z-axis moves. Positive Z becomes negative and vice versa.",
            warning="Use with extreme caution — mirroring Z can cause unexpected plunges into the work or table.",
            related=["AUX 500", "AUX 600", "AUX 800"],
            tags=["mirror", "z axis", "depth"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 500", title="Mirror X & Z Axes",
            category=EntryCategory.AUX_MIRROR,
            description="Mirrors both X and Z axis moves simultaneously.",
            related=["AUX 100", "AUX 400", "AUX 800"],
            tags=["mirror"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 600", title="Mirror Y & Z Axes",
            category=EntryCategory.AUX_MIRROR,
            description="Mirrors both Y and Z axis moves simultaneously.",
            related=["AUX 200", "AUX 400", "AUX 800"],
            tags=["mirror"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 700", title="Mirror X, Y & Z Axes",
            category=EntryCategory.AUX_MIRROR,
            description="Mirrors all three axes simultaneously.",
            related=["AUX 800"],
            tags=["mirror", "all axes"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 800", title="Cancel All Mirrors",
            category=EntryCategory.AUX_MIRROR,
            description="Cancels all active mirror operations and returns to normal axis direction.",
            when_to_use="Always call this after completing mirror operations to restore normal axis behavior.",
            related=["AUX 100", "AUX 200", "AUX 300"],
            tags=["mirror", "cancel", "reset", "normal"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 900", title="Double X, Y & Z Scale",
            category=EntryCategory.AUX_MIRROR,
            description="Doubles the scale of all programmed moves on all axes. A move of X1.0 becomes X2.0, etc.",
            when_to_use="Scaling a program to cut a part at 2× size. Not commonly used — verify with a dry run first.",
            warning="Verify travel limits before running. Doubled moves may exceed machine travel.",
            tags=["scale", "double", "enlarge", "multiply"],
            source="AUX CODES.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # AUX CODES — Contouring & Look-Ahead
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="AUX 1000", title="Turn On Contouring (Look-Ahead)",
            category=EntryCategory.AUX_CONTOURING,
            description="Enables contouring (look-ahead) mode. The controller reads ahead and blends motion between successive linear moves for smoother cutting. Equivalent to M1000.",
            when_to_use="Enable at the start of continuous profile cutting (outside profiles, pockets, complex contours). The controller will maintain feed rate through corners where possible.",
            syntax="AUX 1000  (or M1000 in G-code)",
            related=["AUX 2000", "M1000", "M2000"],
            tags=["contouring", "look-ahead", "blending", "smooth", "profile"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2000", title="Turn Off Contouring Mode",
            category=EntryCategory.AUX_CONTOURING,
            description="Disables contouring (look-ahead) mode. The controller will decelerate to a stop at the end of each move before starting the next. Equivalent to M2000.",
            when_to_use="Disable before drilling cycles, tool changes, or any operation where you need exact positioning at each point. Also disable before program end.",
            syntax="AUX 2000  (or M2000 in G-code)",
            related=["AUX 1000", "M1000", "M2000"],
            tags=["contouring", "look-ahead", "stop", "exact", "positioning"],
            source="AUX CODES.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # AUX CODES — Limits & Backlash
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="AUX 1101", title="Enable Zero Shift",
            category=EntryCategory.AUX_LIMITS,
            description="Enables the zero/origin shift function. Allows you to offset the work coordinate system from the machine home position. Equivalent to M1101 in G-code.",
            when_to_use="Use when setting up a work offset to position the program origin at a specific point on the workpiece (e.g., corner of stock, center of vise).",
            syntax="AUX 1101  (or M1101 in G-code)",
            related=["AUX 1170", "AUX 1171"],
            tags=["zero shift", "origin", "offset", "work coordinate", "datum"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1110", title="Disable Outer Limit Switches",
            category=EntryCategory.AUX_LIMITS,
            description="Disables the outer (travel) software limit switches.",
            warning="Machine can travel beyond safe limits! Only disable temporarily for setup/maintenance.",
            related=["AUX 1111", "AUX 1112", "AUX 1113"],
            tags=["limits", "travel", "outer", "disable", "safety"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1111", title="Set & Enable Software Limit Switches",
            category=EntryCategory.AUX_LIMITS,
            description="Sets the current position as the software limit and enables outer limit switch protection. The controller records the current axis positions as the travel boundaries.",
            when_to_use="After homing the machine, use this to establish the safe travel envelope. Run this after every cold boot.",
            warning="Position all axes at their physical limit positions before executing.",
            related=["AUX 1110", "AUX 1112", "AUX 1113"],
            tags=["limits", "travel", "set", "enable", "software limits", "boundary"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1112", title="Enable Outer Limit Switches",
            category=EntryCategory.AUX_LIMITS,
            description="Re-enables previously set outer software limit switches without resetting the positions.",
            related=["AUX 1110", "AUX 1111"],
            tags=["limits", "enable", "outer"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1113", title="Set Outer Limits Only (No Enable)",
            category=EntryCategory.AUX_LIMITS,
            description="Sets the outer limit positions at the current axis positions but does NOT enable them. Use AUX 1112 later to activate.",
            related=["AUX 1111", "AUX 1112"],
            tags=["limits", "set", "outer"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1114", title="Disable Inner Limit Switches",
            category=EntryCategory.AUX_LIMITS,
            description="Disables inner software limit switches.",
            related=["AUX 1115", "AUX 1116", "AUX 1117"],
            tags=["limits", "inner", "disable"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1115", title="Set & Enable Inner Limit Switches",
            category=EntryCategory.AUX_LIMITS,
            description="Sets the current position as the inner software limit boundary and enables inner limit protection.",
            when_to_use="Use to create a 'keep-out zone' around fixtures, vises, or areas the tool should never enter.",
            related=["AUX 1114", "AUX 1116", "AUX 1117"],
            tags=["limits", "inner", "set", "enable", "keepout"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1116", title="Enable Inner Limit Switches",
            category=EntryCategory.AUX_LIMITS,
            description="Re-enables previously set inner limit switches without resetting positions.",
            related=["AUX 1114", "AUX 1115"],
            tags=["limits", "inner", "enable"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1117", title="Set Inner Limits Only (No Enable)",
            category=EntryCategory.AUX_LIMITS,
            description="Sets inner limit positions at current axis positions but does not enable them.",
            related=["AUX 1115", "AUX 1116"],
            tags=["limits", "inner", "set"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1150", title="Disable Shifted Outer Limits",
            category=EntryCategory.AUX_LIMITS,
            description="Disables shifted outer software limit switches.",
            related=["AUX 1151", "AUX 1152", "AUX 1153"],
            tags=["limits", "shifted", "outer", "disable"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1151", title="Set & Enable Shifted Outer Limits",
            category=EntryCategory.AUX_LIMITS,
            description="Sets and enables shifted outer software limit switches (offset from base limits).",
            related=["AUX 1150", "AUX 1152"],
            tags=["limits", "shifted", "outer", "set"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1152", title="Enable Shifted Outer Limits",
            category=EntryCategory.AUX_LIMITS,
            description="Enables previously set shifted outer limits.",
            related=["AUX 1150", "AUX 1151"],
            tags=["limits", "shifted", "outer", "enable"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1153", title="Set Shifted Outer Limits Only",
            category=EntryCategory.AUX_LIMITS,
            description="Sets shifted outer limit positions without enabling them.",
            related=["AUX 1151", "AUX 1152"],
            tags=["limits", "shifted", "set"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1154", title="Disable Shifted Inner Limits",
            category=EntryCategory.AUX_LIMITS,
            description="Disables shifted inner software limit switches.",
            related=["AUX 1155", "AUX 1156", "AUX 1157"],
            tags=["limits", "shifted", "inner", "disable"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1155", title="Set & Enable Shifted Inner Limits",
            category=EntryCategory.AUX_LIMITS,
            description="Sets and enables shifted inner software limit switches.",
            related=["AUX 1154", "AUX 1156"],
            tags=["limits", "shifted", "inner"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1156", title="Enable Shifted Inner Limits",
            category=EntryCategory.AUX_LIMITS,
            description="Enables previously set shifted inner limits.",
            related=["AUX 1154", "AUX 1155"],
            tags=["limits", "shifted", "inner", "enable"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1157", title="Set Shifted Inner Limits Only",
            category=EntryCategory.AUX_LIMITS,
            description="Sets shifted inner limit positions without enabling them.",
            related=["AUX 1155", "AUX 1156"],
            tags=["limits", "shifted", "inner", "set"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1160", title="Disable Backlash Compensation",
            category=EntryCategory.AUX_LIMITS,
            description="Disables backlash compensation on all axes. The controller will not add correction moves when axes reverse direction.",
            when_to_use="Disable temporarily for diagnostics or if backlash comp values are incorrectly set and causing positioning errors.",
            related=["AUX 1161", "AUX 1162"],
            tags=["backlash", "compensation", "disable", "accuracy"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1161", title="Set & Enable Backlash Compensation",
            category=EntryCategory.AUX_LIMITS,
            description="Sets the backlash compensation values and enables compensation. The controller stores the current backlash settings and applies correction whenever an axis reverses direction.",
            when_to_use="After measuring actual backlash with a dial indicator on each axis. Set V-variables with the measured backlash values, then execute AUX 1161.",
            warning="Incorrect backlash values will make positioning WORSE. Always measure carefully with a dial indicator.",
            related=["AUX 1160", "AUX 1162"],
            tags=["backlash", "compensation", "set", "accuracy", "dial indicator"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1162", title="Enable Backlash Compensation",
            category=EntryCategory.AUX_LIMITS,
            description="Re-enables previously set backlash compensation without changing the stored values.",
            related=["AUX 1160", "AUX 1161"],
            tags=["backlash", "enable"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1165", title="Disable U/W Axis Limits (G-Only)",
            category=EntryCategory.AUX_LIMITS,
            description="Disables limit switches on U and W axes. Crusader G only.",
            related=["AUX 1166", "AUX 1167", "AUX 1168"],
            tags=["limits", "u axis", "w axis", "crusader g"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1166", title="Set & Enable U/W Axis Limits (G-Only)",
            category=EntryCategory.AUX_LIMITS,
            description="Sets and enables limit switches on U and W axes. Crusader G only.",
            related=["AUX 1165", "AUX 1167"],
            tags=["limits", "u axis", "w axis", "crusader g"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1167", title="Enable U/W Axis Limits (G-Only)",
            category=EntryCategory.AUX_LIMITS,
            description="Enables previously set U and W axis limits. Crusader G only.",
            related=["AUX 1165", "AUX 1166"],
            tags=["limits", "u axis", "w axis", "crusader g"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1168", title="Set U/W Axis Limits Only (G-Only)",
            category=EntryCategory.AUX_LIMITS,
            description="Sets U and W axis limit positions without enabling. Crusader G only.",
            related=["AUX 1166", "AUX 1167"],
            tags=["limits", "u axis", "w axis", "crusader g", "set"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1170", title="Display Absolute Coordinates",
            category=EntryCategory.AUX_LIMITS,
            description="Enables display of absolute (machine) coordinates on the CRT screen.",
            related=["AUX 1171"],
            tags=["display", "absolute", "coordinates", "CRT", "screen"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1171", title="Stop Display Absolute Coordinates",
            category=EntryCategory.AUX_LIMITS,
            description="Stops displaying absolute coordinates and returns to work coordinate display.",
            related=["AUX 1170"],
            tags=["display", "coordinates", "work"],
            source="AUX CODES.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # AUX CODES — Homing & Zero Crossing
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="AUX 1121", title="Seek First Zero Crossing — X Axis",
            category=EntryCategory.AUX_HOMING,
            description="Commands the X axis to move slowly until it finds the first encoder zero crossing (index pulse). Used for precision homing.",
            when_to_use="During machine homing sequence. Provides repeatable home position aligned to encoder index.",
            related=["AUX 1122", "AUX 1124", "AUX 1131"],
            tags=["home", "zero crossing", "index", "encoder", "x axis"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1122", title="Seek First Zero Crossing — Y Axis",
            category=EntryCategory.AUX_HOMING,
            description="Commands the Y axis to move slowly until it finds the first encoder zero crossing.",
            related=["AUX 1121", "AUX 1124", "AUX 1132"],
            tags=["home", "zero crossing", "index", "encoder", "y axis"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1124", title="Seek First Zero Crossing — Z Axis",
            category=EntryCategory.AUX_HOMING,
            description="Commands the Z axis to move slowly until it finds the first encoder zero crossing.",
            related=["AUX 1121", "AUX 1122", "AUX 1134"],
            tags=["home", "zero crossing", "index", "encoder", "z axis"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1131", title="Seek Limit, Reverse to Zero Crossing — X",
            category=EntryCategory.AUX_HOMING,
            description="X axis seeks the limit switch, then reverses slowly until it finds the first encoder zero crossing. Provides a repeatable home position using both the limit switch and encoder index.",
            when_to_use="Full homing sequence for X axis. Most reliable homing method — uses limit switch for rough position, then encoder index for exact repeatability.",
            related=["AUX 1132", "AUX 1134", "AUX 1121"],
            tags=["home", "limit switch", "zero crossing", "index", "x axis", "homing sequence"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1132", title="Seek Limit, Reverse to Zero Crossing — Y",
            category=EntryCategory.AUX_HOMING,
            description="Y axis seeks limit switch, reverses to first encoder zero crossing.",
            related=["AUX 1131", "AUX 1134", "AUX 1122"],
            tags=["home", "limit switch", "zero crossing", "y axis"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1134", title="Seek Limit, Reverse to Zero Crossing — Z",
            category=EntryCategory.AUX_HOMING,
            description="Z axis seeks limit switch, reverses to first encoder zero crossing.",
            related=["AUX 1131", "AUX 1132", "AUX 1124"],
            tags=["home", "limit switch", "zero crossing", "z axis"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1141", title="Enable Zero Crossing on X Axis",
            category=EntryCategory.AUX_HOMING,
            description="Enables the zero crossing (encoder index) detection on the X axis.",
            related=["AUX 1142", "AUX 1144"],
            tags=["zero crossing", "enable", "x axis", "encoder"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1142", title="Enable Zero Crossing on Y Axis",
            category=EntryCategory.AUX_HOMING,
            description="Enables the zero crossing detection on the Y axis.",
            related=["AUX 1141", "AUX 1144"],
            tags=["zero crossing", "enable", "y axis"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1144", title="Enable Zero Crossing on Z Axis",
            category=EntryCategory.AUX_HOMING,
            description="Enables the zero crossing detection on the Z axis.",
            related=["AUX 1141", "AUX 1142"],
            tags=["zero crossing", "enable", "z axis"],
            source="AUX CODES.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # AUX CODES — Threading & Lathe
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="AUX 1200", title="Disable Lathe Mode",
            category=EntryCategory.AUX_THREADING,
            description="Disables lathe mode on the controller. Returns to mill operation.",
            related=["AUX 1201", "AUX 1210", "AUX 1211"],
            tags=["lathe", "disable", "mill"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1201", title="Disable Lathe Mode (Alternate)",
            category=EntryCategory.AUX_THREADING,
            description="Disable lathe mode (same function as AUX 1200).",
            related=["AUX 1200"],
            tags=["lathe", "disable"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1210", title="Enable Axial Threading",
            category=EntryCategory.AUX_THREADING,
            description="Enables axial (longitudinal) threading mode for lathe operations.",
            related=["AUX 1211", "AUX 1212", "AUX 1213"],
            tags=["threading", "axial", "lathe", "longitudinal"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1211", title="Enable Radial Threading",
            category=EntryCategory.AUX_THREADING,
            description="Enables radial (face) threading mode for lathe operations.",
            related=["AUX 1210"],
            tags=["threading", "radial", "face", "lathe"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1212", title="Disable Axial Turning",
            category=EntryCategory.AUX_THREADING,
            description="Disables axial turning mode.",
            related=["AUX 1213"],
            tags=["turning", "axial", "disable", "lathe"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1213", title="Enable Axial Turning",
            category=EntryCategory.AUX_THREADING,
            description="Enables axial turning mode for lathe operations.",
            related=["AUX 1212"],
            tags=["turning", "axial", "enable", "lathe"],
            source="AUX CODES.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # AUX CODES — Axis Swap & Retract
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="AUX 1300", title="Cancel Axis Swapping",
            category=EntryCategory.AUX_AXIS_SWAP,
            description="Cancels any active axis swap and returns to normal axis assignment.",
            related=["AUX 1310", "AUX 1311", "AUX 1312"],
            tags=["axis swap", "cancel", "normal"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1310", title="Swap X & Y Axes",
            category=EntryCategory.AUX_AXIS_SWAP,
            description="Swaps X and Y axis assignments. X commands move the Y axis and vice versa.",
            when_to_use="Rarely used — for special fixturing situations where the part orientation is rotated 90°.",
            related=["AUX 1300", "AUX 1311", "AUX 1312"],
            tags=["axis swap", "x", "y", "rotate"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1311", title="Swap Y & Z Axes",
            category=EntryCategory.AUX_AXIS_SWAP,
            description="Swaps Y and Z axis assignments.",
            related=["AUX 1300", "AUX 1310", "AUX 1312"],
            tags=["axis swap", "y", "z"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1312", title="Swap X & Z Axes",
            category=EntryCategory.AUX_AXIS_SWAP,
            description="Swaps X and Z axis assignments.",
            related=["AUX 1300", "AUX 1310", "AUX 1311"],
            tags=["axis swap", "x", "z"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1313", title="Enable Z Plane Retract in G80 Cycles",
            category=EntryCategory.AUX_AXIS_SWAP,
            description="Enables Z-plane retract during canned drilling cycles (G80 series). The tool retracts to the R-plane (clearance) height between holes.",
            related=["AUX 1314", "G80", "G81", "G83"],
            tags=["retract", "z plane", "drilling", "clearance", "canned cycle"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1314", title="Disable Z Plane Retract in G80 Cycles",
            category=EntryCategory.AUX_AXIS_SWAP,
            description="Disables Z-plane retract in canned drilling cycles. Tool stays at drilled depth between positioning moves.",
            related=["AUX 1313"],
            tags=["retract", "z plane", "drilling", "disable"],
            source="AUX CODES.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # AUX CODES — Feed & Rapid Override
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="AUX 1400", title="Disable Feed Rate Override for Rapids",
            category=EntryCategory.AUX_FEED_RAPID,
            description="Disables the feed rate override knob effect on rapid (G00) moves. Rapid moves always run at full rapid speed regardless of override position.",
            related=["AUX 1401"],
            tags=["feed rate", "override", "rapid", "disable", "knob"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1401", title="Enable Feed Rate Override for Rapids",
            category=EntryCategory.AUX_FEED_RAPID,
            description="Enables the feed rate override knob to also affect rapid (G00) moves. Useful when setting up a new program — you can slow down rapids for safety.",
            when_to_use="Enable during program prove-out to slow rapid moves and verify clearances. Disable for production to maintain cycle time.",
            related=["AUX 1400"],
            tags=["feed rate", "override", "rapid", "enable", "prove-out", "safety"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1410", title="Cancel Vectorial Rapid Mode",
            category=EntryCategory.AUX_FEED_RAPID,
            description="Cancels vectorial rapid mode. Axes rapid independently (each at its own max speed).",
            related=["AUX 1411"],
            tags=["vectorial", "rapid", "cancel", "independent"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1411", title="Set Vectorial Rapid Mode",
            category=EntryCategory.AUX_FEED_RAPID,
            description="Enables vectorial rapid mode. During rapids, all axes coordinate their speeds to arrive at the target simultaneously (straight-line rapid). Slower than independent rapids but produces predictable diagonal motion.",
            related=["AUX 1410"],
            tags=["vectorial", "rapid", "coordinated", "straight line", "diagonal"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1420", title="Clear Both Z & Feed Move Inhibit",
            category=EntryCategory.AUX_FEED_RAPID,
            description="Clears both Z-axis and feed move inhibits, allowing normal motion on all axes.",
            related=["AUX 1421", "AUX 1422", "AUX 1423", "AUX 1424", "AUX 1425"],
            tags=["inhibit", "clear", "z axis", "feed", "motion"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1421", title="Set Z Move Inhibit",
            category=EntryCategory.AUX_FEED_RAPID,
            description="Inhibits (locks out) Z-axis motion. The controller will skip Z moves in the program.",
            when_to_use="Use during dry run to prevent Z plunges. Allows checking XY paths safely above the work.",
            warning="Z will NOT move! Ensure this is cleared (AUX 1422) before running actual cuts.",
            related=["AUX 1422", "AUX 1420"],
            tags=["inhibit", "z axis", "lock", "dry run", "safety"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1422", title="Clear Z Move Inhibit",
            category=EntryCategory.AUX_FEED_RAPID,
            description="Clears Z-axis move inhibit, re-enabling Z motion.",
            related=["AUX 1421", "AUX 1420"],
            tags=["inhibit", "clear", "z axis"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1423", title="Set Feed Move Inhibit",
            category=EntryCategory.AUX_FEED_RAPID,
            description="Inhibits all feed moves. Only rapid (G00) moves will execute.",
            related=["AUX 1424", "AUX 1420"],
            tags=["inhibit", "feed", "lock"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1424", title="Clear Feed Move Inhibit",
            category=EntryCategory.AUX_FEED_RAPID,
            description="Clears feed move inhibit, re-enabling feed moves.",
            related=["AUX 1423", "AUX 1420"],
            tags=["inhibit", "feed", "clear"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1425", title="Set Both Z & Feed Move Inhibit",
            category=EntryCategory.AUX_FEED_RAPID,
            description="Sets both Z-axis and feed move inhibits simultaneously.",
            related=["AUX 1420"],
            tags=["inhibit", "z axis", "feed", "both"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1440", title="Set Rapid Speed from V-Variables",
            category=EntryCategory.AUX_FEED_RAPID,
            description="Sets the rapid traverse speed using V-variable values. V01 = X and Y rapid speed (IPM), V02 = Z rapid speed (IPM). After executing AUX 1440, the new rapid speeds take effect.",
            syntax="V01 200.    (X & Y rapid rate in IPM)\nV02 150.    (Z rapid rate in IPM)\nAUX 1440    (activate new rates)",
            example="V01 200.\nV02 150.\nAUX 1440\nEND",
            when_to_use="To change the default rapid speed (factory default is 100 IPM). X/Y max recommended: 200 IPM. Z max recommended: 150 IPM. Values are lost on cold boot — must be re-entered.",
            warning="Do not exceed 200 IPM on X/Y or 150 IPM on Z. Values reset to factory default (100 IPM) on cold boot.",
            related=["V01", "V02"],
            tags=["rapid", "speed", "traverse", "v-variable", "IPM", "velocity", "cold boot"],
            source="70000249-How to program rapid speed.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # AUX CODES — Program Mode
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="AUX 1500", title="Enable Program Enter Mode",
            category=EntryCategory.AUX_PROGRAM,
            description="Enables program enter mode, allowing manual entry of programs via the controller keypad or RS-232.",
            related=["AUX 1501"],
            tags=["program", "enter", "edit", "mode"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1501", title="Disable Program Enter Mode",
            category=EntryCategory.AUX_PROGRAM,
            description="Exits program enter mode and returns to run mode.",
            related=["AUX 1500"],
            tags=["program", "enter", "disable", "run mode"],
            source="AUX CODES.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # AUX CODES — Simulation & Diagnostics
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="AUX 1600", title="Disable Dry Run Mode",
            category=EntryCategory.AUX_SIMULATION,
            description="Disables dry run mode and returns to normal cutting mode.",
            related=["AUX 1601", "AUX 1602"],
            tags=["dry run", "disable", "normal", "cutting"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1601", title="Enable Dry Run WITH Cutter Comp",
            category=EntryCategory.AUX_SIMULATION,
            description="Enables dry run mode with cutter compensation active. The machine moves through the toolpath at rapid speed without cutting, but applies cutter comp offsets. Good for checking tool paths with compensation.",
            when_to_use="First prove-out of a program that uses cutter compensation (G41/G42). Verify the compensated path is correct before cutting.",
            related=["AUX 1600", "AUX 1602"],
            tags=["dry run", "cutter comp", "prove-out", "test", "verify"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1602", title="Enable Dry Run WITHOUT Cutter Comp",
            category=EntryCategory.AUX_SIMULATION,
            description="Enables dry run mode without cutter compensation. Machine traces the programmed path at rapid speed. Faster than AUX 1601 for basic path verification.",
            when_to_use="Quick verification of the basic toolpath geometry without cutter comp offsets.",
            related=["AUX 1600", "AUX 1601"],
            tags=["dry run", "no cutter comp", "test", "verify", "quick"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1603", title="Simulation Off",
            category=EntryCategory.AUX_SIMULATION,
            description="Turns off simulation mode.",
            related=["AUX 1604"],
            tags=["simulation", "off"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1604", title="Simulation On",
            category=EntryCategory.AUX_SIMULATION,
            description="Enables simulation mode. The controller simulates program execution on the CRT display without any axis motion.",
            when_to_use="Use to visually preview a program on the CRT screen before any machine motion. Safest way to check a new program.",
            related=["AUX 1603"],
            tags=["simulation", "on", "preview", "CRT", "display", "no motion", "safe"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1606", title="Beeper On for Keys",
            category=EntryCategory.AUX_SIMULATION,
            description="Enables the key beep sound when pressing buttons on the controller keypad.",
            tags=["beeper", "sound", "keys", "keypad", "audio"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1607", title="Clear Drift Registers",
            category=EntryCategory.AUX_SIMULATION,
            description="Clears the servo drift compensation registers. Used during servo tuning and diagnostics.",
            related=["AUX 2101", "AUX 2102"],
            tags=["drift", "clear", "servo", "registers", "tuning"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1608", title="Display Available Memory",
            category=EntryCategory.AUX_SIMULATION,
            description="Displays the amount of available program memory on the CRT screen.",
            when_to_use="Check how much memory is available before loading a large program.",
            tags=["memory", "available", "display", "CRT", "free space"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1609", title="Clear Handwheel Mode",
            category=EntryCategory.AUX_SIMULATION,
            description="Clears (exits) handwheel/MPG mode and returns to normal jog or program mode.",
            related=["AUX 1610"],
            tags=["handwheel", "MPG", "clear", "jog"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1610", title="Set Handwheel Mode",
            category=EntryCategory.AUX_SIMULATION,
            description="Enables handwheel (MPG — Manual Pulse Generator) mode for manual axis positioning.",
            related=["AUX 1609"],
            tags=["handwheel", "MPG", "manual", "jog", "positioning"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1611", title="System Warm Reset (M Only)",
            category=EntryCategory.AUX_SIMULATION,
            description="Performs a warm reset of the Crusader M system. Resets the controller software without losing programs in memory. Equivalent to pressing the reset button.",
            warning="Will interrupt any running program. Use only when the controller is in a bad state.",
            tags=["reset", "warm", "reboot", "crusader m"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1612", title="Cold Start (M Only)",
            category=EntryCategory.AUX_SIMULATION,
            description="Performs a cold start of the Crusader M system. WARNING: This erases ALL programs in memory and resets ALL parameters to factory defaults.",
            warning="DESTROYS ALL PROGRAMS IN MEMORY! All parameters reset to factory defaults. Back up programs via RS-232 before executing. Rapid speeds, backlash comp, and all settings will need to be re-entered.",
            tags=["cold start", "factory reset", "erase", "memory", "crusader m"],
            source="AUX CODES.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # AUX CODES — Loop Control
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="AUX 1800", title="Break DO Loop if V0 ≠ 0",
            category=EntryCategory.AUX_LOOP,
            description="Breaks out of the current DO loop if V-variable V0 is not zero. Conditional loop exit.",
            syntax="AUX 1800  (exit loop if V0 ≠ 0)",
            related=["AUX 1801", "AUX 1810"],
            tags=["loop", "break", "conditional", "v-variable", "V0", "do loop"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1801–1809", title="Break DO Loop if V1–V9 ≠ 0",
            category=EntryCategory.AUX_LOOP,
            description="Break out of DO loop if the corresponding V-variable (V1 through V9) is not zero. AUX 1801=V1, AUX 1802=V2, ... AUX 1809=V9.",
            syntax="AUX 180x  (exit loop if Vx ≠ 0, where x = 1-9)",
            related=["AUX 1800", "AUX 1810"],
            tags=["loop", "break", "conditional", "v-variable", "do loop"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1810", title="Set Infinite Loop",
            category=EntryCategory.AUX_LOOP,
            description="Sets the current DO loop to run infinitely until manually stopped or broken via AUX 180x conditional exit.",
            when_to_use="Use for continuous production loops that run until the operator stops the machine, combined with AUX 180x for conditional exit.",
            syntax="DO\n  ... (machining operations)\n  AUX 1810  (loop forever)\nEND",
            related=["AUX 1800"],
            tags=["loop", "infinite", "continuous", "production", "do loop"],
            source="AUX CODES.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # AUX CODES — Single Step Mode
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="AUX 1900", title="Single Step by Event (Default)",
            category=EntryCategory.AUX_STEPPING,
            description="Sets single-step mode to stop after each event (program line). This is the default behavior. Press Cycle Start to advance to the next line.",
            when_to_use="Default mode. Use for careful line-by-line program verification.",
            related=["AUX 1901"],
            tags=["single step", "event", "line by line", "debug", "verify"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 1901", title="Single Step by Motion",
            category=EntryCategory.AUX_STEPPING,
            description="Sets single-step mode to stop after each axis motion, not each program line. This gives finer control — non-motion lines (like feed rate changes) are grouped with the next motion.",
            related=["AUX 1900"],
            tags=["single step", "motion", "fine control", "debug"],
            source="AUX CODES.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # AUX CODES — Drift & Gain
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="AUX 2100", title="Turn Off Low Gain at Target Mode",
            category=EntryCategory.AUX_DRIFT,
            description="Disables low gain mode when the servo reaches its target position. Normal servo gain is maintained.",
            related=["AUX 2200"],
            tags=["servo", "gain", "target", "low gain", "disable"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2101", title="Turn On Drift Compensation",
            category=EntryCategory.AUX_DRIFT,
            description="Enables servo drift compensation. The controller actively corrects for servo amplifier drift.",
            related=["AUX 2102", "AUX 1607"],
            tags=["drift", "compensation", "servo", "enable"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2102", title="Turn Off Drift Compensation",
            category=EntryCategory.AUX_DRIFT,
            description="Disables servo drift compensation.",
            related=["AUX 2101"],
            tags=["drift", "compensation", "servo", "disable"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2110", title="Turn Off AC Target Drift",
            category=EntryCategory.AUX_DRIFT,
            description="Disables AC servo target drift compensation.",
            related=["AUX 2111", "AUX 2112", "AUX 2113", "AUX 2114", "AUX 2115", "AUX 2116"],
            tags=["AC", "drift", "target", "servo", "disable"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2111–2116", title="Set AC Drift Gain Levels",
            category=EntryCategory.AUX_DRIFT,
            description="Sets the AC drift gain divisor. Lower divisor = higher gain (more aggressive correction).\n\nAUX 2111 = Gain ÷ 246 (LOWEST — least correction)\nAUX 2112 = Gain ÷ 128\nAUX 2113 = Gain ÷ 64\nAUX 2114 = Gain ÷ 32\nAUX 2115 = Gain ÷ 16\nAUX 2116 = Gain ÷ 8 (HIGHEST — most correction)",
            when_to_use="Servo tuning only. Start with AUX 2111 (lowest gain) and increase gradually. Too high gain causes oscillation/buzzing.",
            warning="Adjusting servo gain can cause oscillation, runaway, or damage. Only trained technicians should modify these settings.",
            related=["AUX 2110"],
            tags=["AC", "drift", "gain", "servo", "tuning", "oscillation"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2200", title="Turn On Low Gain at Target Mode",
            category=EntryCategory.AUX_DRIFT,
            description="Enables low gain mode when servo reaches target position. Reduces servo stiffness at rest, which can reduce buzzing/hunting on worn machines.",
            when_to_use="If the servos buzz or oscillate when holding position (indicating worn ballscrews or high friction), enable this to reduce holding torque.",
            related=["AUX 2100"],
            tags=["servo", "gain", "target", "low gain", "buzzing", "hunting"],
            source="AUX CODES.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # AUX CODES — Z Readout
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="AUX 2500", title="Turn Off Z Axis Readout Only Mode",
            category=EntryCategory.AUX_CODES,
            description="Exits Z-axis readout only mode and returns to normal 3-axis display.",
            related=["AUX 2600"],
            tags=["z axis", "readout", "display", "normal"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2600", title="Turn On Z Axis Readout Only Mode",
            category=EntryCategory.AUX_CODES,
            description="Sets the display to show only the Z axis position. Useful for setup operations focused on Z depth.",
            related=["AUX 2500"],
            tags=["z axis", "readout", "display", "depth"],
            source="AUX CODES.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # AUX CODES — RS-232 Communication
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="AUX 2700", title="Write to RS-232 in RS-274 Format",
            category=EntryCategory.AUX_RS232,
            description="Sends (uploads) the current program to the RS-232 serial port in RS-274 (standard G-code) format. The controller outputs the program data through the serial port to a connected computer or storage device.",
            syntax="AUX 2700  (send program out serial port in G-code format)",
            when_to_use="To back up a program from the controller to a PC. Connect RS-232 cable, start your receiving software, then execute AUX 2700.",
            related=["AUX 2701", "AUX 2702"],
            tags=["RS-232", "serial", "write", "send", "upload", "RS-274", "G-code", "backup", "output"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2701", title="Receive from RS-232 in RS-274 Format",
            category=EntryCategory.AUX_RS232,
            description="Receives (downloads) a program from the RS-232 serial port in RS-274 (standard G-code) format. The controller reads incoming serial data and stores it as a program.\n\nThis is the setting used on the Supermax-30 for program transfer from PC.",
            syntax="AUX 2701  (receive program from serial port in G-code format)",
            when_to_use="To load a program from a PC into the controller. Set up CNC Bridge or your sending software, then execute AUX 2701 on the controller before starting the transfer.",
            example="On controller: AUX 2701 (then press Start/Enter)\nOn PC: Send the .nc file via CNC Bridge",
            related=["AUX 2700", "AUX 2702", "AUX 2711"],
            tags=["RS-232", "serial", "receive", "download", "RS-274", "G-code", "load", "input", "supermax"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2702", title="Write to RS-232 in Anilam Format",
            category=EntryCategory.AUX_RS232,
            description="Sends the current program to the RS-232 port in Anilam's proprietary (native) format, not standard G-code. Anilam format includes additional controller-specific information.",
            when_to_use="When backing up to another Anilam controller or when you need to preserve Anilam-specific formatting. Use AUX 2700 for standard G-code compatibility.",
            related=["AUX 2700", "AUX 2701"],
            tags=["RS-232", "serial", "write", "anilam format", "proprietary", "native"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2711", title="Enable Continuous Download Mode",
            category=EntryCategory.AUX_RS232,
            description="Enables continuous download mode for DNC (Direct Numerical Control) drip-feeding. The controller executes G-code lines as they arrive over RS-232, without storing the entire program in memory first.",
            when_to_use="For programs too large to fit in controller memory. The PC sends lines one at a time (drip-feed) and the controller executes each immediately. Use CNC Bridge's DNC mode for this.",
            warning="Requires reliable serial connection. Any communication interruption will stop the machine mid-cut. Ensure XON/XOFF flow control is configured.",
            related=["AUX 2701", "AUX 2791"],
            tags=["DNC", "drip feed", "continuous", "download", "RS-232", "large program", "memory"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2740", title="RS-232 Loop Back Test",
            category=EntryCategory.AUX_RS232,
            description="Performs a serial port loop-back test. Connect TX to RX on the DB-25 connector (pins 2 and 3) and execute this test. The controller sends data and verifies it is received correctly.",
            when_to_use="To diagnose serial communication problems. If the loop-back test fails, the issue is in the controller's serial port hardware. If it passes but communication still fails, the problem is in cabling or the remote device.",
            syntax="1. Short pins 2 and 3 on the DB-25 connector\n2. Execute AUX 2740\n3. Controller reports PASS or FAIL",
            related=["AUX 2700", "AUX 2701"],
            tags=["RS-232", "loop back", "test", "diagnostic", "troubleshoot", "cable", "DB-25"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2754", title="Use RS-244-A (ISO) Character Set",
            category=EntryCategory.AUX_RS232,
            description="Sets the RS-232 communication to use the RS-244-A (ISO) character set. ISO uses different character assignments than ASCII for some codes.",
            when_to_use="If your PC or software uses ISO encoding. Most modern systems use ASCII — use AUX 2758 instead.",
            related=["AUX 2758"],
            tags=["RS-232", "character set", "ISO", "RS-244", "encoding"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2758", title="Use RS-258 (ASCII) Character Set",
            category=EntryCategory.AUX_RS232,
            description="Sets the RS-232 communication to use the RS-258 (standard ASCII) character set. This is the correct setting for communication with modern PCs, CNC Bridge, and most terminal software.\n\n★ This is the setting used on the Supermax-30.",
            when_to_use="Always use this for PC communication. Only use AUX 2754 (ISO) if connecting to legacy ISO-only equipment.",
            related=["AUX 2754"],
            tags=["RS-232", "character set", "ASCII", "RS-258", "encoding", "standard", "supermax", "PC"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2765", title="Set 5 Bits Per Character",
            category=EntryCategory.AUX_RS232,
            description="Sets RS-232 data format to 5 data bits per character. Obsolete — only used with very old Baudot/teletype equipment.",
            related=["AUX 2766", "AUX 2767", "AUX 2768"],
            tags=["RS-232", "data bits", "5 bit", "baudot"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2766", title="Set 6 Bits Per Character",
            category=EntryCategory.AUX_RS232,
            description="Sets RS-232 data format to 6 data bits per character. Rarely used.",
            related=["AUX 2765", "AUX 2767", "AUX 2768"],
            tags=["RS-232", "data bits", "6 bit"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2767", title="Set 7 Bits Per Character",
            category=EntryCategory.AUX_RS232,
            description="Sets RS-232 data format to 7 data bits per character. This is the correct setting for G-code transfer — standard ASCII G-code only uses 7-bit characters (codes 0–127).\n\n★ This is the setting used on the Supermax-30.",
            when_to_use="Standard setting for G-code transfer. Use with AUX 2758 (ASCII) and AUX 2772 (Even parity). The parity bit fills the 8th bit position.",
            related=["AUX 2765", "AUX 2766", "AUX 2768", "AUX 2772"],
            tags=["RS-232", "data bits", "7 bit", "ASCII", "standard", "G-code", "supermax"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2768", title="Set 8 Bits Per Character",
            category=EntryCategory.AUX_RS232,
            description="Sets RS-232 data format to 8 data bits per character. Use only if parity is set to None (AUX 2770), as the 8th bit replaces the parity bit.",
            when_to_use="Some modern serial devices expect 8N1 (8 data bits, No parity, 1 stop bit). Only use if not using parity checking.",
            related=["AUX 2767", "AUX 2770"],
            tags=["RS-232", "data bits", "8 bit", "8N1"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2770", title="Set No Parity",
            category=EntryCategory.AUX_RS232,
            description="Disables parity checking on RS-232 communication. Use with 8 data bits (AUX 2768) for 8N1 configuration.",
            related=["AUX 2771", "AUX 2772"],
            tags=["RS-232", "parity", "none", "8N1"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2771", title="Set Odd Parity",
            category=EntryCategory.AUX_RS232,
            description="Sets RS-232 communication to use odd parity checking.",
            related=["AUX 2770", "AUX 2772"],
            tags=["RS-232", "parity", "odd"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2772", title="Set Even Parity",
            category=EntryCategory.AUX_RS232,
            description="Sets RS-232 communication to use even parity checking. This is the standard parity setting for Anilam controllers.\n\nWith 7 data bits (AUX 2767): The parity bit occupies the 8th bit position, providing error detection. Most reliable for G-code transfer over serial cables.",
            when_to_use="Standard Anilam setting. Use with AUX 2767 (7 data bits) for 7E1 or 7E2 configuration.",
            related=["AUX 2770", "AUX 2771", "AUX 2767"],
            tags=["RS-232", "parity", "even", "standard", "error detection"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2780", title="Set Baud Rate 110",
            category=EntryCategory.AUX_RS232,
            description="Sets RS-232 baud rate to 110 bits per second. Extremely slow — teletype speed.",
            related=["AUX 2787", "AUX 2788"],
            tags=["RS-232", "baud", "110"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2781", title="Set Baud Rate 150",
            category=EntryCategory.AUX_RS232,
            description="Sets RS-232 baud rate to 150 bits per second.",
            related=["AUX 2787", "AUX 2788"],
            tags=["RS-232", "baud", "150"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2782", title="Set Baud Rate 300",
            category=EntryCategory.AUX_RS232,
            description="Sets RS-232 baud rate to 300 bits per second.",
            related=["AUX 2787", "AUX 2788"],
            tags=["RS-232", "baud", "300"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2783", title="Set Baud Rate 600",
            category=EntryCategory.AUX_RS232,
            description="Sets RS-232 baud rate to 600 bits per second.",
            related=["AUX 2787", "AUX 2788"],
            tags=["RS-232", "baud", "600"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2784", title="Set Baud Rate 1200",
            category=EntryCategory.AUX_RS232,
            description="Sets RS-232 baud rate to 1200 bits per second.",
            related=["AUX 2787", "AUX 2788"],
            tags=["RS-232", "baud", "1200"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2785", title="Set Baud Rate 1800",
            category=EntryCategory.AUX_RS232,
            description="Sets RS-232 baud rate to 1800 bits per second.",
            related=["AUX 2787", "AUX 2788"],
            tags=["RS-232", "baud", "1800"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2786", title="Set Baud Rate 2400",
            category=EntryCategory.AUX_RS232,
            description="Sets RS-232 baud rate to 2400 bits per second.",
            related=["AUX 2787", "AUX 2788"],
            tags=["RS-232", "baud", "2400"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2787", title="Set Baud Rate 4800",
            category=EntryCategory.AUX_RS232,
            description="Sets RS-232 baud rate to 4800 bits per second.\n\n★ This is the baud rate used on the Supermax-30.\n\n4800 baud is a reliable speed for the Anilam Crusader M, providing good transfer speed while maintaining signal integrity over typical shop cable lengths (up to 50 feet).",
            when_to_use="Recommended for most installations. 4800 baud provides a good balance of speed and reliability. If you experience communication errors, try a lower baud rate. If your cable is short (< 10 feet), you may be able to use 9600.",
            related=["AUX 2786", "AUX 2788"],
            tags=["RS-232", "baud", "4800", "speed", "supermax", "recommended"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2788", title="Set Baud Rate 9600",
            category=EntryCategory.AUX_RS232,
            description="Sets RS-232 baud rate to 9600 bits per second. Maximum standard speed for the Anilam Crusader M. May be unreliable over long cable runs or in electrically noisy shop environments.",
            when_to_use="Use only with short, high-quality cables in low-noise environments. If you get communication errors, drop to 4800 (AUX 2787).",
            related=["AUX 2787", "AUX 2789"],
            tags=["RS-232", "baud", "9600", "maximum", "fast"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2789", title="Set Baud Rate 19200",
            category=EntryCategory.AUX_RS232,
            description="Sets RS-232 baud rate to 19200 bits per second. May not be supported by all Crusader M firmware versions.",
            warning="Not all Crusader M firmware versions support 19200 baud. Test thoroughly before relying on this speed.",
            related=["AUX 2788"],
            tags=["RS-232", "baud", "19200"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2790", title="Set No Handshake",
            category=EntryCategory.AUX_RS232,
            description="Disables all flow control (handshaking) on the RS-232 port. Data is sent without waiting for the receiver to be ready.",
            warning="Without handshaking, data can be lost if the receiver's buffer overflows. Not recommended for program transfer — only for diagnostics.",
            related=["AUX 2791", "AUX 2792"],
            tags=["RS-232", "handshake", "flow control", "none", "disable"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2791", title="Set Software Handshake (XON/XOFF)",
            category=EntryCategory.AUX_RS232,
            description="Enables XON/XOFF software flow control on the RS-232 port.\n\n★ This is the handshake setting used on the Supermax-30.\n\nXON (DC1, 0x11) = Resume sending\nXOFF (DC3, 0x13) = Pause sending\n\nWhen the controller's receive buffer is getting full, it sends XOFF to tell the PC to stop sending. When it has processed some data, it sends XON to resume. CNC Bridge handles this automatically.",
            when_to_use="Standard setting for Anilam RS-232 communication. Always use XON/XOFF for program transfer and DNC drip-feed. CNC Bridge is configured for XON/XOFF by default.",
            related=["AUX 2790", "AUX 2792"],
            tags=["RS-232", "handshake", "flow control", "XON", "XOFF", "software", "DC1", "DC3", "supermax", "standard"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2792", title="Set Hardware Handshake (DTR/DSR)",
            category=EntryCategory.AUX_RS232,
            description="Enables DTR/DSR hardware flow control on the RS-232 port. Uses physical signal wires (DTR and DSR) to control data flow instead of in-band characters.",
            when_to_use="Only if your cabling supports hardware handshake wires (pins 6 and 20 on DB-25). XON/XOFF (AUX 2791) is more commonly used and doesn't require special cabling.",
            related=["AUX 2790", "AUX 2791"],
            tags=["RS-232", "handshake", "flow control", "hardware", "DTR", "DSR", "wiring"],
            source="AUX CODES.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # AUX CODES — Data Conversion
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="AUX 2800", title="Convert 13-Byte to Compact Form",
            category=EntryCategory.AUX_ADVANCED,
            description="Converts program data from 13-byte per entry format to compact format. Saves memory space.",
            related=["AUX 2801", "AUX 2900"],
            tags=["convert", "compact", "memory", "format"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2801", title="Convert Compact to 13-Byte Form",
            category=EntryCategory.AUX_ADVANCED,
            description="Converts program data from compact format back to 13-byte per entry format.",
            related=["AUX 2800"],
            tags=["convert", "expand", "format"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 2900", title="Pack Program to Shortest Form",
            category=EntryCategory.AUX_ADVANCED,
            description="Packs the current program into the most memory-efficient format possible. Optimizes storage without changing program behavior.",
            when_to_use="When running low on program memory. Pack the program to free up space for additional programs.",
            related=["AUX 2800", "AUX 1608"],
            tags=["pack", "compress", "memory", "optimize", "space"],
            source="AUX CODES.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # AUX CODES — Math & Variables
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="AUX 4000", title="Scaled Variable Assignment",
            category=EntryCategory.AUX_MATH,
            description="Assigns a scaled V-variable value: Vxx ← scaled Vxx.",
            tags=["v-variable", "math", "scale", "assign"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 4300", title="Add Without Type Convert",
            category=EntryCategory.AUX_MATH,
            description="Adds V-variable values without automatic type conversion (integer/float).",
            related=["AUX 4400", "AUX 4500", "AUX 4600"],
            tags=["v-variable", "math", "add", "addition"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 4400", title="Subtract Without Type Convert",
            category=EntryCategory.AUX_MATH,
            description="Subtracts V-variable values without automatic type conversion.",
            related=["AUX 4300", "AUX 4500", "AUX 4600"],
            tags=["v-variable", "math", "subtract"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 4500", title="Multiply With Type Convert",
            category=EntryCategory.AUX_MATH,
            description="Multiplies V-variable values with automatic type conversion.",
            related=["AUX 4300", "AUX 4400", "AUX 4600"],
            tags=["v-variable", "math", "multiply"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 4600", title="Divide With Type Convert",
            category=EntryCategory.AUX_MATH,
            description="Divides V-variable values with automatic type conversion.",
            related=["AUX 4300", "AUX 4400", "AUX 4500"],
            tags=["v-variable", "math", "divide"],
            source="AUX CODES.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # AUX CODES — Advanced / Mold
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="AUX 9000", title="Store Feed Rate & Position in V Registers",
            category=EntryCategory.AUX_ADVANCED,
            description="Stores the current machine state into V-variables:\n  V26 ← actual X coordinate\n  V27 ← actual Y coordinate\n  V28 ← actual Z coordinate\n  V29 ← programmed feed rate\n\nUseful for probing cycles, part measurement, or custom positioning routines.",
            syntax="AUX 9000\n(Now V26=X, V27=Y, V28=Z, V29=Feed)",
            when_to_use="In custom probing or measurement routines where you need to capture the current position. Also useful for saving position before a manual operation.",
            related=["V26", "V27", "V28", "V29"],
            tags=["position", "capture", "v-variable", "probe", "measurement", "coordinates", "feed rate"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 9030", title="Cancel Mold Rotation",
            category=EntryCategory.AUX_ADVANCED,
            description="Cancels mold rotation mode.",
            related=["AUX 9031", "AUX 9032", "AUX 9033"],
            tags=["mold", "rotation", "cancel"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 9031", title="Mold Rotation on X",
            category=EntryCategory.AUX_ADVANCED,
            description="Enables mold rotation around the X axis.",
            related=["AUX 9030", "AUX 9032", "AUX 9033"],
            tags=["mold", "rotation", "x axis"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 9032", title="Mold Rotation on Y",
            category=EntryCategory.AUX_ADVANCED,
            description="Enables mold rotation around the Y axis.",
            related=["AUX 9030", "AUX 9031"],
            tags=["mold", "rotation", "y axis"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 9033", title="Mold Rotation on Z",
            category=EntryCategory.AUX_ADVANCED,
            description="Enables mold rotation around the Z axis.",
            related=["AUX 9030"],
            tags=["mold", "rotation", "z axis"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 9090", title="Cancel G8x Cycle Expansion",
            category=EntryCategory.AUX_ADVANCED,
            description="Cancels X, Y, and Z expansion in G80-series canned drilling cycles.",
            related=["AUX 9093", "AUX 9094", "AUX 9095"],
            tags=["canned cycle", "expansion", "cancel", "drilling"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 9093", title="Clear Units/Rev Expansion",
            category=EntryCategory.AUX_ADVANCED,
            description="Clears the units-per-revolution feed rate expansion mode.",
            related=["AUX 9094", "AUX 9095"],
            tags=["units", "revolution", "feed rate", "clear"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 9094", title="Enable Units/Min Mode",
            category=EntryCategory.AUX_ADVANCED,
            description="Sets feed rate interpretation to units per minute (IPM or mm/min). This is the standard mode for milling.",
            related=["AUX 9095"],
            tags=["feed rate", "units per minute", "IPM", "standard"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 9095", title="Enable Units/Rev Mode",
            category=EntryCategory.AUX_ADVANCED,
            description="Sets feed rate interpretation to units per revolution (IPR). Used for lathe threading and turning operations.",
            related=["AUX 9094"],
            tags=["feed rate", "units per revolution", "IPR", "lathe", "threading"],
            source="AUX CODES.pdf",
        ),
        ReferenceEntry(
            code="AUX 17xx", title="Fill Register xx with Spindle Direction",
            category=EntryCategory.AUX_ADVANCED,
            description="Stores the current spindle direction status into V-register number xx (where xx = 00-99). Useful in custom macros that need to check spindle state.",
            syntax="AUX 17xx  (V[xx] ← spindle direction)",
            tags=["spindle", "direction", "register", "v-variable", "status"],
            source="AUX CODES.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # G-CODES
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="G00", title="Rapid Positioning",
            category=EntryCategory.G_CODES,
            description="Rapid traverse (non-cutting) move to the specified coordinates at maximum speed. All axes move independently at their maximum rapid rate. Default rapid speed is 100 IPM (changeable via AUX 1440 + V01/V02).",
            syntax="G00 X__ Y__ Z__",
            example="G00 X1.0 Y2.0 Z0.1  (rapid to position)",
            when_to_use="Use for non-cutting positioning moves: approach to workpiece, tool changes, moving between features. NEVER use G00 for cutting — use G01 instead.",
            warning="Machine moves at maximum speed! Ensure clearance from workpiece, fixtures, and clamps.",
            related=["G01", "AUX 1440"],
            tags=["rapid", "positioning", "traverse", "fast", "non-cutting"],
        ),
        ReferenceEntry(
            code="G01", title="Linear Interpolation (Feed Move)",
            category=EntryCategory.G_CODES,
            description="Straight-line cutting move at the programmed feed rate. The tool moves in a straight line from current position to the target coordinates.",
            syntax="G01 X__ Y__ Z__ F__",
            example="G01 X3.0 Y2.0 F20.0  (cut to X3 Y2 at 20 IPM)",
            when_to_use="All straight-line cutting: profiling, pocketing, facing, plunging, slotting.",
            related=["G00", "G02", "G03"],
            tags=["linear", "feed", "cut", "straight", "interpolation"],
        ),
        ReferenceEntry(
            code="G02", title="Circular Interpolation CW",
            category=EntryCategory.G_CODES,
            description="Clockwise circular arc cutting move. Specify the endpoint and either the arc center (I, J) or radius (R). Looking down at the XY plane from above, G02 cuts clockwise.",
            syntax="G02 X__ Y__ I__ J__ F__\nG02 X__ Y__ R__ F__",
            example="G02 X2.0 Y1.0 I0.5 J0.0 F15.0  (CW arc)\nG02 X2.0 Y1.0 R1.0 F15.0        (CW arc with radius)",
            when_to_use="Cutting clockwise arcs and circles. For a full circle, the endpoint equals the start point.",
            related=["G03", "G01"],
            tags=["arc", "circle", "clockwise", "CW", "circular", "interpolation", "radius"],
        ),
        ReferenceEntry(
            code="G03", title="Circular Interpolation CCW",
            category=EntryCategory.G_CODES,
            description="Counter-clockwise circular arc cutting move.",
            syntax="G03 X__ Y__ I__ J__ F__\nG03 X__ Y__ R__ F__",
            example="G03 X2.0 Y1.0 I0.5 J0.0 F15.0  (CCW arc)",
            related=["G02", "G01"],
            tags=["arc", "circle", "counter-clockwise", "CCW", "circular"],
        ),
        ReferenceEntry(
            code="G04", title="Dwell",
            category=EntryCategory.G_CODES,
            description="Pauses program execution for the specified time. Used for chip clearing, spot facing, and allowing the spindle to reach speed.",
            syntax="G04 P__  (P = dwell time in seconds)",
            example="G04 P1.0  (dwell for 1 second)",
            when_to_use="After plunge cuts (let chips clear), at bottom of spot drill (clean hole), after spindle speed change (reach RPM).",
            tags=["dwell", "pause", "wait", "time", "delay"],
        ),
        ReferenceEntry(
            code="G17", title="XY Plane Selection",
            category=EntryCategory.G_CODES,
            description="Selects the XY plane for circular interpolation (G02/G03) and cutter compensation. This is the default plane for vertical mill operations.",
            related=["G18", "G19"],
            tags=["plane", "XY", "selection", "default"],
        ),
        ReferenceEntry(
            code="G18", title="XZ Plane Selection",
            category=EntryCategory.G_CODES,
            description="Selects the XZ plane for circular interpolation and cutter compensation.",
            related=["G17", "G19"],
            tags=["plane", "XZ", "selection"],
        ),
        ReferenceEntry(
            code="G19", title="YZ Plane Selection",
            category=EntryCategory.G_CODES,
            description="Selects the YZ plane for circular interpolation and cutter compensation.",
            related=["G17", "G18"],
            tags=["plane", "YZ", "selection"],
        ),
        ReferenceEntry(
            code="G20/G70", title="Inch Mode",
            category=EntryCategory.G_CODES,
            description="Sets the unit system to inches. All coordinates, feed rates, and dimensions are in inches. G70 is the Anilam equivalent of the standard G20.",
            syntax="G70  or  G20",
            related=["G21", "G71"],
            tags=["inch", "units", "imperial", "G70"],
        ),
        ReferenceEntry(
            code="G21/G71", title="Metric Mode",
            category=EntryCategory.G_CODES,
            description="Sets the unit system to millimeters. G71 is the Anilam equivalent of the standard G21.",
            syntax="G71  or  G21",
            related=["G20", "G70"],
            tags=["metric", "millimeter", "units", "G71"],
        ),
        ReferenceEntry(
            code="G28", title="Return to Machine Home",
            category=EntryCategory.G_CODES,
            description="Returns all axes to machine home position through an intermediate point if specified.",
            syntax="G28 X__ Y__ Z__  (optional intermediate point)",
            example="G28 Z0  (return Z to home first)\nG28 X0 Y0  (then return XY to home)",
            when_to_use="At the end of a program or before tool change to ensure the machine returns to a known position.",
            tags=["home", "return", "reference", "machine zero"],
        ),
        ReferenceEntry(
            code="G29", title="Subroutine System",
            category=EntryCategory.G_CODES,
            description="Anilam subroutine call system. Used with S# (define subroutine), C# (call subroutine), and E (end subroutine).\n\nG29 S1 = Define subroutine #1\nG29 C1 = Call (execute) subroutine #1\nG29 E = End subroutine definition\n\nSubroutines are stored in program memory and can be called multiple times. CNC Bridge's post processor uses G29 C1 for tool changes.",
            syntax="G29 S#  (start/define sub)\n... (sub body)\nG29 E   (end sub)\nG29 C#  (call sub)",
            example="N10 G29 S1     (define tool change sub)\nN20 G00 Z1.0   (retract Z)\nN30 M05        (spindle off)\nN40 M06        (tool change)\nN50 G29 E      (end sub)\n...\nN100 G29 C1    (call tool change sub)",
            when_to_use="For repeated operations (tool changes, approach sequences, repeated patterns). Saves memory and makes programs shorter.",
            related=["G29 S", "G29 C", "G29 E"],
            tags=["subroutine", "sub", "call", "define", "G29", "S", "C", "E", "macro"],
        ),
        ReferenceEntry(
            code="G40", title="Cancel Cutter Compensation",
            category=EntryCategory.G_CODES,
            description="Cancels cutter radius compensation (G41/G42). The tool returns to following the programmed path exactly.",
            related=["G41", "G42"],
            tags=["cutter comp", "cancel", "compensation", "radius"],
        ),
        ReferenceEntry(
            code="G41", title="Cutter Compensation Left",
            category=EntryCategory.G_CODES,
            description="Activates cutter radius compensation, offsetting the tool to the LEFT of the programmed path (when looking in the direction of travel). Used for climb milling on outside profiles.",
            syntax="G41 D__  (D = offset register number)",
            when_to_use="Outside profile climb milling, or inside profile conventional milling.",
            related=["G40", "G42"],
            tags=["cutter comp", "left", "compensation", "radius", "climb", "offset"],
        ),
        ReferenceEntry(
            code="G42", title="Cutter Compensation Right",
            category=EntryCategory.G_CODES,
            description="Activates cutter radius compensation, offsetting the tool to the RIGHT of the programmed path.",
            syntax="G42 D__  (D = offset register number)",
            when_to_use="Outside profile conventional milling, or inside profile climb milling.",
            related=["G40", "G41"],
            tags=["cutter comp", "right", "compensation", "radius", "conventional", "offset"],
        ),
        ReferenceEntry(
            code="G43", title="Tool Length Compensation +",
            category=EntryCategory.G_CODES,
            description="Activates tool length compensation in the positive direction. Adds the tool length offset to the Z position.",
            syntax="G43 H__  (H = tool length offset register)",
            related=["G44", "G49"],
            tags=["tool length", "compensation", "offset", "height"],
        ),
        ReferenceEntry(
            code="G49", title="Cancel Tool Length Compensation",
            category=EntryCategory.G_CODES,
            description="Cancels tool length compensation.",
            related=["G43"],
            tags=["tool length", "cancel", "compensation"],
        ),
        ReferenceEntry(
            code="G80", title="Cancel Canned Cycle",
            category=EntryCategory.G_CODES,
            description="Cancels any active canned drilling cycle (G81–G89).",
            related=["G81", "G82", "G83", "G84"],
            tags=["canned cycle", "cancel", "drilling"],
        ),
        ReferenceEntry(
            code="G81", title="Drill Cycle (No Dwell)",
            category=EntryCategory.G_CODES,
            description="Standard drilling cycle. Rapid to R-plane, feed to depth, rapid retract. No dwell at bottom.",
            syntax="G81 X__ Y__ Z__ R__ F__",
            related=["G80", "G82", "G83"],
            tags=["drill", "canned cycle", "hole"],
        ),
        ReferenceEntry(
            code="G82", title="Drill Cycle with Dwell",
            category=EntryCategory.G_CODES,
            description="Spot drilling / counterboring cycle. Same as G81 but with a dwell at the bottom of the hole.",
            syntax="G82 X__ Y__ Z__ R__ P__ F__  (P = dwell time)",
            when_to_use="Spot drilling, counterboring, or any hole where you need a flat bottom (dwell cleans the hole bottom).",
            related=["G80", "G81", "G83"],
            tags=["drill", "dwell", "spot drill", "counterbore", "canned cycle"],
        ),
        ReferenceEntry(
            code="G83", title="Peck Drill Cycle",
            category=EntryCategory.G_CODES,
            description="Peck drilling cycle. Drills in incremental pecks, retracting to the R-plane between pecks to clear chips. Essential for deep holes.\n\nOn the Anilam Crusader M, peck drilling uses V-variables:\n  V20 = Feed rate (IPM)\n  V21 = Clearance plane height\n  V22 = Dwell at bottom (seconds, 0 = none)\n  V23 = Peck depth increment\n  V24 = Retract amount after each peck",
            syntax="V20=5.0  (feed)\nV21=0.1  (clearance)\nV22=0.0  (dwell)\nV23=0.050 (peck depth)\nV24=0.1  (retract)\nG00 X__ Y__  (position)\nG83         (peck drill)",
            example="V20=5.0\nV21=0.1\nV22=0.0\nV23=0.050\nV24=0.1\nG00 X0.5 Y0.5\nG83\nG00 X1.0 Y1.0\nG83\nG80  (cancel cycle)",
            when_to_use="Any hole deeper than 3× the drill diameter. Prevents chip packing, drill breakage, and poor hole quality.",
            related=["G80", "G81", "V20", "V21", "V22", "V23", "V24"],
            tags=["peck drill", "deep hole", "chip clear", "canned cycle", "v-variable"],
        ),
        ReferenceEntry(
            code="G84", title="Tapping Cycle",
            category=EntryCategory.G_CODES,
            description="Tapping cycle for cutting internal threads. The spindle rotates forward during the feed-in and reverses for retract.",
            syntax="G84 X__ Y__ Z__ R__ F__",
            warning="Feed rate MUST match the tap pitch × RPM exactly. Wrong feed = broken tap.",
            related=["G80"],
            tags=["tap", "tapping", "thread", "canned cycle"],
        ),
        ReferenceEntry(
            code="G90", title="Absolute Positioning",
            category=EntryCategory.G_CODES,
            description="Sets absolute positioning mode. All coordinate values are measured from the current work origin (zero point).",
            syntax="G90",
            when_to_use="Default mode for most programming. Use absolute coordinates for clarity and to avoid cumulative errors.",
            related=["G91"],
            tags=["absolute", "positioning", "mode", "coordinates"],
        ),
        ReferenceEntry(
            code="G91", title="Incremental Positioning",
            category=EntryCategory.G_CODES,
            description="Sets incremental positioning mode. All coordinate values are relative to the current position (distance to move, not destination).",
            syntax="G91",
            when_to_use="Use for repeated patterns, bolt circles, or when programming relative distances is easier than absolute positions. Switch back to G90 when done.",
            warning="Cumulative errors can build up in incremental mode. Use absolute (G90) when possible.",
            related=["G90"],
            tags=["incremental", "relative", "positioning", "mode"],
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # M-CODES
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="M00", title="Program Stop",
            category=EntryCategory.M_CODES,
            description="Unconditional program stop. The machine stops and waits for the operator to press Cycle Start to continue.",
            when_to_use="When you need the operator to perform a manual action (check dimension, flip part, remove chips).",
            related=["M01", "M02", "M30"],
            tags=["stop", "pause", "operator", "manual"],
        ),
        ReferenceEntry(
            code="M01", title="Optional Stop",
            category=EntryCategory.M_CODES,
            description="Optional program stop. Only stops if the Optional Stop button on the controller is activated.",
            when_to_use="Add at strategic points (after roughing, before finishing) where the operator MIGHT want to check the part.",
            related=["M00", "M02"],
            tags=["optional stop", "operator", "check"],
        ),
        ReferenceEntry(
            code="M02", title="Program End",
            category=EntryCategory.M_CODES,
            description="End of program. Stops spindle, coolant, and program execution. Does NOT rewind to the beginning.",
            related=["M30", "M00"],
            tags=["end", "program", "stop", "finish"],
        ),
        ReferenceEntry(
            code="M03", title="Spindle On CW",
            category=EntryCategory.M_CODES,
            description="Starts the spindle rotating clockwise (from above). Standard cutting direction for right-hand tooling.",
            syntax="S3000 M03  (start spindle at 3000 RPM clockwise)",
            related=["M04", "M05"],
            tags=["spindle", "on", "clockwise", "CW", "forward"],
        ),
        ReferenceEntry(
            code="M04", title="Spindle On CCW",
            category=EntryCategory.M_CODES,
            description="Starts the spindle rotating counter-clockwise. Used for left-hand tooling or tapping retract.",
            related=["M03", "M05"],
            tags=["spindle", "on", "counter-clockwise", "CCW", "reverse"],
        ),
        ReferenceEntry(
            code="M05", title="Spindle Off",
            category=EntryCategory.M_CODES,
            description="Stops the spindle. Always call before tool change and at program end.",
            related=["M03", "M04"],
            tags=["spindle", "off", "stop"],
        ),
        ReferenceEntry(
            code="M06", title="Tool Change",
            category=EntryCategory.M_CODES,
            description="Initiates a tool change. On manual machines like the Supermax-30, this stops the program and prompts the operator to change the tool. Used with T-word for tool selection.\n\nAnilam T-code format: T10xx where xx = tool number (T1001 = tool 1, T1002 = tool 2, etc.).",
            syntax="T1001 M06  (select tool 1 and change)",
            example="G29 C1     (call tool change subroutine)\nT1003 M06  (change to tool 3)\nS2500 M03  (start spindle)",
            related=["M03", "M05"],
            tags=["tool change", "ATC", "tool", "T-code", "manual"],
        ),
        ReferenceEntry(
            code="M07", title="Mist Coolant On",
            category=EntryCategory.M_CODES,
            description="Turns on mist coolant (air/oil mist). Controlled by the M-function relay board — the specific relay must be configured on the controller.",
            related=["M08", "M09"],
            tags=["coolant", "mist", "on", "flood"],
        ),
        ReferenceEntry(
            code="M08", title="Flood Coolant On",
            category=EntryCategory.M_CODES,
            description="Turns on flood coolant. Controlled by the M-function relay board.",
            related=["M07", "M09"],
            tags=["coolant", "flood", "on"],
        ),
        ReferenceEntry(
            code="M09", title="Coolant Off",
            category=EntryCategory.M_CODES,
            description="Turns off all coolant (both mist and flood).",
            related=["M07", "M08"],
            tags=["coolant", "off", "stop"],
        ),
        ReferenceEntry(
            code="M30", title="Program End and Rewind",
            category=EntryCategory.M_CODES,
            description="Ends the program, stops spindle and coolant, and rewinds to the beginning for the next cycle.",
            related=["M02"],
            tags=["end", "rewind", "reset", "program"],
        ),
        ReferenceEntry(
            code="M1000", title="Look-Ahead Mode ON (Contouring)",
            category=EntryCategory.M_CODES,
            description="Enables look-ahead / contouring mode. Same function as AUX 1000. The controller reads ahead and blends motion between lines for smoother cutting at higher feed rates.",
            when_to_use="Enable at the start of continuous profile cutting. Disable (M2000) before drilling, tool changes, or exact positioning.",
            syntax="M1000  (enable look-ahead)",
            related=["M2000", "AUX 1000", "AUX 2000"],
            tags=["look-ahead", "contouring", "blending", "smooth", "M1000"],
        ),
        ReferenceEntry(
            code="M1101", title="Enable Zero/Origin Shift",
            category=EntryCategory.M_CODES,
            description="Enables the work coordinate origin shift. Same function as AUX 1101.",
            related=["AUX 1101"],
            tags=["origin", "zero shift", "offset", "work coordinate"],
        ),
        ReferenceEntry(
            code="M2000", title="Look-Ahead Mode OFF",
            category=EntryCategory.M_CODES,
            description="Disables look-ahead / contouring mode. Same function as AUX 2000. The controller decelerates to exact position at each line endpoint.",
            when_to_use="Before drilling cycles, tool changes, or any operation needing exact stop at each programmed point.",
            syntax="M2000  (disable look-ahead)",
            related=["M1000", "AUX 1000", "AUX 2000"],
            tags=["look-ahead", "off", "exact stop", "positioning", "M2000"],
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # V-VARIABLES
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="V01", title="X & Y Rapid Speed (for AUX 1440)",
            category=EntryCategory.V_VARIABLES,
            description="Sets the X and Y axis rapid traverse speed in IPM. Used in conjunction with AUX 1440 to change the rapid speed from the factory default of 100 IPM. Maximum recommended: 200 IPM.",
            syntax="V01 200.  (set X/Y rapid to 200 IPM)",
            related=["V02", "AUX 1440"],
            tags=["rapid", "speed", "x axis", "y axis", "v-variable", "IPM"],
            source="70000249-How to program rapid speed.pdf",
        ),
        ReferenceEntry(
            code="V02", title="Z Rapid Speed (for AUX 1440)",
            category=EntryCategory.V_VARIABLES,
            description="Sets the Z axis rapid traverse speed in IPM. Used with AUX 1440. Maximum recommended: 150 IPM.",
            syntax="V02 150.  (set Z rapid to 150 IPM)",
            related=["V01", "AUX 1440"],
            tags=["rapid", "speed", "z axis", "v-variable", "IPM"],
            source="70000249-How to program rapid speed.pdf",
        ),
        ReferenceEntry(
            code="V20", title="Drilling Cycle Feed Rate",
            category=EntryCategory.V_VARIABLES,
            description="Sets the feed rate for V-variable drilling cycles (G83 peck drill, etc.) in IPM.",
            syntax="V20=5.0  (5 IPM drilling feed)",
            related=["V21", "V22", "V23", "V24", "G83"],
            tags=["drilling", "feed rate", "v-variable", "peck"],
        ),
        ReferenceEntry(
            code="V21", title="Drilling Cycle Clearance Plane",
            category=EntryCategory.V_VARIABLES,
            description="Sets the clearance plane height above the work surface for drilling cycles.",
            syntax="V21=0.1  (0.1 inch above work surface)",
            related=["V20", "V22", "V23", "V24"],
            tags=["drilling", "clearance", "v-variable", "height", "retract"],
        ),
        ReferenceEntry(
            code="V22", title="Drilling Cycle Bottom Dwell",
            category=EntryCategory.V_VARIABLES,
            description="Sets the dwell time (in seconds) at the bottom of each drilling peck. 0 = no dwell.",
            syntax="V22=0.5  (0.5 second dwell at bottom)",
            related=["V20", "V21", "V23", "V24"],
            tags=["drilling", "dwell", "v-variable", "bottom"],
        ),
        ReferenceEntry(
            code="V23", title="Drilling Cycle Peck Depth",
            category=EntryCategory.V_VARIABLES,
            description="Sets the peck depth increment for peck drilling cycles. The drill advances this amount before retracting to clear chips.",
            syntax="V23=0.050  (0.050 inch peck increments)",
            when_to_use="Set to approximately 1-2× the drill diameter for most materials. Reduce for deep holes, hard materials, or small drills.",
            related=["V20", "V21", "V22", "V24", "G83"],
            tags=["drilling", "peck", "depth", "increment", "v-variable"],
        ),
        ReferenceEntry(
            code="V24", title="Drilling Cycle Retract Amount",
            category=EntryCategory.V_VARIABLES,
            description="Sets the retract distance after each peck in a drilling cycle.",
            syntax="V24=0.1  (retract 0.1 inch after each peck)",
            related=["V20", "V21", "V22", "V23"],
            tags=["drilling", "retract", "v-variable"],
        ),
        ReferenceEntry(
            code="V26–V29", title="Position & Feed Capture (AUX 9000)",
            category=EntryCategory.V_VARIABLES,
            description="Read-only after AUX 9000 execution:\n  V26 = Current X position\n  V27 = Current Y position\n  V28 = Current Z position\n  V29 = Current programmed feed rate\n\nThese are populated by executing AUX 9000.",
            related=["AUX 9000"],
            tags=["position", "capture", "coordinates", "feed rate", "v-variable", "AUX 9000"],
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # RS-232 / DNC Reference
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="RS-232 SETUP", title="RS-232 Serial Communication Setup",
            category=EntryCategory.RS232_SETTINGS,
            description="Complete RS-232 setup procedure for the Anilam Crusader M:\n\n1. Connect RS-232 cable from PC to controller DB-25 port\n2. Set AUX codes on the controller (at the keypad):\n   AUX 2758 — ASCII character set\n   AUX 2767 — 7 data bits\n   AUX 2772 — Even parity\n   AUX 2787 — 4800 baud (or AUX 2788 for 9600)\n   AUX 2791 — XON/XOFF handshake\n3. On the PC, configure CNC Bridge to match:\n   4800 baud, 7 data bits, Even parity, XON/XOFF\n4. To receive a program: AUX 2701 on controller, then send from PC\n5. To send a program: Start receiving on PC, then AUX 2700 on controller",
            when_to_use="One-time setup when first connecting the RS-232 cable. These settings persist until cold boot (AUX 1612).",
            related=["AUX 2758", "AUX 2767", "AUX 2772", "AUX 2787", "AUX 2791", "AUX 2700", "AUX 2701"],
            tags=["RS-232", "setup", "serial", "communication", "connection", "cable", "DB-25", "configuration"],
        ),
        ReferenceEntry(
            code="RS-232 SUPERMAX", title="Supermax-30 RS-232 Configuration",
            category=EntryCategory.RS232_SETTINGS,
            description="Specific RS-232 settings used on the Supermax-30 knee mill with Anilam Crusader M controller:\n\n  AUX 2758 — ASCII character set (RS-258)\n  AUX 2767 — 7 bits per character\n  AUX 2787 — 4800 baud rate\n  AUX 2791 — XON/XOFF software handshake\n  AUX 2701 — Receive in RS-274 (G-code) format\n\nCNC Bridge default settings are configured to match these exactly.",
            related=["AUX 2758", "AUX 2767", "AUX 2787", "AUX 2791", "AUX 2701"],
            tags=["supermax", "supermax-30", "RS-232", "configuration", "settings", "baud", "4800"],
        ),
        ReferenceEntry(
            code="DNC DRIP FEED", title="DNC Drip-Feed Operation",
            category=EntryCategory.RS232_SETTINGS,
            description="DNC (Direct Numerical Control) drip-feed allows execution of programs that are too large for the controller's memory. The PC sends G-code lines one at a time through the RS-232 port, and the controller executes each line as it arrives.\n\nSetup:\n1. Configure RS-232 settings (see RS-232 SETUP)\n2. On controller: AUX 2711 to enable continuous download mode\n3. On PC: Open CNC Bridge, load G-code file, select 'Drip Feed' mode\n4. Start the transfer — CNC Bridge handles XON/XOFF flow control\n\nIMPORTANT: The serial connection must be reliable throughout the cut. Any interruption stops the machine mid-operation.",
            warning="DNC drip-feed requires continuous serial connection. Do NOT disconnect the cable, sleep the PC, or close CNC Bridge during operation. Ensure XON/XOFF flow control is working.",
            related=["AUX 2711", "AUX 2791", "AUX 2701"],
            tags=["DNC", "drip feed", "large program", "continuous", "RS-232", "memory", "transfer"],
        ),
        ReferenceEntry(
            code="DB-25 PINOUT", title="RS-232 DB-25 Connector Pinout",
            category=EntryCategory.RS232_SETTINGS,
            description="Anilam Crusader M RS-232 DB-25 connector pinout:\n\n  Pin 1  — Chassis Ground\n  Pin 2  — TXD (Transmit Data) — Controller sends\n  Pin 3  — RXD (Receive Data) — Controller receives\n  Pin 4  — RTS (Request to Send)\n  Pin 5  — CTS (Clear to Send)\n  Pin 6  — DSR (Data Set Ready)\n  Pin 7  — Signal Ground (MUST be connected)\n  Pin 20 — DTR (Data Terminal Ready)\n\nMinimum connections for XON/XOFF: Pins 2, 3, and 7\n\nFor USB-to-RS232 adapter: Connect adapter DB-9 to DB-25 with a DB-9 to DB-25 adapter cable. Ensure Pin 7 (ground) is connected.",
            when_to_use="When building or troubleshooting the serial cable. Pin 7 (ground) must ALWAYS be connected.",
            related=["AUX 2740", "AUX 2791", "AUX 2792"],
            tags=["DB-25", "pinout", "connector", "cable", "wiring", "RS-232", "TXD", "RXD", "ground"],
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # Programming Reference
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="PROGRAM FORMAT", title="Anilam G-Code Program Format",
            category=EntryCategory.PROGRAMMING,
            description="Anilam Crusader M program structure:\n\n%              (program start delimiter)\n(Program Name) (comment in parentheses)\nN10 G70        (inch mode)\nN20 G90        (absolute mode)\n...\n(program body)\n...\nN999 M02       (program end)\n%              (program end delimiter)\n\nRules:\n- Lines start with N (sequence number) — optional but recommended\n- Comments in parentheses: (this is a comment)\n- Semicolon at end of line: optional\n- % delimiters required for RS-232/DNC transfer\n- Decimal points required for dimensions: X1.0 not X1",
            example="%\n(SQUARE PROFILE)\nN10 G70\nN20 G90\nN30 G00 X0 Y0 Z1.0\nN40 T1001 M06\nN50 S3000 M03\nN60 G01 X1.0 F20.0\nN70 M05\nN80 M02\n%",
            tags=["program", "format", "structure", "percent", "delimiter", "comment", "N-word"],
        ),
        ReferenceEntry(
            code="TOOL TABLE", title="Anilam Tool Table Format (T10xx)",
            category=EntryCategory.PROGRAMMING,
            description="Anilam Crusader M uses T10xx tool numbering:\n  T1001 = Tool position 1\n  T1002 = Tool position 2\n  ...\n  T1099 = Tool position 99\n\nTool table entries include:\n  X = Tool diameter\n  Z = Tool length offset\n\nTools are selected with the T-word and changed with M06.",
            syntax="T10xx M06  (select and change to tool xx)",
            example="T1001 M06  (tool 1)\nT1005 M06  (tool 5)\nT1012 M06  (tool 12)",
            tags=["tool", "table", "T10xx", "tool number", "diameter", "length"],
        ),
        ReferenceEntry(
            code="RAPID SPEED", title="Programming Rapid Speed",
            category=EntryCategory.PROGRAMMING,
            description="The rapid speed for all axes defaults to 100 IPM on cold boot. To change:\n\n1. Enter this program:\n   V01 200.    (X & Y rapid rate)\n   V02 150.    (Z rapid rate)\n   AUX 1440    (apply new rates)\n   END\n\n2. Run the program\n\nMaximum recommended speeds:\n  X & Y: 200 IPM\n  Z: 150 IPM\n\nThese values are LOST on cold boot and must be re-entered.",
            warning="Values reset to 100 IPM on cold boot (AUX 1612). Must be reprogrammed after every power loss that triggers a cold start.",
            related=["AUX 1440", "V01", "V02"],
            tags=["rapid", "speed", "traverse", "IPM", "cold boot", "V01", "V02"],
            source="70000249-How to program rapid speed.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # Servo Setup & Maintenance
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="SERVO BALANCE", title="Servo Balance Procedure",
            category=EntryCategory.SERVO_SETUP,
            description="Procedure to balance the servo drive for each axis to eliminate drift:\n\n1. Turn off 110VAC to controller\n2. Open servo box door — find the board rack\n3. Identify board version:\n   — Terminal strip type (30100154/30100125)\n   — PC board type (PC 803, part #31500328)\n\nFor terminal strip type:\n  X axis: meter on terminals 9 and 10\n  Y axis: terminals 7 and 8\n  Z axis: terminals 4 and 6\n\nFor PC 803 board type:\n  X axis: P8 pins 1 and 2\n  Y axis: P8 pins 3 and 4\n  Z axis: P8 pins 5 and 6\n\n4. Turn on power, reset servo\n5. Adjust the Balance pot (on the red-tabbed board) for 0 mV DC\n6. Move meter to Westamp drive card J1 pins 3 and 4\n7. Adjust the BAL pot on the drive card for 0 mV\n8. Verify: handwheel should NOT be turning when balanced\n9. Repeat for all axes",
            warning="Work carefully around live servo electronics. Press E-Stop before moving meter leads between axes.",
            tags=["servo", "balance", "drift", "millivolt", "potentiometer", "calibration", "maintenance", "Westamp"],
            source="Balance-M-or-G.pdf",
        ),
        ReferenceEntry(
            code="SERVO SIGNAL", title="Westamp Drive Card Signal Adjustment",
            category=EntryCategory.SERVO_SETUP,
            description="Adjusting the signal level on Westamp servo drive cards (Series M):\n\n1. Press E-Stop and power off\n2. Identify board version (30100154 PC803 type or 30100125 terminal strip)\n3. Hook meter to signal test points (same as balance procedure)\n4. Write a loop program:\n   DO 30\n   FEED 20\n   X FEED 0\" ABS\n   X FEED 5\" ABS\n   END\n   END\n5. Run the program — observe meter\n6. Adjust SIG potentiometer on drive card for 0.8V DC while axis moves\n7. Repeat for all axes\n\nTarget: 0.8 volts DC on the signal line during axis motion at 10% of rapid speed.",
            when_to_use="When an axis drifts, oscillates, or doesn't track properly during motion. Also after replacing a servo drive card.",
            warning="Only qualified technicians should adjust servo drive cards. Incorrect adjustment can cause runaway.",
            related=["SERVO BALANCE"],
            tags=["servo", "signal", "Westamp", "drive card", "adjustment", "0.8V", "SIG pot", "maintenance"],
            source="ADJUSTMENT-OF-SIGNAL-FOR-Westamp-DRIVE-CARDS-series-M.pdf",
        ),
        ReferenceEntry(
            code="SERVO TURN-ON", title="Crusader M/G Servo Turn-On Circuit",
            category=EntryCategory.SERVO_SETUP,
            description="The servo turn-on circuit path for the Crusader M/G:\n\n1. SVO ON signal from P11-803 → P4-502\n2. Through E-STOP loop (P6-803 → P7-803)\n3. Through DEAD STOP loop\n4. Through THERMAL loop (overtemp protection)\n5. Through K1 and K4 relays\n6. RESET button on P3-801\n\nJW1 and JW2 jumpers select AUTO/MAN mode.\n\nIf servos won't turn on, check:\n  — E-Stop not pressed\n  — Dead stop loop intact (all axis drives connected)\n  — Thermal protection not tripped\n  — K1 and K4 relays\n  — Reset button functionality",
            when_to_use="Troubleshooting when servos won't engage after pressing Reset.",
            tags=["servo", "turn-on", "circuit", "E-Stop", "relay", "troubleshoot", "dead stop", "thermal"],
            source="M_G_servo_turn_on.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # CRT Alignment
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="CRT COMPUTRON", title="Computron CRT Alignment Guide",
            category=EntryCategory.CRT_ALIGNMENT,
            description="Alignment procedure for Computron CRT displays (shipped before Aug 14, 1989):\n\n1. IMAGES FUZZY → Adjust FOCUS on small board attached to tube\n2. VERTICAL SIZE WRONG → Adjust VERTICAL SIZE pot for 4½ inches\n3. TOP/BOTTOM SIZE UNEVEN → Adjust VERTICAL LINEARITY\n4. VIDEO NOT CENTERED → Adjust HORIZONTAL HOLD (careful — too much loses sync)\n\nMotherboard wiring: Pin 1=HORIZ, Pin 4=VERT, Pin 3=VIDEO, Pin 5=GND\nCRT wiring: Pin 45=HORIZ, Pin 47=VERT, Pin 49=VIDEO, Pins 46/48/50=GND",
            tags=["CRT", "Computron", "alignment", "display", "focus", "vertical", "horizontal"],
            source="ComputronCRT.pdf",
        ),
        ReferenceEntry(
            code="CRT NEW COMPUTRON", title="New Computron CRT Alignment Guide",
            category=EntryCategory.CRT_ALIGNMENT,
            description="Alignment procedure for new Computron CRT displays (shipped after Aug 14, 1989):\n\nUsing diagnostic BULLSEYE pattern:\na. CONTRAST pot down until display barely visible\nb. BRIGHTNESS pot up until background raster visible\nc. BRIGHTNESS back down until raster just disappears\nd. CONTRAST up to desired brightness\ne. FOCUS pot until picture is sharp\nf. HORIZONTAL WIDTH coil slug for 6 inch width\ng. VERTICAL SIZE pot for 4½ inch height\nh. HORIZONTAL HOLD pot to center display\ni. On SQUARES pattern: adjust LINEARITY until top and bottom squares same height",
            tags=["CRT", "Computron", "alignment", "display", "new", "focus", "brightness", "contrast"],
            source="NewComputronCRT.pdf",
        ),
        ReferenceEntry(
            code="CRT AUDIOTRONICS", title="Audiotronics/Dotronix CRT Alignment Guide",
            category=EntryCategory.CRT_ALIGNMENT,
            description="Alignment for Audiotronics/Dotronix CRT:\n\n1. IMAGES FUZZY → Adjust FOCUS on circuit board mounted on CRT\n2. HORIZONTAL SIZE → Adjust COIL WIDTH slug for 6 inch width\n3. VIDEO NOT CENTERED → Adjust HORIZONTAL PHASE\n4. PICTURE ROLLS → Adjust VERTICAL HOLD\n5. VERTICAL SIZE → VERTICAL HEIGHT control for 4½ inch height\n6. PICTURE TILTED → Loosen yoke set screw, rotate yoke, re-tighten",
            tags=["CRT", "Audiotronics", "Dotronix", "alignment", "display", "yoke"],
            source="AudiotronicsCRT.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # Service Parts reference
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="PARTS CPU", title="CPU Board Sets — Service Parts",
            category=EntryCategory.PARTS,
            description="Crusader M Mill CPU board sets (repaired in SETS ONLY):\n\n3X Mill Version 3:\n  318003R — Complete board set\n  31800990R — Green tab PCB 513-523\n  31800051R — Orange tab PCB 503\n  31800065R — White tab PCB 500\n\n2X Mill Version 3:\n  318002R — Complete board set\n  31800892R — Green tab PCB 523\n  31800989R — Orange tab PCB 503\n  31800988R — White tab PCB 500\n\nCommon parts:\n  31800039S — CRT Assembly\n  90600306S — Power Supply\n  90700006 — Battery for PCB 503\n  90400533 — Dallas RAM Memory\n  31800054R — Counter board PCB 504\n  31800053R — D/A & Opto PCB 502",
            tags=["parts", "CPU", "board", "PCB", "repair", "service", "mill"],
            source="CRUSADER2,M,G PARTS3.pdf",
        ),
        ReferenceEntry(
            code="PARTS SERVO", title="Servo Drive Parts — Service",
            category=EntryCategory.PARTS,
            description="Common servo drive parts (CR2/M/G):\n\n  31500192R — M-Function board (mill)\n  31500191R — M-Function board (lathe)\n  31500321S — PCB 801 Servo Interface Board\n  31500328S — PCB 803 I/O Interface Board\n  31500190S — Power Supply +24VDC\n  31500798S — Power Supply ±15VDC (servo board bias)\n  80600072M — Reset Switch\n  31501009S — Servo Drive Board (replaces all previous)\n  31501005S — Alternate Servo Drive Board\n\nMotors:\n  37000116 — 3NM without encoder\n  37000202 — 4.5NM without encoder\n  37000111 — Brushes for SEM motors",
            tags=["parts", "servo", "drive", "motor", "board", "power supply", "repair"],
            source="CRUSADER2,M,G PARTS3.pdf",
        ),
        ReferenceEntry(
            code="PARTS DNC KIT", title="DNC Kit — Part Number",
            category=EntryCategory.PARTS,
            description="Anilam DNC Kit part number: 31801249M\nUse with software versions 1013-1B13.\n\nAlso: 31800948M — 3K Memory Upgrade Kit",
            tags=["DNC", "kit", "part number", "memory", "upgrade"],
            source="CRUSADER2,M,G PARTS3.pdf",
        ),
    ])

    # ═══════════════════════════════════════════════════════════
    # SCANNED DOCUMENTS — PDF page viewers
    # ═══════════════════════════════════════════════════════════
    entries.extend([
        ReferenceEntry(
            code="DOC PROGRAMMING", title="Crusader M 3X Programming Manual (220 pages)",
            category=EntryCategory.DOCUMENTS,
            description="Complete Anilam Crusader M 3X Programming Manual (Part# 70000135).\n\nCovers all aspects of programming the Crusader M controller:\n- Coordinate system and axis conventions\n- Manual data input (MDI)\n- Program editing and storage\n- G-code reference with examples\n- Canned drilling cycles (G80-G89)\n- Cutter compensation (G40-G42)\n- Subroutines (G29)\n- DO loops and conditional branching\n- V-variable system\n- AUX code reference\n- M-function reference\n- Tool table setup\n- Part programs and examples\n- Error messages and troubleshooting\n\nThis is the primary reference for all Crusader M programming.",
            when_to_use="The main programming reference. Consult for G-code syntax, canned cycle parameters, subroutine structure, V-variable usage, and program examples.",
            tags=["programming", "manual", "reference", "G-code", "canned cycle", "subroutine", "V-variable",
                  "cutter comp", "tool table", "DO loop", "MDI", "example", "complete", "70000135",
                  "coordinate", "error", "troubleshooting", "training"],
            source="Crusader_M_3X_Programming_70000135.pdf",
            pdf_file="Crusader_M_3X_Programming_70000135.pdf",
            pdf_pages=220,
        ),
        ReferenceEntry(
            code="DOC RS232 MANUAL", title="RS-232 Communication Manual — Crusader II (24 pages)",
            category=EntryCategory.DOCUMENTS,
            description="Detailed RS-232 serial communication manual for the Crusader II/M controller.\n\nCovers:\n- RS-232 hardware interface and DB-25 pinout\n- Signal descriptions (TXD, RXD, RTS, CTS, DTR, DSR)\n- Cable wiring diagrams (null modem, straight-through)\n- Communication protocol and handshaking\n- AUX codes for serial configuration\n- Data format (baud rate, data bits, parity, stop bits)\n- Program transfer procedures (send and receive)\n- DNC drip-feed operation\n- Troubleshooting serial problems\n- Loop-back test procedure",
            when_to_use="Primary reference for RS-232 cable building, serial configuration, and troubleshooting communication problems.",
            related=["AUX 2700", "AUX 2701", "AUX 2787", "AUX 2791", "AUX 2740", "DB-25 PINOUT"],
            tags=["RS-232", "serial", "manual", "cable", "wiring", "DB-25", "communication",
                  "protocol", "handshake", "pinout", "null modem", "troubleshoot"],
            source="RS232 manual CRUSADER II.PDF",
            pdf_file="RS232 manual CRUSADER II.PDF",
            pdf_pages=24,
        ),
        ReferenceEntry(
            code="DOC M-FUNCTIONS", title="M-Codes & AUX Codes Reference (with diagrams)",
            category=EntryCategory.DOCUMENTS,
            description="Scanned reference pages for M-function codes and AUX codes with additional detail beyond the summary sheets.\n\nIncludes:\n- M-function relay assignments\n- M-function timing diagrams\n- Relay board wiring\n- AUX code detailed descriptions\n- Code interaction charts",
            related=["M03", "M06", "M08", "AUX 1000"],
            tags=["M-code", "M-function", "AUX code", "relay", "wiring", "timing", "diagram"],
            source="70000169-m-functions (1).PDF",
            pdf_file="70000169-m-functions (1).PDF",
            pdf_pages=11,
        ),
        ReferenceEntry(
            code="DOC AUX SCANNED", title="AUX Codes — Detailed Scanned Reference (8 pages)",
            category=EntryCategory.DOCUMENTS,
            description="Scanned original AUX code reference pages with handwritten notes and additional context.\nMay contain information not in the typed AUX CODES.pdf summary.",
            tags=["AUX code", "reference", "scanned", "original", "notes"],
            source="Aux Codes 001.pdf",
            pdf_file="Aux Codes 001.pdf",
            pdf_pages=8,
        ),
        ReferenceEntry(
            code="DOC MCODES-AUX", title="M-Codes & AUX Codes Combined Reference (8 pages)",
            category=EntryCategory.DOCUMENTS,
            description="Combined M-code and AUX code reference pages scanned from the original Crusader M manual.\nIncludes both standard and Anilam-specific codes.",
            tags=["M-code", "AUX code", "combined", "reference", "manual"],
            source="Mcodes-Aux Codes 001.pdf",
            pdf_file="Mcodes-Aux Codes 001.pdf",
            pdf_pages=8,
        ),
        ReferenceEntry(
            code="DOC GCODE-RS232", title="G-Code & RS-232 Format Specification (22 pages)",
            category=EntryCategory.DOCUMENTS,
            description="Technical specification for G-code format and RS-232 data transfer format used by the Anilam Crusader.\n\nCovers:\n- G-code syntax and format rules\n- Block structure and word definitions\n- RS-232 data frame format\n- Character encoding and control codes\n- Program start/end delimiters\n- Sequence numbering\n- Data validation",
            related=["PROGRAM FORMAT", "RS-232 SETUP"],
            tags=["G-code", "RS-232", "format", "specification", "syntax", "block", "frame",
                  "delimiter", "encoding", "protocol"],
            source="Gcode-RS232-FormatSpec 001.pdf",
            pdf_file="Gcode-RS232-FormatSpec 001.pdf",
            pdf_pages=22,
        ),
        ReferenceEntry(
            code="DOC RS232-FORMAT", title="RS-232 Format Specification — Alternate Copy (22 pages)",
            category=EntryCategory.DOCUMENTS,
            description="Additional RS-232 format specification document. May contain different revision or supplementary information compared to the G-code/RS-232 spec.",
            related=["DOC GCODE-RS232", "RS-232 SETUP"],
            tags=["RS-232", "format", "specification", "alternate"],
            source="RS232-FormatSpec 001.pdf",
            pdf_file="RS232-FormatSpec 001.pdf",
            pdf_pages=22,
        ),
        ReferenceEntry(
            code="DOC CONSOLE WIRING", title="Console Wiring Diagrams — Crusader M (26 pages)",
            category=EntryCategory.DOCUMENTS,
            description="Complete set of wiring diagrams for the Crusader M console (controller enclosure).\n\nIncludes:\n- Main power distribution\n- CPU board interconnections\n- Servo interface wiring\n- M-function relay board connections\n- RS-232 port wiring\n- CRT display connections\n- Keypad matrix wiring\n- Encoder inputs\n- Emergency stop circuit\n- Power supply connections",
            when_to_use="Essential for hardware troubleshooting, replacing boards, or modifying the controller wiring.",
            warning="Work on wiring only with power OFF and E-Stop engaged.",
            tags=["wiring", "diagram", "schematic", "console", "power", "CPU", "servo",
                  "relay", "RS-232", "CRT", "keypad", "encoder", "E-Stop", "electrical"],
            source="Console-Wiring Diagrams Crusader M.pdf",
            pdf_file="Console-Wiring Diagrams Crusader M.pdf",
            pdf_pages=26,
        ),
        ReferenceEntry(
            code="DOC SERVO WIRING 1", title="Servo Drive Wiring Diagram — Sheet 1",
            category=EntryCategory.DOCUMENTS,
            description="Wiring diagram for the Crusader M servo drive system (Part# 30100154), sheet 1 of 2.\n\nShows servo amplifier connections, motor wiring, encoder feedback, and power connections for the Westamp drive cards.",
            related=["DOC SERVO WIRING 2", "SERVO BALANCE", "SERVO SIGNAL"],
            tags=["servo", "wiring", "diagram", "schematic", "drive", "motor", "encoder",
                  "amplifier", "Westamp", "30100154"],
            source="30100154-1-M-servo-dr-wiring-dwg.pdf",
            pdf_file="30100154-1-M-servo-dr-wiring-dwg.pdf",
            pdf_pages=1,
        ),
        ReferenceEntry(
            code="DOC SERVO WIRING 2", title="Servo Drive Wiring Diagram — Sheet 2",
            category=EntryCategory.DOCUMENTS,
            description="Wiring diagram for the Crusader M servo drive system (Part# 30100154), sheet 2 of 2.\n\nContinuation of servo drive wiring showing signal paths, feedback loops, and safety interlocks.",
            related=["DOC SERVO WIRING 1", "SERVO BALANCE"],
            tags=["servo", "wiring", "diagram", "schematic", "drive", "signal", "interlock", "30100154"],
            source="30100154-2-M-servo-dr-wiring-dwg.pdf",
            pdf_file="30100154-2-M-servo-dr-wiring-dwg.pdf",
            pdf_pages=1,
        ),
        ReferenceEntry(
            code="DOC SERVO PC801", title="Servo Diagrams — PC801 Board Style (3 pages)",
            category=EntryCategory.DOCUMENTS,
            description="Servo system diagrams specific to the PC801 board style controllers.\n\nShows:\n- PC801 board layout and component locations\n- Signal routing between boards\n- Potentiometer locations for balance and signal adjustment\n- Connector pinouts",
            related=["SERVO BALANCE", "SERVO SIGNAL"],
            tags=["servo", "PC801", "diagram", "board", "layout", "potentiometer", "connector"],
            source="M servo diagrams pc801 style.pdf",
            pdf_file="M servo diagrams pc801 style.pdf",
            pdf_pages=3,
        ),
        ReferenceEntry(
            code="DOC CRT ALIGNMENT", title="CRT Alignment — M/G Controller (Scanned, 2 pages)",
            category=EntryCategory.DOCUMENTS,
            description="Scanned CRT alignment instructions with photos/diagrams for the Crusader M/G controller.\nShows physical locations of adjustment pots and coils on the CRT assembly.",
            related=["CRT COMPUTRON", "CRT NEW COMPUTRON", "CRT AUDIOTRONICS"],
            tags=["CRT", "alignment", "display", "adjustment", "photo", "diagram"],
            source="M-G-CRT-ALIGNMENT.pdf",
            pdf_file="M-G-CRT-ALIGNMENT.pdf",
            pdf_pages=2,
        ),
        ReferenceEntry(
            code="DOC COMPUTRON DATA", title="Computron CRT Technical Data (31 pages)",
            category=EntryCategory.DOCUMENTS,
            description="Detailed technical data sheets and specifications for the Computron CRT display used in Anilam controllers.\n\nIncludes:\n- CRT tube specifications\n- Deflection circuit schematics\n- Video amplifier circuits\n- Power supply schematics\n- Component values and part numbers\n- PCB layout drawings\n- Test procedures",
            related=["CRT COMPUTRON", "CRT NEW COMPUTRON"],
            tags=["CRT", "Computron", "technical data", "schematic", "circuit", "specification",
                  "PCB", "video", "deflection", "power supply"],
            source="ComputronCRTdata.pdf",
            pdf_file="ComputronCRTdata.pdf",
            pdf_pages=31,
        ),
        ReferenceEntry(
            code="DOC DNC", title="DNC Operation Guide (2 pages)",
            category=EntryCategory.DOCUMENTS,
            description="Scanned DNC (Direct Numerical Control) operation guide showing step-by-step procedure for drip-feed program execution.",
            related=["DNC DRIP FEED", "AUX 2711"],
            tags=["DNC", "drip feed", "guide", "procedure", "operation"],
            source="DNC 001.pdf",
            pdf_file="DNC 001.pdf",
            pdf_pages=2,
        ),
        ReferenceEntry(
            code="DOC DNC DRIP", title="DNC Drip-Feed Procedure (2 pages)",
            category=EntryCategory.DOCUMENTS,
            description="Detailed drip-feed / DNC setup and operation procedure. Shows controller and PC configuration steps for continuous serial program execution.",
            related=["DNC DRIP FEED", "AUX 2711", "AUX 2791"],
            tags=["DNC", "drip feed", "procedure", "serial", "continuous", "setup"],
            source="dripFeed-DNC 001.pdf",
            pdf_file="dripFeed-DNC 001.pdf",
            pdf_pages=2,
        ),
        ReferenceEntry(
            code="DOC ADVANCED", title="Advanced Programming Guide (22 pages)",
            category=EntryCategory.DOCUMENTS,
            description="Advanced programming techniques for the Anilam Crusader M controller.\n\nCovers:\n- Complex subroutine nesting\n- V-variable arithmetic and conditional logic\n- Parametric programming\n- Pattern repetition with DO loops\n- Coordinate rotation and scaling\n- Custom probing cycles\n- Multi-pass roughing strategies\n- Cutter compensation techniques\n- Error recovery in programs",
            when_to_use="After mastering basic programming. Covers techniques for complex parts, parametric programs, and advanced machining strategies.",
            related=["G29", "AUX 1810", "AUX 9000"],
            tags=["advanced", "programming", "parametric", "V-variable", "subroutine",
                  "DO loop", "rotation", "scaling", "probing", "roughing", "cutter comp"],
            source="advanced programing.pdf",
            pdf_file="advanced programing.pdf",
            pdf_pages=22,
        ),
        ReferenceEntry(
            code="DOC QUANTUM SCALE", title="Quantum Scale Installation Manual (17 pages)",
            category=EntryCategory.DOCUMENTS,
            description="Installation manual for the Anilam Quantum linear scale system (Part# 70000036).\n\nCovers:\n- Scale mounting and alignment\n- Reader head installation\n- Cable routing and connection\n- Counter board (PCB 504) setup\n- Resolution settings\n- Direction settings\n- Testing and calibration\n- Troubleshooting encoder signals",
            when_to_use="When installing or replacing linear scales (encoders) on the machine axes.",
            tags=["Quantum", "scale", "encoder", "linear scale", "installation", "reader head",
                  "mounting", "alignment", "calibration", "resolution", "70000036"],
            source="Quantum_Scale_Install_70000036.pdf",
            pdf_file="Quantum_Scale_Install_70000036.pdf",
            pdf_pages=17,
        ),
        ReferenceEntry(
            code="DOC SUPERMAX MANUAL", title="Supermax YCM-16VS Machine Manual (50 pages)",
            category=EntryCategory.DOCUMENTS,
            description="Complete machine manual for the Supermax YCM-16VS vertical milling machine "
                        "(the mechanical base on which the Anilam Crusader M controller is installed).\n\n"
                        "Covers:\n"
                        "- Machine specifications and dimensions\n"
                        "- Spindle assembly and speed ranges\n"
                        "- Feed mechanisms and gear train\n"
                        "- Lubrication system and schedule\n"
                        "- Electrical schematics and wiring\n"
                        "- Mechanical adjustments (gibs, bearings, spindle)\n"
                        "- Installation and leveling\n"
                        "- Parts breakdown and exploded views\n"
                        "- Maintenance procedures and troubleshooting",
            when_to_use="When servicing, adjusting, or troubleshooting the Supermax YCM-16VS mill "
                        "mechanical components — spindle, ways, gibs, lubrication, or electrical.",
            warning="This covers the mechanical mill only, not the Anilam Crusader M CNC controller. "
                    "For CNC-specific topics see the programming manual and AUX code references.",
            tags=["Supermax", "YCM-16VS", "mill", "manual", "machine", "spindle", "lubrication",
                  "gibs", "bearings", "wiring", "electrical", "mechanical", "parts", "exploded view",
                  "maintenance", "installation", "specifications"],
            source="ijohnsen.com/Supermax_YCM-16VS_Manual.pdf",
            pdf_file="Supermax_YCM-16VS_Manual.pdf",
            pdf_pages=50,
        ),
    ])

    return entries


# ─── Convenience functions ───────────────────────────────────

_library_cache: Optional[List[ReferenceEntry]] = None


def get_library() -> List[ReferenceEntry]:
    """Get the reference library (cached after first build)."""
    global _library_cache
    if _library_cache is None:
        _library_cache = build_library()
    return _library_cache


def search_library(query: str, category: Optional[EntryCategory] = None) -> List[ReferenceEntry]:
    """Search the library and return matching entries sorted by relevance."""
    library = get_library()

    results = []
    for entry in library:
        if category and entry.category != category:
            continue
        if entry.matches(query):
            results.append((entry.match_score(query), entry))

    # Sort by score descending
    results.sort(key=lambda x: x[0], reverse=True)
    return [entry for _, entry in results]


def get_categories() -> List[EntryCategory]:
    """Get all categories that have entries."""
    library = get_library()
    cats = set(e.category for e in library)
    return sorted(cats, key=lambda c: c.value)


def get_entries_by_category(category: EntryCategory) -> List[ReferenceEntry]:
    """Get all entries in a specific category."""
    return [e for e in get_library() if e.category == category]
