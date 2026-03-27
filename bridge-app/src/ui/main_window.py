"""
CNC Bridge — Main Application Window

PyQt6-based GUI providing:
  - Connection panel (port selection, serial settings)
  - G-code file manager (load, view, validate)
  - DNC transfer controls (send, drip feed, pause, abort)
  - Real-time monitoring dashboard
  - Serial terminal / console
  - Connection test / handshake verification
  - Error logging with rotating files
  - Recent files menu, drag-and-drop, audible alerts
"""

import sys
import os
import time
import winsound
import logging
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QSplitter, QStatusBar, QMenuBar, QMenu, QToolBar,
    QLabel, QComboBox, QPushButton, QGroupBox, QFormLayout,
    QTextEdit, QPlainTextEdit, QProgressBar, QFileDialog,
    QSpinBox, QDoubleSpinBox, QCheckBox, QMessageBox, QFrame,
    QGridLayout, QSizePolicy, QLineEdit,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QAction, QIcon, QTextCursor

from ..core.serial_manager import (
    SerialManager, SerialConfig, ConnectionState, FlowControl, Parity
)
from ..core.dnc_sender import DNCEngine, SendMode, TransferState, TransferProgress
from ..core.gcode_parser import GCodeParser, GCodeValidator, Severity
from ..core.settings import AppSettings, ConnectionProfile
from ..core.traffic_logger import SerialTrafficLogger
from ..core.backup_vault import ProgramBackupVault
from ..core.update_checker import check_for_updates, UpdateInfo
from ..core.connection_tester import ConnectionTester
from ..core.macro_recorder import MacroRecorder, MacroPlayer, Macro
from ..core.program_library import ProgramLibrary, ProgramEntry
from ..core.comment_translator import translate_gcode, get_supported_languages
from .library_panel import LibraryPanel
from .gcode_editor import GCodeEditorPanel
from .backplotter import BackplotterPanel
from .tool_library import ToolLibraryPanel
from .file_diff import FileDiffPanel


class StatusIndicator(QFrame):
    """A colored circle indicator for status display."""
    
    COLORS = {
        "green": "#4CAF50",
        "red": "#F44336",
        "yellow": "#FFC107",
        "blue": "#2196F3",
        "gray": "#9E9E9E",
        "orange": "#FF9800",
    }

    def __init__(self, color: str = "gray", size: int = 14, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.set_color(color)

    def set_color(self, color: str):
        hex_color = self.COLORS.get(color, color)
        self.setStyleSheet(
            f"background-color: {hex_color}; border-radius: {self.width()//2}px; "
            f"border: 1px solid #555;"
        )


class ConnectionPanel(QGroupBox):
    """Serial port connection settings panel."""
    
    connect_requested = pyqtSignal(dict)
    disconnect_requested = pyqtSignal()
    refresh_ports = pyqtSignal()
    profile_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Connection", parent)
        self._profiles: list[ConnectionProfile] = []
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout()
        layout.setSpacing(4)

        # Profile selection
        profile_row = QHBoxLayout()
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(120)
        self.profile_combo.currentTextChanged.connect(self._on_profile_change)
        profile_row.addWidget(self.profile_combo)
        layout.addRow("Profile:", profile_row)

        # Port selection
        port_row = QHBoxLayout()
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(120)
        self.refresh_btn = QPushButton("⟳")
        self.refresh_btn.setFixedWidth(30)
        self.refresh_btn.setToolTip("Refresh port list")
        self.refresh_btn.clicked.connect(self.refresh_ports.emit)
        port_row.addWidget(self.port_combo)
        port_row.addWidget(self.refresh_btn)
        layout.addRow("Port:", port_row)

        # Baud rate
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("4800")
        layout.addRow("Baud:", self.baud_combo)

        # Data bits
        self.databits_combo = QComboBox()
        self.databits_combo.addItems(["7", "8"])
        self.databits_combo.setCurrentText("7")
        layout.addRow("Data bits:", self.databits_combo)

        # Parity
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["None", "Even", "Odd"])
        self.parity_combo.setCurrentText("Even")
        layout.addRow("Parity:", self.parity_combo)

        # Stop bits
        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems(["1", "1.5", "2"])
        self.stopbits_combo.setCurrentText("2")
        layout.addRow("Stop bits:", self.stopbits_combo)

        # Flow control
        self.flow_combo = QComboBox()
        self.flow_combo.addItems(["None", "XON/XOFF", "RTS/CTS", "DSR/DTR"])
        self.flow_combo.setCurrentText("XON/XOFF")
        layout.addRow("Flow ctrl:", self.flow_combo)

        # Connect / Disconnect buttons
        btn_row = QHBoxLayout()
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
        self.connect_btn.clicked.connect(self._on_connect)
        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.setStyleSheet("QPushButton { background-color: #F44336; color: white; }")
        self.disconnect_btn.clicked.connect(self.disconnect_requested.emit)
        btn_row.addWidget(self.connect_btn)
        btn_row.addWidget(self.disconnect_btn)
        layout.addRow(btn_row)

        # Status indicator
        status_row = QHBoxLayout()
        self.status_light = StatusIndicator("gray")
        self.status_label = QLabel("Disconnected")
        status_row.addWidget(self.status_light)
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        layout.addRow(status_row)

        self.setLayout(layout)

    def _on_connect(self):
        parity_map = {"None": "N", "Even": "E", "Odd": "O"}
        flow_map = {"None": "none", "XON/XOFF": "xon/xoff", "RTS/CTS": "rts/cts", "DSR/DTR": "dsr/dtr"}
        config = {
            "port": self.port_combo.currentText(),
            "baud_rate": int(self.baud_combo.currentText()),
            "data_bits": int(self.databits_combo.currentText()),
            "parity": parity_map.get(self.parity_combo.currentText(), "E"),
            "stop_bits": float(self.stopbits_combo.currentText()),
            "flow_control": flow_map.get(self.flow_combo.currentText(), "xon/xoff"),
        }
        self.connect_requested.emit(config)

    def set_ports(self, ports: list[dict]):
        self.port_combo.clear()
        for p in ports:
            label = f"{p['port']} — {p['description']}"
            self.port_combo.addItem(label, p['port'])

    def set_connected(self, connected: bool):
        self.connect_btn.setEnabled(not connected)
        self.disconnect_btn.setEnabled(connected)
        self.port_combo.setEnabled(not connected)
        self.baud_combo.setEnabled(not connected)
        self.databits_combo.setEnabled(not connected)
        self.parity_combo.setEnabled(not connected)
        self.stopbits_combo.setEnabled(not connected)
        self.flow_combo.setEnabled(not connected)
        if connected:
            self.status_light.set_color("green")
            self.status_label.setText("Connected")
        else:
            self.status_light.set_color("gray")
            self.status_label.setText("Disconnected")

    def set_profiles(self, profiles: list):
        """Load connection profiles into the profile combo."""
        self._profiles = profiles
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        self.profile_combo.addItem("(Custom)")
        for p in profiles:
            self.profile_combo.addItem(p.name)
        self.profile_combo.blockSignals(False)

    def _on_profile_change(self, name: str):
        """Apply selected profile settings."""
        for p in self._profiles:
            if p.name == name:
                self.baud_combo.setCurrentText(str(p.baud_rate))
                self.databits_combo.setCurrentText(str(p.data_bits))
                self.parity_combo.setCurrentText(p.parity)
                self.stopbits_combo.setCurrentText(str(p.stop_bits))
                self.flow_combo.setCurrentText(p.flow_control)
                self.profile_changed.emit(name)
                break

    def apply_settings(self, serial_settings):
        """Apply saved serial settings to combos."""
        if serial_settings.port:
            idx = self.port_combo.findData(serial_settings.port)
            if idx >= 0:
                self.port_combo.setCurrentIndex(idx)
        self.baud_combo.setCurrentText(str(serial_settings.baud_rate))
        self.databits_combo.setCurrentText(str(serial_settings.data_bits))
        self.parity_combo.setCurrentText(serial_settings.parity)
        self.stopbits_combo.setCurrentText(str(serial_settings.stop_bits))
        self.flow_combo.setCurrentText(serial_settings.flow_control)


