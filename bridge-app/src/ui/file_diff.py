"""
CNC Bridge — G-code File Diff Tool

Side-by-side comparison of two G-code files with diff highlighting.
Useful for comparing post processor output or program revisions.
"""

import difflib
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QPlainTextEdit, QFileDialog, QMessageBox,
    QSplitter, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QTextCursor


class DiffView(QPlainTextEdit):
    """A G-code diff view with colored line highlighting."""

    COLOR_ADD = QColor("#1e3a1e")      # green background
    COLOR_REMOVE = QColor("#3a1e1e")   # red background
    COLOR_CHANGE = QColor("#3a3a1e")   # yellow background
    COLOR_NORMAL = QColor("#1e1e1e")   # default dark

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setStyleSheet(
            "QPlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; }"
        )

    def set_diff_content(self, lines: list[tuple[str, str]]):
        """
        Set content with diff markers.
        lines: list of (marker, text) where marker is '+', '-', '~', or ' '
        """
        self.clear()
        cursor = self.textCursor()

        for marker, text in lines:
            fmt = QTextCharFormat()
            if marker == '+':
                fmt.setBackground(self.COLOR_ADD)
                fmt.setForeground(QColor("#6A9955"))
                prefix = "+ "
            elif marker == '-':
                fmt.setBackground(self.COLOR_REMOVE)
                fmt.setForeground(QColor("#F44336"))
                prefix = "- "
            elif marker == '~':
                fmt.setBackground(self.COLOR_CHANGE)
                fmt.setForeground(QColor("#DCDCAA"))
                prefix = "~ "
            else:
                fmt.setForeground(QColor("#d4d4d4"))
                prefix = "  "

            cursor.movePosition(QTextCursor.MoveOperation.End)
            cursor.insertText(prefix + text + "\n", fmt)

        self.setTextCursor(cursor)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.setTextCursor(cursor)


