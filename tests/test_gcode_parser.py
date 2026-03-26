"""
CNC Bridge — Unit Tests: G-Code Parser

Tests for GCodeParser and GCodeValidator from src.core.gcode_parser.
"""

import sys
from pathlib import Path

# Ensure bridge-app/src is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "bridge-app"))

from src.core.gcode_parser import (
    GCodeParser, GCodeValidator, GCodeWord, GCodeLine,
    Severity, ValidationIssue, ProgramStats,
)


# ── GCodeWord ────────────────────────────────────────────────────

class TestGCodeWord:
    def test_int_value(self):
        w = GCodeWord(letter="G", value=1.0, raw="G1")
        assert w.int_value == 1

    def test_str(self):
        w = GCodeWord(letter="X", value=1.5, raw="X1.5")
        assert str(w) == "X1.5"


# ── GCodeLine ────────────────────────────────────────────────────

class TestGCodeLine:
    def _make_line(self, raw: str) -> GCodeLine:
        parser = GCodeParser()
        return parser.parse_line(raw, 1)

    def test_get_word(self):
        line = self._make_line("G01 X1.0 Y2.0 F100")
        assert line.get_word("X") is not None
        assert line.get_word("X").value == 1.0
        assert line.get_word("Z") is None

    def test_has_word(self):
        line = self._make_line("G00 X5 Y5")
        assert line.has_word("X")
        assert not line.has_word("Z")

    def test_g_codes(self):
        line = self._make_line("G00 G40 X1 Y1")
        assert 0 in line.g_codes
        assert 40 in line.g_codes

    def test_m_codes(self):
        line = self._make_line("M03 S2500")
        assert 3 in line.m_codes


# ── GCodeParser ──────────────────────────────────────────────────

class TestGCodeParser:
    def setup_method(self):
        self.parser = GCodeParser()

    def test_empty_line(self):
        line = self.parser.parse_line("")
        assert line.is_empty

    def test_percent_line(self):
        line = self.parser.parse_line("%")
        assert line.is_percent

    def test_comment_only_paren(self):
        line = self.parser.parse_line("(This is a comment)")
        assert line.is_comment_only
        assert "This is a comment" in line.comment

    def test_comment_only_semicolon(self):
        line = self.parser.parse_line("; This is a comment")
        assert line.is_comment_only
        assert "This is a comment" in line.comment

    def test_inline_comment(self):
        line = self.parser.parse_line("G01 X1.0 (move to 1)")
        assert not line.is_comment_only
        assert "move to 1" in line.comment
        assert line.has_word("G")
        assert line.has_word("X")

    def test_sequence_number(self):
        line = self.parser.parse_line("N100 G01 X1.0")
        assert line.sequence_number == 100
        assert line.has_word("G")

    def test_word_extraction(self):
        line = self.parser.parse_line("G01 X1.5 Y-2.5 Z0.125 F10.0")
        assert len(line.words) == 5
        x = line.get_word("X")
        assert x is not None and x.value == 1.5
        y = line.get_word("Y")
        assert y is not None and y.value == -2.5
        z = line.get_word("Z")
        assert z is not None and z.value == 0.125

    def test_parse_program(self):
        program = "%\nG90\nG01 X1 Y1\nM30\n%"
        lines = self.parser.parse_program(program)
        assert len(lines) == 5
        assert lines[0].is_percent
        assert lines[4].is_percent
        assert 90 in lines[1].g_codes
        assert 30 in lines[3].m_codes

    def test_tool_change(self):
        line = self.parser.parse_line("T1001 M06")
        t = line.get_word("T")
        assert t is not None
        assert t.int_value == 1001
        assert 6 in line.m_codes

    def test_arc_command(self):
        line = self.parser.parse_line("G02 X1.0 Y0.0 I0.5 J0.0")
        assert 2 in line.g_codes
        assert line.has_word("I")
        assert line.has_word("J")

    def test_spindle_speed(self):
        line = self.parser.parse_line("M03 S2500")
        s = line.get_word("S")
        assert s is not None and s.value == 2500

    def test_line_numbers(self):
        lines = self.parser.parse_program("G00\nG01\nG02")
        assert lines[0].line_number == 1
        assert lines[1].line_number == 2
        assert lines[2].line_number == 3


# ── GCodeValidator ───────────────────────────────────────────────

class TestGCodeValidator:
    def setup_method(self):
        self.validator = GCodeValidator()

    def test_valid_program(self):
        text = "%\nG90\nG00 X0 Y0\nG01 X1.0 Y1.0 F10\nM30\n%"
        issues, stats = self.validator.validate_text(text)
        # No errors should occur on a valid program
        errors = [i for i in issues if i.severity == Severity.ERROR]
        assert len(errors) == 0

    def test_stats_line_count(self):
        text = "%\nG90\nG01 X1 Y1 F10\nM30\n%"
        _, stats = self.validator.validate_text(text)
        assert stats.total_lines == 5

    def test_detects_tool_usage(self):
        text = "%\nT1001 M06\nG01 X1 Y1 F10\nT1002 M06\nM30\n%"
        _, stats = self.validator.validate_text(text)
        # Validator counts M06 occurrences; tools_used tracks distinct tools
        assert len(stats.tools_used) >= 2

    def test_validates_unsupported_code(self):
        # G50 is not in the Anilam supported G-code set
        text = "%\nG50\nM30\n%"
        issues, _ = self.validator.validate_text(text)
        # Should generate a warning about unrecognized code
        assert len(issues) > 0
        assert any("G50" in i.message for i in issues)
