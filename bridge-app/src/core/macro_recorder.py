"""
CNC Bridge — Macro Recorder

Records sequences of serial terminal commands and replays them.
Macros are saved as JSON files in the config/macros/ directory.
"""

import json
import logging
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, Callable

logger = logging.getLogger(__name__)

MACRO_DIR = Path(__file__).parent.parent.parent / "config" / "macros"


@dataclass
class MacroStep:
    """A single command in a macro sequence."""
    command: str = ""
    delay_ms: int = 500  # delay before sending this step (ms)
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "MacroStep":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Macro:
    """A recorded macro — a named sequence of serial commands."""
    name: str = ""
    description: str = ""
    steps: list[MacroStep] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Macro":
        steps = [MacroStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            steps=steps,
        )

    def save(self):
        """Save macro to JSON file."""
        MACRO_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in self.name)
        filepath = MACRO_DIR / f"{safe_name}.json"
        try:
            with open(filepath, "w") as f:
                json.dump(self.to_dict(), f, indent=2)
            logger.info(f"Macro saved: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save macro: {e}")

    @staticmethod
    def load(filepath: str) -> Optional["Macro"]:
        """Load macro from JSON file."""
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            return Macro.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load macro: {e}")
            return None

    @staticmethod
    def list_macros() -> list[tuple[str, str]]:
        """Return list of (name, filepath) for all saved macros."""
        MACRO_DIR.mkdir(parents=True, exist_ok=True)
        result = []
        for p in sorted(MACRO_DIR.glob("*.json")):
            try:
                with open(p, "r") as f:
                    data = json.load(f)
                result.append((data.get("name", p.stem), str(p)))
            except Exception:
                result.append((p.stem, str(p)))
        return result


class MacroRecorder:
    """Records terminal commands into a Macro."""

    def __init__(self):
        self.recording = False
        self._steps: list[MacroStep] = []
        self._last_time: float = 0

    def start(self):
        """Start recording."""
        self.recording = True
        self._steps = []
        self._last_time = time.time()
        logger.info("Macro recording started")

    def record_command(self, command: str):
        """Record a command with timing."""
        if not self.recording:
            return
        now = time.time()
        delay = int((now - self._last_time) * 1000)
        delay = min(delay, 10000)  # Cap at 10 seconds
        self._steps.append(MacroStep(command=command, delay_ms=delay))
        self._last_time = now

    def stop(self, name: str = "Untitled Macro", description: str = "") -> Macro:
        """Stop recording and return the Macro."""
        self.recording = False
        macro = Macro(name=name, description=description, steps=list(self._steps))
        self._steps = []
        logger.info(f"Macro recording stopped: {len(macro.steps)} steps")
        return macro


class MacroPlayer:
    """Plays back a macro by sending commands through a callback."""

    def __init__(self, send_callback: Callable[[str], None] = None):
        self.send = send_callback
        self.playing = False
        self._abort = False

    def play(self, macro: Macro,
             send_callback: Callable[[str], None] = None,
             on_step: Callable[[int, str], None] = None):
        """Play a macro. Blocks the calling thread. Call from a worker thread.
        
        Args:
            macro: The Macro to play
            send_callback: Override send function (uses constructor default if None)
            on_step: Optional callback(step_index, command) after each step
        """
        send_fn = send_callback or self.send
        if not send_fn:
            raise ValueError("No send_callback provided")

        self.playing = True
        self._abort = False
        logger.info(f"Playing macro: {macro.name} ({len(macro.steps)} steps)")

        for i, step in enumerate(macro.steps):
            if self._abort:
                break
            if step.delay_ms > 0 and i > 0:
                time.sleep(step.delay_ms / 1000.0)
            if self._abort:
                break
            send_fn(step.command)
            if on_step:
                on_step(i, step.command)

        self.playing = False
        logger.info("Macro playback finished")

    def abort(self):
        """Abort playback."""
        self._abort = True
