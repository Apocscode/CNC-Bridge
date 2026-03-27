"""
CNC Bridge — Application Entry Point

Launch the CNC Bridge desktop application for communicating
with the Anilam Crusader M controller via RS232 serial.

Usage:
    python -m src.main
    python main.py
"""

import sys
import logging
from pathlib import Path

# Setup structured logging (rotating files + console)
from .core.error_logger import setup_logging
setup_logging(level=logging.DEBUG, console=True)
logger = logging.getLogger("CNCBridge")


def main():
    """Launch the CNC Bridge application."""
    logger.info("Starting CNC Bridge v3.0.0")

    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtGui import QFont
        from .ui.main_window import MainWindow
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        print(f"\nError: {e}")
        print("Install dependencies: pip install -r requirements.txt")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName("CNC Bridge")
    app.setApplicationVersion("3.0.0")
    app.setOrganizationName("CNC Bridge Project")

    # Default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Create and show main window
    window = MainWindow()
    window.show()

    logger.info("Application ready")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
