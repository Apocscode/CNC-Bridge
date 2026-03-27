"""
CNC Bridge — Program Library / Favorites

Manages a library of frequently-used G-code programs with
descriptions, tags, and quick-load capability.
Stored as JSON in config/program_library.json.
"""

import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

LIBRARY_FILE = Path(__file__).parent.parent.parent / "config" / "program_library.json"


@dataclass
class ProgramEntry:
    """A saved program in the library."""
    name: str = ""
    filepath: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=list)
    favorite: bool = False
    date_added: str = ""
    last_used: str = ""
    use_count: int = 0
    material: str = ""
    operation: str = ""  # e.g., "roughing", "finishing", "drilling"

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> "ProgramEntry":
        valid = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid)


class ProgramLibrary:
    """Manages a searchable library of G-code programs."""

    def __init__(self):
        self.entries: list[ProgramEntry] = []
        self.load()

    def load(self):
        """Load program library from JSON."""
        if not LIBRARY_FILE.exists():
            self.entries = []
            return
        try:
            with open(LIBRARY_FILE, "r") as f:
                data = json.load(f)
            self.entries = [ProgramEntry.from_dict(e) for e in data]
            logger.info(f"Loaded {len(self.entries)} programs from library")
        except Exception as e:
            logger.error(f"Failed to load program library: {e}")
            self.entries = []

    def save(self):
        """Save program library to JSON."""
        LIBRARY_FILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = [e.to_dict() for e in self.entries]
            with open(LIBRARY_FILE, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug(f"Saved {len(self.entries)} programs to library")
        except Exception as e:
            logger.error(f"Failed to save program library: {e}")

    def add(self, entry: ProgramEntry):
        """Add or update a program entry (by name)."""
        if not entry.date_added:
            entry.date_added = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.entries = [e for e in self.entries if e.name != entry.name]
        self.entries.append(entry)
        self.entries.sort(key=lambda e: e.name.lower())
        self.save()

    def remove(self, name: str):
        """Remove a program by name."""
        self.entries = [e for e in self.entries if e.name != name]
        self.save()

    def get(self, name: str) -> Optional[ProgramEntry]:
        """Get a program by name."""
        for e in self.entries:
            if e.name == name:
                return e
        return None

    def mark_used(self, name: str):
        """Mark a program as used (updates last_used and use_count)."""
        entry = self.get(name)
        if entry:
            entry.last_used = datetime.now().strftime("%Y-%m-%d %H:%M")
            entry.use_count += 1
            self.save()

    def toggle_favorite(self, name: str) -> bool:
        """Toggle favorite status. Returns new state."""
        entry = self.get(name)
        if entry:
            entry.favorite = not entry.favorite
            self.save()
            return entry.favorite
        return False

    def search(self, query: str) -> list[ProgramEntry]:
        """Search programs by name, description, tags, material, or operation."""
        q = query.lower()
        results = []
        for e in self.entries:
            searchable = f"{e.name} {e.description} {' '.join(e.tags)} {e.material} {e.operation}".lower()
            if q in searchable:
                results.append(e)
        return results

    def get_favorites(self) -> list[ProgramEntry]:
        """Return only favorited programs."""
        return [e for e in self.entries if e.favorite]

    def get_recent(self, count: int = 10) -> list[ProgramEntry]:
        """Return most recently used programs."""
        used = [e for e in self.entries if e.last_used]
        used.sort(key=lambda e: e.last_used, reverse=True)
        return used[:count]
