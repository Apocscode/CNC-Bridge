"""
CNC Bridge — Unit Tests: Settings, Profiles, Backup Vault, Traffic Logger, Update Checker

Tests for non-GUI core modules.
"""

import json
import os
import sys
import tempfile
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "bridge-app"))

from src.core.settings import (
    AppSettings, WindowSettings, SerialSettings, TransferSettings,
    ConnectionProfile, ToolEntry,
    CONFIG_DIR, CONFIG_FILE, PROFILES_FILE, TOOL_LIBRARY_FILE,
)
from src.core.traffic_logger import SerialTrafficLogger
from src.core.backup_vault import ProgramBackupVault, BackupRecord
from src.core.update_checker import _compare_versions, CURRENT_VERSION


# ── ConnectionProfile ────────────────────────────────────────────

class TestConnectionProfile:
    def test_round_trip(self):
        p = ConnectionProfile(
            name="Test", port="COM3", baud_rate=9600,
            data_bits=8, parity="None", stop_bits="1",
            flow_control="None", description="Test profile"
        )
        d = p.to_dict()
        p2 = ConnectionProfile.from_dict(d)
        assert p2.name == "Test"
        assert p2.baud_rate == 9600
        assert p2.parity == "None"

    def test_from_dict_ignores_extra_keys(self):
        d = {"name": "Test", "baud_rate": 4800, "unknown_key": "ignored"}
        p = ConnectionProfile.from_dict(d)
        assert p.name == "Test"
        assert p.baud_rate == 4800


# ── ToolEntry ────────────────────────────────────────────────────

class TestToolEntry:
    def test_round_trip(self):
        t = ToolEntry(number=5, diameter=0.5, length=3.0,
                      description="End Mill", flutes=4)
        d = t.to_dict()
        t2 = ToolEntry.from_dict(d)
        assert t2.number == 5
        assert t2.diameter == 0.5
        assert t2.flutes == 4

    def test_t_code(self):
        t = ToolEntry(number=3, diameter=0.25, length=2.5)
        assert t.t_code == "T1003 X0.2500 Z2.5000"

    def test_t_code_large_number(self):
        t = ToolEntry(number=99, diameter=1.0, length=5.0)
        assert t.t_code == "T1099 X1.0000 Z5.0000"


# ── Version Comparison ──────────────────────────────────────────

class TestVersionCompare:
    def test_equal(self):
        assert _compare_versions("1.0.0", "1.0.0") == 0

    def test_newer(self):
        assert _compare_versions("2.0.0", "1.0.0") > 0

    def test_older(self):
        assert _compare_versions("1.0.0", "2.0.0") < 0

    def test_minor(self):
        assert _compare_versions("1.1.0", "1.0.0") > 0

    def test_patch(self):
        assert _compare_versions("1.0.1", "1.0.0") > 0

    def test_different_lengths(self):
        assert _compare_versions("1.0", "1.0.0") == 0

    def test_major_difference(self):
        assert _compare_versions("2.0.0", "1.9.9") > 0


# ── SerialTrafficLogger ─────────────────────────────────────────

class TestSerialTrafficLogger:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.logger = SerialTrafficLogger(log_dir=self.tmpdir)

    def teardown_method(self):
        self.logger.stop_session()
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_start_creates_file(self):
        self.logger.start_session("COM3", 4800)
        assert self.logger.filepath is not None
        assert self.logger.filepath.exists()

    def test_log_tx_rx(self):
        self.logger.start_session("COM3", 4800)
        self.logger.log_tx("G01 X1.0 Y1.0")
        self.logger.log_rx("OK")
        self.logger.stop_session()

        content = self.logger.filepath.read_text()
        assert "TX:" in content
        assert "RX:" in content
        assert "G01" in content

    def test_log_event(self):
        self.logger.start_session("COM3", 4800)
        self.logger.log_event("Connected")
        self.logger.stop_session()

        content = self.logger.filepath.read_text()
        assert "EVENT: Connected" in content

    def test_disabled_does_not_log(self):
        self.logger.enabled = False
        self.logger.start_session("COM3", 4800)
        self.logger.log_tx("should not appear")
        self.logger.stop_session()

        content = self.logger.filepath.read_text()
        assert "should not appear" not in content

    def test_bytes_logged(self):
        self.logger.start_session("COM3", 4800)
        self.logger.log_tx("Hello")
        assert self.logger.bytes_logged == 5

    def test_session_files(self):
        self.logger.start_session("COM3", 4800)
        self.logger.stop_session()
        files = self.logger.get_session_files()
        assert len(files) >= 1


# ── ProgramBackupVault ───────────────────────────────────────────

class TestProgramBackupVault:
    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.vault = ProgramBackupVault(backup_dir=self.tmpdir)

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_backup_text(self):
        record = self.vault.backup_text(
            "G90\nG01 X1 Y1\nM30",
            name="test.nc", direction="sent", port="COM3"
        )
        assert record is not None
        assert record.original_name == "test.nc"
        assert record.direction == "sent"
        assert record.line_count == 3

    def test_backup_count(self):
        self.vault.backup_text("G90\nM30", name="a.nc")
        self.vault.backup_text("G91\nM30", name="b.nc")
        assert self.vault.backup_count == 2

    def test_get_backups_filtered(self):
        self.vault.backup_text("G90", name="sent.nc", direction="sent")
        self.vault.backup_text("G91", name="recv.nc", direction="received")
        sent = self.vault.get_backups(direction="sent")
        assert len(sent) == 1
        assert sent[0].direction == "sent"

    def test_backup_file(self):
        # Create a temp file to backup
        src = self.tmpdir / "source.nc"
        src.write_text("G90\nG01 X1\nM30")
        record = self.vault.backup_file(str(src), direction="sent")
        assert record is not None
        assert record.original_name == "source.nc"

    def test_delete_backup(self):
        record = self.vault.backup_text("G90", name="del.nc")
        assert self.vault.backup_count == 1
        self.vault.delete_backup(record.id)
        assert self.vault.backup_count == 0

    def test_disabled_returns_none(self):
        self.vault.enabled = False
        record = self.vault.backup_text("G90", name="nope.nc")
        assert record is None
        assert self.vault.backup_count == 0

    def test_restore_backup(self):
        record = self.vault.backup_text("G90\nM30", name="restore.nc")
        dest = self.tmpdir / "restored.nc"
        assert self.vault.restore_backup(record, str(dest))
        assert dest.exists()
        assert "G90" in dest.read_text()


# ── BackupRecord ─────────────────────────────────────────────────

class TestBackupRecord:
    def test_round_trip(self):
        r = BackupRecord(
            id="20250101_120000",
            original_name="test.nc",
            backup_path="/tmp/backup.nc",
            timestamp="2025-01-01 12:00:00",
            direction="sent",
            port="COM3",
            file_size=100,
            line_count=10,
        )
        d = r.to_dict()
        r2 = BackupRecord.from_dict(d)
        assert r2.id == r.id
        assert r2.original_name == r.original_name
        assert r2.file_size == 100
