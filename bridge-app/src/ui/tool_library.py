"""
CNC Bridge — Tool Library Manager

UI panel for managing a persistent tool database.
  - Add/edit/delete tools
  - Store diameter, length, flutes, material, max RPM/feed
  - Generate Anilam T10xx tool table block
  - Copy tool table to clipboard
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QMessageBox, QDialog, QFormLayout, QLineEdit, QSpinBox,
    QDoubleSpinBox, QDialogButtonBox, QApplication, QTextEdit,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from ..core.settings import AppSettings, ToolEntry


class ToolEditDialog(QDialog):
    """Dialog for adding/editing a tool entry."""

    def __init__(self, tool: ToolEntry = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Tool" if tool else "Add Tool")
        self.setMinimumWidth(350)
        self._tool = tool or ToolEntry()
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout()

        self.num_spin = QSpinBox()
        self.num_spin.setRange(1, 99)
        self.num_spin.setValue(self._tool.number)
        layout.addRow("Tool #:", self.num_spin)

        self.desc_edit = QLineEdit(self._tool.description)
        self.desc_edit.setPlaceholderText("e.g., 1/2\" 4-flute end mill")
        layout.addRow("Description:", self.desc_edit)

        self.dia_spin = QDoubleSpinBox()
        self.dia_spin.setRange(0.0, 20.0)
        self.dia_spin.setDecimals(4)
        self.dia_spin.setSuffix('"')
        self.dia_spin.setValue(self._tool.diameter)
        layout.addRow("Diameter:", self.dia_spin)

        self.len_spin = QDoubleSpinBox()
        self.len_spin.setRange(0.0, 20.0)
        self.len_spin.setDecimals(4)
        self.len_spin.setSuffix('"')
        self.len_spin.setValue(self._tool.length)
        layout.addRow("Length:", self.len_spin)

        self.mat_edit = QLineEdit(self._tool.material)
        self.mat_edit.setPlaceholderText("e.g., HSS, Carbide, Cobalt")
        layout.addRow("Material:", self.mat_edit)

        self.flute_spin = QSpinBox()
        self.flute_spin.setRange(0, 12)
        self.flute_spin.setValue(self._tool.flutes)
        layout.addRow("Flutes:", self.flute_spin)

        self.rpm_spin = QSpinBox()
        self.rpm_spin.setRange(0, 10000)
        self.rpm_spin.setSuffix(" RPM")
        self.rpm_spin.setValue(self._tool.max_rpm)
        layout.addRow("Max RPM:", self.rpm_spin)

        self.feed_spin = QDoubleSpinBox()
        self.feed_spin.setRange(0.0, 500.0)
        self.feed_spin.setDecimals(1)
        self.feed_spin.setSuffix(" IPM")
        self.feed_spin.setValue(self._tool.max_feed)
        layout.addRow("Max Feed:", self.feed_spin)

        self.notes_edit = QLineEdit(self._tool.notes)
        self.notes_edit.setPlaceholderText("Additional notes...")
        layout.addRow("Notes:", self.notes_edit)

        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        self.setLayout(layout)

    def get_tool(self) -> ToolEntry:
        """Return the edited tool entry."""
        return ToolEntry(
            number=self.num_spin.value(),
            diameter=self.dia_spin.value(),
            length=self.len_spin.value(),
            description=self.desc_edit.text().strip(),
            material=self.mat_edit.text().strip(),
            flutes=self.flute_spin.value(),
            max_rpm=self.rpm_spin.value(),
            max_feed=self.feed_spin.value(),
            notes=self.notes_edit.text().strip(),
        )


class ToolLibraryPanel(QGroupBox):
    """Tool library manager panel / tab."""

    def __init__(self, settings: AppSettings, parent=None):
        super().__init__("Tool Library", parent)
        self._settings = settings
        self._build_ui()
        self._refresh_table()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(6)

        # ── Toolbar ──
        toolbar = QHBoxLayout()

        self.add_btn = QPushButton("+ Add Tool")
        self.add_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        self.add_btn.clicked.connect(self._add_tool)
        toolbar.addWidget(self.add_btn)

        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._edit_tool)
        toolbar.addWidget(self.edit_btn)

        self.delete_btn = QPushButton("Delete")
        self.delete_btn.setStyleSheet("QPushButton { background-color: #F44336; color: white; }")
        self.delete_btn.clicked.connect(self._delete_tool)
        toolbar.addWidget(self.delete_btn)

        toolbar.addSpacing(20)

        self.gen_btn = QPushButton("Generate T10xx Table")
        self.gen_btn.clicked.connect(self._generate_table)
        toolbar.addWidget(self.gen_btn)

        self.copy_btn = QPushButton("Copy Table")
        self.copy_btn.clicked.connect(self._copy_table)
        toolbar.addWidget(self.copy_btn)

        toolbar.addStretch()

        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #888;")
        toolbar.addWidget(self.count_label)

        layout.addLayout(toolbar)

        # ── Tool Table ──
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "T#", "Description", "Dia", "Length", "Material", "Flutes", "Max RPM", "Max Feed"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setFont(QFont("Consolas", 10))
        self.table.doubleClicked.connect(self._edit_tool)
        self.table.setStyleSheet(
            "QTableWidget { background-color: #1e1e1e; alternate-background-color: #252526; color: #d4d4d4; gridline-color: #3c3c3c; }"
            "QHeaderView::section { background-color: #3c3c3c; color: #d4d4d4; padding: 4px; border: 1px solid #555; }"
        )
        layout.addWidget(self.table, 1)

        # ── Generated table preview ──
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFont(QFont("Consolas", 10))
        self.preview.setMaximumHeight(120)
        self.preview.setStyleSheet("QTextEdit { background-color: #1e1e1e; color: #4EC9B0; }")
        self.preview.setVisible(False)
        layout.addWidget(self.preview)

        self.setLayout(layout)

    def _refresh_table(self):
        """Reload the table from settings."""
        tools = self._settings.tools
        self.table.setRowCount(len(tools))

        for row, tool in enumerate(tools):
            self.table.setItem(row, 0, QTableWidgetItem(f"T{tool.number}"))
            self.table.setItem(row, 1, QTableWidgetItem(tool.description))
            self.table.setItem(row, 2, QTableWidgetItem(f"{tool.diameter:.4f}\""))
            self.table.setItem(row, 3, QTableWidgetItem(f"{tool.length:.4f}\""))
            self.table.setItem(row, 4, QTableWidgetItem(tool.material))
            self.table.setItem(row, 5, QTableWidgetItem(str(tool.flutes) if tool.flutes else ""))
            self.table.setItem(row, 6, QTableWidgetItem(str(tool.max_rpm) if tool.max_rpm else ""))
            self.table.setItem(row, 7, QTableWidgetItem(f"{tool.max_feed:.1f}" if tool.max_feed else ""))

        self.count_label.setText(f"{len(tools)} tools")

    def _get_selected_tool(self) -> int:
        """Get selected tool number, or -1."""
        row = self.table.currentRow()
        if row < 0 or row >= len(self._settings.tools):
            return -1
        return self._settings.tools[row].number

    def _add_tool(self):
        # Default to next available number
        existing = {t.number for t in self._settings.tools}
        next_num = 1
        while next_num in existing:
            next_num += 1
        default = ToolEntry(number=next_num)

        dialog = ToolEditDialog(default, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            tool = dialog.get_tool()
            self._settings.add_tool(tool)
            self._refresh_table()

    def _edit_tool(self):
        num = self._get_selected_tool()
        if num < 0:
            QMessageBox.information(self, "Select Tool", "Select a tool to edit.")
            return
        tool = self._settings.get_tool(num)
        if not tool:
            return
        dialog = ToolEditDialog(tool, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_tool = dialog.get_tool()
            self._settings.add_tool(new_tool)
            self._refresh_table()

    def _delete_tool(self):
        num = self._get_selected_tool()
        if num < 0:
            QMessageBox.information(self, "Select Tool", "Select a tool to delete.")
            return
        result = QMessageBox.question(
            self, "Delete Tool",
            f"Delete Tool #{num}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if result == QMessageBox.StandardButton.Yes:
            self._settings.delete_tool(num)
            self._refresh_table()

    def _generate_table(self):
        """Generate and show T10xx table."""
        table_text = self._settings.generate_tool_table()
        if not table_text:
            QMessageBox.information(self, "No Tools", "Add tools first.")
            return
        self.preview.setPlainText(table_text)
        self.preview.setVisible(True)

    def _copy_table(self):
        """Copy T10xx table to clipboard."""
        table_text = self._settings.generate_tool_table()
        if not table_text:
            QMessageBox.information(self, "No Tools", "Add tools first.")
            return
        clipboard = QApplication.clipboard()
        clipboard.setText(table_text)
        QMessageBox.information(self, "Copied", "Tool table copied to clipboard.")
