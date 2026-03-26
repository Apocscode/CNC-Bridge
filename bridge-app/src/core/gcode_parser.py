"""
CNC Bridge — Anilam Crusader M G-code Parser & Validator

Parses and validates G-code against the Anilam Crusader M dialect.
Provides:
  - G-code tokenization and line parsing
  - Validation against supported G/M codes
  - Tool usage analysis
  - Program statistics (line count, estimated time, travel distance)
  - Error and warning reporting
"""

import re
import math
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# Anilam Crusader M Supported Codes
# ============================================================================

SUPPORTED_G_CODES = {
    0: "Rapid traverse",
    1: "Linear interpolation",
    2: "Circular interpolation CW",
    3: "Circular interpolation CCW",
    4: "Dwell",
    17: "XY plane selection",
    18: "XZ plane selection",
    19: "YZ plane selection",
    20: "Inch mode (alt)",
    21: "Metric mode (alt)",
    28: "Return to home",
    29: "Subroutine call/define",
    40: "Cutter compensation cancel",
    41: "Cutter compensation left",
    42: "Cutter compensation right",
    70: "Inch mode",
    71: "Metric mode",
    80: "Cancel canned cycle",
    81: "Drilling cycle",
    82: "Counter-boring cycle (dwell)",
    83: "Peck drilling cycle",
    84: "Tapping cycle RH",
    85: "Reaming / boring cycle",
    86: "Stop boring cycle",
    87: "Back boring cycle",
    88: "Manual boring cycle",
    89: "Boring cycle with dwell",
    90: "Absolute positioning",
    91: "Incremental positioning",
    92: "Set position / coordinate shift",
    98: "Retract to initial level",
    99: "Retract to R level",
}

SUPPORTED_M_CODES = {
    0: "Program stop",
    1: "Optional stop",
    2: "Program end",
    3: "Spindle CW",
    4: "Spindle CCW",
    5: "Spindle stop",
    6: "Tool change",
    7: "Mist coolant on",
    8: "Flood coolant on",
    9: "Coolant off",
    19: "Spindle orient",
    30: "Program end and rewind",
    1000: "Look-ahead on",
    1101: "Origin shift",
    2000: "Look-ahead off",
}

ANILAM_MAX_FEED_IPM = 500
ANILAM_MAX_FEED_MMPM = 12700
ANILAM_MAX_RPM = 10000
ANILAM_MAX_TOOLS = 99


class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class ValidationIssue:
    line_number: int
    severity: Severity
    code: str
    message: str
    raw_line: str = ""


@dataclass
class GCodeWord:
    """A single G-code word (letter + value)."""
    letter: str
    value: float
    raw: str = ""

    @property
    def int_value(self) -> int:
        return int(self.value)

    def __str__(self):
        return self.raw or f"{self.letter}{self.value}"


@dataclass
class GCodeLine:
    """A parsed G-code line."""
    line_number: int
    raw: str
    sequence_number: Optional[int] = None
    words: list = field(default_factory=list)  # list[GCodeWord]
    comment: str = ""
    is_comment_only: bool = False
    is_empty: bool = False
    is_percent: bool = False

    def get_word(self, letter: str) -> Optional[GCodeWord]:
        """Get first word matching the letter."""
        for w in self.words:
            if w.letter == letter.upper():
                return w
        return None

    def get_words(self, letter: str) -> list:
        """Get all words matching the letter."""
        return [w for w in self.words if w.letter == letter.upper()]

    def has_word(self, letter: str) -> bool:
        return self.get_word(letter) is not None

    @property
    def g_codes(self) -> list[int]:
        return [w.int_value for w in self.words if w.letter == 'G']

    @property
    def m_codes(self) -> list[int]:
        return [w.int_value for w in self.words if w.letter == 'M']


@dataclass
class ToolInfo:
    """Information about a tool used in the program."""
    number: int
    diameter: float = 0.0
    length: float = 0.0
    description: str = ""
    first_use_line: int = 0
    operations: list = field(default_factory=list)


@dataclass
class ProgramStats:
    """Statistics for a parsed program."""
    total_lines: int = 0
    code_lines: int = 0
    comment_lines: int = 0
    empty_lines: int = 0
    total_characters: int = 0
    
    # Motion analysis
    rapid_moves: int = 0
    linear_moves: int = 0
    arc_moves: int = 0
    drill_cycles: int = 0
    
    # Tool usage
    tool_changes: int = 0
    tools_used: list = field(default_factory=list)  # list[ToolInfo]
    
    # Coordinate ranges
    x_min: float = float('inf')
    x_max: float = float('-inf')
    y_min: float = float('inf')
    y_max: float = float('-inf')
    z_min: float = float('inf')
    z_max: float = float('-inf')
    
    # Feed/speed
    max_feed: float = 0.0
    min_feed: float = float('inf')
    max_rpm: float = 0.0
    
    # Subroutines
    subroutine_defines: int = 0
    subroutine_calls: int = 0
    
    # Estimated totals
    estimated_time_minutes: float = 0.0
    total_distance_inches: float = 0.0


