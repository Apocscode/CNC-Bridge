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

# Setup logging before imports
LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "cnc_bridge.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("CNCBridge")


def main():
    """Launch the CNC Bridge application."""
    logger.info("Starting CNC Bridge v1.0.0")

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
    app.setApplicationVersion("1.0.0")
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
