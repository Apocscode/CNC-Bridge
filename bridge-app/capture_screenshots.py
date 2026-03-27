"""
Capture dashboard screenshots for README documentation.

Launches the app, auto-loads test data into each tab, and saves PNG screenshots.
Run:  python capture_screenshots.py
"""

import sys
import os
import time

# Ensure we can import the src package
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from src.ui.main_window import MainWindow

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "images")
TEST_FILE = os.path.join(os.path.dirname(__file__), "test_programs", "test_part_v1.txt")
TEST_FILE_2 = os.path.join(os.path.dirname(__file__), "test_programs", "test_part_v2.txt")


def capture_tab(window: MainWindow, tab_index: int, filename: str):
    """Switch to a tab and capture its screenshot."""
    window.tabs.setCurrentIndex(tab_index)
    QApplication.processEvents()
    time.sleep(0.3)
    QApplication.processEvents()

    # Grab the whole window
    screen = window.grab()
    filepath = os.path.join(OUTPUT_DIR, filename)
    screen.save(filepath, "PNG")
    print(f"  Saved: {filepath}")


def run_captures(window: MainWindow):
    """Load data and capture all tabs."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Read test file
    with open(TEST_FILE, 'r', encoding='utf-8') as f:
        test_code = f.read()

    print("Loading test data into tabs...")

    # --- Tab 0: G-code Viewer ---
    window.tabs.setCurrentIndex(0)
    QApplication.processEvents()
    window.gcode_viewer.load_file(TEST_FILE)
    QApplication.processEvents()
    # Run validation to show color-coded output
    window.gcode_viewer._validate()
    QApplication.processEvents()
    time.sleep(0.3)
    capture_tab(window, 0, "dashboard-gcode-viewer.png")

    # --- Tab 1: G-code Editor ---
    window.tabs.setCurrentIndex(1)
    QApplication.processEvents()
    window.gcode_editor.load_file(TEST_FILE)
    QApplication.processEvents()
    time.sleep(0.3)
    capture_tab(window, 1, "dashboard-gcode-editor.png")

    # --- Tab 2: Backplotter ---
    window.tabs.setCurrentIndex(2)
    QApplication.processEvents()
    window.backplotter.load_text(test_code, "test_part_v1.txt")
    QApplication.processEvents()
    time.sleep(0.5)
    capture_tab(window, 2, "dashboard-backplotter.png")

    # --- Tab 3: Serial Terminal ---
    capture_tab(window, 3, "dashboard-serial-terminal.png")

    # --- Tab 4: Tool Library ---
    # Import tools from the loaded code
    window.tabs.setCurrentIndex(4)
    QApplication.processEvents()
    from src.ui.tool_library import ToolLibraryPanel
    tools = ToolLibraryPanel._parse_tools_from_gcode(test_code)
    for tool in tools:
        window.tool_library._settings.add_tool(tool)
    window.tool_library._refresh_table()
    QApplication.processEvents()
    time.sleep(0.3)
    capture_tab(window, 4, "dashboard-tool-library.png")

    # --- Tab 5: File Diff ---
    window.tabs.setCurrentIndex(5)
    QApplication.processEvents()
    with open(TEST_FILE, 'r', encoding='utf-8') as f:
        text_a = f.read()
    with open(TEST_FILE_2, 'r', encoding='utf-8') as f:
        text_b = f.read()
    from pathlib import Path
    window.file_diff._load_texts(text_a, text_b,
                                  Path(TEST_FILE).name, Path(TEST_FILE_2).name)
    QApplication.processEvents()
    time.sleep(0.3)
    capture_tab(window, 5, "dashboard-file-diff.png")

    # --- Tab 6: Reference Library ---
    capture_tab(window, 6, "dashboard-reference-library.png")

    # --- Main overview (tab 0) ---
    capture_tab(window, 0, "dashboard-main.png")

    print(f"\nAll screenshots saved to {OUTPUT_DIR}")
    QApplication.quit()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()

    # Delay to let the window fully render
    QTimer.singleShot(1500, lambda: run_captures(window))

    app.exec()


if __name__ == "__main__":
    main()