class GCodeParser:
    """
    Parses G-code text into structured line/word objects.
    """

    # Regex to match G-code words: letter + number (with optional sign and decimal)
    WORD_PATTERN = re.compile(r'([A-Z])([+-]?\d*\.?\d+)', re.IGNORECASE)
    
    # Comment patterns
    PAREN_COMMENT = re.compile(r'\(([^)]*)\)')
    SEMICOLON_COMMENT = re.compile(r';(.*)')
    
    # Sequence number
    SEQ_PATTERN = re.compile(r'^N(\d+)', re.IGNORECASE)

    def parse_line(self, raw: str, line_number: int = 0) -> GCodeLine:
        """Parse a single line of G-code."""
        line = GCodeLine(line_number=line_number, raw=raw.strip())
        
        text = raw.strip()
        
        # Empty line
        if not text:
            line.is_empty = True
            return line

        # Percent sign (program boundary)
        if text == '%':
            line.is_percent = True
            return line

        # Extract comments
        comment_parts = []
        
        # Parenthetical comments: ( ... )
        for match in self.PAREN_COMMENT.finditer(text):
            comment_parts.append(match.group(1).strip())
        text = self.PAREN_COMMENT.sub('', text)
        
        # Semicolon comments
        semi_match = self.SEMICOLON_COMMENT.search(text)
        if semi_match:
            comment_parts.append(semi_match.group(1).strip())
            text = text[:semi_match.start()]

        line.comment = ' | '.join(comment_parts)

        text = text.strip()
        if not text:
            line.is_comment_only = True
            return line

        # Extract sequence number
        seq_match = self.SEQ_PATTERN.match(text)
        if seq_match:
            line.sequence_number = int(seq_match.group(1))
            text = text[seq_match.end():].strip()

        # Extract words
        for match in self.WORD_PATTERN.finditer(text):
            word = GCodeWord(
                letter=match.group(1).upper(),
                value=float(match.group(2)),
                raw=match.group(0),
            )
            line.words.append(word)

        return line

    def parse_program(self, text: str) -> list[GCodeLine]:
        """Parse a complete G-code program."""
        lines = text.splitlines()
        return [self.parse_line(line, i + 1) for i, line in enumerate(lines)]

    def parse_file(self, filepath: str) -> list[GCodeLine]:
        """Parse a G-code file."""
        path = Path(filepath)
        with open(path, 'r', encoding='ascii', errors='replace') as f:
            return self.parse_program(f.read())


