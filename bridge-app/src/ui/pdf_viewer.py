"""
CNC Bridge — Embedded PDF Page Viewer

Renders scanned PDF pages as images using PyMuPDF (fitz).
Supports page navigation, zoom, and full-screen viewing.
"""

import os
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QSlider, QSizePolicy, QComboBox,
)
from PyQt6.QtCore import Qt, QSize, QPoint, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage, QCursor, QMouseEvent

try:
    import fitz  # PyMuPDF
    HAS_FITZ = True
except ImportError:
    HAS_FITZ = False


# Default path to the Anilam PDF collection
ANILAM_PDF_DIR = Path(r"F:\anilam\Anilam crusader m")


class PdfPageViewer(QWidget):
    """Widget that renders and displays individual PDF pages as images."""

    page_changed = pyqtSignal(int, int)  # current_page, total_pages

    def __init__(self, parent=None):
        super().__init__(parent)
        self._doc = None
        self._current_page = 0
        self._total_pages = 0
        self._zoom = 2.0  # render at 2× for clarity (144 DPI)
        self._pdf_path: Optional[str] = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # ── Navigation toolbar ──
        nav_bar = QFrame()
        nav_bar.setStyleSheet("QFrame { background: #0f3460; border-radius: 4px; }")
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(8, 4, 8, 4)
        nav_layout.setSpacing(6)

        self._btn_first = QPushButton("⏮")
        self._btn_prev = QPushButton("◀")
        self._page_label = QLabel("Page 0 / 0")
        self._page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._page_label.setStyleSheet("color: #e0e0e0; font-size: 12px; min-width: 90px;")
        self._btn_next = QPushButton("▶")
        self._btn_last = QPushButton("⏭")

        for btn in (self._btn_first, self._btn_prev, self._btn_next, self._btn_last):
            btn.setFixedSize(32, 28)
            btn.setStyleSheet("""
                QPushButton {
                    background: #1a1a2e; color: #e0e0e0; border: 1px solid #1a1a4e;
                    border-radius: 4px; font-size: 14px;
                }
                QPushButton:hover { background: #e94560; color: white; }
                QPushButton:disabled { background: #111; color: #444; }
            """)

        self._btn_first.clicked.connect(lambda: self.go_to_page(0))
        self._btn_prev.clicked.connect(lambda: self.go_to_page(self._current_page - 1))
        self._btn_next.clicked.connect(lambda: self.go_to_page(self._current_page + 1))
        self._btn_last.clicked.connect(lambda: self.go_to_page(self._total_pages - 1))

        nav_layout.addWidget(self._btn_first)
        nav_layout.addWidget(self._btn_prev)
        nav_layout.addWidget(self._page_label)
        nav_layout.addWidget(self._btn_next)
        nav_layout.addWidget(self._btn_last)
        nav_layout.addStretch()

        # Zoom controls
        zoom_label = QLabel("Zoom:")
        zoom_label.setStyleSheet("color: #8899aa; font-size: 11px;")
        nav_layout.addWidget(zoom_label)

        self._zoom_combo = QComboBox()
        self._zoom_combo.addItems(["75%", "100%", "125%", "150%", "200%", "250%", "300%"])
        self._zoom_combo.setCurrentText("200%")
        self._zoom_combo.setStyleSheet("""
            QComboBox {
                background: #1a1a2e; color: #e0e0e0; border: 1px solid #1a1a4e;
                border-radius: 4px; padding: 2px 8px; font-size: 11px; min-width: 60px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #0f3460; color: #e0e0e0;
                selection-background-color: #e94560;
            }
        """)
        self._zoom_combo.currentTextChanged.connect(self._on_zoom_changed)
        nav_layout.addWidget(self._zoom_combo)

        # PDF filename label
        self._file_label = QLabel("")
        self._file_label.setStyleSheet("color: #667788; font-size: 11px;")
        self._file_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        nav_layout.addWidget(self._file_label, stretch=1)

        layout.addWidget(nav_bar)

        # ── Scrollable image area ──
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(False)
        self._scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._scroll.setStyleSheet("""
            QScrollArea { background: #111; border: none; }
            QScrollBar:vertical {
                background: #1a1a2e; width: 10px;
            }
            QScrollBar::handle:vertical {
                background: #0f3460; border-radius: 5px; min-height: 30px;
            }
            QScrollBar:horizontal {
                background: #1a1a2e; height: 10px;
            }
            QScrollBar::handle:horizontal {
                background: #0f3460; border-radius: 5px; min-width: 30px;
            }
        """)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self._image_label.setStyleSheet("background: #111; padding: 8px;")
        self._scroll.setWidget(self._image_label)

        # Enable mouse drag-to-pan (grab hand)
        self._scroll.viewport().setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        self._dragging = False
        self._drag_start = QPoint()
        self._scroll_start_h = 0
        self._scroll_start_v = 0
        self._scroll.viewport().installEventFilter(self)

        layout.addWidget(self._scroll, stretch=1)

        self._update_nav_buttons()

    def load_pdf(self, pdf_path: str) -> bool:
        """Load a PDF file for viewing. Returns True on success."""
        if not HAS_FITZ:
            self._show_error("PyMuPDF (fitz) is not installed.\nInstall: pip install PyMuPDF")
            return False

        full_path = pdf_path
        if not os.path.isabs(pdf_path):
            full_path = str(ANILAM_PDF_DIR / pdf_path)

        if not os.path.exists(full_path):
            self._show_error(f"PDF not found:\n{full_path}")
            return False

        try:
            if self._doc:
                self._doc.close()
            self._doc = fitz.open(full_path)
            self._total_pages = len(self._doc)
            self._current_page = 0
            self._pdf_path = full_path
            self._file_label.setText(os.path.basename(full_path))
            self._render_current_page()
            return True
        except Exception as e:
            self._show_error(f"Error opening PDF:\n{e}")
            return False

    def go_to_page(self, page: int):
        """Navigate to a specific page (0-indexed)."""
        if self._doc is None or self._total_pages == 0:
            return
        page = max(0, min(page, self._total_pages - 1))
        if page != self._current_page:
            self._current_page = page
            self._render_current_page()
            self.page_changed.emit(self._current_page, self._total_pages)

    def _render_current_page(self):
        """Render the current page to a QPixmap and display it."""
        if self._doc is None or self._total_pages == 0:
            return

        try:
            page = self._doc[self._current_page]
            # Render at zoom factor (1.0 = 72 DPI, 2.0 = 144 DPI)
            mat = fitz.Matrix(self._zoom, self._zoom)
            pix = page.get_pixmap(matrix=mat)

            # Convert to QImage → QPixmap
            if pix.alpha:
                fmt = QImage.Format.Format_RGBA8888
            else:
                fmt = QImage.Format.Format_RGB888

            img = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
            pixmap = QPixmap.fromImage(img)

            self._image_label.setPixmap(pixmap)
            self._image_label.adjustSize()

        except Exception as e:
            self._show_error(f"Error rendering page {self._current_page + 1}:\n{e}")

        self._update_nav_buttons()

    def _update_nav_buttons(self):
        """Enable/disable navigation buttons based on current page."""
        has_doc = self._doc is not None and self._total_pages > 0
        at_first = self._current_page <= 0
        at_last = self._current_page >= self._total_pages - 1

        self._btn_first.setEnabled(has_doc and not at_first)
        self._btn_prev.setEnabled(has_doc and not at_first)
        self._btn_next.setEnabled(has_doc and not at_last)
        self._btn_last.setEnabled(has_doc and not at_last)

        if has_doc:
            self._page_label.setText(f"Page {self._current_page + 1} / {self._total_pages}")
        else:
            self._page_label.setText("No document")

    def _on_zoom_changed(self, text: str):
        """Handle zoom level change."""
        try:
            self._zoom = int(text.replace("%", "")) / 100.0
            if self._doc:
                self._render_current_page()
        except ValueError:
            pass

    def _show_error(self, msg: str):
        """Display error message in the image area."""
        self._image_label.setPixmap(QPixmap())
        self._image_label.setText(msg)
        self._image_label.setStyleSheet("color: #e94560; font-size: 14px; padding: 40px; background: #111;")

    # ── Zoom presets for scroll-wheel stepping ──
    _ZOOM_STEPS = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0, 4.0]

    def eventFilter(self, obj, event):
        """Handle mouse events on the scroll viewport for drag-to-pan and scroll-wheel zoom."""
        if obj is self._scroll.viewport():
            # ── Drag-to-pan ──
            if event.type() == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._dragging = True
                self._drag_start = event.globalPosition().toPoint()
                self._scroll_start_h = self._scroll.horizontalScrollBar().value()
                self._scroll_start_v = self._scroll.verticalScrollBar().value()
                self._scroll.viewport().setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
                return True
            elif event.type() == event.Type.MouseMove and self._dragging:
                delta = event.globalPosition().toPoint() - self._drag_start
                self._scroll.horizontalScrollBar().setValue(self._scroll_start_h - delta.x())
                self._scroll.verticalScrollBar().setValue(self._scroll_start_v - delta.y())
                return True
            elif event.type() == event.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self._dragging = False
                self._scroll.viewport().setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
                return True

            # ── Scroll-wheel zoom ──
            if event.type() == event.Type.Wheel:
                delta = event.angleDelta().y()
                if delta != 0:
                    # Find current position in zoom steps
                    cur = self._zoom
                    if delta > 0:  # scroll up = zoom in
                        new_zoom = cur
                        for z in self._ZOOM_STEPS:
                            if z > cur + 0.01:
                                new_zoom = z
                                break
                        else:
                            new_zoom = self._ZOOM_STEPS[-1]
                    else:  # scroll down = zoom out
                        new_zoom = cur
                        for z in reversed(self._ZOOM_STEPS):
                            if z < cur - 0.01:
                                new_zoom = z
                                break
                        else:
                            new_zoom = self._ZOOM_STEPS[0]
                    if abs(new_zoom - cur) > 0.01:
                        self._zoom = new_zoom
                        # Update combo box text (without triggering re-render)
                        pct = f"{int(new_zoom * 100)}%"
                        self._zoom_combo.blockSignals(True)
                        idx = self._zoom_combo.findText(pct)
                        if idx >= 0:
                            self._zoom_combo.setCurrentIndex(idx)
                        else:
                            self._zoom_combo.setCurrentText(pct)
                        self._zoom_combo.blockSignals(False)
                        if self._doc:
                            self._render_current_page()
                    return True

        return super().eventFilter(obj, event)

    def close_doc(self):
        """Close the current PDF document."""
        if self._doc:
            self._doc.close()
            self._doc = None
        self._total_pages = 0
        self._current_page = 0
        self._image_label.setPixmap(QPixmap())
        self._file_label.setText("")
        self._update_nav_buttons()

    def __del__(self):
        self.close_doc()
