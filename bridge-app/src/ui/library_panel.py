"""
CNC Bridge — Searchable Reference Library Panel

Provides a PyQt6 widget with:
  - Full-text search bar with instant filtering
  - Category dropdown filter
  - Results tree with relevance sorting
  - Detailed entry view with rich formatting
  - Embedded PDF page viewer for scanned documents
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox,
    QTreeWidget, QTreeWidgetItem, QTextBrowser, QSplitter,
    QLabel, QFrame, QHeaderView, QPushButton, QStackedWidget,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor

from ..core.reference_library import (
    get_library, search_library, get_categories,
    get_entries_by_category, EntryCategory, ReferenceEntry
)
from .pdf_viewer import PdfPageViewer


class LibraryPanel(QWidget):
    """Searchable Anilam Crusader M reference library."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_entries = get_library()
        self._current_results = list(self._all_entries)
        self._current_entry = None
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(200)  # 200ms debounce
        self._search_timer.timeout.connect(self._do_search)
        self._init_ui()
        self._populate_results(self._all_entries)

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # ── Title bar ──
        title_bar = QFrame()
        title_bar.setStyleSheet("QFrame { background: #1a1a2e; border-bottom: 2px solid #0f3460; padding: 8px; }")
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(12, 8, 12, 8)
        title_label = QLabel("Anilam Crusader M Reference Library")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_label.setStyleSheet("color: #e94560;")
        tb_layout.addWidget(title_label)
        self._count_label = QLabel(f"{len(self._all_entries)} entries")
        self._count_label.setStyleSheet("color: #8899aa; font-size: 12px;")
        self._count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        tb_layout.addWidget(self._count_label)
        layout.addWidget(title_bar)

        # ── Search & filter bar ──
        search_frame = QFrame()
        search_frame.setStyleSheet("QFrame { background: #16213e; padding: 6px; }")
        sf_layout = QHBoxLayout(search_frame)
        sf_layout.setContentsMargins(12, 6, 12, 6)
        sf_layout.setSpacing(8)

        # Search box
        search_icon = QLabel("\U0001F50D")
        search_icon.setStyleSheet("font-size: 16px;")
        sf_layout.addWidget(search_icon)

        self._search_box = QLineEdit()
        self._search_box.setPlaceholderText("Search AUX codes, G-codes, M-codes, procedures, documents...")
        self._search_box.setStyleSheet("""
            QLineEdit {
                background: #0f3460;
                color: #e0e0e0;
                border: 1px solid #1a1a4e;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #e94560;
            }
        """)
        self._search_box.textChanged.connect(self._on_search_text_changed)
        self._search_box.returnPressed.connect(self._do_search)
        sf_layout.addWidget(self._search_box, stretch=3)

        # Category filter
        cat_label = QLabel("Category:")
        cat_label.setStyleSheet("color: #8899aa; font-size: 12px;")
        sf_layout.addWidget(cat_label)

        self._category_combo = QComboBox()
        self._category_combo.setStyleSheet("""
            QComboBox {
                background: #0f3460;
                color: #e0e0e0;
                border: 1px solid #1a1a4e;
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 12px;
                min-width: 180px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox::down-arrow { image: none; border: none; }
            QComboBox QAbstractItemView {
                background: #0f3460;
                color: #e0e0e0;
                selection-background-color: #e94560;
            }
        """)
        self._category_combo.addItem("All Categories", None)
        for cat in get_categories():
            self._category_combo.addItem(cat.value, cat)
        self._category_combo.currentIndexChanged.connect(self._do_search)
        sf_layout.addWidget(self._category_combo)

        layout.addWidget(search_frame)

        # ── Splitter: results tree | detail stack ──
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: #0f3460;
                width: 3px;
            }
        """)

        # Results tree
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Code", "Title", "Category"])
        self._tree.setStyleSheet("""
            QTreeWidget {
                background: #1a1a2e;
                color: #e0e0e0;
                border: none;
                font-size: 12px;
                alternate-background-color: #16213e;
            }
            QTreeWidget::item {
                padding: 4px 8px;
                border-bottom: 1px solid #0f3460;
            }
            QTreeWidget::item:selected {
                background: #0f3460;
                color: #e94560;
            }
            QTreeWidget::item:hover {
                background: #16213e;
            }
            QHeaderView::section {
                background: #0f3460;
                color: #e94560;
                padding: 6px 8px;
                border: none;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        self._tree.setAlternatingRowColors(True)
        self._tree.setRootIsDecorated(False)
        self._tree.setSortingEnabled(True)
        self._tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        header = self._tree.header()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.currentItemChanged.connect(self._on_item_selected)
        splitter.addWidget(self._tree)

        # ── Right side: stacked detail + PDF viewer ──
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Stacked widget: page 0 = text detail, page 1 = PDF viewer
        self._stack = QStackedWidget()

        # Page 0: Text detail browser
        self._detail = QTextBrowser()
        self._detail.setOpenExternalLinks(False)
        self._detail.setStyleSheet("""
            QTextBrowser {
                background: #1a1a2e;
                color: #e0e0e0;
                border: none;
                font-size: 13px;
                padding: 12px;
            }
        """)
        self._detail.setHtml(self._welcome_html())
        self._stack.addWidget(self._detail)

        # Page 1: PDF page viewer
        self._pdf_viewer = PdfPageViewer()
        self._stack.addWidget(self._pdf_viewer)

        right_layout.addWidget(self._stack, stretch=1)

        # View Document / Back button bar
        self._doc_bar = QFrame()
        self._doc_bar.setStyleSheet("QFrame { background: #16213e; border-top: 1px solid #0f3460; }")
        db_layout = QHBoxLayout(self._doc_bar)
        db_layout.setContentsMargins(8, 4, 8, 4)

        self._btn_view_doc = QPushButton("\U0001F4C4  View Document")
        self._btn_view_doc.setStyleSheet("""
            QPushButton {
                background: #0f3460; color: #4fc3f7; border: 1px solid #1a1a4e;
                border-radius: 4px; padding: 8px 16px; font-size: 13px; font-weight: bold;
            }
            QPushButton:hover { background: #e94560; color: white; }
        """)
        self._btn_view_doc.clicked.connect(self._show_pdf_viewer)

        self._btn_back_detail = QPushButton("\u25C0  Back to Details")
        self._btn_back_detail.setStyleSheet("""
            QPushButton {
                background: #0f3460; color: #e0e0e0; border: 1px solid #1a1a4e;
                border-radius: 4px; padding: 8px 16px; font-size: 13px;
            }
            QPushButton:hover { background: #e94560; color: white; }
        """)
        self._btn_back_detail.clicked.connect(self._show_detail_view)
        self._btn_back_detail.hide()

        self._doc_page_info = QLabel("")
        self._doc_page_info.setStyleSheet("color: #8899aa; font-size: 12px;")
        self._doc_page_info.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        db_layout.addWidget(self._btn_view_doc)
        db_layout.addWidget(self._btn_back_detail)
        db_layout.addStretch()
        db_layout.addWidget(self._doc_page_info)
        self._doc_bar.hide()

        right_layout.addWidget(self._doc_bar)

        splitter.addWidget(right_widget)
        splitter.setSizes([400, 600])
        layout.addWidget(splitter, stretch=1)

    # ── Search logic ──

    def _on_search_text_changed(self, text: str):
        """Debounced search trigger."""
        self._search_timer.start()

    def _do_search(self):
        """Execute search with current query and category filter."""
        query = self._search_box.text().strip()
        cat_data = self._category_combo.currentData()

        if query:
            results = search_library(query, category=cat_data)
        elif cat_data:
            results = get_entries_by_category(cat_data)
        else:
            results = list(self._all_entries)

        self._current_results = results
        self._populate_results(results)

    def _populate_results(self, entries: list):
        """Fill the tree widget with search results."""
        self._tree.clear()
        for entry in entries:
            code_display = f"\U0001F4C4 {entry.code}" if entry.pdf_file else entry.code
            item = QTreeWidgetItem([code_display, entry.title, entry.category.value])
            item.setData(0, Qt.ItemDataRole.UserRole, entry)

            # Color code by category type
            color = self._category_color(entry.category)
            item.setForeground(0, QColor(color))

            self._tree.addTopLevelItem(item)

        self._count_label.setText(f"{len(entries)} of {len(self._all_entries)} entries")

        # Auto-select first result
        if entries:
            self._tree.setCurrentItem(self._tree.topLevelItem(0))

    def _on_item_selected(self, current, previous):
        """Display detailed information for the selected entry."""
        if current is None:
            self._detail.setHtml(self._welcome_html())
            self._doc_bar.hide()
            self._show_detail_view()
            return

        entry: ReferenceEntry = current.data(0, Qt.ItemDataRole.UserRole)
        if entry is None:
            return

        self._current_entry = entry
        self._detail.setHtml(self._entry_to_html(entry))

        # Show/hide document bar based on whether entry has a PDF
        if entry.pdf_file:
            self._doc_bar.show()
            self._doc_page_info.setText(f"{entry.pdf_pages} pages  \u2022  {entry.pdf_file}")
            self._btn_view_doc.show()
            self._btn_back_detail.hide()
        else:
            self._doc_bar.hide()

        # Always switch back to detail view on new selection
        self._show_detail_view()

    def _show_pdf_viewer(self):
        """Switch to PDF viewer for the current entry."""
        if self._current_entry and self._current_entry.pdf_file:
            if self._pdf_viewer.load_pdf(self._current_entry.pdf_file):
                self._stack.setCurrentIndex(1)
                self._btn_view_doc.hide()
                self._btn_back_detail.show()

    def _show_detail_view(self):
        """Switch back to the text detail view."""
        self._stack.setCurrentIndex(0)
        self._pdf_viewer.close_doc()
        if self._current_entry and self._current_entry.pdf_file:
            self._btn_view_doc.show()
            self._btn_back_detail.hide()

    # ── HTML rendering ──

    def _entry_to_html(self, e: ReferenceEntry) -> str:
        """Convert a ReferenceEntry to styled HTML for the detail pane."""
        color = self._category_color(e.category)
        html = f"""
        <div style="font-family: 'Segoe UI', sans-serif;">
            <h2 style="color: {color}; margin-bottom: 2px;">{self._esc(e.code)}</h2>
            <h3 style="color: #e0e0e0; margin-top: 0;">{self._esc(e.title)}</h3>
            <p style="color: #667788; font-size: 11px; margin-top: 0;">
                Category: <b style="color: {color};">{self._esc(e.category.value)}</b>
                {f'&nbsp;&nbsp;|&nbsp;&nbsp;Source: {self._esc(e.source)}' if e.source else ''}
            </p>
            <hr style="border: 1px solid #0f3460;">
        """

        # PDF document badge
        if e.pdf_file:
            html += f"""
            <div style="background: #0f3460; border: 1px solid #1a4a7e; padding: 10px; margin: 8px 0; border-radius: 6px;">
                <span style="font-size: 18px;">\U0001F4C4</span>
                <b style="color: #4fc3f7; font-size: 13px;">&nbsp;Scanned Document Available</b>
                <p style="color: #8899aa; margin: 4px 0 0 0; font-size: 12px;">
                    {self._esc(e.pdf_file)} &nbsp;\u2014&nbsp; {e.pdf_pages} pages<br>
                    Click <b style="color: #4fc3f7;">View Document</b> below to browse pages.
                </p>
            </div>
            """

        # Description
        html += f"""
            <h4 style="color: #e94560;">Description</h4>
            <p style="color: #c0c0c0; white-space: pre-wrap;">{self._esc(e.description)}</p>
        """

        # Syntax
        if e.syntax:
            html += f"""
            <h4 style="color: #e94560;">Syntax</h4>
            <pre style="background: #0f3460; color: #4fc3f7; padding: 10px; border-radius: 4px; font-family: 'Consolas', monospace; font-size: 13px;">{self._esc(e.syntax)}</pre>
            """

        # Example
        if e.example:
            html += f"""
            <h4 style="color: #e94560;">Example</h4>
            <pre style="background: #0a2540; color: #81c784; padding: 10px; border-radius: 4px; font-family: 'Consolas', monospace; font-size: 13px;">{self._esc(e.example)}</pre>
            """

        # When to use
        if e.when_to_use:
            html += f"""
            <h4 style="color: #4fc3f7;">When to Use</h4>
            <p style="color: #c0c0c0; white-space: pre-wrap;">{self._esc(e.when_to_use)}</p>
            """

        # Warning
        if e.warning:
            html += f"""
            <div style="background: #3e1a1a; border-left: 4px solid #e94560; padding: 10px; margin: 8px 0; border-radius: 4px;">
                <b style="color: #e94560;">⚠ Warning</b>
                <p style="color: #e0a0a0; margin: 4px 0;">{self._esc(e.warning)}</p>
            </div>
            """

        # Related codes
        if e.related:
            links = ", ".join(
                f'<span style="color: #4fc3f7; cursor: pointer;">{self._esc(r)}</span>'
                for r in e.related
            )
            html += f"""
            <h4 style="color: #aabbcc;">Related</h4>
            <p>{links}</p>
            """

        # Tags
        if e.tags:
            tag_html = " ".join(
                f'<span style="background: #0f3460; color: #8899aa; padding: 2px 8px; border-radius: 10px; font-size: 11px; margin: 2px;">{self._esc(t)}</span>'
                for t in e.tags
            )
            html += f"""
            <h4 style="color: #aabbcc;">Tags</h4>
            <p>{tag_html}</p>
            """

        html += "</div>"
        return html

    def _welcome_html(self) -> str:
        """Generate welcome/landing page HTML."""
        cat_counts = {}
        doc_count = 0
        doc_pages = 0
        for e in self._all_entries:
            cat_counts[e.category.value] = cat_counts.get(e.category.value, 0) + 1
            if e.pdf_file:
                doc_count += 1
                doc_pages += e.pdf_pages

        cats_html = ""
        for cat_name, count in sorted(cat_counts.items()):
            cats_html += f'<li style="color: #8899aa; padding: 2px 0;">{cat_name} — <b style="color: #e0e0e0;">{count}</b> entries</li>'

        return f"""
        <div style="font-family: 'Segoe UI', sans-serif; padding: 20px;">
            <h2 style="color: #e94560;">Anilam Crusader M Reference Library</h2>
            <p style="color: #8899aa;">
                Comprehensive searchable reference for the Anilam Crusader M controller.
                Covers AUX codes, G-codes, M-codes, V-variables, RS-232 settings,
                servo procedures, CRT alignment, service parts, and scanned manuals.
            </p>
            <div style="background: #0f3460; border: 1px solid #1a4a7e; padding: 12px; border-radius: 6px; margin: 10px 0;">
                <span style="font-size: 18px;">\U0001F4C4</span>
                <b style="color: #4fc3f7;">&nbsp;{doc_count} Scanned Documents</b>
                <span style="color: #8899aa;">&nbsp;({doc_pages} total pages)</span>
                <p style="color: #c0c0c0; margin: 4px 0 0 0; font-size: 12px;">
                    Scanned manuals, wiring diagrams, and technical documents are viewable
                    directly in the library. Search or browse the \u201cScanned Documents\u201d category.
                </p>
            </div>
            <h3 style="color: #4fc3f7;">Quick Start</h3>
            <ul style="color: #c0c0c0;">
                <li>Type in the search box to find any code, setting, procedure, or document</li>
                <li>Use the category dropdown to browse by topic</li>
                <li>Click any result to see full details, examples, and warnings</li>
                <li>\U0001F4C4 entries have viewable scanned pages \u2014 click <b>View Document</b> to browse</li>
                <li>Search examples: <b style="color: #4fc3f7;">baud</b>, <b style="color: #4fc3f7;">mirror</b>,
                    <b style="color: #4fc3f7;">G83</b>, <b style="color: #4fc3f7;">servo balance</b>,
                    <b style="color: #4fc3f7;">XON</b>, <b style="color: #4fc3f7;">wiring diagram</b>,
                    <b style="color: #4fc3f7;">programming manual</b></li>
            </ul>
            <h3 style="color: #4fc3f7;">Categories ({len(cat_counts)})</h3>
            <ul>{cats_html}</ul>
            <p style="color: #556677; font-size: 11px; margin-top: 20px;">
                Total entries: {len(self._all_entries)} &nbsp;|&nbsp;
                Documents: {doc_count} ({doc_pages} pages) &nbsp;|&nbsp;
                Sources: AUX CODES.pdf, Crusader M/G manuals, Westamp drive docs, CRT guides, parts catalogs
            </p>
        </div>
        """

    @staticmethod
    def _esc(text: str) -> str:
        """Escape HTML special characters."""
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))

    @staticmethod
    def _category_color(cat: EntryCategory) -> str:
        """Return a color string for a category."""
        colors = {
            EntryCategory.AUX_CODES: "#ff9800",
            EntryCategory.AUX_MIRROR: "#ff9800",
            EntryCategory.AUX_CONTOURING: "#ff9800",
            EntryCategory.AUX_LIMITS: "#ff9800",
            EntryCategory.AUX_HOMING: "#ff9800",
            EntryCategory.AUX_THREADING: "#ff9800",
            EntryCategory.AUX_AXIS_SWAP: "#ff9800",
            EntryCategory.AUX_FEED_RAPID: "#ff9800",
            EntryCategory.AUX_PROGRAM: "#ff9800",
            EntryCategory.AUX_SIMULATION: "#ff9800",
            EntryCategory.AUX_LOOP: "#ff9800",
            EntryCategory.AUX_STEPPING: "#ff9800",
            EntryCategory.AUX_DRIFT: "#ff9800",
            EntryCategory.AUX_RS232: "#e94560",
            EntryCategory.AUX_MATH: "#ff9800",
            EntryCategory.AUX_ADVANCED: "#ff9800",
            EntryCategory.G_CODES: "#4fc3f7",
            EntryCategory.M_CODES: "#81c784",
            EntryCategory.V_VARIABLES: "#ce93d8",
            EntryCategory.RS232_SETTINGS: "#e94560",
            EntryCategory.PROGRAMMING: "#4fc3f7",
            EntryCategory.SUBROUTINES: "#4fc3f7",
            EntryCategory.DRILLING: "#4fc3f7",
            EntryCategory.SERVO_SETUP: "#ffcc80",
            EntryCategory.CRT_ALIGNMENT: "#bcaaa4",
            EntryCategory.WIRING: "#bcaaa4",
            EntryCategory.PARTS: "#90a4ae",
            EntryCategory.DOCUMENTS: "#42a5f5",
            EntryCategory.GENERAL: "#8899aa",
        }
        return colors.get(cat, "#8899aa")
