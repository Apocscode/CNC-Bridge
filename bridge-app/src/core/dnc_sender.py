"""
CNC Bridge — DNC Sender Engine

Manages DNC (Direct Numerical Control) drip-feed transmission of G-code
programs to the Anilam Crusader M controller. Supports:
  - Full program upload (store in controller memory)
  - Drip feed mode (stream line-by-line during execution)
  - Pause / Resume / Abort controls
  - Progress tracking with callbacks
  - Flow control awareness (XON/XOFF)
  - Program download from controller
"""

import threading
import time
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

from .serial_manager import SerialManager, ConnectionState

logger = logging.getLogger(__name__)


class SendMode(Enum):
    UPLOAD = "upload"        # Send entire program to controller memory
    DRIP_FEED = "drip_feed"  # Stream line-by-line during execution


class TransferState(Enum):
    IDLE = "idle"
    SENDING = "sending"
    PAUSED = "paused"
    RECEIVING = "receiving"
    COMPLETED = "completed"
    ABORTED = "aborted"
    ERROR = "error"


@dataclass
class TransferProgress:
    """Real-time transfer progress data."""
    state: TransferState = TransferState.IDLE
    mode: SendMode = SendMode.UPLOAD
    file_name: str = ""
    total_lines: int = 0
    current_line: int = 0
    total_bytes: int = 0
    bytes_sent: int = 0
    start_time: float = 0.0
    elapsed_time: float = 0.0
    estimated_remaining: float = 0.0
    current_gcode: str = ""
    error_message: str = ""

    @property
    def percent_complete(self) -> float:
        if self.total_lines == 0:
            return 0.0
        return min(100.0, (self.current_line / self.total_lines) * 100.0)

    @property
    def lines_per_second(self) -> float:
        if self.elapsed_time <= 0:
            return 0.0
        return self.current_line / self.elapsed_time

    @property
    def bytes_per_second(self) -> float:
        if self.elapsed_time <= 0:
            return 0.0
        return self.bytes_sent / self.elapsed_time


