"""
CNC Bridge — Main Application Window

PyQt6-based GUI providing:
  - Connection panel (port selection, serial settings)
  - G-code file manager (load, view, validate)
  - DNC transfer controls (send, drip feed, pause, abort)
  - Real-time monitoring dashboard
  - Serial terminal / console
"""

import sys
import os
import time
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
from PyQt6.QtGui import QFont, QColor, QTextCharFormat, QAction, QIcon

from ..core.serial_manager import (
    SerialManager, SerialConfig, ConnectionState, FlowControl, Parity
)
from ..core.dnc_sender import DNCEngine, SendMode, TransferState, TransferProgress
from ..core.gcode_parser import GCodeParser, GCodeValidator
from .library_panel import LibraryPanel


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

    def __init__(self, parent=None):
        super().__init__("Connection", parent)
        self._build_ui()

    def _build_ui(self):
        layout = QFormLayout()
        layout.setSpacing(4)

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

        self.setLayout(layout)

    def _on_send(self):
        text = self.input_field.text().strip()
        if text:
            self.append_text(f">>> {text}", "#569CD6")
            self.send_command.emit(text)
            self.input_field.clear()

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
        self.stats_label = QLabel("")
        toolbar.addWidget(self.load_btn)
        toolbar.addWidget(self.validate_btn)
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

    def get_text(self) -> str:
        return self._current_text


class MainWindow(QMainWindow):
    """CNC Bridge main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("CNC Bridge — Anilam Crusader M")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)

        # Core objects
        self.serial_mgr = SerialManager()
        self.dnc_engine = DNCEngine(self.serial_mgr)

        # Build UI
        self._build_menu()
        self._build_ui()
        self._setup_timers()
        self._connect_signals()

        # Initial port scan
        self._refresh_ports()

        # Apply dark theme
        self._apply_theme()

    def _build_menu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")
        open_action = QAction("&Open G-code...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)
        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

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

        # Transfer menu
        xfer_menu = menubar.addMenu("&Transfer")
        send_action = QAction("&Send File...", self)
        send_action.triggered.connect(lambda: self.transfer_panel._on_send())
        xfer_menu.addAction(send_action)
        xfer_menu.addSeparator()
        receive_action = QAction("&Receive from Controller", self)
        receive_action.triggered.connect(self._receive_program)
        xfer_menu.addAction(receive_action)

        # Help menu
        help_menu = menubar.addMenu("&Help")
        library_action = QAction("Reference &Library", self)
        library_action.setShortcut("F1")
        library_action.triggered.connect(self._show_library)
        help_menu.addAction(library_action)
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

        self.terminal = SerialTerminal()
        self.tabs.addTab(self.terminal, "Serial Terminal")

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
            self.conn_panel.set_connected(True)
            self.terminal.append_info(f"Connected to {config.port} at {config.baud_rate} baud")
            self.statusBar().showMessage(f"Connected: {config.port}")
        else:
            QMessageBox.critical(self, "Connection Failed",
                                 f"Could not connect to {config.port}")

    def _disconnect(self):
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
            self.gcode_viewer.load_file(filepath)
            self.tabs.setCurrentWidget(self.gcode_viewer)

    def _send_file(self, filepath: str, mode: str):
        if not self.serial_mgr.is_connected:
            QMessageBox.warning(self, "Not Connected",
                                "Connect to a serial port first.")
            return

        send_mode = SendMode.DRIP_FEED if mode == "drip_feed" else SendMode.UPLOAD
        if self.dnc_engine.load_file(filepath):
            self.dnc_engine.send(send_mode)
            self.terminal.append_info(f"Sending {Path(filepath).name} ({mode})")

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
        else:
            self.terminal.append_error("Not connected")

    # --- Callbacks (may be called from background threads) ---

    def _on_serial_line(self, line: str):
        # Thread-safe: use QTimer.singleShot to update GUI
        QTimer.singleShot(0, lambda: self.terminal.append_received(line))

    def _on_connection_state(self, state: ConnectionState):
        QTimer.singleShot(0, lambda: self.monitor_panel.update_connection(state))

    def _on_serial_error(self, message: str):
        QTimer.singleShot(0, lambda: self.terminal.append_error(message))
        QTimer.singleShot(0, lambda: self.statusBar().showMessage(f"Error: {message}"))

    def _on_flow_control(self, is_xon: bool):
        QTimer.singleShot(0, lambda: self.monitor_panel.update_flow(is_xon))

    def _on_transfer_progress(self, progress: TransferProgress):
        QTimer.singleShot(0, lambda: self.transfer_panel.update_progress(progress))

    def _on_transfer_complete(self, progress: TransferProgress):
        QTimer.singleShot(0, lambda: self.terminal.append_info(
            f"Transfer complete: {progress.current_line} lines in {progress.elapsed_time:.1f}s"
        ))

    def _on_transfer_error(self, message: str):
        QTimer.singleShot(0, lambda: self.terminal.append_error(f"Transfer error: {message}"))

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

    # --- About ---

    def _show_about(self):
        QMessageBox.about(self, "About CNC Bridge",
            "<h2>CNC Bridge</h2>"
            "<p>Anilam Crusader M Communication Bridge</p>"
            "<p>Version 1.0.0</p>"
            "<p>Features:</p>"
            "<ul>"
            "<li>Fusion 360 Post Processor</li>"
            "<li>DNC Drip Feed & Upload</li>"
            "<li>G-code Validation</li>"
            "<li>Real-time Controller Monitoring</li>"
            "<li>Serial Terminal</li>"
            "</ul>"
            "<p>© 2026 CNC Bridge Project</p>"
        )

    # --- Theme ---

    def _apply_theme(self):
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

    # --- Cleanup ---

    def closeEvent(self, event):
        if self.dnc_engine.is_active:
            self.dnc_engine.abort()
        if self.serial_mgr.is_connected:
            self.serial_mgr.disconnect()
        event.accept()
