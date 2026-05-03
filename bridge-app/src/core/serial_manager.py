"""
CNC Bridge — Serial Port Manager

Handles RS232 serial communication with the Anilam Crusader M controller.
Supports configurable baud rate, parity, flow control (XON/XOFF and RTS/CTS),
and provides connection state management with event callbacks.

Anilam Crusader M RS232 defaults (Supermax-30 AUX settings):
  - Baud: 4800 (AUX 2787)
  - Data bits: 7 (AUX 2767)
  - Character set: ASCII (AUX 2758)
  - Parity: Even
  - Flow control: XON/XOFF (AUX 2791)
  - Format: RS-274 (AUX 2701)
"""

import threading
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional
import serial
import serial.tools.list_ports

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class FlowControl(Enum):
    NONE = "none"
    XONXOFF = "xon/xoff"     # Software flow control (most common for Anilam)
    RTSCTS = "rts/cts"       # Hardware flow control
    DSRDTR = "dsr/dtr"       # Hardware flow control (less common)


class Parity(Enum):
    NONE = "N"
    EVEN = "E"
    ODD = "O"


@dataclass
class SerialConfig:
    """Serial port configuration for Anilam Crusader M."""
    port: str = ""
    baud_rate: int = 4800
    data_bits: int = 7
    stop_bits: float = 1.0    # 1, 1.5, or 2
    parity: Parity = Parity.EVEN
    flow_control: FlowControl = FlowControl.XONXOFF
    read_timeout: float = 1.0
    write_timeout: float = 5.0
    
    # Anilam-specific
    inter_char_delay: float = 0.0    # Delay between characters (seconds)
    line_delay: float = 0.05         # Delay between lines (seconds)
    
    def to_dict(self) -> dict:
        return {
            "port": self.port,
            "baud_rate": self.baud_rate,
            "data_bits": self.data_bits,
            "stop_bits": self.stop_bits,
            "parity": self.parity.value,
            "flow_control": self.flow_control.value,
            "read_timeout": self.read_timeout,
            "write_timeout": self.write_timeout,
            "inter_char_delay": self.inter_char_delay,
            "line_delay": self.line_delay,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SerialConfig":
        config = cls()
        config.port = data.get("port", "")
        config.baud_rate = data.get("baud_rate", 9600)
        config.data_bits = data.get("data_bits", 8)
        config.stop_bits = data.get("stop_bits", 1.0)
        config.parity = Parity(data.get("parity", "E"))
        config.flow_control = FlowControl(data.get("flow_control", "xon/xoff"))
        config.read_timeout = data.get("read_timeout", 1.0)
        config.write_timeout = data.get("write_timeout", 5.0)
        config.inter_char_delay = data.get("inter_char_delay", 0.0)
        config.line_delay = data.get("line_delay", 0.05)
        return config

    @classmethod
    def anilam_default(cls) -> "SerialConfig":
        """Return default config matching Supermax-30 / Anilam Crusader M.
        
        Based on AUX code configuration:
          AUX 2758 — ASCII character set
          AUX 2767 — 7 bits per character
          AUX 2787 — 4800 baud
          AUX 2791 — XON/XOFF software handshake
          AUX 2701 — Receive RS-274 format
        """
        return cls(
            baud_rate=4800,
            data_bits=7,
            stop_bits=1.0,
            parity=Parity.EVEN,
            flow_control=FlowControl.XONXOFF,
            line_delay=0.05,
        )


@dataclass
class SerialStats:
    """Transfer statistics."""
    bytes_sent: int = 0
    bytes_received: int = 0
    lines_sent: int = 0
    lines_received: int = 0
    errors: int = 0
    xon_count: int = 0
    xoff_count: int = 0
    last_activity: float = 0.0
    connect_time: float = 0.0
    
    def reset(self):
        self.bytes_sent = 0
        self.bytes_received = 0
        self.lines_sent = 0
        self.lines_received = 0
        self.errors = 0
        self.xon_count = 0
        self.xoff_count = 0
        self.last_activity = 0.0

    @property
    def uptime(self) -> float:
        if self.connect_time > 0:
            return time.time() - self.connect_time
        return 0.0


class SerialManager:
    """
    Manages serial port communication with the Anilam Crusader M.
    
    Provides:
    - Connection lifecycle management
    - Threaded read loop with callbacks
    - Flow control monitoring (XON/XOFF state tracking)
    - Transfer statistics
    - Port enumeration
    """

    XON = b'\x11'   # DC1 — Resume transmission
    XOFF = b'\x13'  # DC3 — Pause transmission

    def __init__(self, config: Optional[SerialConfig] = None):
        self.config = config or SerialConfig.anilam_default()
        self._serial: Optional[serial.Serial] = None
        self._state = ConnectionState.DISCONNECTED
        self._stats = SerialStats()
        self._read_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._xoff_event = threading.Event()
        self._xoff_event.set()  # Start in XON state (ready to send)
        
        # Callbacks
        self._on_data_received: Optional[Callable[[bytes], None]] = None
        self._on_line_received: Optional[Callable[[str], None]] = None
        self._on_state_changed: Optional[Callable[[ConnectionState], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None
        self._on_flow_control: Optional[Callable[[bool], None]] = None  # True=XON, False=XOFF
        
        self._receive_buffer = bytearray()

    # --- Properties ---

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED and self._serial is not None and self._serial.is_open

    @property
    def stats(self) -> SerialStats:
        return self._stats

    @property
    def can_send(self) -> bool:
        """True if connected and not in XOFF state."""
        return self.is_connected and self._xoff_event.is_set()

    # --- Callback Registration ---

    def on_data_received(self, callback: Callable[[bytes], None]):
        self._on_data_received = callback

    def on_line_received(self, callback: Callable[[str], None]):
        self._on_line_received = callback

    def on_state_changed(self, callback: Callable[[ConnectionState], None]):
        self._on_state_changed = callback

    def on_error(self, callback: Callable[[str], None]):
        self._on_error = callback

    def on_flow_control(self, callback: Callable[[bool], None]):
        self._on_flow_control = callback

    # --- Port Enumeration ---

    @staticmethod
    def list_ports() -> list[dict]:
        """List available serial ports with metadata."""
        ports = []
        for port_info in serial.tools.list_ports.comports():
            ports.append({
                "port": port_info.device,
                "description": port_info.description,
                "hwid": port_info.hwid,
                "manufacturer": port_info.manufacturer or "",
                "vid": port_info.vid,
                "pid": port_info.pid,
                "serial_number": port_info.serial_number or "",
            })
        return sorted(ports, key=lambda p: p["port"])

    # --- Connection Management ---

    def connect(self, config: Optional[SerialConfig] = None) -> bool:
        """Open serial connection with given or stored config."""
        if config:
            self.config = config

        if not self.config.port:
            self._set_error("No serial port specified")
            return False

        self._set_state(ConnectionState.CONNECTING)

        try:
            # Map parity
            parity_map = {
                Parity.NONE: serial.PARITY_NONE,
                Parity.EVEN: serial.PARITY_EVEN,
                Parity.ODD: serial.PARITY_ODD,
            }
            # Map stop bits
            stopbits_map = {
                1.0: serial.STOPBITS_ONE,
                1.5: serial.STOPBITS_ONE_POINT_FIVE,
                2.0: serial.STOPBITS_TWO,
            }

            self._serial = serial.Serial(
                port=self.config.port,
                baudrate=self.config.baud_rate,
                bytesize=self.config.data_bits,
                parity=parity_map.get(self.config.parity, serial.PARITY_EVEN),
                stopbits=stopbits_map.get(self.config.stop_bits, serial.STOPBITS_TWO),
                timeout=self.config.read_timeout,
                write_timeout=self.config.write_timeout,
                xonxoff=(self.config.flow_control == FlowControl.XONXOFF),
                rtscts=(self.config.flow_control == FlowControl.RTSCTS),
                dsrdtr=(self.config.flow_control == FlowControl.DSRDTR),
            )

            self._stats.reset()
            self._stats.connect_time = time.time()
            self._xoff_event.set()

            # Start read thread
            self._running = True
            self._read_thread = threading.Thread(
                target=self._read_loop,
                name="SerialReadThread",
                daemon=True,
            )
            self._read_thread.start()

            self._set_state(ConnectionState.CONNECTED)
            logger.info(f"Connected to {self.config.port} at {self.config.baud_rate} baud")
            return True

        except serial.SerialException as e:
            self._set_error(f"Failed to open {self.config.port}: {e}")
            return False
        except Exception as e:
            self._set_error(f"Unexpected error: {e}")
            return False

    def disconnect(self):
        """Close serial connection and stop read thread."""
        self._running = False
        
        if self._read_thread and self._read_thread.is_alive():
            self._read_thread.join(timeout=3.0)
        
        with self._lock:
            if self._serial and self._serial.is_open:
                try:
                    self._serial.close()
                except Exception as e:
                    logger.warning(f"Error closing serial port: {e}")
                self._serial = None

        self._set_state(ConnectionState.DISCONNECTED)
        logger.info("Disconnected from serial port")

    # --- Data I/O ---

    def send_bytes(self, data: bytes) -> bool:
        """Send raw bytes to the serial port."""
        if not self.is_connected:
            return False

        try:
            with self._lock:
                if self.config.inter_char_delay > 0:
                    for byte in data:
                        self._serial.write(bytes([byte]))
                        time.sleep(self.config.inter_char_delay)
                else:
                    self._serial.write(data)

            self._stats.bytes_sent += len(data)
            self._stats.last_activity = time.time()
            return True

        except serial.SerialTimeoutException:
            self._set_error("Write timeout — controller may be busy")
            return False
        except serial.SerialException as e:
            self._set_error(f"Serial write error: {e}")
            return False

    def send_line(self, line: str, add_newline: bool = True) -> bool:
        """Send a line of text (G-code) to the controller."""
        if add_newline and not line.endswith('\n'):
            line += '\n'

        result = self.send_bytes(line.encode('ascii', errors='replace'))
        if result:
            self._stats.lines_sent += 1

            # Inter-line delay
            if self.config.line_delay > 0:
                time.sleep(self.config.line_delay)

        return result

    def send_xon(self):
        """Send XON to controller (resume)."""
        if self.is_connected:
            with self._lock:
                self._serial.write(self.XON)

    def send_xoff(self):
        """Send XOFF to controller (pause)."""
        if self.is_connected:
            with self._lock:
                self._serial.write(self.XOFF)

    def flush(self):
        """Flush output buffer."""
        if self.is_connected:
            with self._lock:
                self._serial.flush()

    def reset_buffers(self):
        """Clear input and output buffers."""
        if self.is_connected:
            with self._lock:
                self._serial.reset_input_buffer()
                self._serial.reset_output_buffer()

    # --- Port Status ---

    def get_port_status(self) -> dict:
        """Get current status of serial port signals."""
        if not self.is_connected:
            return {
                "cts": False, "dsr": False, "ri": False, "cd": False,
                "rts": False, "dtr": False,
            }
        try:
            return {
                "cts": self._serial.cts,
                "dsr": self._serial.dsr,
                "ri": self._serial.ri,
                "cd": self._serial.cd,
                "rts": self._serial.rts,
                "dtr": self._serial.dtr,
            }
        except Exception:
            return {
                "cts": False, "dsr": False, "ri": False, "cd": False,
                "rts": False, "dtr": False,
            }

    # --- Internal Methods ---

    def _read_loop(self):
        """Background thread: continuously read from serial port."""
        while self._running:
            try:
                if not self._serial or not self._serial.is_open:
                    break

                data = self._serial.read(self._serial.in_waiting or 1)
                if not data:
                    continue

                self._stats.bytes_received += len(data)
                self._stats.last_activity = time.time()

                # Process XON/XOFF in received data
                cleaned_data = bytearray()
                for byte in data:
                    if byte == self.XON[0]:
                        self._xoff_event.set()
                        self._stats.xon_count += 1
                        if self._on_flow_control:
                            self._on_flow_control(True)
                    elif byte == self.XOFF[0]:
                        self._xoff_event.clear()
                        self._stats.xoff_count += 1
                        if self._on_flow_control:
                            self._on_flow_control(False)
                    else:
                        cleaned_data.append(byte)

                if cleaned_data:
                    # Raw data callback
                    if self._on_data_received:
                        self._on_data_received(bytes(cleaned_data))

                    # Buffer for line-based callback
                    self._receive_buffer.extend(cleaned_data)
                    self._process_line_buffer()

            except serial.SerialException as e:
                if self._running:
                    self._set_error(f"Serial read error: {e}")
                break
            except Exception as e:
                if self._running:
                    logger.error(f"Read thread error: {e}")
                break

        logger.debug("Read thread exiting")

    def _process_line_buffer(self):
        """Extract complete lines from receive buffer and invoke callback."""
        while b'\n' in self._receive_buffer or b'\r' in self._receive_buffer:
            # Find line terminator
            idx_n = self._receive_buffer.find(b'\n')
            idx_r = self._receive_buffer.find(b'\r')
            
            if idx_n >= 0 and (idx_r < 0 or idx_n < idx_r):
                idx = idx_n
            elif idx_r >= 0:
                idx = idx_r
            else:
                break

            line_bytes = bytes(self._receive_buffer[:idx])
            self._receive_buffer = self._receive_buffer[idx + 1:]
            
            # Skip empty / whitespace-only lines
            line = line_bytes.decode('ascii', errors='replace').strip()
            if line:
                self._stats.lines_received += 1
                if self._on_line_received:
                    self._on_line_received(line)

    def _set_state(self, state: ConnectionState):
        """Update connection state and invoke callback."""
        self._state = state
        logger.debug(f"Connection state: {state.value}")
        if self._on_state_changed:
            self._on_state_changed(state)

    def _set_error(self, message: str):
        """Log error, update state, and invoke callback."""
        logger.error(message)
        self._stats.errors += 1
        self._state = ConnectionState.ERROR
        if self._on_error:
            self._on_error(message)

    # --- Context Manager ---

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