class DNCEngine:
    """
    DNC (Direct Numeric Control) transfer engine for Anilam Crusader M.
    
    Handles sending G-code programs to the controller via serial,
    with support for both full upload and drip-feed streaming.
    """

    def __init__(self, serial_mgr: SerialManager):
        self._serial = serial_mgr
        self._state = TransferState.IDLE
        self._progress = TransferProgress()
        self._send_thread: Optional[threading.Thread] = None
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused
        self._abort_flag = False
        self._lock = threading.Lock()
        
        # Lines to send
        self._lines: list[str] = []
        
        # Callbacks
        self._on_progress: Optional[Callable[[TransferProgress], None]] = None
        self._on_complete: Optional[Callable[[TransferProgress], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        self._on_line_sent: Optional[Callable[[int, str], None]] = None
        self._on_ack: Optional[Callable[[str], None]] = None

    # --- Properties ---

    @property
    def state(self) -> TransferState:
        return self._state

    @property
    def progress(self) -> TransferProgress:
        return self._progress

    @property
    def is_active(self) -> bool:
        return self._state in (TransferState.SENDING, TransferState.PAUSED)

    # --- Callback Registration ---

    def on_progress(self, callback: Callable[[TransferProgress], None]):
        self._on_progress = callback

    def on_complete(self, callback: Callable[[TransferProgress], None]):
        self._on_complete = callback

    def on_error(self, callback: Callable[[str], None]):
        self._on_error = callback

    def on_line_sent(self, callback: Callable[[int, str], None]):
        self._on_line_sent = callback

    def on_ack(self, callback: Callable[[str], None]):
        """Register a callback for controller acknowledgment after transfer."""
        self._on_ack = callback

    # --- File Loading ---

    def load_file(self, filepath: str) -> bool:
        """Load a G-code file for transmission."""
        try:
            path = Path(filepath)
            if not path.exists():
                self._report_error(f"File not found: {filepath}")
                return False

            with open(path, 'r', encoding='ascii', errors='replace') as f:
                raw_lines = f.readlines()

            # Store lines (preserve original formatting)
            self._lines = [line.rstrip('\r\n') for line in raw_lines]
            
            self._progress = TransferProgress(
                file_name=path.name,
                total_lines=len(self._lines),
                total_bytes=sum(len(line) + 1 for line in self._lines),  # +1 for newline
            )

            logger.info(f"Loaded {len(self._lines)} lines from {path.name}")
            return True

        except Exception as e:
            self._report_error(f"Error loading file: {e}")
            return False

    def load_lines(self, lines: list[str], name: str = "manual"):
        """Load G-code lines directly (not from file)."""
        self._lines = [line.rstrip('\r\n') for line in lines]
        self._progress = TransferProgress(
            file_name=name,
            total_lines=len(self._lines),
            total_bytes=sum(len(line) + 1 for line in self._lines),
        )

    # --- Transfer Control ---

    def send(self, mode: SendMode = SendMode.UPLOAD) -> bool:
        """Start sending the loaded program."""
        if not self._lines:
            self._report_error("No program loaded")
            return False

        if not self._serial.is_connected:
            self._report_error("Not connected to controller")
            return False

        if self.is_active:
            self._report_error("Transfer already in progress")
            return False

        self._abort_flag = False
        self._pause_event.set()
        self._progress.mode = mode
        self._progress.state = TransferState.SENDING
        self._progress.start_time = time.time()
        self._progress.current_line = 0
        self._progress.bytes_sent = 0
        self._progress.error_message = ""
        self._state = TransferState.SENDING

        self._send_thread = threading.Thread(
            target=self._send_loop,
            name="DNCsendThread",
            daemon=True,
        )
        self._send_thread.start()
        return True

    def pause(self):
        """Pause the current transfer."""
        if self._state == TransferState.SENDING:
            self._pause_event.clear()
            self._state = TransferState.PAUSED
            self._progress.state = TransferState.PAUSED
            self._notify_progress()
            logger.info("Transfer paused")

    def resume(self):
        """Resume a paused transfer."""
        if self._state == TransferState.PAUSED:
            self._state = TransferState.SENDING
            self._progress.state = TransferState.SENDING
            self._pause_event.set()
            self._notify_progress()
            logger.info("Transfer resumed")

    def abort(self):
        """Abort the current transfer."""
        self._abort_flag = True
        self._pause_event.set()  # Unpause if paused so thread can exit
        
        if self._send_thread and self._send_thread.is_alive():
            self._send_thread.join(timeout=5.0)

        self._state = TransferState.ABORTED
        self._progress.state = TransferState.ABORTED
        self._notify_progress()
        logger.info("Transfer aborted")

    # --- Program Download (receive from controller) ---

    def receive_program(self, timeout: float = 30.0) -> Optional[list[str]]:
        """
        Receive a program from the Anilam controller.
        Waits for incoming data and collects lines until timeout or end marker.
        
        Returns list of lines or None on error.
        """
        if not self._serial.is_connected:
            self._report_error("Not connected to controller")
            return None

        self._state = TransferState.RECEIVING
        self._progress.state = TransferState.RECEIVING
        self._notify_progress()

        received_lines: list[str] = []
        last_data_time = time.time()

        def on_line(line: str):
            nonlocal last_data_time
            received_lines.append(line)
            last_data_time = time.time()
            self._progress.current_line = len(received_lines)
            self._notify_progress()

        # Temporarily set line callback
        original_callback = self._serial._on_line_received
        self._serial.on_line_received(on_line)

        try:
            # Send XON to tell controller we're ready to receive
            self._serial.send_xon()

            # Wait for data
            while not self._abort_flag:
                time.sleep(0.1)
                
                # Check for end marker (% is standard G-code program boundary)
                if received_lines and received_lines[-1].strip() == '%':
                    break
                
                # Timeout check
                if time.time() - last_data_time > timeout:
                    if received_lines:
                        logger.info("Receive timeout — assuming end of program")
                        break
                    else:
                        self._report_error("No data received from controller")
                        return None

            self._state = TransferState.COMPLETED
            self._progress.state = TransferState.COMPLETED
            self._progress.total_lines = len(received_lines)
            self._notify_progress()
            return received_lines

        except Exception as e:
            self._report_error(f"Error receiving program: {e}")
            return None
        finally:
            # Restore original callback
            self._serial._on_line_received = original_callback

    # --- Internal Send Loop ---

    def _send_loop(self):
        """Main send loop — runs in background thread."""
        try:
            logger.info(f"_send_loop started: {len(self._lines)} lines, mode={self._progress.mode}")
            for i, line in enumerate(self._lines):
                # Check abort
                if self._abort_flag:
                    return

                # Check pause
                self._pause_event.wait()
                if self._abort_flag:
                    return

                # Check connection
                if not self._serial.is_connected:
                    self._report_error("Connection lost during transfer")
                    return

                # Skip empty lines in drip feed mode
                stripped = line.strip()
                if self._progress.mode == SendMode.DRIP_FEED and not stripped:
                    continue

                # Send the line
                if not self._serial.send_line(line):
                    self._report_error(f"Failed to send line {i + 1}: {line}")
                    return

                # Update progress
                self._progress.current_line = i + 1
                self._progress.bytes_sent += len(line) + 1
                self._progress.elapsed_time = time.time() - self._progress.start_time
                self._progress.current_gcode = stripped

                # Estimate remaining time
                if self._progress.current_line > 0:
                    rate = self._progress.elapsed_time / self._progress.current_line
                    remaining = self._progress.total_lines - self._progress.current_line
                    self._progress.estimated_remaining = rate * remaining

                # Callbacks
                if self._on_line_sent:
                    self._on_line_sent(i + 1, stripped)
                self._notify_progress()

            # Transfer complete
            self._serial.flush()
            self._state = TransferState.COMPLETED
            self._progress.state = TransferState.COMPLETED
            self._progress.elapsed_time = time.time() - self._progress.start_time
            self._progress.estimated_remaining = 0.0
            self._notify_progress()

            if self._on_complete:
                self._on_complete(self._progress)

            # Listen for controller acknowledgment (up to 3 seconds)
            self._wait_for_ack(timeout=3.0)

            logger.info(
                f"Transfer complete: {self._progress.current_line} lines, "
                f"{self._progress.bytes_sent} bytes in {self._progress.elapsed_time:.1f}s"
            )

        except Exception as e:
            self._report_error(f"Send error: {e}")

    # --- Internal Helpers ---

    def _wait_for_ack(self, timeout: float = 3.0):
        """Listen for any response bytes from the controller after transfer."""
        try:
            ser = self._serial._serial
            if not ser or not ser.is_open:
                return
            deadline = time.time() + timeout
            buf = b''
            while time.time() < deadline:
                waiting = ser.in_waiting
                if waiting > 0:
                    buf += ser.read(waiting)
                    # Reset deadline on new data
                    deadline = time.time() + 1.0
                else:
                    time.sleep(0.05)
            if buf and self._on_ack:
                text = buf.decode('ascii', errors='replace').strip()
                if text:
                    self._on_ack(f"Controller response: {repr(text)}")
                else:
                    # Control chars only (e.g. XON 0x11)
                    hex_str = ' '.join(f'0x{b:02X}' for b in buf)
                    self._on_ack(f"Controller ACK: {hex_str}")
            elif self._on_ack:
                self._on_ack("No response from controller (normal for Anilam store mode)")
        except Exception as e:
            logger.debug(f"ACK listen error: {e}")

    def _notify_progress(self):
        if self._on_progress:
            self._on_progress(self._progress)

    def _report_error(self, message: str):
        logger.error(message)
        self._state = TransferState.ERROR
        self._progress.state = TransferState.ERROR
        self._progress.error_message = message
        self._notify_progress()
        if self._on_error:
            self._on_error(message)