class GCodeValidator:
    """
    Validates parsed G-code against the Anilam Crusader M dialect.
    Reports errors, warnings, and info messages.
    """

    def __init__(self):
        self.parser = GCodeParser()
        self.issues: list[ValidationIssue] = []
        self.stats = ProgramStats()
        self._current_tool: int = 0
        self._current_feed: float = 0
        self._current_rpm: float = 0
        self._current_x: float = 0.0
        self._current_y: float = 0.0
        self._current_z: float = 0.0
        self._is_absolute: bool = True
        self._is_inch: bool = True
        self._tool_table: dict[int, ToolInfo] = {}
        self._motion_mode: int = 0  # G0

    def validate_file(self, filepath: str) -> tuple[list[ValidationIssue], ProgramStats]:
        """Validate a G-code file. Returns (issues, stats)."""
        lines = self.parser.parse_file(filepath)
        return self.validate_lines(lines)

    def validate_text(self, text: str) -> tuple[list[ValidationIssue], ProgramStats]:
        """Validate G-code text. Returns (issues, stats)."""
        lines = self.parser.parse_program(text)
        return self.validate_lines(lines)

    def validate_lines(self, lines: list[GCodeLine]) -> tuple[list[ValidationIssue], ProgramStats]:
        """Validate parsed G-code lines. Returns (issues, stats)."""
        self.issues = []
        self.stats = ProgramStats()
        self._current_tool = 0
        self._current_feed = 0
        self._current_rpm = 0
        self._current_x = 0.0
        self._current_y = 0.0
        self._current_z = 0.0
        self._is_absolute = True
        self._is_inch = True
        self._tool_table = {}
        self._motion_mode = 0

        has_percent_start = False
        has_percent_end = False

        for line in lines:
            self.stats.total_lines += 1
            self.stats.total_characters += len(line.raw)

            if line.is_empty:
                self.stats.empty_lines += 1
                continue
            if line.is_comment_only:
                self.stats.comment_lines += 1
                continue
            if line.is_percent:
                if not has_percent_start:
                    has_percent_start = True
                else:
                    has_percent_end = True
                continue

            self.stats.code_lines += 1
            self._validate_line(line)

        # Post-validation checks
        if has_percent_start and not has_percent_end:
            self._add_issue(0, Severity.WARNING, "W001",
                           "Program starts with % but missing closing %")

        # Build tool list
        self.stats.tools_used = list(self._tool_table.values())
        self.stats.tool_changes = max(0, len(self._tool_table) - 1)

        return self.issues, self.stats

    def _validate_line(self, line: GCodeLine):
        """Validate a single parsed line."""

        # --- Validate G codes ---
        for g in line.g_codes:
            if g not in SUPPORTED_G_CODES:
                self._add_issue(line.line_number, Severity.WARNING, "G001",
                               f"G{g} is not a recognized Anilam Crusader M code",
                               line.raw)

            # Track motion mode
            if g in (0, 1, 2, 3):
                self._motion_mode = g

            # Track absolute/incremental
            if g == 90:
                self._is_absolute = True
            elif g == 91:
                self._is_absolute = False

            # Track units
            if g in (70, 20):
                self._is_inch = True
            elif g in (71, 21):
                self._is_inch = False

            # Motion counting
            if g == 0:
                self.stats.rapid_moves += 1
            elif g == 1:
                self.stats.linear_moves += 1
            elif g in (2, 3):
                self.stats.arc_moves += 1
            elif g in (81, 82, 83, 84, 85, 86, 87, 88, 89):
                self.stats.drill_cycles += 1

            # Subroutine tracking (G29)
            if g == 29:
                s_word = line.get_word('S')
                c_word = line.get_word('C')
                if s_word:
                    self.stats.subroutine_defines += 1
                elif c_word:
                    self.stats.subroutine_calls += 1

        # --- Validate M codes ---
        for m in line.m_codes:
            if m not in SUPPORTED_M_CODES:
                self._add_issue(line.line_number, Severity.WARNING, "M001",
                               f"M{m} is not a recognized Anilam Crusader M code",
                               line.raw)

        # --- Validate Tool ---
        t_word = line.get_word('T')
        if t_word:
            tool_num = t_word.int_value
            
            # Check for T10xx format (tool table definition) vs Txx (tool select)
            if tool_num > 1000:
                # Tool table entry: T10xx
                actual_num = tool_num - 1000
                if actual_num > ANILAM_MAX_TOOLS:
                    self._add_issue(line.line_number, Severity.ERROR, "T001",
                                   f"Tool number {actual_num} exceeds maximum ({ANILAM_MAX_TOOLS})",
                                   line.raw)
                # Record tool info
                x_word = line.get_word('X')
                z_word = line.get_word('Z')
                if actual_num not in self._tool_table:
                    self._tool_table[actual_num] = ToolInfo(number=actual_num)
                if x_word:
                    self._tool_table[actual_num].diameter = x_word.value
                if z_word:
                    self._tool_table[actual_num].length = z_word.value
            else:
                if tool_num > ANILAM_MAX_TOOLS and tool_num != 0:
                    self._add_issue(line.line_number, Severity.ERROR, "T002",
                                   f"Tool number {tool_num} exceeds maximum ({ANILAM_MAX_TOOLS})",
                                   line.raw)
                self._current_tool = tool_num
                if tool_num > 0 and tool_num not in self._tool_table:
                    self._tool_table[tool_num] = ToolInfo(
                        number=tool_num,
                        first_use_line=line.line_number
                    )

        # --- Validate Feed ---
        f_word = line.get_word('F')
        if f_word:
            feed = f_word.value
            self._current_feed = feed
            max_feed = ANILAM_MAX_FEED_IPM if self._is_inch else ANILAM_MAX_FEED_MMPM
            if feed > max_feed:
                self._add_issue(line.line_number, Severity.WARNING, "F001",
                               f"Feed rate {feed} exceeds maximum ({max_feed})",
                               line.raw)
            if feed > self.stats.max_feed:
                self.stats.max_feed = feed
            if feed < self.stats.min_feed:
                self.stats.min_feed = feed

        # --- Validate Spindle Speed ---
        s_word = line.get_word('S')
        if s_word:
            rpm = s_word.value
            self._current_rpm = rpm
            if rpm > ANILAM_MAX_RPM:
                self._add_issue(line.line_number, Severity.WARNING, "S001",
                               f"Spindle speed {rpm} exceeds maximum ({ANILAM_MAX_RPM} RPM)",
                               line.raw)
            if rpm > self.stats.max_rpm:
                self.stats.max_rpm = rpm

        # --- Track coordinates ---
        x_word = line.get_word('X')
        y_word = line.get_word('Y')
        z_word = line.get_word('Z')

        old_x, old_y, old_z = self._current_x, self._current_y, self._current_z

        if x_word:
            if self._is_absolute:
                self._current_x = x_word.value
            else:
                self._current_x += x_word.value
            self.stats.x_min = min(self.stats.x_min, self._current_x)
            self.stats.x_max = max(self.stats.x_max, self._current_x)

        if y_word:
            if self._is_absolute:
                self._current_y = y_word.value
            else:
                self._current_y += y_word.value
            self.stats.y_min = min(self.stats.y_min, self._current_y)
            self.stats.y_max = max(self.stats.y_max, self._current_y)

        if z_word:
            if self._is_absolute:
                self._current_z = z_word.value
            else:
                self._current_z += z_word.value
            self.stats.z_min = min(self.stats.z_min, self._current_z)
            self.stats.z_max = max(self.stats.z_max, self._current_z)

        # Calculate distance for time estimation
        if x_word or y_word or z_word:
            dx = self._current_x - old_x
            dy = self._current_y - old_y
            dz = self._current_z - old_z
            dist = math.sqrt(dx*dx + dy*dy + dz*dz)
            self.stats.total_distance_inches += dist

            # Rough time estimate
            if self._motion_mode == 0:
                # Rapid — assume 200 IPM
                if dist > 0:
                    self.stats.estimated_time_minutes += dist / 200.0
            elif self._current_feed > 0:
                self.stats.estimated_time_minutes += dist / self._current_feed

        # --- Check for feed rate on cutting moves ---
        if self._motion_mode in (1, 2, 3) and (x_word or y_word or z_word):
            if self._current_feed <= 0 and not f_word:
                # Only warn if it's a motion block without prior feed
                if not line.has_word('G') or any(g in (1, 2, 3) for g in line.g_codes):
                    pass  # Feed is modal — may have been set earlier

    def _add_issue(self, line: int, severity: Severity, code: str,
                   message: str, raw: str = ""):
        self.issues.append(ValidationIssue(
            line_number=line,
            severity=severity,
            code=code,
            message=message,
            raw_line=raw,
        ))

    def get_summary(self) -> str:
        """Get a text summary of validation results."""
        s = self.stats
        lines = [
            f"=== Anilam Crusader M G-code Validation ===",
            f"Lines: {s.total_lines} total ({s.code_lines} code, {s.comment_lines} comments, {s.empty_lines} empty)",
            f"Characters: {s.total_characters}",
            f"",
            f"Motion: {s.rapid_moves} rapid, {s.linear_moves} linear, {s.arc_moves} arc, {s.drill_cycles} drill",
            f"Subroutines: {s.subroutine_defines} defined, {s.subroutine_calls} calls",
            f"",
        ]

        if s.tools_used:
            lines.append(f"Tools ({len(s.tools_used)}):")
            for t in s.tools_used:
                desc = f"  T{t.number}: dia={t.diameter}, len={t.length}"
                if t.description:
                    desc += f" ({t.description})"
                lines.append(desc)
            lines.append("")

        if s.x_min != float('inf'):
            lines.append(f"Work envelope:")
            lines.append(f"  X: {s.x_min:.4f} to {s.x_max:.4f}")
            lines.append(f"  Y: {s.y_min:.4f} to {s.y_max:.4f}")
            lines.append(f"  Z: {s.z_min:.4f} to {s.z_max:.4f}")
            lines.append("")

        lines.append(f"Feed range: {s.min_feed:.1f} - {s.max_feed:.1f}")
        lines.append(f"Max RPM: {s.max_rpm:.0f}")
        lines.append(f"Estimated distance: {s.total_distance_inches:.2f} inches")
        lines.append(f"Estimated time: {s.estimated_time_minutes:.1f} minutes")
        lines.append("")

        errors = [i for i in self.issues if i.severity == Severity.ERROR]
        warnings = [i for i in self.issues if i.severity == Severity.WARNING]
        lines.append(f"Issues: {len(errors)} errors, {len(warnings)} warnings")

        for issue in self.issues:
            prefix = "ERROR" if issue.severity == Severity.ERROR else "WARN"
            lines.append(f"  [{prefix}] Line {issue.line_number}: {issue.code} — {issue.message}")

        return "\n".join(lines)
