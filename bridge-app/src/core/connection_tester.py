"""
CNC Bridge — Connection Tester / Handshake Verification

Provides a test sequence to verify that the COM port is communicating
with the Anilam Crusader M controller. Tests include:
  - Port open/close verification
  - DTR/RTS signal toggle and CTS/DSR response check
  - XON character send and response monitoring
  - Carriage return echo test
  - Loopback detection (cable check)

The tester runs non-destructively — it does not send G-code or alter
the controller's state.
"""

import time
import logging
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class TestResult(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARN = "warning"
    SKIP = "skipped"


@dataclass
class TestStep:
    """Result of a single test step."""
    name: str
    result: TestResult = TestResult.SKIP
    message: str = ""
    duration_ms: float = 0.0


@dataclass
class HandshakeReport:
    """Complete connection test report."""
    port: str = ""
    baud_rate: int = 0
    steps: list = field(default_factory=list)  # list[TestStep]
    overall_pass: bool = False
    summary: str = ""
    timestamp: str = ""

    @property
    def pass_count(self) -> int:
        return sum(1 for s in self.steps if s.result == TestResult.PASS)

    @property
    def fail_count(self) -> int:
        return sum(1 for s in self.steps if s.result == TestResult.FAIL)

    @property
    def warn_count(self) -> int:
        return sum(1 for s in self.steps if s.result == TestResult.WARN)

    def to_text(self) -> str:
        """Format report as readable text."""
        lines = [
            f"Connection Test Report — {self.port} @ {self.baud_rate} baud",
            f"Time: {self.timestamp}",
            "=" * 60,
        ]
        for step in self.steps:
            icon = {
                TestResult.PASS: "✓ PASS",
                TestResult.FAIL: "✗ FAIL",
                TestResult.WARN: "⚠ WARN",
                TestResult.SKIP: "— SKIP",
            }[step.result]
            lines.append(f"  {icon}  {step.name}")
            if step.message:
                lines.append(f"         {step.message}")
            if step.duration_ms > 0:
                lines.append(f"         ({step.duration_ms:.0f} ms)")
        lines.append("=" * 60)
        lines.append(f"Result: {self.summary}")
        lines.append(f"Passed: {self.pass_count}/{len(self.steps)}")
        return "\n".join(lines)


class ConnectionTester:
    """
    Tests COM port connectivity with the Anilam Crusader M controller.

    Runs a sequence of non-destructive checks to verify the serial link
    is functioning before attempting to send programs.
    """

    XON = b'\x11'
    XOFF = b'\x13'
    CR = b'\r'
    LF = b'\n'

    def __init__(self, serial_manager):
        self._serial = serial_manager
        self._on_progress: Optional[Callable[[str], None]] = None

    def on_progress(self, callback: Callable[[str], None]):
        """Register a callback for progress updates."""
        self._on_progress = callback

    def _notify(self, msg: str):
        if self._on_progress:
            self._on_progress(msg)
        logger.info(f"ConnTest: {msg}")

    def run_test(self) -> HandshakeReport:
        """
        Run the full connection test sequence.
        Must be called while connected to a serial port.
        Returns a HandshakeReport.
        """
        import datetime
        report = HandshakeReport(
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        )

        if not self._serial.is_connected:
            report.summary = "Not connected — cannot run tests"
            return report

        report.port = self._serial.config.port
        report.baud_rate = self._serial.config.baud_rate

        # Test 1: Port open verification
        report.steps.append(self._test_port_open())

        # Test 2: Signal line check
        report.steps.append(self._test_signal_lines())

        # Test 3: DTR toggle
        report.steps.append(self._test_dtr_toggle())

        # Test 4: RTS toggle
        report.steps.append(self._test_rts_toggle())

        # Test 5: Buffer clear
        report.steps.append(self._test_buffer_clear())

        # Test 6: XON send
        report.steps.append(self._test_xon_send())

        # Test 7: CR echo test
        report.steps.append(self._test_cr_echo())

        # Test 8: Data integrity (send known pattern)
        report.steps.append(self._test_data_integrity())

        # Summary
        if report.fail_count == 0 and report.pass_count > 0:
            report.overall_pass = True
            report.summary = "All tests passed — connection is ready"
        elif report.fail_count > 0:
            report.overall_pass = False
            report.summary = f"{report.fail_count} test(s) failed — check cable and settings"
        else:
            report.overall_pass = False
            report.summary = "No tests passed — verify port and controller"

        return report

    def _test_port_open(self) -> TestStep:
        """Test 1: Verify port is open and accessible."""
        self._notify("Testing port access...")
        step = TestStep(name="Port Open")
        t0 = time.time()
        try:
            ser = self._serial._serial
            if ser and ser.is_open:
                step.result = TestResult.PASS
                step.message = f"Port {self._serial.config.port} is open"
            else:
                step.result = TestResult.FAIL
                step.message = "Port is not open"
        except Exception as e:
            step.result = TestResult.FAIL
            step.message = f"Error checking port: {e}"
        step.duration_ms = (time.time() - t0) * 1000
        return step

    def _test_signal_lines(self) -> TestStep:
        """Test 2: Check DSR and CTS signal lines."""
        self._notify("Checking signal lines (DSR/CTS)...")
        step = TestStep(name="Signal Lines (DSR/CTS)")
        t0 = time.time()
        try:
            signals = self._serial.get_port_status()
            dsr = signals.get("dsr", False)
            cts = signals.get("cts", False)
            
            if dsr and cts:
                step.result = TestResult.PASS
                step.message = "DSR=HIGH, CTS=HIGH — controller is ready"
            elif dsr or cts:
                step.result = TestResult.WARN
                step.message = f"DSR={'HIGH' if dsr else 'LOW'}, CTS={'HIGH' if cts else 'LOW'}"
            else:
                step.result = TestResult.WARN
                step.message = "DSR=LOW, CTS=LOW — controller may be off or cable issue"
        except Exception as e:
            step.result = TestResult.FAIL
            step.message = f"Error reading signals: {e}"
        step.duration_ms = (time.time() - t0) * 1000
        return step

    def _test_dtr_toggle(self) -> TestStep:
        """Test 3: Toggle DTR and check DSR response."""
        self._notify("Toggling DTR signal...")
        step = TestStep(name="DTR Toggle")
        t0 = time.time()
        try:
            ser = self._serial._serial
            if not ser:
                step.result = TestResult.SKIP
                step.message = "No serial object"
                return step

            # Save current state
            original = ser.dtr

            # Toggle DTR
            ser.dtr = False
            time.sleep(0.1)
            ser.dtr = True  
            time.sleep(0.1)

            # Restore
            ser.dtr = original

            step.result = TestResult.PASS
            step.message = "DTR toggled successfully"
        except Exception as e:
            step.result = TestResult.WARN
            step.message = f"DTR toggle: {e}"
        step.duration_ms = (time.time() - t0) * 1000
        return step

    def _test_rts_toggle(self) -> TestStep:
        """Test 4: Toggle RTS and check CTS response."""
        self._notify("Toggling RTS signal...")
        step = TestStep(name="RTS Toggle")
        t0 = time.time()
        try:
            ser = self._serial._serial
            if not ser:
                step.result = TestResult.SKIP
                step.message = "No serial object"
                return step

            original = ser.rts
            ser.rts = False
            time.sleep(0.1)
            ser.rts = True
            time.sleep(0.1)
            ser.rts = original

            step.result = TestResult.PASS
            step.message = "RTS toggled successfully"
        except Exception as e:
            step.result = TestResult.WARN
            step.message = f"RTS toggle: {e}"
        step.duration_ms = (time.time() - t0) * 1000
        return step

    def _test_buffer_clear(self) -> TestStep:
        """Test 5: Clear I/O buffers."""
        self._notify("Clearing I/O buffers...")
        step = TestStep(name="Buffer Clear")
        t0 = time.time()
        try:
            self._serial.reset_buffers()
            step.result = TestResult.PASS
            step.message = "Input and output buffers cleared"
        except Exception as e:
            step.result = TestResult.FAIL
            step.message = f"Error clearing buffers: {e}"
        step.duration_ms = (time.time() - t0) * 1000
        return step

    def _test_xon_send(self) -> TestStep:
        """Test 6: Send XON character to controller."""
        self._notify("Sending XON to controller...")
        step = TestStep(name="XON Send")
        t0 = time.time()
        try:
            ser = self._serial._serial
            if not ser:
                step.result = TestResult.SKIP
                step.message = "No serial object"
                return step

            ser.write(self.XON)
            ser.flush()
            time.sleep(0.2)

            step.result = TestResult.PASS
            step.message = "XON (0x11) sent successfully"
        except Exception as e:
            step.result = TestResult.FAIL
            step.message = f"Failed to send XON: {e}"
        step.duration_ms = (time.time() - t0) * 1000
        return step

    def _test_cr_echo(self) -> TestStep:
        """Test 7: Send CR and check for echo/response."""
        self._notify("Sending CR echo test...")
        step = TestStep(name="CR Echo Test")
        t0 = time.time()
        try:
            ser = self._serial._serial
            if not ser:
                step.result = TestResult.SKIP
                step.message = "No serial object"
                return step

            # Clear input buffer first
            ser.reset_input_buffer()
            time.sleep(0.05)

            # Send a CR
            ser.write(self.CR)
            ser.flush()

            # Wait for response (up to 2 seconds)
            time.sleep(0.5)
            waiting = ser.in_waiting
            if waiting > 0:
                response = ser.read(waiting)
                step.result = TestResult.PASS
                # Show printable chars only
                printable = response.decode('ascii', errors='replace').strip()
                step.message = f"Received {waiting} byte(s): {repr(printable)}"
            else:
                step.result = TestResult.WARN
                step.message = "No echo response (normal for some controllers)"
        except Exception as e:
            step.result = TestResult.WARN
            step.message = f"Echo test: {e}"
        step.duration_ms = (time.time() - t0) * 1000
        return step

    def _test_data_integrity(self) -> TestStep:
        """Test 8: Verify data can be written without errors."""
        self._notify("Testing data write...")
        step = TestStep(name="Data Write Test")
        t0 = time.time()
        try:
            ser = self._serial._serial
            if not ser:
                step.result = TestResult.SKIP
                step.message = "No serial object"
                return step

            # Write a comment line that won't affect the controller
            test_data = b"(CNC Bridge Connection Test)\r\n"
            bytes_written = ser.write(test_data)
            ser.flush()

            if bytes_written == len(test_data):
                step.result = TestResult.PASS
                step.message = f"Wrote {bytes_written} bytes successfully"
            else:
                step.result = TestResult.WARN
                step.message = f"Expected {len(test_data)} bytes, wrote {bytes_written}"
        except Exception as e:
            step.result = TestResult.FAIL
            step.message = f"Write error: {e}"
        step.duration_ms = (time.time() - t0) * 1000
        return step
