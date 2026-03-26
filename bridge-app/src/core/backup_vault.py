"""
CNC Bridge — Program Backup Vault

Automatically archives every G-code program sent to or received from
the controller. Each backup is timestamped and stored in the backups
directory with metadata (direction, port, file size, line count).
"""

import json
import shutil
import logging
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional

logger = logging.getLogger(__name__)

BACKUP_DIR = Path(__file__).parent.parent.parent / "backups"
MANIFEST_FILE = BACKUP_DIR / "manifest.json"


@dataclass
class BackupRecord:
    """A record of a backed-up program."""
    id: str = ""
    original_name: str = ""
    backup_path: str = ""
    timestamp: str = ""
    direction: str = ""  # "sent" or "received"
    port: str = ""
    file_size: int = 0
    line_count: int = 0
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BackupRecord":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class ProgramBackupVault:
    """Archives G-code programs sent/received with metadata."""

    def __init__(self, backup_dir: Optional[Path] = None):
        self._dir = backup_dir or BACKUP_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._manifest: list[BackupRecord] = []
        self._load_manifest()
        self._enabled = True

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value

    @property
    def backup_count(self) -> int:
        return len(self._manifest)

    def backup_file(self, filepath: str, direction: str = "sent",
                    port: str = "", notes: str = "") -> Optional[BackupRecord]:
        """Backup a file to the vault. Returns the backup record."""
        if not self._enabled:
            return None

        src = Path(filepath)
        if not src.exists():
            logger.error(f"Backup source not found: {filepath}")
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{timestamp}_{direction}_{src.name}"
            backup_path = self._dir / backup_name

            shutil.copy2(src, backup_path)

            # Count lines and get size
            with open(src, 'r', encoding='ascii', errors='replace') as f:
                content = f.read()
            line_count = content.count('\n') + 1
            file_size = src.stat().st_size

            record = BackupRecord(
                id=timestamp,
                original_name=src.name,
                backup_path=str(backup_path),
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                direction=direction,
                port=port,
                file_size=file_size,
                line_count=line_count,
                notes=notes,
            )

            self._manifest.append(record)
            self._save_manifest()

            logger.info(f"Backed up {src.name} → {backup_name}")
            return record

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return None

    def backup_text(self, text: str, name: str = "received_program.nc",
                    direction: str = "received", port: str = "",
                    notes: str = "") -> Optional[BackupRecord]:
        """Backup raw text (e.g., received from controller)."""
        if not self._enabled:
            return None

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{timestamp}_{direction}_{name}"
            backup_path = self._dir / backup_name

            with open(backup_path, 'w', encoding='ascii', errors='replace') as f:
                f.write(text)

            line_count = text.count('\n') + 1
            file_size = len(text.encode('ascii', errors='replace'))

            record = BackupRecord(
                id=timestamp,
                original_name=name,
                backup_path=str(backup_path),
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                direction=direction,
                port=port,
                file_size=file_size,
                line_count=line_count,
                notes=notes,
            )

            self._manifest.append(record)
            self._save_manifest()

            logger.info(f"Backed up text as {backup_name}")
            return record

        except Exception as e:
            logger.error(f"Text backup failed: {e}")
            return None

    def get_backups(self, direction: Optional[str] = None,
                    limit: int = 50) -> list[BackupRecord]:
        """Get backup records, newest first."""
        records = list(reversed(self._manifest))
        if direction:
            records = [r for r in records if r.direction == direction]
        return records[:limit]

    def restore_backup(self, record: BackupRecord, dest_path: str) -> bool:
        """Restore a backup to a destination path."""
        try:
            src = Path(record.backup_path)
            if not src.exists():
                logger.error(f"Backup file missing: {record.backup_path}")
                return False
            shutil.copy2(src, dest_path)
            logger.info(f"Restored {record.original_name} → {dest_path}")
            return True
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return False

    def delete_backup(self, record_id: str) -> bool:
        """Delete a backup by ID."""
        for r in self._manifest:
            if r.id == record_id:
                try:
                    Path(r.backup_path).unlink(missing_ok=True)
                except Exception:
                    pass
                self._manifest.remove(r)
                self._save_manifest()
                return True
        return False

    def _load_manifest(self):
        """Load manifest from JSON."""
        if not MANIFEST_FILE.exists():
            self._manifest = []
            return
        try:
            with open(MANIFEST_FILE, 'r') as f:
                data = json.load(f)
            self._manifest = [BackupRecord.from_dict(r) for r in data]
            logger.info(f"Loaded {len(self._manifest)} backup records")
        except Exception as e:
            logger.error(f"Failed to load backup manifest: {e}")
            self._manifest = []

    def _save_manifest(self):
        """Save manifest to JSON."""
        try:
            data = [r.to_dict() for r in self._manifest]
            with open(MANIFEST_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save backup manifest: {e}")
