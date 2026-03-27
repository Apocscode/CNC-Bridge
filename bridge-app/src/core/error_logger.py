"""
CNC Bridge — Error Logging System

Provides a centralized, file-rotating error logging system for the app.
Logs to:
  - logs/cnc_bridge.log        (all events, rotating)
  - logs/errors.log             (errors only)
  - Console (when running from terminal)

Each log entry includes timestamp, module, severity, and message.
Rotating file handler keeps logs from growing unbounded.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime

LOG_DIR = Path(__file__).parent.parent.parent / "logs"


def setup_logging(level: int = logging.DEBUG, console: bool = True) -> logging.Logger:
    """
    Configure the root logging for CNC Bridge.

    Args:
        level: Minimum log level for the main log file (default: DEBUG).
        console: Whether to also log to console (default: True).

    Returns:
        The root logger configured for the application.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Remove any existing handlers (prevent duplicates on re-init)
    root_logger.handlers.clear()

    # ── Format ──
    detailed_fmt = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    brief_fmt = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    # ── Main Log File (rotating, 5 MB x 5 backups) ──
    main_log = LOG_DIR / "cnc_bridge.log"
    main_handler = logging.handlers.RotatingFileHandler(
        main_log, maxBytes=5 * 1024 * 1024, backupCount=5,
        encoding="utf-8",
    )
    main_handler.setLevel(level)
    main_handler.setFormatter(detailed_fmt)
    root_logger.addHandler(main_handler)

    # ── Error-only Log File (rotating, 2 MB x 3 backups) ──
    error_log = LOG_DIR / "errors.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_log, maxBytes=2 * 1024 * 1024, backupCount=3,
        encoding="utf-8",
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_fmt)
    root_logger.addHandler(error_handler)

    # ── Console Handler ──
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(brief_fmt)
        root_logger.addHandler(console_handler)

    # Log startup marker
    root_logger.info("=" * 60)
    root_logger.info(f"CNC Bridge started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    root_logger.info(f"Log directory: {LOG_DIR}")
    root_logger.info("=" * 60)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a named logger for a specific module."""
    return logging.getLogger(name)