class FileDiffPanel(QGroupBox):
    """Side-by-side file diff panel / tab."""

    def __init__(self, parent=None):
        super().__init__("File Diff", parent)
        self._file_a = ""
        self._file_b = ""
        self._text_a = ""
        self._text_b = ""
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(4)

        # ── Toolbar ──
        toolbar = QHBoxLayout()

        self.open_a_btn = QPushButton("Open File A")
        self.open_a_btn.clicked.connect(self._open_file_a)
        toolbar.addWidget(self.open_a_btn)

        self.label_a = QLabel("No file")
        self.label_a.setStyleSheet("color: #888;")
        toolbar.addWidget(self.label_a)

        toolbar.addSpacing(20)

        self.open_b_btn = QPushButton("Open File B")
        self.open_b_btn.clicked.connect(self._open_file_b)
        toolbar.addWidget(self.open_b_btn)

        self.label_b = QLabel("No file")
        self.label_b.setStyleSheet("color: #888;")
        toolbar.addWidget(self.label_b)

        toolbar.addSpacing(20)

        self.diff_btn = QPushButton("Compare")
        self.diff_btn.setStyleSheet("QPushButton { background-color: #569CD6; color: white; font-weight: bold; }")
        self.diff_btn.clicked.connect(self._run_diff)
        toolbar.addWidget(self.diff_btn)

        self.swap_btn = QPushButton("⇄ Swap")
        self.swap_btn.clicked.connect(self._swap_files)
        toolbar.addWidget(self.swap_btn)

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear)
        toolbar.addWidget(self.clear_btn)

        toolbar.addStretch()

        self.stats_label = QLabel("")
        self.stats_label.setFont(QFont("Consolas", 9))
        self.stats_label.setStyleSheet("color: #888;")
        toolbar.addWidget(self.stats_label)

        layout.addLayout(toolbar)

        # ── Side-by-side diff views ──
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel (File A)
        left = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        self.header_a = QLabel("File A")
        self.header_a.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.header_a.setStyleSheet("color: #569CD6; padding: 2px;")
        left_layout.addWidget(self.header_a)
        self.diff_view_a = DiffView()
        left_layout.addWidget(self.diff_view_a)
        left.setLayout(left_layout)
        splitter.addWidget(left)

        # Right panel (File B)
        right = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        self.header_b = QLabel("File B")
        self.header_b.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
        self.header_b.setStyleSheet("color: #569CD6; padding: 2px;")
        right_layout.addWidget(self.header_b)
        self.diff_view_b = DiffView()
        right_layout.addWidget(self.diff_view_b)
        right.setLayout(right_layout)
        splitter.addWidget(right)

        # Sync scrolling
        self.diff_view_a.verticalScrollBar().valueChanged.connect(
            self.diff_view_b.verticalScrollBar().setValue
        )
        self.diff_view_b.verticalScrollBar().valueChanged.connect(
            self.diff_view_a.verticalScrollBar().setValue
        )

        layout.addWidget(splitter, 1)

        # ── Legend ──
        legend = QHBoxLayout()
        for text, color in [
            ("+ Added", "#6A9955"), ("- Removed", "#F44336"),
            ("~ Changed", "#DCDCAA"), ("  Unchanged", "#888"),
        ]:
            lbl = QLabel(text)
            lbl.setFont(QFont("Consolas", 9))
            lbl.setStyleSheet(f"color: {color};")
            legend.addWidget(lbl)
        legend.addStretch()
        layout.addLayout(legend)

        self.setLayout(layout)

    def _open_file_a(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open File A", "",
            "G-code Files (*.txt *.nc *.ngc *.gcode *.tap);;All Files (*)"
        )
        if filepath:
            self._file_a = filepath
            self._text_a = self._read_file(filepath)
            self.label_a.setText(Path(filepath).name)
            self.label_a.setStyleSheet("color: #d4d4d4;")
            self.header_a.setText(Path(filepath).name)

    def _open_file_b(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open File B", "",
            "G-code Files (*.txt *.nc *.ngc *.gcode *.tap);;All Files (*)"
        )
        if filepath:
            self._file_b = filepath
            self._text_b = self._read_file(filepath)
            self.label_b.setText(Path(filepath).name)
            self.label_b.setStyleSheet("color: #d4d4d4;")
            self.header_b.setText(Path(filepath).name)

    def _read_file(self, filepath: str) -> str:
        try:
            with open(filepath, 'r', encoding='ascii', errors='replace') as f:
                return f.read()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to read file: {e}")
            return ""

    def _swap_files(self):
        self._file_a, self._file_b = self._file_b, self._file_a
        self._text_a, self._text_b = self._text_b, self._text_a
        na = Path(self._file_a).name if self._file_a else "No file"
        nb = Path(self._file_b).name if self._file_b else "No file"
        self.label_a.setText(na)
        self.label_b.setText(nb)
        self.header_a.setText(na)
        self.header_b.setText(nb)
        if self._text_a and self._text_b:
            self._run_diff()

    def _clear(self):
        """Clear both diff views and reset file state."""
        self._file_a = ""
        self._file_b = ""
        self._text_a = ""
        self._text_b = ""
        self.label_a.setText("No file")
        self.label_a.setStyleSheet("color: #888;")
        self.label_b.setText("No file")
        self.label_b.setStyleSheet("color: #888;")
        self.header_a.setText("File A")
        self.header_b.setText("File B")
        self.diff_view_a.clear()
        self.diff_view_b.clear()
        self.stats_label.setText("")

    def _load_texts(self, text_a: str, text_b: str, name_a: str = "A", name_b: str = "B"):
        """Load two text strings directly and run diff (for programmatic use)."""
        self._text_a = text_a
        self._text_b = text_b
        self._file_a = name_a
        self._file_b = name_b
        self.label_a.setText(name_a)
        self.label_a.setStyleSheet("color: #d4d4d4;")
        self.label_b.setText(name_b)
        self.label_b.setStyleSheet("color: #d4d4d4;")
        self.header_a.setText(name_a)
        self.header_b.setText(name_b)
        self._run_diff()

    def _run_diff(self):
        """Run the diff comparison."""
        if not self._text_a or not self._text_b:
            QMessageBox.information(self, "Load Files", "Open both files first.")
            return

        lines_a = self._text_a.splitlines()
        lines_b = self._text_b.splitlines()

        # Use difflib to compute diff
        matcher = difflib.SequenceMatcher(None, lines_a, lines_b)
        opcodes = matcher.get_opcodes()

        view_a_lines = []
        view_b_lines = []
        adds = removes = changes = 0

        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'equal':
                for i in range(i1, i2):
                    view_a_lines.append((' ', lines_a[i]))
                for j in range(j1, j2):
                    view_b_lines.append((' ', lines_b[j]))
            elif tag == 'replace':
                changes += max(i2 - i1, j2 - j1)
                for i in range(i1, i2):
                    view_a_lines.append(('~', lines_a[i]))
                for j in range(j1, j2):
                    view_b_lines.append(('~', lines_b[j]))
                # Pad shorter side
                diff = (i2 - i1) - (j2 - j1)
                if diff > 0:
                    for _ in range(diff):
                        view_b_lines.append((' ', ''))
                elif diff < 0:
                    for _ in range(-diff):
                        view_a_lines.append((' ', ''))
            elif tag == 'insert':
                adds += j2 - j1
                for _ in range(j2 - j1):
                    view_a_lines.append((' ', ''))
                for j in range(j1, j2):
                    view_b_lines.append(('+', lines_b[j]))
            elif tag == 'delete':
                removes += i2 - i1
                for i in range(i1, i2):
                    view_a_lines.append(('-', lines_a[i]))
                for _ in range(i2 - i1):
                    view_b_lines.append((' ', ''))

        self.diff_view_a.set_diff_content(view_a_lines)
        self.diff_view_b.set_diff_content(view_b_lines)

        total = len(lines_a)
        identical = total - removes - changes
        pct = (identical / total * 100) if total > 0 else 100
        self.stats_label.setText(
            f"{adds} added | {removes} removed | {changes} changed | {pct:.0f}% identical"
        )
