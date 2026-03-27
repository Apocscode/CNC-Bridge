"""
CNC Bridge — Settings Persistence

Saves and restores user preferences between sessions using JSON config.
Stores: window geometry, last COM port, serial settings, connection profiles,
last opened file, and general preferences.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
CONFIG_FILE = CONFIG_DIR / "settings.json"
PROFILES_FILE = CONFIG_DIR / "connection_profiles.json"
TOOL_LIBRARY_FILE = CONFIG_DIR / "tool_library.json"
BACKUP_DIR = Path(__file__).parent.parent.parent / "backups"
LOG_DIR = Path(__file__).parent.parent.parent / "logs"


@dataclass
class WindowSettings:
    """Window geometry and layout preferences."""
    x: int = 100
    y: int = 100
    width: int = 1400
    height: int = 900
    maximized: bool = False
    last_tab: int = 0
    theme: str = "dark"          # "dark" or "light"
    touch_mode: bool = False     # larger buttons for touch screens


@dataclass
class SerialSettings:
    """Last-used serial port settings."""
    port: str = ""
    baud_rate: int = 4800
    data_bits: int = 7
    parity: str = "Even"
    stop_bits: str = "2"
    flow_control: str = "XON/XOFF"


@dataclass
class TransferSettings:
    """DNC transfer preferences."""
    last_directory: str = ""
    default_mode: str = "Upload"
    auto_backup: bool = True
    log_serial_traffic: bool = True


@dataclass
class ConnectionProfile:
    """A saved RS232 connection profile."""
    name: str = ""
    port: str = ""
    baud_rate: int = 4800
    data_bits: int = 7
    parity: str = "Even"
    stop_bits: str = "2"
    flow_control: str = "XON/XOFF"
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ConnectionProfile":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ToolEntry:
    """A tool in the tool library."""
    number: int = 1
    diameter: float = 0.0
    length: float = 0.0
    description: str = ""
    material: str = ""
    flutes: int = 0
    max_rpm: int = 0
    max_feed: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ToolEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def t_code(self) -> str:
        """Get Anilam T10xx format tool table line."""
        return f"T{1000 + self.number} X{self.diameter:.4f} Z{self.length:.4f}"


class AppSettings:
    """Application settings manager — load/save JSON config."""

    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        LOG_DIR.mkdir(parents=True, exist_ok=True)

        self.window = WindowSettings()
        self.serial = SerialSettings()
        self.transfer = TransferSettings()
        self.recent_files: list[str] = []
        self.profiles: list[ConnectionProfile] = []
        self.tools: list[ToolEntry] = []

        self.load()
        self._load_profiles()
        self._load_tools()

    # ── Main Settings ────────────────────────────────────────────

    def load(self):
        """Load settings from JSON config file."""
        if not CONFIG_FILE.exists():
            logger.info("No config file found, using defaults")
            return

        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)

            # Window
            if 'window' in data:
                w = data['window']
                self.window = WindowSettings(
                    x=w.get('x', 100), y=w.get('y', 100),
                    width=w.get('width', 1400), height=w.get('height', 900),
                    maximized=w.get('maximized', False),
                    last_tab=w.get('last_tab', 0),
                    theme=w.get('theme', 'dark'),
                    touch_mode=w.get('touch_mode', False),
                )

            # Serial
            if 'serial' in data:
                s = data['serial']
                self.serial = SerialSettings(
                    port=s.get('port', ''),
                    baud_rate=s.get('baud_rate', 4800),
                    data_bits=s.get('data_bits', 7),
                    parity=s.get('parity', 'Even'),
                    stop_bits=s.get('stop_bits', '2'),
                    flow_control=s.get('flow_control', 'XON/XOFF'),
                )

            # Transfer
            if 'transfer' in data:
                t = data['transfer']
                self.transfer = TransferSettings(
                    last_directory=t.get('last_directory', ''),
                    default_mode=t.get('default_mode', 'Upload'),
                    auto_backup=t.get('auto_backup', True),
                    log_serial_traffic=t.get('log_serial_traffic', True),
                )

            # Recent files
            self.recent_files = data.get('recent_files', [])[:10]

            logger.info(f"Settings loaded from {CONFIG_FILE}")

        except Exception as e:
            logger.error(f"Failed to load settings: {e}")

    def save(self):
        """Save current settings to JSON config file."""
        try:
            data = {
                'window': asdict(self.window),
                'serial': asdict(self.serial),
                'transfer': asdict(self.transfer),
                'recent_files': self.recent_files[:10],
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Settings saved to {CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def add_recent_file(self, filepath: str):
        """Add a file to the recent files list."""
        filepath = str(Path(filepath).resolve())
        if filepath in self.recent_files:
            self.recent_files.remove(filepath)
        self.recent_files.insert(0, filepath)
        self.recent_files = self.recent_files[:10]
        self.save()

    # ── Connection Profiles ──────────────────────────────────────

    def _load_profiles(self):
        """Load connection profiles from JSON."""
        if not PROFILES_FILE.exists():
            # Create default profiles
            self.profiles = [
                ConnectionProfile(
                    name="Crusader M (Default)",
                    baud_rate=4800, data_bits=7, parity="Even",
                    stop_bits="2", flow_control="XON/XOFF",
                    description="Anilam Crusader M — Supermax-30 factory defaults"
                ),
                ConnectionProfile(
                    name="Crusader II",
                    baud_rate=2400, data_bits=7, parity="None",
                    stop_bits="1", flow_control="None",
                    description="Anilam Crusader II RS232 defaults"
                ),
            ]
            self.save_profiles()
            return

        try:
            with open(PROFILES_FILE, 'r') as f:
                data = json.load(f)
            self.profiles = [ConnectionProfile.from_dict(p) for p in data]
            logger.info(f"Loaded {len(self.profiles)} connection profiles")
        except Exception as e:
            logger.error(f"Failed to load profiles: {e}")
            self.profiles = []

    def save_profiles(self):
        """Save connection profiles to JSON."""
        try:
            data = [p.to_dict() for p in self.profiles]
            with open(PROFILES_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(self.profiles)} profiles")
        except Exception as e:
            logger.error(f"Failed to save profiles: {e}")

    def add_profile(self, profile: ConnectionProfile):
        """Add or update a connection profile."""
        # Replace if name exists
        self.profiles = [p for p in self.profiles if p.name != profile.name]
        self.profiles.append(profile)
        self.save_profiles()

    def delete_profile(self, name: str):
        """Delete a profile by name."""
        self.profiles = [p for p in self.profiles if p.name != name]
        self.save_profiles()

    def get_profile(self, name: str) -> Optional[ConnectionProfile]:
        """Get a profile by name."""
        for p in self.profiles:
            if p.name == name:
                return p
        return None

    # ── Tool Library ─────────────────────────────────────────────

    def _load_tools(self):
        """Load tool library from JSON."""
        if not TOOL_LIBRARY_FILE.exists():
            self.tools = []
            return

        try:
            with open(TOOL_LIBRARY_FILE, 'r') as f:
                data = json.load(f)
            self.tools = [ToolEntry.from_dict(t) for t in data]
            logger.info(f"Loaded {len(self.tools)} tools")
        except Exception as e:
            logger.error(f"Failed to load tool library: {e}")
            self.tools = []

    def save_tools(self):
        """Save tool library to JSON."""
        try:
            data = [t.to_dict() for t in self.tools]
            with open(TOOL_LIBRARY_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(self.tools)} tools")
        except Exception as e:
            logger.error(f"Failed to save tool library: {e}")

    def add_tool(self, tool: ToolEntry):
        """Add or update a tool (by number)."""
        self.tools = [t for t in self.tools if t.number != tool.number]
        self.tools.append(tool)
        self.tools.sort(key=lambda t: t.number)
        self.save_tools()

    def delete_tool(self, number: int):
        """Delete a tool by number."""
        self.tools = [t for t in self.tools if t.number != number]
        self.save_tools()

    def get_tool(self, number: int) -> Optional[ToolEntry]:
        """Get a tool by number."""
        for t in self.tools:
            if t.number == number:
                return t
        return None

    def generate_tool_table(self) -> str:
        """Generate Anilam T10xx tool table block for G-code."""
        if not self.tools:
            return ""
        lines = ["(TOOL TABLE)"]
        for t in self.tools:
            comment = f" ({t.description})" if t.description else ""
            lines.append(f"T{1000 + t.number} X{t.diameter:.4f} Z{t.length:.4f}{comment}")
        return "\n".join(lines)
