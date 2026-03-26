"""
CNC Bridge — G-code Editor with Syntax Highlighting

Full-featured G-code editor with:
  - Syntax highlighting (G/M codes, coordinates, comments, etc.)
  - Line numbers
  - Inline validation markers
  - Find/Replace
  - Edit programs without leaving the app
"""

import re
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QTextEdit,
    QPushButton, QLabel, QFileDialog, QMessageBox, QLineEdit,
    QGroupBox, QCheckBox, QFrame,
)
from PyQt6.QtCore import Qt, QRect, QSize, pyqtSignal
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QTextFormat, QSyntaxHighlighter,
    QTextCharFormat, QTextDocument, QTextCursor, QPen,
)


# ── Syntax Highlighter ──────────────────────────────────────────

class GCodeHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Anilam Crusader M G-code."""

    def __init__(self, document: QTextDocument):
        super().__init__(document)
        self._rules = []
        self._build_rules()

    def _build_rules(self):
        """Build highlighting rules."""

        # G-codes — blue
        g_fmt = QTextCharFormat()
        g_fmt.setForeground(QColor("#569CD6"))
        g_fmt.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r'\bG\d{1,3}\b', re.IGNORECASE), g_fmt))

        # M-codes — purple
        m_fmt = QTextCharFormat()
        m_fmt.setForeground(QColor("#C586C0"))
        m_fmt.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r'\bM\d{1,4}\b', re.IGNORECASE), m_fmt))

        # Coordinates X Y Z — green
        coord_fmt = QTextCharFormat()
        coord_fmt.setForeground(QColor("#4EC9B0"))
        self._rules.append((re.compile(r'\b[XYZ][+-]?\d*\.?\d+', re.IGNORECASE), coord_fmt))

        # Arc centers I J K — teal
        arc_fmt = QTextCharFormat()
        arc_fmt.setForeground(QColor("#4FC1FF"))
        self._rules.append((re.compile(r'\b[IJK][+-]?\d*\.?\d+', re.IGNORECASE), arc_fmt))

        # Feed rate F — orange
        feed_fmt = QTextCharFormat()
        feed_fmt.setForeground(QColor("#CE9178"))
        self._rules.append((re.compile(r'\bF\d*\.?\d+', re.IGNORECASE), feed_fmt))

        # Spindle speed S — yellow
        speed_fmt = QTextCharFormat()
        speed_fmt.setForeground(QColor("#DCDCAA"))
        self._rules.append((re.compile(r'\bS\d+', re.IGNORECASE), speed_fmt))

        # Tool numbers T — red/orange
        tool_fmt = QTextCharFormat()
        tool_fmt.setForeground(QColor("#D7BA7D"))
        tool_fmt.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r'\bT\d+', re.IGNORECASE), tool_fmt))

        # Sequence number N — gray
        n_fmt = QTextCharFormat()
        n_fmt.setForeground(QColor("#808080"))
        self._rules.append((re.compile(r'^N\d+', re.IGNORECASE | re.MULTILINE), n_fmt))

        # R values — light blue
        r_fmt = QTextCharFormat()
        r_fmt.setForeground(QColor("#9CDCFE"))
        self._rules.append((re.compile(r'\bR[+-]?\d*\.?\d+', re.IGNORECASE), r_fmt))

        # V-variables — pink
        v_fmt = QTextCharFormat()
        v_fmt.setForeground(QColor("#F472B6"))
        self._rules.append((re.compile(r'\bV\d+', re.IGNORECASE), v_fmt))

        # Percent signs — yellow
        pct_fmt = QTextCharFormat()
        pct_fmt.setForeground(QColor("#FFC107"))
        pct_fmt.setFontWeight(QFont.Weight.Bold)
        self._rules.append((re.compile(r'^%$', re.MULTILINE), pct_fmt))

        # Comments (parenthetical) — green italic
        comment_fmt = QTextCharFormat()
        comment_fmt.setForeground(QColor("#6A9955"))
        comment_fmt.setFontItalic(True)
        self._rules.append((re.compile(r'\([^)]*\)'), comment_fmt))

        # Comments (semicolon) — green italic
        self._rules.append((re.compile(r';.*$', re.MULTILINE), comment_fmt))

    def highlightBlock(self, text: str):
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)


# ── Line Number Area ─────────────────────────────────────────────

class LineNumberArea(QWidget):
    """Line number gutter for the code editor."""

    def __init__(self, editor: "GCodeEditor"):
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self._editor.line_number_area_paint_event(event)


# ── G-code Editor Widget ────────────────────────────────────────

class GCodeEditor(QPlainTextEdit):
    """G-code text editor with line numbers and syntax highlighting."""

    content_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Consolas", 11))
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setTabStopDistance(40)
        self.setStyleSheet(
            "QPlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; "
            "selection-background-color: #264f78; border: none; }"
        )

        # Line number area
        self._line_area = LineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_area_width)
        self.updateRequest.connect(self._update_line_area)
        self.cursorPositionChanged.connect(self._highlight_current_line)
        self._update_line_area_width(0)

        # Syntax highlighter
        self._highlighter = GCodeHighlighter(self.document())

        # Track modifications
        self.textChanged.connect(self.content_changed.emit)

    def line_number_area_width(self) -> int:
        digits = max(1, len(str(self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance('9') * (digits + 1)

    def _update_line_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_area(self, rect, dy):
        if dy:
            self._line_area.scroll(0, dy)
        else:
            self._line_area.update(0, rect.y(), self._line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_area_width(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def line_number_area_paint_event(self, event):
        painter = QPainter(self._line_area)
        painter.fillRect(event.rect(), QColor("#252526"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#858585"))
                painter.setFont(QFont("Consolas", 9))
                painter.drawText(
                    0, top, self._line_area.width() - 5,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, number,
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

        painter.end()

    def _highlight_current_line(self):
        selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor("#2a2d2e"))
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            selections.append(selection)
        self.setExtraSelections(selections)

    def goto_line(self, line_number: int):
        """Move cursor to a specific line number (1-based)."""
        block = self.document().findBlockByLineNumber(line_number - 1)
        if block.isValid():
            cursor = QTextCursor(block)
            self.setTextCursor(cursor)
            self.centerCursor()


# ── Editor Panel (tab widget) ───────────────────────────────────

class GCodeEditorPanel(QGroupBox):
    """G-code editor tab with toolbar, find/replace, and status."""

    file_modified = pyqtSignal(str)  # filepath

    def __init__(self, parent=None):
        super().__init__("G-code Editor", parent)
        self._filepath = ""
        self._is_modified = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(4)

        # ── Toolbar ──
        toolbar = QHBoxLayout()

        self.new_btn = QPushButton("New")
        self.new_btn.clicked.connect(self._new_file)
        toolbar.addWidget(self.new_btn)

        self.open_btn = QPushButton("Open")
        self.open_btn.clicked.connect(self._open_file)
        toolbar.addWidget(self.open_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save_file)
        toolbar.addWidget(self.save_btn)

        self.saveas_btn = QPushButton("Save As")
        self.saveas_btn.clicked.connect(self._save_file_as)
        toolbar.addWidget(self.saveas_btn)

        toolbar.addSpacing(20)

        self.undo_btn = QPushButton("Undo")
        self.undo_btn.clicked.connect(lambda: self.editor.undo())
        toolbar.addWidget(self.undo_btn)

        self.redo_btn = QPushButton("Redo")
        self.redo_btn.clicked.connect(lambda: self.editor.redo())
        toolbar.addWidget(self.redo_btn)

        toolbar.addStretch()

        self.status_label = QLabel("")
        self.status_label.setFont(QFont("Consolas", 9))
        self.status_label.setStyleSheet("color: #888;")
        toolbar.addWidget(self.status_label)

        layout.addLayout(toolbar)

        # ── Find/Replace bar ──
        self._find_frame = QFrame()
        find_layout = QHBoxLayout()
        find_layout.setContentsMargins(0, 0, 0, 0)
        find_layout.setSpacing(4)

        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Find...")
        self.find_input.setFixedWidth(200)
        self.find_input.returnPressed.connect(self._find_next)
        find_layout.addWidget(self.find_input)

        self.find_next_btn = QPushButton("Next")
        self.find_next_btn.clicked.connect(self._find_next)
        find_layout.addWidget(self.find_next_btn)

        self.find_prev_btn = QPushButton("Prev")
        self.find_prev_btn.clicked.connect(self._find_prev)
        find_layout.addWidget(self.find_prev_btn)

        find_layout.addSpacing(10)

        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace...")
        self.replace_input.setFixedWidth(200)
        find_layout.addWidget(self.replace_input)

        self.replace_btn = QPushButton("Replace")
        self.replace_btn.clicked.connect(self._replace_one)
        find_layout.addWidget(self.replace_btn)

        self.replace_all_btn = QPushButton("All")
        self.replace_all_btn.clicked.connect(self._replace_all)
        find_layout.addWidget(self.replace_all_btn)

        self.case_check = QCheckBox("Aa")
        self.case_check.setToolTip("Case sensitive")
        find_layout.addWidget(self.case_check)

        self.find_close_btn = QPushButton("✕")
        self.find_close_btn.setFixedWidth(24)
        self.find_close_btn.clicked.connect(lambda: self._find_frame.setVisible(False))
        find_layout.addWidget(self.find_close_btn)

        find_layout.addStretch()
        self._find_frame.setLayout(find_layout)
        self._find_frame.setVisible(False)
        layout.addWidget(self._find_frame)

        # ── Editor ──
        self.editor = GCodeEditor()
        self.editor.content_changed.connect(self._on_content_changed)
        self.editor.cursorPositionChanged.connect(self._update_cursor_pos)
        layout.addWidget(self.editor, 1)

        self.setLayout(layout)

    # ── File Operations ──

    def _new_file(self):
        if self._is_modified and not self._confirm_discard():
            return
        self.editor.clear()
        self._filepath = ""
        self._is_modified = False
        self._update_title()

    def _open_file(self):
        if self._is_modified and not self._confirm_discard():
            return
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open G-code File", "",
            "G-code Files (*.txt *.nc *.ngc *.gcode *.tap);;All Files (*)"
        )
        if filepath:
            self.load_file(filepath)

    def load_file(self, filepath: str):
        """Load a file into the editor."""
        try:
            with open(filepath, 'r', encoding='ascii', errors='replace') as f:
                text = f.read()
            self.editor.setPlainText(text)
            self._filepath = filepath
            self._is_modified = False
            self._update_title()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {e}")

    def _save_file(self):
        if not self._filepath:
            self._save_file_as()
            return
        self._write_file(self._filepath)

    def _save_file_as(self):
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Save G-code File", self._filepath or "",
            "G-code Files (*.nc);;Text Files (*.txt);;All Files (*)"
        )
        if filepath:
            self._write_file(filepath)

    def _write_file(self, filepath: str):
        try:
            with open(filepath, 'w', encoding='ascii', errors='replace') as f:
                f.write(self.editor.toPlainText())
            self._filepath = filepath
            self._is_modified = False
            self._update_title()
            self.file_modified.emit(filepath)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {e}")

    def _confirm_discard(self) -> bool:
        result = QMessageBox.question(
            self, "Unsaved Changes",
            "You have unsaved changes. Discard them?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes

    # ── Find / Replace ──

    def toggle_find(self):
        """Toggle find bar visibility."""
        visible = not self._find_frame.isVisible()
        self._find_frame.setVisible(visible)
        if visible:
            self.find_input.setFocus()
            self.find_input.selectAll()

    def _find_next(self):
        text = self.find_input.text()
        if not text:
            return
        flags = QTextDocument.FindFlag(0)
        if self.case_check.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if not self.editor.find(text, flags):
            # Wrap around
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cursor)
            self.editor.find(text, flags)

    def _find_prev(self):
        text = self.find_input.text()
        if not text:
            return
        flags = QTextDocument.FindFlag.FindBackward
        if self.case_check.isChecked():
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if not self.editor.find(text, flags):
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.editor.setTextCursor(cursor)
            self.editor.find(text, flags)

    def _replace_one(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == self.find_input.text():
            cursor.insertText(self.replace_input.text())
        self._find_next()

    def _replace_all(self):
        text = self.find_input.text()
        replacement = self.replace_input.text()
        if not text:
            return
        content = self.editor.toPlainText()
        if self.case_check.isChecked():
            count = content.count(text)
            content = content.replace(text, replacement)
        else:
            import re as re_mod
            pattern = re_mod.compile(re_mod.escape(text), re_mod.IGNORECASE)
            matches = pattern.findall(content)
            count = len(matches)
            content = pattern.sub(replacement, content)
        self.editor.setPlainText(content)
        QMessageBox.information(self, "Replace All", f"Replaced {count} occurrences.")

    # ── State ──

    def _on_content_changed(self):
        self._is_modified = True
        self._update_title()

    def _update_title(self):
        name = Path(self._filepath).name if self._filepath else "Untitled"
        modified = " •" if self._is_modified else ""
        lines = self.editor.blockCount()
        self.status_label.setText(f"{name}{modified} | {lines} lines")

    def _update_cursor_pos(self):
        cursor = self.editor.textCursor()
        line = cursor.blockNumber() + 1
        col = cursor.columnNumber() + 1
        current_text = self.status_label.text().split(" | Ln")[0]
        self.status_label.setText(f"{current_text} | Ln {line}, Col {col}")

    def get_text(self) -> str:
        return self.editor.toPlainText()

    @property
    def filepath(self) -> str:
        return self._filepath

    @property
    def is_modified(self) -> bool:
        return self._is_modified