class MonitorPanel(QGroupBox):
    """Real-time monitoring dashboard."""

    def __init__(self, parent=None):
        super().__init__("Controller Monitor", parent)
        self._build_ui()

    def _build_ui(self):
        layout = QGridLayout()
        layout.setSpacing(6)

        # --- Connection Status ---
        row = 0
        layout.addWidget(QLabel("Connection:"), row, 0)
        self.conn_indicator = StatusIndicator("gray")
        self.conn_label = QLabel("Disconnected")
        layout.addWidget(self.conn_indicator, row, 1)
        layout.addWidget(self.conn_label, row, 2)

        # --- Serial Signal Lines ---
        row += 1
        layout.addWidget(self._make_separator(), row, 0, 1, 3)

        row += 1
        layout.addWidget(QLabel("Signal Lines:"), row, 0, 1, 3)
        
        self.signal_indicators = {}
        for i, signal_name in enumerate(["CTS", "DSR", "RTS", "DTR"]):
            r = row + 1 + i // 2
            c = (i % 2) * 2
            ind = StatusIndicator("gray", 10)
            lbl = QLabel(signal_name)
            layout.addWidget(ind, r, c)
            layout.addWidget(lbl, r, c + 1)
            self.signal_indicators[signal_name.lower()] = ind

        # --- Flow Control ---
        row += 3
        layout.addWidget(self._make_separator(), row, 0, 1, 3)

        row += 1
        layout.addWidget(QLabel("Flow Control:"), row, 0)
        self.flow_indicator = StatusIndicator("green")
        self.flow_label = QLabel("XON (Ready)")
        layout.addWidget(self.flow_indicator, row, 1)
        layout.addWidget(self.flow_label, row, 2)

        # --- Transfer Stats ---
        row += 1
        layout.addWidget(self._make_separator(), row, 0, 1, 3)

        row += 1
        layout.addWidget(QLabel("Transfer:"), row, 0, 1, 3)

        stats_labels = [
            ("Bytes Sent:", "bytes_sent"),
            ("Bytes Recv:", "bytes_recv"),
            ("Lines Sent:", "lines_sent"),
            ("Lines Recv:", "lines_recv"),
            ("XON count:", "xon_count"),
            ("XOFF count:", "xoff_count"),
            ("Errors:", "errors"),
            ("Uptime:", "uptime"),
        ]
        self.stat_values = {}
        for label_text, key in stats_labels:
            row += 1
            layout.addWidget(QLabel(label_text), row, 0)
            val = QLabel("0")
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            val.setFont(QFont("Consolas", 9))
            layout.addWidget(val, row, 1, 1, 2)
            self.stat_values[key] = val

        layout.setRowStretch(row + 1, 1)
        self.setLayout(layout)

    def _make_separator(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        return sep

    def update_connection(self, state: ConnectionState):
        color_map = {
            ConnectionState.DISCONNECTED: ("gray", "Disconnected"),
            ConnectionState.CONNECTING: ("yellow", "Connecting..."),
            ConnectionState.CONNECTED: ("green", "Connected"),
            ConnectionState.ERROR: ("red", "Error"),
        }
        color, text = color_map.get(state, ("gray", "Unknown"))
        self.conn_indicator.set_color(color)
        self.conn_label.setText(text)

    def update_signals(self, signals: dict):
        for name, indicator in self.signal_indicators.items():
            indicator.set_color("green" if signals.get(name, False) else "gray")

    def update_flow(self, is_xon: bool):
        if is_xon:
            self.flow_indicator.set_color("green")
            self.flow_label.setText("XON (Ready)")
        else:
            self.flow_indicator.set_color("red")
            self.flow_label.setText("XOFF (Busy)")

    def update_stats(self, stats):
        self.stat_values["bytes_sent"].setText(f"{stats.bytes_sent:,}")
        self.stat_values["bytes_recv"].setText(f"{stats.bytes_received:,}")
        self.stat_values["lines_sent"].setText(f"{stats.lines_sent:,}")
        self.stat_values["lines_recv"].setText(f"{stats.lines_received:,}")
        self.stat_values["xon_count"].setText(f"{stats.xon_count:,}")
        self.stat_values["xoff_count"].setText(f"{stats.xoff_count:,}")
        self.stat_values["errors"].setText(f"{stats.errors}")
        uptime = stats.uptime
        if uptime > 0:
            hrs = int(uptime // 3600)
            mins = int((uptime % 3600) // 60)
            secs = int(uptime % 60)
            self.stat_values["uptime"].setText(f"{hrs:02d}:{mins:02d}:{secs:02d}")
        else:
            self.stat_values["uptime"].setText("--:--:--")


class TransferPanel(QGroupBox):
    """DNC transfer controls and progress."""

    send_file = pyqtSignal(str, str)  # filepath, mode
    pause_transfer = pyqtSignal()
    resume_transfer = pyqtSignal()
    abort_transfer = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("DNC Transfer", parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(6)

        # File selection
        file_row = QHBoxLayout()
        self.file_label = QLabel("No file loaded")
        self.file_label.setStyleSheet("color: #888;")
        self.load_btn = QPushButton("Load File")
        self.load_btn.clicked.connect(self._load_file)
        file_row.addWidget(self.file_label, 1)
        file_row.addWidget(self.load_btn)
        layout.addLayout(file_row)

        # Mode selection
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Upload", "Drip Feed"])
        self.mode_combo.setCurrentText("Upload")
        mode_row.addWidget(self.mode_combo)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # Control buttons
        ctrl_row = QHBoxLayout()
        self.send_btn = QPushButton("▶ Send")
        self.send_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 6px; }")
        self.send_btn.clicked.connect(self._on_send)
        
        self.pause_btn = QPushButton("⏸ Pause")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._on_pause_resume)
        
        self.abort_btn = QPushButton("⏹ Abort")
        self.abort_btn.setEnabled(False)
        self.abort_btn.setStyleSheet("QPushButton { background-color: #F44336; color: white; }")
        self.abort_btn.clicked.connect(self.abort_transfer.emit)
        
        ctrl_row.addWidget(self.send_btn)
        ctrl_row.addWidget(self.pause_btn)
        ctrl_row.addWidget(self.abort_btn)
        layout.addLayout(ctrl_row)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # Progress details
        detail_layout = QGridLayout()
        self.prog_labels = {}
        details = [
            ("Status:", "status"), ("Line:", "line"),
            ("Speed:", "speed"), ("ETA:", "eta"),
            ("Current:", "current"),
        ]
        for i, (label, key) in enumerate(details):
            r, c = divmod(i, 2)
            detail_layout.addWidget(QLabel(label), r, c * 2)
            val = QLabel("—")
            val.setFont(QFont("Consolas", 9))
            detail_layout.addWidget(val, r, c * 2 + 1)
            self.prog_labels[key] = val
        layout.addLayout(detail_layout)

        self._filepath = ""
        self._is_paused = False
        self.setLayout(layout)

    def _load_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open G-code File", "",
            "G-code Files (*.txt *.nc *.ngc *.gcode *.tap);;All Files (*)"
        )
        if filepath:
            self._filepath = filepath
            name = Path(filepath).name
            self.file_label.setText(name)
            self.file_label.setStyleSheet("color: white;")

    def _on_send(self):
        if self._filepath:
            mode = "drip_feed" if self.mode_combo.currentText() == "Drip Feed" else "upload"
            self.send_file.emit(self._filepath, mode)
        else:
            QMessageBox.warning(self, "No File", "Please load a G-code file first.")

    def _on_pause_resume(self):
        if self._is_paused:
            self.resume_transfer.emit()
            self.pause_btn.setText("⏸ Pause")
            self._is_paused = False
        else:
            self.pause_transfer.emit()
            self.pause_btn.setText("▶ Resume")
            self._is_paused = True

    def update_progress(self, progress: TransferProgress):
        self.progress_bar.setValue(int(progress.percent_complete))
        self.prog_labels["status"].setText(progress.state.value.upper())
        self.prog_labels["line"].setText(f"{progress.current_line}/{progress.total_lines}")
        self.prog_labels["speed"].setText(f"{progress.lines_per_second:.1f} ln/s")
        
        if progress.estimated_remaining > 0:
            eta_min = int(progress.estimated_remaining // 60)
            eta_sec = int(progress.estimated_remaining % 60)
            self.prog_labels["eta"].setText(f"{eta_min:02d}:{eta_sec:02d}")
        else:
            self.prog_labels["eta"].setText("—")

        current = progress.current_gcode
        if len(current) > 40:
            current = current[:40] + "..."
        self.prog_labels["current"].setText(current or "—")

        is_active = progress.state in (TransferState.SENDING, TransferState.PAUSED)
        self.send_btn.setEnabled(not is_active)
        self.pause_btn.setEnabled(is_active)
        self.abort_btn.setEnabled(is_active)
        self.load_btn.setEnabled(not is_active)


class SerialTerminal(QGroupBox):
    """Serial terminal for direct communication with the controller."""

    send_command = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Serial Terminal", parent)
        self._macro_recorder = MacroRecorder()
        self._macro_player = MacroPlayer()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()

        # Terminal output
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Consolas", 10))
        self.output.setMaximumBlockCount(5000)
        self.output.setStyleSheet(
            "QPlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; }"
        )
        layout.addWidget(self.output)

        # Input row
        input_row = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setFont(QFont("Consolas", 10))
        self.input_field.setPlaceholderText("Enter command (G-code or text)...")
        self.input_field.returnPressed.connect(self._on_send)
        
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._on_send)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.output.clear)
        
        input_row.addWidget(self.input_field, 1)
        input_row.addWidget(self.send_btn)
        input_row.addWidget(self.clear_btn)
        layout.addLayout(input_row)

        # Macro row
        macro_row = QHBoxLayout()
        macro_row.addWidget(QLabel("Macros:"))

        self.macro_record_btn = QPushButton("⏺ Record")
        self.macro_record_btn.setToolTip("Start recording terminal commands as a macro")
        self.macro_record_btn.clicked.connect(self._on_macro_record)

        self.macro_stop_btn = QPushButton("⏹ Stop")
        self.macro_stop_btn.setToolTip("Stop recording the current macro")
        self.macro_stop_btn.setEnabled(False)
        self.macro_stop_btn.clicked.connect(self._on_macro_stop)

        self.macro_play_btn = QPushButton("▶ Play")
        self.macro_play_btn.setToolTip("Play a saved macro")
        self.macro_play_btn.clicked.connect(self._on_macro_play)

        self.macro_combo = QComboBox()
        self.macro_combo.setMinimumWidth(140)
        self.macro_combo.setToolTip("Select a macro to play")
        self._refresh_macros()

        macro_row.addWidget(self.macro_record_btn)
        macro_row.addWidget(self.macro_stop_btn)
        macro_row.addWidget(self.macro_combo, 1)
        macro_row.addWidget(self.macro_play_btn)
        layout.addLayout(macro_row)

        self.setLayout(layout)

    def _on_send(self):
        text = self.input_field.text().strip()
        if text:
            self.append_text(f">>> {text}", "#569CD6")
            self.send_command.emit(text)
            # Record macro step if recording
            if self._macro_recorder.is_recording:
                self._macro_recorder.record_command(text)
            self.input_field.clear()

    def _refresh_macros(self):
        """Reload available macros into the combo box."""
        self.macro_combo.clear()
        macros = Macro.list_macros()
        if macros:
            for name in macros:
                self.macro_combo.addItem(name)
        else:
            self.macro_combo.addItem("(no macros)")

    def _on_macro_record(self):
        """Start recording terminal commands as a macro."""
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(
            self, "Record Macro", "Macro name:",
        )
        if ok and name.strip():
            self._macro_recorder.start(name.strip())
            self.macro_record_btn.setEnabled(False)
            self.macro_record_btn.setText("⏺ Recording...")
            self.macro_record_btn.setStyleSheet("QPushButton { color: #F44336; font-weight: bold; }")
            self.macro_stop_btn.setEnabled(True)
            self.append_info(f"Recording macro: {name.strip()}")

    def _on_macro_stop(self):
        """Stop recording and save the macro."""
        macro = self._macro_recorder.stop()
        if macro and macro.steps:
            macro.save()
            self.append_info(f"Macro saved: {macro.name} ({len(macro.steps)} steps)")
            self._refresh_macros()
            self.macro_combo.setCurrentText(macro.name)
        else:
            self.append_info("Macro discarded (no commands recorded)")
        self.macro_record_btn.setEnabled(True)
        self.macro_record_btn.setText("⏺ Record")
        self.macro_record_btn.setStyleSheet("")
        self.macro_stop_btn.setEnabled(False)

    def _on_macro_play(self):
        """Play the selected macro."""
        name = self.macro_combo.currentText()
        if not name or name == "(no macros)":
            return
        macro = Macro.load(name)
        if not macro:
            self.append_error(f"Macro not found: {name}")
            return

        self.append_info(f"Playing macro: {name} ({len(macro.steps)} steps)")
        self.macro_play_btn.setEnabled(False)
        total_steps = len(macro.steps)

        def send_fn(cmd):
            self.append_text(f">>> {cmd}", "#569CD6")
            self.send_command.emit(cmd)

        def on_step(step_idx, cmd):
            self.append_info(f"  Step {step_idx + 1}/{total_steps}: {cmd}")

        def on_done():
            self.append_info(f"Macro complete: {name}")

        import threading
        def run():
            self._macro_player.play(
                macro, send_callback=send_fn,
                on_step=lambda i, c: QTimer.singleShot(0, lambda: on_step(i, c)),
            )
            QTimer.singleShot(0, on_done)
            QTimer.singleShot(0, lambda: self.macro_play_btn.setEnabled(True))

        threading.Thread(target=run, daemon=True).start()

    def append_text(self, text: str, color: str = "#d4d4d4"):
        self.output.appendHtml(f'<span style="color: {color};">{text}</span>')

    def append_received(self, text: str):
        self.append_text(f"<<< {text}", "#6A9955")

    def append_error(self, text: str):
        self.append_text(f"[ERROR] {text}", "#F44336")

    def append_info(self, text: str):
        self.append_text(f"[INFO] {text}", "#FFC107")


