"""
CNC Bridge — Unit Tests: Settings Persistence (AppSettings with temp config)

Tests for AppSettings load/save cycle using isolated temp directories.
"""

import json
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "bridge-app"))

from src.core.settings import (
    AppSettings, WindowSettings, SerialSettings,
    ConnectionProfile, ToolEntry,
)


class TestAppSettingsIsolated:
    """Tests that use monkey-patched config paths to avoid touching real config."""

    def setup_method(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.config_dir = self.tmpdir / "config"
        self.config_dir.mkdir()

        # Patch the module-level path constants
        import src.core.settings as settings_mod
        self._orig_config_dir = settings_mod.CONFIG_DIR
        self._orig_config_file = settings_mod.CONFIG_FILE
        self._orig_profiles_file = settings_mod.PROFILES_FILE
        self._orig_tool_library = settings_mod.TOOL_LIBRARY_FILE
        self._orig_backup_dir = settings_mod.BACKUP_DIR
        self._orig_log_dir = settings_mod.LOG_DIR

        settings_mod.CONFIG_DIR = self.config_dir
        settings_mod.CONFIG_FILE = self.config_dir / "settings.json"
        settings_mod.PROFILES_FILE = self.config_dir / "connection_profiles.json"
        settings_mod.TOOL_LIBRARY_FILE = self.config_dir / "tool_library.json"
        settings_mod.BACKUP_DIR = self.tmpdir / "backups"
        settings_mod.LOG_DIR = self.tmpdir / "logs"

    def teardown_method(self):
        import src.core.settings as settings_mod
        settings_mod.CONFIG_DIR = self._orig_config_dir
        settings_mod.CONFIG_FILE = self._orig_config_file
        settings_mod.PROFILES_FILE = self._orig_profiles_file
        settings_mod.TOOL_LIBRARY_FILE = self._orig_tool_library
        settings_mod.BACKUP_DIR = self._orig_backup_dir
        settings_mod.LOG_DIR = self._orig_log_dir
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_default_profiles_created(self):
        s = AppSettings()
        assert len(s.profiles) >= 2
        names = [p.name for p in s.profiles]
        assert "Crusader M (Default)" in names
        assert "Crusader II" in names

    def test_save_and_reload(self):
        s = AppSettings()
        s.serial.port = "COM7"
        s.serial.baud_rate = 9600
        s.window.width = 1600
        s.save()

        s2 = AppSettings()
        assert s2.serial.port == "COM7"
        assert s2.serial.baud_rate == 9600
        assert s2.window.width == 1600

    def test_add_recent_file(self):
        s = AppSettings()
        s.add_recent_file("C:\\test\\file1.nc")
        s.add_recent_file("C:\\test\\file2.nc")
        assert len(s.recent_files) == 2
        # Most recent first
        assert "file2.nc" in s.recent_files[0]

    def test_recent_files_dedup(self):
        s = AppSettings()
        s.add_recent_file("C:\\test\\file1.nc")
        s.add_recent_file("C:\\test\\file2.nc")
        s.add_recent_file("C:\\test\\file1.nc")
        assert len(s.recent_files) == 2
        assert "file1.nc" in s.recent_files[0]

    def test_add_profile(self):
        s = AppSettings()
        p = ConnectionProfile(name="Custom", baud_rate=19200, parity="None")
        s.add_profile(p)
        assert s.get_profile("Custom") is not None
        assert s.get_profile("Custom").baud_rate == 19200

    def test_delete_profile(self):
        s = AppSettings()
        initial = len(s.profiles)
        s.delete_profile("Crusader II")
        assert len(s.profiles) == initial - 1
        assert s.get_profile("Crusader II") is None

    def test_add_tool(self):
        s = AppSettings()
        t = ToolEntry(number=1, diameter=0.5, length=2.0, description="End Mill")
        s.add_tool(t)
        assert s.get_tool(1) is not None
        assert s.get_tool(1).diameter == 0.5

    def test_delete_tool(self):
        s = AppSettings()
        s.add_tool(ToolEntry(number=1, diameter=0.5, length=2.0))
        s.delete_tool(1)
        assert s.get_tool(1) is None

    def test_generate_tool_table(self):
        s = AppSettings()
        s.add_tool(ToolEntry(number=1, diameter=0.5, length=2.0, description="EM"))
        s.add_tool(ToolEntry(number=2, diameter=0.25, length=1.5))
        table = s.generate_tool_table()
        assert "(TOOL TABLE)" in table
        assert "T1001" in table
        assert "T1002" in table
        assert "(EM)" in table

    def test_tool_table_empty(self):
        s = AppSettings()
        assert s.generate_tool_table() == ""
