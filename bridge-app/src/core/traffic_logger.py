"""
CNC Bridge — Serial Traffic Logger

Automatically logs all TX/RX serial data to timestamped log files.
Each session creates a new log file with all sent and received data,
flow control events, and connection state changes.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "serial"


class SerialTrafficLogger:
    """Logs serial TX/RX data to timestamped files."""

    def __init__(self, log_dir: Optional[Path] = None):
        self._log_dir = log_dir or LOG_DIR
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._file = None
        self._filepath: Optional[Path] = None
        self._session_start: float = 0
        self._bytes_logged: int = 0
        self._enabled: bool = True

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    @property
    def filepath(self) -> Optional[Path]:
        return self._filepath

    @property
    def bytes_logged(self) -> int:
        return self._bytes_logged

    def start_session(self, port: str = "", baud: int = 0):
        """Start a new logging session — creates a new timestamped file."""
        self.stop_session()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        port_clean = port.replace("/", "_").replace("\\", "_").replace(":", "")
        filename = f"serial_{timestamp}_{port_clean}.log"
        self._filepath = self._log_dir / filename
        self._session_start = time.time()
        self._bytes_logged = 0

        try:
            self._file = open(self._filepath, 'w', encoding='utf-8')
            self._write_header(port, baud)
            logger.info(f"Serial traffic logging started: {self._filepath}")
        except Exception as e:
            logger.error(f"Failed to start serial log: {e}")
            self._file = None

    def stop_session(self):
        """Stop the current logging session."""
        if self._file:
            elapsed = time.time() - self._session_start
            self._file.write(f"\n{'='*60}\n")
            self._file.write(f"SESSION ENDED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            self._file.write(f"Duration: {elapsed:.1f}s | Bytes logged: {self._bytes_logged:,}\n")
            self._file.write(f"{'='*60}\n")
            self._file.close()
            self._file = None
            logger.info(f"Serial traffic log closed: {self._filepath}")

    def log_tx(self, data: str):
        """Log transmitted data."""
        if not self._enabled or not self._file:
            return
        self._write_entry("TX", data)

    def log_rx(self, data: str):
        """Log received data."""
        if not self._enabled or not self._file:
            return
        self._write_entry("RX", data)

    def log_event(self, event: str):
        """Log a connection/flow control event."""
        if not self._file:
            return
        timestamp = self._elapsed_str()
        try:
            self._file.write(f"[{timestamp}] EVENT: {event}\n")
            self._file.flush()
        except Exception:
            pass

    def log_error(self, message: str):
        """Log an error event."""
        if not self._file:
            return
        timestamp = self._elapsed_str()
        try:
            self._file.write(f"[{timestamp}] ERROR: {message}\n")
            self._file.flush()
        except Exception:
            pass

    def _write_header(self, port: str, baud: int):
        """Write session header."""
        self._file.write(f"{'='*60}\n")
        self._file.write(f"CNC Bridge — Serial Traffic Log\n")
        self._file.write(f"{'='*60}\n")
        self._file.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        self._file.write(f"Port: {port}\n")
        self._file.write(f"Baud: {baud}\n")
        self._file.write(f"{'='*60}\n\n")
        self._file.flush()

    def _write_entry(self, direction: str, data: str):
        """Write a TX/RX entry."""
        timestamp = self._elapsed_str()
        data_clean = data.rstrip('\r\n')
        try:
            self._file.write(f"[{timestamp}] {direction}: {data_clean}\n")
            self._file.flush()
            self._bytes_logged += len(data)
        except Exception:
            pass

    def _elapsed_str(self) -> str:
        """Get elapsed time as formatted string."""
        elapsed = time.time() - self._session_start
        mins = int(elapsed // 60)
        secs = elapsed % 60
        return f"{mins:03d}:{secs:06.3f}"

    def get_session_files(self, limit: int = 20) -> list[Path]:
        """Get recent session log files, newest first."""
        try:
            files = sorted(self._log_dir.glob("serial_*.log"), reverse=True)
            return files[:limit]
        except Exception:
            return []

    def __del__(self):
        self.stop_session()