class GCodeViewerPanel(QGroupBox):
    """G-code file viewer with validation results."""

    def __init__(self, parent=None):
        super().__init__("G-code Viewer", parent)
        self._build_ui()
        self.validator = GCodeValidator()

    def _build_ui(self):
        layout = QVBoxLayout()

        # Toolbar
        toolbar = QHBoxLayout()
        self.load_btn = QPushButton("Open File")
        self.load_btn.clicked.connect(self._load_file)
        self.validate_btn = QPushButton("Validate")
        self.validate_btn.clicked.connect(self._validate)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear)
        self.stats_label = QLabel("")
        toolbar.addWidget(self.load_btn)
        toolbar.addWidget(self.validate_btn)
        toolbar.addWidget(self.clear_btn)
        toolbar.addWidget(self.stats_label, 1)
        layout.addLayout(toolbar)

        # Splitter: code view | validation output
        splitter = QSplitter(Qt.Orientation.Vertical)

        self.code_view = QPlainTextEdit()
        self.code_view.setReadOnly(True)
        self.code_view.setFont(QFont("Consolas", 10))
        self.code_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.code_view.setStyleSheet(
            "QPlainTextEdit { background-color: #1e1e1e; color: #d4d4d4; }"
        )
        splitter.addWidget(self.code_view)

        self.validation_output = QPlainTextEdit()
        self.validation_output.setReadOnly(True)
        self.validation_output.setFont(QFont("Consolas", 9))
        self.validation_output.setMaximumBlockCount(1000)
        self.validation_output.setStyleSheet(
            "QPlainTextEdit { background-color: #252526; color: #d4d4d4; }"
        )
        splitter.addWidget(self.validation_output)
        splitter.setSizes([400, 150])

        layout.addWidget(splitter)
        self._current_file = ""
        self._current_text = ""
        self.setLayout(layout)

    def _load_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open G-code File", "",
            "G-code Files (*.txt *.nc *.ngc *.gcode *.tap);;All Files (*)"
        )
        if filepath:
            self.load_file(filepath)

    def load_file(self, filepath: str):
        try:
            with open(filepath, 'r', encoding='ascii', errors='replace') as f:
                self._current_text = f.read()
            self._current_file = filepath
            self.code_view.setPlainText(self._current_text)
            name = Path(filepath).name
            lines = self._current_text.count('\n') + 1
            self.stats_label.setText(f"{name} — {lines} lines")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {e}")

    def _validate(self):
        if not self._current_text:
            QMessageBox.information(self, "No File", "Load a G-code file first.")
            return
        issues, stats = self.validator.validate_text(self._current_text)
        summary = self.validator.get_summary()
        self.validation_output.setPlainText(summary)
        self._highlight_issues(issues)
        self._highlight_validation_output()

    def _clear(self):
        """Clear the viewer display."""
        self.code_view.clear()
        self.validation_output.clear()
        self._current_text = ""
        self._current_file = ""
        self.stats_label.setText("")

    def _highlight_issues(self, issues):
        """Color-code lines in the code view that have validation issues."""
        if not issues:
            return
        # Build a map: line_number → worst severity
        line_severity: dict[int, Severity] = {}
        for issue in issues:
            ln = issue.line_number
            if ln not in line_severity or issue.severity.value > line_severity[ln].value:
                line_severity[ln] = issue.severity

        # Build tooltip map: line_number → list of messages
        line_tips: dict[int, list[str]] = {}
        for issue in issues:
            ln = issue.line_number
            prefix = "ERROR" if issue.severity == Severity.ERROR else "WARN"
            line_tips.setdefault(ln, []).append(f"[{prefix}] {issue.code}: {issue.message}")

        # Apply background highlights to affected lines
        doc = self.code_view.document()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()

        for line_num, severity in line_severity.items():
            block = doc.findBlockByNumber(line_num - 1)  # 0-indexed blocks
            if not block.isValid():
                continue

            fmt = QTextCharFormat()
            if severity == Severity.ERROR:
                fmt.setBackground(QColor("#3a1e1e"))       # red tint
                fmt.setForeground(QColor("#F44336"))
            elif severity == Severity.WARNING:
                fmt.setBackground(QColor("#3a3a1e"))       # yellow tint
                fmt.setForeground(QColor("#DCDCAA"))
            else:
                fmt.setBackground(QColor("#1e2a3a"))       # blue tint
                fmt.setForeground(QColor("#569CD6"))

            # Build tooltip
            tip = "\n".join(line_tips.get(line_num, []))
            fmt.setToolTip(tip)

            # Select entire block and apply format
            cursor.setPosition(block.position())
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
            cursor.setCharFormat(fmt)

        cursor.endEditBlock()

    def _highlight_validation_output(self):
        """Color-code [ERROR] and [WARN] lines in the validation output pane."""
        doc = self.validation_output.document()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()

        block = doc.begin()
        while block.isValid():
            text = block.text()
            fmt = QTextCharFormat()

            if text.strip().startswith("[ERROR]"):
                fmt.setBackground(QColor("#3a1e1e"))
                fmt.setForeground(QColor("#F44336"))
            elif text.strip().startswith("[WARN]"):
                fmt.setBackground(QColor("#3a3a1e"))
                fmt.setForeground(QColor("#DCDCAA"))
            else:
                block = block.next()
                continue

            cursor.setPosition(block.position())
            cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock,
                                QTextCursor.MoveMode.KeepAnchor)
            cursor.setCharFormat(fmt)
            block = block.next()

        cursor.endEditBlock()

    def get_text(self) -> str:
        return self._current_text


class MainWindow(QMainWindow):
    """CNC Bridge main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CNC Bridge — Anilam Crusader M")
        self.setMinimumSize(1200, 800)

        # Settings persistence
        self.settings = AppSettings()

        # Core objects
        self.serial_mgr = SerialManager()
        self.dnc_engine = DNCEngine(self.serial_mgr)
        self.traffic_logger = SerialTrafficLogger()
        self.traffic_logger.enabled = self.settings.transfer.log_serial_traffic
        self.backup_vault = ProgramBackupVault()
        self.backup_vault.enabled = self.settings.transfer.auto_backup

        # Build UI
        self._build_menu()
        self._build_ui()
        self._setup_timers()
        self._connect_signals()

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Connection tester
        self.conn_tester = ConnectionTester(self.serial_mgr)

        # Program library
        self.program_library = ProgramLibrary()

        # Theme state
        self._current_theme = "dark"

        # Auto-reconnect state
        self._auto_reconnect = True
        self._reconnect_timer = QTimer()
        self._reconnect_timer.setInterval(5000)
        self._reconnect_timer.timeout.connect(self._attempt_reconnect)
        self._last_config = None

        # Load saved settings
        self._apply_saved_settings()

        # Initial port scan
        self._refresh_ports()

        # Apply dark theme
        self._current_theme = self.settings.window.theme or "dark"
        self._apply_theme()

        # Apply touch mode if saved
        if self.settings.window.touch_mode:
            self.touch_mode_action.setChecked(True)
            self._apply_touch_mode(True)

        # Update theme checkmarks
        self.dark_theme_action.setChecked(self._current_theme == "dark")
        self.light_theme_action.setChecked(self._current_theme == "light")

        # Check for updates (background)
        self._check_updates()

    def _build_menu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        open_action = QAction("&Open G-code...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        new_action = QAction("&New G-code", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_editor)
        file_menu.addAction(new_action)

        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_editor)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        # Recent files submenu
        self.recent_menu = file_menu.addMenu("Recent &Files")
        self._update_recent_menu()

        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        find_action = QAction("&Find / Replace", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self._toggle_find)
        edit_menu.addAction(find_action)

        renumber_action = QAction("&Renumber N-lines...", self)
        renumber_action.triggered.connect(self._renumber_lines)
        edit_menu.addAction(renumber_action)

        # Insert menu (G-code snippet templates)
        insert_menu = menubar.addMenu("&Insert")
        snippets = [
            ("Program &Header (Anilam)", "%\n(PROGRAM NAME)\n(DATE: )\n(TOOL: T1 - )\nG70 G90 G40 G80\n"),
            ("Program &Footer", "M5\nM9\nG28\nM30\n%\n"),
            ("Tool &Change Block", "M5\nM9\nT____ M6\n(TOOL: )\nG43 H__ Z1.0\nM3 S____\nM8\n"),
            ("&Drill Cycle (G81)", "G81 X____ Y____ Z____ R0.1 F____\nG80\n"),
            ("&Peck Drill (G83)", "G83 X____ Y____ Z____ R0.1 Q0.1 F____\nG80\n"),
            ("&Subroutine Shell", "N9000 G29\n(SUBROUTINE)\n\nM2\n"),
            ("Safe &Start Line", "G70 G90 G40 G80 G17\n"),
            ("Coolant &On/Off", "M8 (FLOOD COOLANT ON)\n(... machining ...)\nM9 (COOLANT OFF)\n"),
        ]
        for name, code in snippets:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, c=code: self._insert_snippet(c))
            insert_menu.addAction(action)

        # Connection menu
        conn_menu = menubar.addMenu("&Connection")
        self.connect_action = QAction("&Connect", self)
        self.connect_action.triggered.connect(lambda: self.conn_panel._on_connect())
        conn_menu.addAction(self.connect_action)
        self.disconnect_action = QAction("&Disconnect", self)
        self.disconnect_action.triggered.connect(self._disconnect)
        conn_menu.addAction(self.disconnect_action)
        conn_menu.addSeparator()
        refresh_action = QAction("&Refresh Ports", self)
        refresh_action.triggered.connect(self._refresh_ports)
        conn_menu.addAction(refresh_action)

        test_action = QAction("&Test Connection...", self)
        test_action.triggered.connect(self._test_connection)
        conn_menu.addAction(test_action)

        # Transfer menu
        xfer_menu = menubar.addMenu("&Transfer")
        send_action = QAction("&Send File...", self)
        send_action.triggered.connect(lambda: self.transfer_panel._on_send())
        xfer_menu.addAction(send_action)
        xfer_menu.addSeparator()
        receive_action = QAction("&Receive from Controller", self)
        receive_action.triggered.connect(self._receive_program)
        xfer_menu.addAction(receive_action)

        xfer_menu.addSeparator()
        verify_action = QAction("Send-Receive-&Verify", self)
        verify_action.triggered.connect(self._send_receive_verify)
        xfer_menu.addAction(verify_action)

        # View menu
        view_menu = menubar.addMenu("&View")
        tabs_info = [
            ("G-code &Viewer", 0), ("G-code &Editor", 1),
            ("&Backplotter", 2), ("&Serial Terminal", 3),
            ("&Tool Library", 4), ("File &Diff", 5),
            ("Reference &Library", 6),
        ]
        for name, idx in tabs_info:
            action = QAction(name, self)
            action.triggered.connect(lambda checked, i=idx: self.tabs.setCurrentIndex(i))
            view_menu.addAction(action)

        view_menu.addSeparator()

        # Theme toggle
        theme_menu = view_menu.addMenu("&Theme")
        self.dark_theme_action = QAction("&Dark Theme", self)
        self.dark_theme_action.setCheckable(True)
        self.dark_theme_action.setChecked(True)
        self.dark_theme_action.triggered.connect(lambda: self._set_theme("dark"))
        theme_menu.addAction(self.dark_theme_action)

        self.light_theme_action = QAction("&Light Theme", self)
        self.light_theme_action.setCheckable(True)
        self.light_theme_action.triggered.connect(lambda: self._set_theme("light"))
        theme_menu.addAction(self.light_theme_action)

        view_menu.addSeparator()

        # Touch-screen mode
        self.touch_mode_action = QAction("Touch-Screen &Mode", self)
        self.touch_mode_action.setCheckable(True)
        self.touch_mode_action.triggered.connect(self._toggle_touch_mode)
        view_menu.addAction(self.touch_mode_action)

        # Tools menu
        tools_menu = menubar.addMenu("Too&ls")
        diff_action = QAction("Compare &Files...", self)
        diff_action.triggered.connect(lambda: self.tabs.setCurrentIndex(5))
        tools_menu.addAction(diff_action)

        backplot_action = QAction("&Backplot Current File", self)
        backplot_action.triggered.connect(self._backplot_current)
        tools_menu.addAction(backplot_action)

        tools_menu.addSeparator()

        translate_menu = tools_menu.addMenu("Translate &Comments")
        translate_es = QAction("English → Español", self)
        translate_es.triggered.connect(lambda: self._translate_comments("es"))
        translate_menu.addAction(translate_es)
        translate_en = QAction("Español → English", self)
        translate_en.triggered.connect(lambda: self._translate_comments("en"))
        translate_menu.addAction(translate_en)

        tools_menu.addSeparator()

        prog_lib_action = QAction("&Program Library...", self)
        prog_lib_action.triggered.connect(self._show_program_library)
        tools_menu.addAction(prog_lib_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")
        library_action = QAction("Reference &Library", self)
        library_action.setShortcut("F1")
        library_action.triggered.connect(self._show_library)
        help_menu.addAction(library_action)
        help_menu.addSeparator()
        update_action = QAction("Check for &Updates", self)
        update_action.triggered.connect(lambda: self._check_updates(manual=True))
        help_menu.addAction(update_action)
        bug_action = QAction("Report a &Bug...", self)
        bug_action.triggered.connect(lambda: __import__('webbrowser').open("https://github.com/Apocscode/CNC-Bridge/issues"))
        help_menu.addAction(bug_action)
        help_menu.addSeparator()
        about_action = QAction("&About CNC Bridge", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    def _build_ui(self):
        central = QWidget()
        main_layout = QHBoxLayout()
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(6, 6, 6, 6)

        # --- Left sidebar: Connection + Monitor ---
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setSpacing(6)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.conn_panel = ConnectionPanel()
        left_layout.addWidget(self.conn_panel)

        self.monitor_panel = MonitorPanel()
        left_layout.addWidget(self.monitor_panel)

        left_layout.addStretch()
        left_panel.setLayout(left_layout)
        left_panel.setFixedWidth(280)

        # --- Center: Tabs (G-code Viewer, Terminal) ---
        self.tabs = QTabWidget()

        self.gcode_viewer = GCodeViewerPanel()
        self.tabs.addTab(self.gcode_viewer, "G-code Viewer")

        self.gcode_editor = GCodeEditorPanel()
        self.tabs.addTab(self.gcode_editor, "G-code Editor")

        self.backplotter = BackplotterPanel()
        self.tabs.addTab(self.backplotter, "Backplotter")

        self.terminal = SerialTerminal()
        self.tabs.addTab(self.terminal, "Serial Terminal")

        self.tool_library = ToolLibraryPanel(self.settings)
        self.tabs.addTab(self.tool_library, "Tool Library")

        self.file_diff = FileDiffPanel()
        self.tabs.addTab(self.file_diff, "File Diff")

        self.library_panel = LibraryPanel()
        self.tabs.addTab(self.library_panel, "Reference Library")

        # --- Right sidebar: Transfer ---
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setSpacing(6)
        right_layout.setContentsMargins(0, 0, 0, 0)

        self.transfer_panel = TransferPanel()
        right_layout.addWidget(self.transfer_panel)

        right_layout.addStretch()
        right_panel.setLayout(right_layout)
        right_panel.setFixedWidth(320)

        # Assemble
        main_layout.addWidget(left_panel)
        main_layout.addWidget(self.tabs, 1)
        main_layout.addWidget(right_panel)

        central.setLayout(main_layout)
        self.setCentralWidget(central)

        # Status bar
        self.statusBar().showMessage("CNC Bridge — Ready")

    def _setup_timers(self):
        # Poll serial stats every 500ms
        self.stats_timer = QTimer()
        self.stats_timer.timeout.connect(self._update_monitor)
        self.stats_timer.start(500)

    def _connect_signals(self):
        # Connection panel
        self.conn_panel.connect_requested.connect(self._connect)
        self.conn_panel.disconnect_requested.connect(self._disconnect)
        self.conn_panel.refresh_ports.connect(self._refresh_ports)

        # Transfer panel
        self.transfer_panel.send_file.connect(self._send_file)
        self.transfer_panel.pause_transfer.connect(self.dnc_engine.pause)
        self.transfer_panel.resume_transfer.connect(self.dnc_engine.resume)
        self.transfer_panel.abort_transfer.connect(self.dnc_engine.abort)

        # Terminal
        self.terminal.send_command.connect(self._send_terminal_command)

        # Serial callbacks (thread-safe via QTimer poll)
        self.serial_mgr.on_line_received(self._on_serial_line)
        self.serial_mgr.on_state_changed(self._on_connection_state)
        self.serial_mgr.on_error(self._on_serial_error)
        self.serial_mgr.on_flow_control(self._on_flow_control)

        # DNC callbacks
        self.dnc_engine.on_progress(self._on_transfer_progress)
        self.dnc_engine.on_complete(self._on_transfer_complete)
        self.dnc_engine.on_error(self._on_transfer_error)

        # Editor file-modified: auto-backplot
        self.gcode_editor.file_modified.connect(self._on_editor_saved)

        # Editor send-to-controller
        self.gcode_editor.send_requested.connect(self._send_editor_text)

    # --- Actions ---

    def _refresh_ports(self):
        ports = SerialManager.list_ports()
        self.conn_panel.set_ports(ports)

    def _connect(self, config_dict: dict):
        config = SerialConfig.from_dict(config_dict)
        # Extract actual port from combo data
        port_data = self.conn_panel.port_combo.currentData()
        if port_data:
            config.port = port_data
        if self.serial_mgr.connect(config):
            self._last_config = config_dict  # Save for auto-reconnect
            self._reconnect_timer.stop()
            self.conn_panel.set_connected(True)
            self.terminal.append_info(f"Connected to {config.port} at {config.baud_rate} baud")
            self.statusBar().showMessage(f"Connected: {config.port}")

            # Start traffic logging
            self.traffic_logger.start_session(config.port, config.baud_rate)
            self.traffic_logger.log_event(f"Connected: {config.port} @ {config.baud_rate} baud")

            # Save last-used serial settings
            self.settings.serial.port = config.port
            self.settings.serial.baud_rate = config.baud_rate
            self.settings.save()
        else:
            QMessageBox.critical(self, "Connection Failed",
                                 f"Could not connect to {config.port}")

    def _disconnect(self):
        self.traffic_logger.log_event("Disconnecting")
        self.traffic_logger.stop_session()
        self.serial_mgr.disconnect()
        self.conn_panel.set_connected(False)
        self.terminal.append_info("Disconnected")
        self.statusBar().showMessage("Disconnected")

    def _open_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open G-code File", "",
            "G-code Files (*.txt *.nc *.ngc *.gcode *.tap);;All Files (*)"
        )
        if filepath:
            self.settings.add_recent_file(filepath)
            self._update_recent_menu()
            current = self.tabs.currentWidget()
            if current == self.gcode_editor:
                self.gcode_editor.load_file(filepath)
            elif current == self.backplotter:
                self.backplotter.load_file(filepath)
            else:
                self.gcode_viewer.load_file(filepath)
                self.tabs.setCurrentWidget(self.gcode_viewer)

    def _send_file(self, filepath: str, mode: str):
        if not self.serial_mgr.is_connected:
            QMessageBox.warning(self, "Not Connected",
                                "Connect to a serial port first.")
            return

        # Backup before sending
        port = self.serial_mgr.config.port if self.serial_mgr.config else ""
        self.backup_vault.backup_file(filepath, direction="sent", port=port)
        self.traffic_logger.log_event(f"Sending file: {Path(filepath).name} ({mode})")

        # Track recent files
        self.settings.add_recent_file(filepath)

        send_mode = SendMode.DRIP_FEED if mode == "drip_feed" else SendMode.UPLOAD
        if self.dnc_engine.load_file(filepath):
            self.dnc_engine.send(send_mode)
            self.terminal.append_info(f"Sending {Path(filepath).name} ({mode})")

    def _send_editor_text(self, text: str):
        """Send the current editor content directly to the controller."""
        if not self.serial_mgr.is_connected:
            QMessageBox.warning(self, "Not Connected",
                                "Connect to a serial port first.")
            return

        lines = text.splitlines()
        name = Path(self.gcode_editor.filepath).name if self.gcode_editor.filepath else "Editor"
        self.dnc_engine.load_lines(lines, name)
        self.dnc_engine.send(SendMode.UPLOAD)
        self.terminal.append_info(f"Sending from editor: {name} ({len(lines)} lines)")
        self.tabs.setCurrentWidget(self.terminal)

    def _receive_program(self):
        if not self.serial_mgr.is_connected:
            QMessageBox.warning(self, "Not Connected",
                                "Connect to a serial port first.")
            return
        self.terminal.append_info("Waiting to receive program from controller...")
        # Run in thread to avoid blocking GUI
        import threading
        def receive_thread():
            lines = self.dnc_engine.receive_program(timeout=60)
            if lines:
                text = '\n'.join(lines)
                # Save to file
                filepath, _ = QFileDialog.getSaveFileName(
                    self, "Save Received Program", "",
                    "G-code Files (*.txt);;All Files (*)"
                )
                if filepath:
                    with open(filepath, 'w') as f:
                        f.write(text)
        threading.Thread(target=receive_thread, daemon=True).start()

    def _send_terminal_command(self, command: str):
        if self.serial_mgr.is_connected:
            self.serial_mgr.send_line(command)
            self.traffic_logger.log_tx(command)
        else:
            self.terminal.append_error("Not connected")

    # --- Callbacks (may be called from background threads) ---

    def _on_serial_line(self, line: str):
        # Thread-safe: use QTimer.singleShot to update GUI
        QTimer.singleShot(0, lambda: self.terminal.append_received(line))
        self.traffic_logger.log_rx(line)

    def _on_connection_state(self, state: ConnectionState):
        QTimer.singleShot(0, lambda: self.monitor_panel.update_connection(state))

    def _on_serial_error(self, message: str):
        QTimer.singleShot(0, lambda: self.terminal.append_error(message))
        QTimer.singleShot(0, lambda: self.statusBar().showMessage(f"Error: {message}"))
        logging.getLogger("CNCBridge").error(f"Serial error: {message}")
        # Start auto-reconnect if enabled
        if self._auto_reconnect and self._last_config and not self._reconnect_timer.isActive():
            QTimer.singleShot(0, lambda: self.terminal.append_info(
                "Auto-reconnect will attempt in 5 seconds..."
            ))
            self._reconnect_timer.start()

    def _on_flow_control(self, is_xon: bool):
        QTimer.singleShot(0, lambda: self.monitor_panel.update_flow(is_xon))

    def _on_transfer_progress(self, progress: TransferProgress):
        QTimer.singleShot(0, lambda: self.transfer_panel.update_progress(progress))

    def _on_transfer_complete(self, progress: TransferProgress):
        QTimer.singleShot(0, lambda: self.terminal.append_info(
            f"Transfer complete: {progress.current_line} lines in {progress.elapsed_time:.1f}s"
        ))
        # Audible alert — success (two ascending beeps)
        try:
            winsound.Beep(800, 200)
            winsound.Beep(1200, 300)
        except Exception:
            pass

    def _on_transfer_error(self, message: str):
        QTimer.singleShot(0, lambda: self.terminal.append_error(f"Transfer error: {message}"))
        # Audible alert — error (three low beeps)
        try:
            for _ in range(3):
                winsound.Beep(400, 250)
                time.sleep(0.1)
        except Exception:
            pass

    # --- Periodic Monitor Update ---

    def _update_monitor(self):
        if self.serial_mgr.is_connected:
            self.monitor_panel.update_stats(self.serial_mgr.stats)
            signals = self.serial_mgr.get_port_status()
            self.monitor_panel.update_signals(signals)

    # --- Library ---

    def _show_library(self):
        """Switch to the Reference Library tab."""
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == "Reference Library":
                self.tabs.setCurrentIndex(i)
                self.library_panel._search_box.setFocus()
                break

    # --- New Feature Methods ---

    def _apply_saved_settings(self):
        """Restore window/serial settings from last session."""
        ws = self.settings.window
        if ws.maximized:
            self.showMaximized()
        else:
            self.resize(ws.width, ws.height)
            self.move(ws.x, ws.y)

        # Restore serial settings
        self.conn_panel.apply_settings(self.settings.serial)

        # Load profiles
        self.conn_panel.set_profiles(self.settings.profiles)

        # Restore last tab
        if 0 <= ws.last_tab < self.tabs.count():
            self.tabs.setCurrentIndex(ws.last_tab)

    def _save_window_settings(self):
        """Save current window state before closing."""
        if self.isMaximized():
            self.settings.window.maximized = True
        else:
            self.settings.window.maximized = False
            geo = self.geometry()
            self.settings.window.x = geo.x()
            self.settings.window.y = geo.y()
            self.settings.window.width = geo.width()
            self.settings.window.height = geo.height()

        self.settings.window.last_tab = self.tabs.currentIndex()

        # Save theme / touch mode
        self.settings.window.theme = self._current_theme
        self.settings.window.touch_mode = self.touch_mode_action.isChecked()

        # Save serial combo state
        self.settings.serial.baud_rate = int(self.conn_panel.baud_combo.currentText())
        self.settings.serial.data_bits = int(self.conn_panel.databits_combo.currentText())
        self.settings.serial.parity = self.conn_panel.parity_combo.currentText()
        self.settings.serial.stop_bits = self.conn_panel.stopbits_combo.currentText()
        self.settings.serial.flow_control = self.conn_panel.flow_combo.currentText()

        port_data = self.conn_panel.port_combo.currentData()
        if port_data:
            self.settings.serial.port = port_data

        self.settings.save()

    def _check_updates(self, manual: bool = False):
        """Check for updates in a background thread."""
        import threading
        def _check():
            info = check_for_updates()
            if info:
                QTimer.singleShot(0, lambda: self._show_update_notification(info))
            elif manual:
                QTimer.singleShot(0, lambda: QMessageBox.information(
                    self, "Up to Date", "You are running the latest version."))
        threading.Thread(target=_check, daemon=True).start()

    def _show_update_notification(self, info):
        """Show update available dialog."""
        msg = QMessageBox(self)
        msg.setWindowTitle("Update Available")
        msg.setText(f"<b>CNC Bridge v{info.version}</b> is available!")
        msg.setInformativeText(
            f"Published: {info.published}\n\n"
            f"{info.release_notes[:300]}..."
            if len(info.release_notes) > 300 else info.release_notes
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        if info.release_url:
            msg.setDetailedText(f"Download: {info.release_url}")
        msg.exec()

    def _backplot_current(self):
        """Backplot the file currently in the G-code viewer or editor."""
        text = self.gcode_editor.get_text()
        if not text:
            text = self.gcode_viewer.get_text()
        if text:
            self.backplotter.load_text(text, "Current File")
            self.tabs.setCurrentWidget(self.backplotter)
        else:
            QMessageBox.information(self, "No File",
                                    "Open a G-code file in the Viewer or Editor first.")

    def _on_editor_saved(self, filepath: str):
        """When editor saves a file, update recent files."""
        self.settings.add_recent_file(filepath)

    def _new_editor(self):
        """Create new file in editor."""
        self.gcode_editor._new_file()
        self.tabs.setCurrentWidget(self.gcode_editor)

    def _save_editor(self):
        """Save current editor file."""
        self.gcode_editor._save_file()

    def _toggle_find(self):
        """Toggle find bar in editor."""
        if self.tabs.currentWidget() == self.gcode_editor:
            self.gcode_editor.toggle_find()
        else:
            self.tabs.setCurrentWidget(self.gcode_editor)
            self.gcode_editor.toggle_find()

    # --- About ---

    def _show_about(self):
        QMessageBox.about(self, "About CNC Bridge",
            "<h2>CNC Bridge v3.0</h2>"
            "<p>Anilam Crusader M / II Communication Bridge</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>Fusion 360 Post Processor</li>"
            "<li>G-code Editor with Syntax Highlighting</li>"
            "<li>2D Toolpath Backplotter with Heat Map</li>"
            "<li>Toolpath Animation (Play/Pause/Step)</li>"
            "<li>DNC Drip Feed & Upload</li>"
            "<li>Send-Receive-Verify Workflow</li>"
            "<li>G-code Validation with Inline Markers</li>"
            "<li>Tool Library Manager</li>"
            "<li>File Diff Comparison</li>"
            "<li>Real-time Controller Monitoring</li>"
            "<li>Connection Test / Handshake</li>"
            "<li>Auto-Reconnect on Disconnect</li>"
            "<li>Serial Traffic Logging</li>"
            "<li>Program Backup Vault</li>"
            "<li>Drag-and-Drop File Loading</li>"
            "<li>G-code Snippet Templates</li>"
            "<li>Backplot Export (PNG/PDF)</li>"
            "<li>228-entry Reference Library</li>"
            "<li>Macro Recorder & Playback</li>"
            "<li>Program Library & Favorites</li>"
            "<li>Multi-language Comment Translation</li>"
            "<li>Dark / Light Theme Toggle</li>"
            "<li>Touch-Screen Mode</li>"
            "</ul>"
            "<p>© 2026 Apocscode — MIT License</p>"
        )

    # --- Theme ---

    def _set_theme(self, theme: str):
        """Switch between dark and light themes."""
        self._current_theme = theme
        self.settings.window.theme = theme
        self.settings.save()
        self.dark_theme_action.setChecked(theme == "dark")
        self.light_theme_action.setChecked(theme == "light")
        self._apply_theme()

    def _apply_theme(self):
        if self._current_theme == "light":
            self._apply_light_theme()
        else:
            self._apply_dark_theme()

    def _apply_dark_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QWidget { background-color: #252526; color: #d4d4d4; font-size: 12px; }
            QGroupBox {
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 16px;
                font-weight: bold;
                color: #569CD6;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 3px;
                color: #d4d4d4;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #3c3c3c;
                color: #d4d4d4;
                selection-background-color: #094771;
            }
            QPushButton {
                background-color: #3c3c3c;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 4px 12px;
                color: #d4d4d4;
            }
            QPushButton:hover { background-color: #4a4a4a; }
            QPushButton:pressed { background-color: #2a2a2a; }
            QPushButton:disabled { background-color: #2a2a2a; color: #666; }
            QTabWidget::pane { border: 1px solid #3c3c3c; }
            QTabBar::tab {
                background-color: #2d2d2d;
                border: 1px solid #3c3c3c;
                padding: 6px 16px;
                color: #888;
            }
            QTabBar::tab:selected { background-color: #1e1e1e; color: #d4d4d4; border-bottom: 2px solid #569CD6; }
            QTabBar::tab:hover { color: #d4d4d4; }
            QProgressBar {
                border: 1px solid #555;
                border-radius: 3px;
                text-align: center;
                background-color: #3c3c3c;
                color: #d4d4d4;
            }
            QProgressBar::chunk { background-color: #4CAF50; border-radius: 2px; }
            QStatusBar { background-color: #007ACC; color: white; }
            QMenuBar { background-color: #3c3c3c; color: #d4d4d4; }
            QMenuBar::item:selected { background-color: #094771; }
            QMenu { background-color: #3c3c3c; color: #d4d4d4; }
            QMenu::item:selected { background-color: #094771; }
            QSplitter::handle { background-color: #3c3c3c; height: 2px; }
            QLabel { background-color: transparent; }
            QFrame { background-color: transparent; }
        """)

    def _apply_light_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #f5f5f5; }
            QWidget { background-color: #ffffff; color: #1e1e1e; font-size: 12px; }
            QGroupBox {
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 16px;
                font-weight: bold;
                color: #0060C0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {
                background-color: #ffffff;
                border: 1px solid #c0c0c0;
                border-radius: 3px;
                padding: 3px;
                color: #1e1e1e;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #ffffff;
                color: #1e1e1e;
                selection-background-color: #cce5ff;
            }
            QPushButton {
                background-color: #e8e8e8;
                border: 1px solid #c0c0c0;
                border-radius: 3px;
                padding: 4px 12px;
                color: #1e1e1e;
            }
            QPushButton:hover { background-color: #d0d0d0; }
            QPushButton:pressed { background-color: #b0b0b0; }
            QPushButton:disabled { background-color: #f0f0f0; color: #aaa; }
            QTabWidget::pane { border: 1px solid #c0c0c0; }
            QTabBar::tab {
                background-color: #e8e8e8;
                border: 1px solid #c0c0c0;
                padding: 6px 16px;
                color: #666;
            }
            QTabBar::tab:selected { background-color: #ffffff; color: #1e1e1e; border-bottom: 2px solid #0060C0; }
            QTabBar::tab:hover { color: #1e1e1e; }
            QProgressBar {
                border: 1px solid #c0c0c0;
                border-radius: 3px;
                text-align: center;
                background-color: #e8e8e8;
                color: #1e1e1e;
            }
            QProgressBar::chunk { background-color: #4CAF50; border-radius: 2px; }
            QStatusBar { background-color: #007ACC; color: white; }
            QMenuBar { background-color: #e8e8e8; color: #1e1e1e; }
            QMenuBar::item:selected { background-color: #cce5ff; }
            QMenu { background-color: #ffffff; color: #1e1e1e; }
            QMenu::item:selected { background-color: #cce5ff; }
            QSplitter::handle { background-color: #c0c0c0; height: 2px; }
            QPlainTextEdit { background-color: #fafafa; color: #1e1e1e; }
            QLabel { background-color: transparent; }
            QFrame { background-color: transparent; }
        """)

    # --- Touch-Screen Mode ---

    def _toggle_touch_mode(self):
        """Toggle touch-screen mode with larger buttons."""
        enabled = self.touch_mode_action.isChecked()
        self.settings.window.touch_mode = enabled
        self.settings.save()
        self._apply_touch_mode(enabled)

    def _apply_touch_mode(self, enabled: bool):
        """Apply or remove touch-screen scaling."""
        if enabled:
            # Increase all button/input sizes for touch screens
            extra = """
                QPushButton { min-height: 36px; font-size: 14px; padding: 6px 16px; }
                QComboBox { min-height: 32px; font-size: 14px; }
                QLineEdit { min-height: 32px; font-size: 14px; }
                QSpinBox, QDoubleSpinBox { min-height: 32px; font-size: 14px; }
                QTabBar::tab { padding: 10px 20px; font-size: 14px; }
                QLabel { font-size: 14px; }
                QGroupBox { font-size: 14px; }
            """
            current = self.styleSheet()
            self.setStyleSheet(current + extra)
            self.statusBar().showMessage("Touch-screen mode enabled")
        else:
            # Re-apply the regular theme to remove overrides
            self._apply_theme()
            self.statusBar().showMessage("Touch-screen mode disabled")

    # --- Comment Translation ---

    def _translate_comments(self, to_language: str):
        """Translate G-code comments in the editor."""
        if self.tabs.currentWidget() != self.gcode_editor:
            self.tabs.setCurrentWidget(self.gcode_editor)

        text = self.gcode_editor.get_text()
        if not text.strip():
            QMessageBox.information(self, "Empty", "No G-code to translate.")
            return

        translated = translate_gcode(text, to_language)
        lang_name = "Español" if to_language == "es" else "English"

        if translated != text:
            self.gcode_editor.editor.setPlainText(translated)
            self.terminal.append_info(f"Comments translated to {lang_name}")
            self.statusBar().showMessage(f"Comments translated to {lang_name}", 5000)
        else:
            self.statusBar().showMessage("No translatable comments found", 5000)

    # --- Program Library ---

    def _show_program_library(self):
        """Show program library management dialog."""
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QListWidget, QListWidgetItem

        dlg = QDialog(self)
        dlg.setWindowTitle("Program Library")
        dlg.resize(600, 450)

        layout = QVBoxLayout()

        # Search bar
        search_row = QHBoxLayout()
        search_lbl = QLabel("Search:")
        search_input = QLineEdit()
        search_input.setPlaceholderText("Search programs, tags, materials...")
        search_row.addWidget(search_lbl)
        search_row.addWidget(search_input, 1)
        layout.addLayout(search_row)

        # Program list
        prog_list = QListWidget()
        prog_list.setFont(QFont("Consolas", 10))
        layout.addWidget(prog_list)

        # Info display
        info_label = QLabel("")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Buttons
        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Current File")
        fav_btn = QPushButton("★ Toggle Favorite")
        load_btn = QPushButton("Load Selected")
        remove_btn = QPushButton("Remove")

        btn_row.addWidget(add_btn)
        btn_row.addWidget(fav_btn)
        btn_row.addWidget(load_btn)
        btn_row.addWidget(remove_btn)
        layout.addLayout(btn_row)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn)

        dlg.setLayout(layout)

        def refresh_list(query=""):
            prog_list.clear()
            if query:
                entries = self.program_library.search(query)
            else:
                entries = list(self.program_library.entries.values())
            entries.sort(key=lambda e: (not e.favorite, e.name.lower()))
            for entry in entries:
                star = "★ " if entry.favorite else "  "
                item = QListWidgetItem(f"{star}{entry.name}")
                item.setData(Qt.ItemDataRole.UserRole, entry.name)
                prog_list.addItem(item)

        def on_select():
            item = prog_list.currentItem()
            if item:
                name = item.data(Qt.ItemDataRole.UserRole)
                entry = self.program_library.get(name)
                if entry:
                    info = f"<b>{entry.name}</b>"
                    if entry.description:
                        info += f"<br>{entry.description}"
                    if entry.material:
                        info += f"<br>Material: {entry.material}"
                    if entry.tags:
                        info += f"<br>Tags: {', '.join(entry.tags)}"
                    info += f"<br>Used {entry.use_count}x"
                    info_label.setText(info)

        def on_add():
            filepath = self.gcode_editor.filepath if hasattr(self.gcode_editor, 'filepath') else ""
            if not filepath:
                # Try viewer
                filepath = getattr(self.gcode_viewer, '_current_file', '')
            if not filepath:
                QMessageBox.information(dlg, "No File", "Open a G-code file first.")
                return
            from PyQt6.QtWidgets import QInputDialog
            desc, ok = QInputDialog.getText(dlg, "Description", "Description (optional):")
            if ok:
                entry = ProgramEntry(
                    name=Path(filepath).name,
                    filepath=str(filepath),
                    description=desc or "",
                )
                self.program_library.add(entry)
                refresh_list(search_input.text())

        def on_load():
            item = prog_list.currentItem()
            if item:
                name = item.data(Qt.ItemDataRole.UserRole)
                entry = self.program_library.get(name)
                if entry and Path(entry.filepath).exists():
                    self.program_library.mark_used(name)
                    self.gcode_editor.load_file(entry.filepath)
                    self.tabs.setCurrentWidget(self.gcode_editor)
                    dlg.accept()
                elif entry:
                    QMessageBox.warning(dlg, "Not Found",
                                        f"File no longer exists:\n{entry.filepath}")

        def on_fav():
            item = prog_list.currentItem()
            if item:
                name = item.data(Qt.ItemDataRole.UserRole)
                self.program_library.toggle_favorite(name)
                refresh_list(search_input.text())

        def on_remove():
            item = prog_list.currentItem()
            if item:
                name = item.data(Qt.ItemDataRole.UserRole)
                self.program_library.remove(name)
                refresh_list(search_input.text())

        add_btn.clicked.connect(on_add)
        load_btn.clicked.connect(on_load)
        fav_btn.clicked.connect(on_fav)
        remove_btn.clicked.connect(on_remove)
        search_input.textChanged.connect(refresh_list)
        prog_list.currentItemChanged.connect(lambda: on_select())
        prog_list.doubleClicked.connect(on_load)

        refresh_list()
        dlg.exec()

    # --- Recent Files ---

    def _update_recent_menu(self):
        """Rebuild the Recent Files submenu from settings."""
        self.recent_menu.clear()
        for filepath in self.settings.recent_files[:10]:
            name = Path(filepath).name
            action = QAction(name, self)
            action.setToolTip(filepath)
            action.triggered.connect(lambda checked, fp=filepath: self._open_recent(fp))
            self.recent_menu.addAction(action)
        if not self.settings.recent_files:
            empty = QAction("(no recent files)", self)
            empty.setEnabled(False)
            self.recent_menu.addAction(empty)

    def _open_recent(self, filepath: str):
        """Open a file from the Recent Files menu."""
        if not Path(filepath).exists():
            QMessageBox.warning(self, "File Not Found",
                                f"File no longer exists:\n{filepath}")
            self.settings.recent_files = [
                f for f in self.settings.recent_files if f != filepath
            ]
            self.settings.save()
            self._update_recent_menu()
            return
        self.settings.add_recent_file(filepath)
        self._update_recent_menu()
        current = self.tabs.currentWidget()
        if current == self.gcode_editor:
            self.gcode_editor.load_file(filepath)
        elif current == self.backplotter:
            self.backplotter.load_file(filepath)
        else:
            self.gcode_viewer.load_file(filepath)
            self.tabs.setCurrentWidget(self.gcode_viewer)

    # --- Drag-and-Drop ---

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().lower().endswith(
                    ('.txt', '.nc', '.ngc', '.gcode', '.tap')
                ):
                    event.acceptProposedAction()
                    return
        event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            filepath = url.toLocalFile()
            if filepath:
                self.settings.add_recent_file(filepath)
                self._update_recent_menu()
                current = self.tabs.currentWidget()
                if current == self.gcode_editor:
                    self.gcode_editor.load_file(filepath)
                elif current == self.backplotter:
                    self.backplotter.load_file(filepath)
                else:
                    self.gcode_viewer.load_file(filepath)
                    self.tabs.setCurrentWidget(self.gcode_viewer)
                break  # Load first dropped file

    # --- Connection Test ---

    def _test_connection(self):
        """Run connection handshake test sequence."""
        if not self.serial_mgr.is_connected:
            QMessageBox.warning(self, "Not Connected",
                                "Connect to a serial port first.")
            return

        self.terminal.append_info("Running connection test...")
        self.tabs.setCurrentWidget(self.terminal)

        import threading
        def run():
            def on_progress(msg):
                QTimer.singleShot(0, lambda: self.terminal.append_info(msg))

            self.conn_tester.on_progress(on_progress)
            report = self.conn_tester.run_test()

            def show_result():
                self.terminal.append_text("", "#d4d4d4")
                for line in report.to_text().split("\n"):
                    if "PASS" in line:
                        self.terminal.append_text(line, "#4CAF50")
                    elif "FAIL" in line:
                        self.terminal.append_text(line, "#F44336")
                    elif "WARN" in line:
                        self.terminal.append_text(line, "#FFC107")
                    else:
                        self.terminal.append_text(line, "#d4d4d4")

                if report.overall_pass:
                    self.statusBar().showMessage("Connection test: PASSED")
                    winsound.Beep(1000, 200)
                else:
                    self.statusBar().showMessage("Connection test: FAILED")
                    winsound.Beep(400, 400)

            QTimer.singleShot(0, show_result)

        threading.Thread(target=run, daemon=True).start()

    # --- Auto-Reconnect ---

    def _attempt_reconnect(self):
        """Try to reconnect using the last known config."""
        if self.serial_mgr.is_connected:
            self._reconnect_timer.stop()
            return
        if not self._last_config:
            self._reconnect_timer.stop()
            return

        self.terminal.append_info("Attempting auto-reconnect...")
        config = SerialConfig.from_dict(self._last_config)
        port_data = self.conn_panel.port_combo.currentData()
        if port_data:
            config.port = port_data

        if self.serial_mgr.connect(config):
            self._reconnect_timer.stop()
            self.conn_panel.set_connected(True)
            self.terminal.append_info(f"Reconnected to {config.port}")
            self.statusBar().showMessage(f"Reconnected: {config.port}")
            self.traffic_logger.start_session(config.port, config.baud_rate)
            winsound.Beep(1000, 200)
        else:
            self.terminal.append_info("Reconnect failed, retrying in 5s...")

    # --- Send-Receive-Verify ---

    def _send_receive_verify(self):
        """Send a file, receive it back, and compare for integrity."""
        if not self.serial_mgr.is_connected:
            QMessageBox.warning(self, "Not Connected",
                                "Connect to a serial port first.")
            return

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select G-code to Send & Verify", "",
            "G-code Files (*.txt *.nc *.ngc *.gcode *.tap);;All Files (*)"
        )
        if not filepath:
            return

        self.tabs.setCurrentWidget(self.terminal)
        self.terminal.append_info(f"Send-Receive-Verify: {Path(filepath).name}")

        import threading
        def run():
            try:
                # Read original
                with open(filepath, 'r', encoding='ascii', errors='replace') as f:
                    original = f.read()

                original_lines = [l.strip() for l in original.splitlines() if l.strip()]

                # Send
                QTimer.singleShot(0, lambda: self.terminal.append_info("Phase 1: Sending..."))
                if not self.dnc_engine.load_file(filepath):
                    QTimer.singleShot(0, lambda: self.terminal.append_error("Failed to load file"))
                    return

                self.dnc_engine.send(SendMode.UPLOAD)
                # Wait for completion
                while self.dnc_engine.is_active:
                    time.sleep(0.2)

                if self.dnc_engine.state != TransferState.COMPLETED:
                    QTimer.singleShot(0, lambda: self.terminal.append_error("Send failed"))
                    return

                # Receive back
                QTimer.singleShot(0, lambda: self.terminal.append_info("Phase 2: Receiving back..."))
                received = self.dnc_engine.receive_program(timeout=30)
                if not received:
                    QTimer.singleShot(0, lambda: self.terminal.append_error(
                        "No data received back — controller may not support read-back"
                    ))
                    return

                received_clean = [l.strip() for l in received if l.strip()]

                # Compare
                QTimer.singleShot(0, lambda: self.terminal.append_info("Phase 3: Verifying..."))
                match = original_lines == received_clean
                diff_count = 0
                for i, (orig, recv) in enumerate(zip(original_lines, received_clean)):
                    if orig != recv:
                        diff_count += 1
                diff_count += abs(len(original_lines) - len(received_clean))

                def show_result():
                    if match:
                        self.terminal.append_text(
                            "✓ VERIFY PASSED — sent and received data match!", "#4CAF50")
                        winsound.Beep(1000, 300)
                    else:
                        self.terminal.append_text(
                            f"✗ VERIFY FAILED — {diff_count} line(s) differ", "#F44336")
                        winsound.Beep(400, 500)
                        # Load into diff viewer
                        self.file_diff._load_texts(
                            original, '\n'.join(received),
                            "Sent", "Received"
                        )

                QTimer.singleShot(0, show_result)

            except Exception as e:
                QTimer.singleShot(0, lambda: self.terminal.append_error(f"Verify error: {e}"))

        threading.Thread(target=run, daemon=True).start()

    # --- Snippet Insertion ---

    def _insert_snippet(self, code: str):
        """Insert a G-code snippet at the editor cursor."""
        self.tabs.setCurrentWidget(self.gcode_editor)
        cursor = self.gcode_editor.editor.textCursor()
        cursor.insertText(code)

    # --- N-line Renumber ---

    def _renumber_lines(self):
        """Renumber or add N-line sequence numbers in the editor."""
        if self.tabs.currentWidget() != self.gcode_editor:
            self.tabs.setCurrentWidget(self.gcode_editor)

        text = self.gcode_editor.get_text()
        if not text.strip():
            QMessageBox.information(self, "Empty", "No G-code to renumber.")
            return

        import re as re_mod
        lines = text.splitlines()
        new_lines = []
        n = 10
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped == '%' or stripped.startswith('('):
                new_lines.append(line)
                continue
            # Remove existing N number
            cleaned = re_mod.sub(r'^N\d+\s*', '', stripped)
            new_lines.append(f"N{n} {cleaned}")
            n += 10

        self.gcode_editor.editor.setPlainText('\n'.join(new_lines))
        self.terminal.append_info(f"Renumbered {(n - 10) // 10} lines (N10, N20, ...)")

    # --- Estimated Cycle Time ---

    def _show_cycle_time(self, text: str):
        """Parse G-code and display estimated cycle time in status bar."""
        try:
            validator = GCodeValidator()
            issues, stats = validator.validate_text(text)
            if stats.estimated_time_minutes > 0:
                mins = int(stats.estimated_time_minutes)
                secs = int((stats.estimated_time_minutes - mins) * 60)
                dist = getattr(stats, 'total_distance_inches', 0)
                msg = f"Est. cycle: {mins}m {secs}s"
                if dist > 0:
                    msg += f" | Travel: {dist:.1f}\""
                self.statusBar().showMessage(msg, 10000)
        except Exception:
            pass

    # --- Cleanup ---

    def closeEvent(self, event):
        # Save settings
        self._save_window_settings()

        # Stop auto-reconnect
        self._reconnect_timer.stop()

        # Stop traffic logging
        self.traffic_logger.stop_session()

        if self.dnc_engine.is_active:
            self.dnc_engine.abort()
        if self.serial_mgr.is_connected:
            self.serial_mgr.disconnect()

        # Check for unsaved editor changes
        if self.gcode_editor.is_modified:
            result = QMessageBox.question(
                self, "Unsaved Changes",
                "The editor has unsaved changes. Save before closing?",
                QMessageBox.StandardButton.Save |
                QMessageBox.StandardButton.Discard |
                QMessageBox.StandardButton.Cancel,
            )
            if result == QMessageBox.StandardButton.Save:
                self.gcode_editor._save_file()
            elif result == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return

        event.accept()
