"""
CNC Bridge — G-code Backplotter (2D Toolpath Preview)

Renders a 2D visualization of G-code toolpaths using QPainter.
Supports:
  - Rapid moves (dashed red)
  - Linear moves (solid green)
  - Arc moves (solid blue/cyan)
  - Drill locations (markers)
  - Tool change markers
  - Pan & zoom
  - Grid overlay
  - Coordinate display
  - Work envelope bounding box
"""

import math
import re
from dataclasses import dataclass, field
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QComboBox, QCheckBox, QFileDialog, QMessageBox,
    QFrame, QSizePolicy,
)
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, QBrush, QPainterPath,
    QMouseEvent, QWheelEvent, QPaintEvent, QTransform,
)


# ── Parsed Move Data ─────────────────────────────────────────────

@dataclass
class PlotMove:
    """A single toolpath move for plotting."""
    move_type: str  # "rapid", "linear", "cw_arc", "ccw_arc", "drill"
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0
    z0: float = 0.0
    z1: float = 0.0
    # Arc params
    cx: float = 0.0  # arc center X
    cy: float = 0.0  # arc center Y
    radius: float = 0.0
    # Metadata
    line_number: int = 0
    tool: int = 0
    feed: float = 0.0


@dataclass
class PlotData:
    """Complete parsed plot data."""
    moves: list = field(default_factory=list)  # list[PlotMove]
    x_min: float = 0.0
    x_max: float = 0.0
    y_min: float = 0.0
    y_max: float = 0.0
    z_min: float = 0.0
    z_max: float = 0.0
    tool_changes: list = field(default_factory=list)  # list of (x, y, tool_num)
    drill_points: list = field(default_factory=list)  # list of (x, y, z_depth)


# ── G-code to Plot Parser ───────────────────────────────────────

class GCodePlotParser:
    """Parse G-code into plottable move data."""

    WORD_RE = re.compile(r'([A-Z])([+-]?\d*\.?\d+)', re.IGNORECASE)

    def parse(self, text: str) -> PlotData:
        """Parse G-code text into PlotData."""
        data = PlotData()
        
        # State
        x, y, z = 0.0, 0.0, 0.0
        motion_mode = 0  # G0
        is_absolute = True
        current_tool = 0
        current_feed = 0.0
        
        x_min = x_max = y_min = y_max = z_min = z_max = 0.0

        for line_num, raw_line in enumerate(text.splitlines(), 1):
            line = raw_line.strip()
            if not line or line.startswith('(') or line.startswith(';') or line == '%':
                continue

            # Remove comments
            line = re.sub(r'\([^)]*\)', '', line)
            line = re.sub(r';.*$', '', line).strip()
            if not line:
                continue

            # Parse words
            words = {}
            for m in self.WORD_RE.finditer(line):
                letter = m.group(1).upper()
                value = float(m.group(2))
                words[letter] = value

            # Process G-codes
            if 'G' in words:
                g = int(words['G'])
                if g in (0, 1, 2, 3):
                    motion_mode = g
                elif g == 90:
                    is_absolute = True
                elif g == 91:
                    is_absolute = False
                elif g in (81, 82, 83, 84, 85, 86, 87, 88, 89):
                    # Drill cycle — mark position
                    nx = words.get('X', x if is_absolute else 0)
                    ny = words.get('Y', y if is_absolute else 0)
                    nz = words.get('Z', z if is_absolute else 0)
                    if is_absolute:
                        dx, dy = nx, ny
                        dz = nz
                    else:
                        dx, dy = x + nx, y + ny
                        dz = z + nz

                    # Add rapid to XY position
                    if dx != x or dy != y:
                        data.moves.append(PlotMove(
                            move_type="rapid", x0=x, y0=y, x1=dx, y1=dy,
                            z0=z, z1=z, line_number=line_num, tool=current_tool,
                        ))
                        x, y = dx, dy

                    data.drill_points.append((x, y, dz))
                    data.moves.append(PlotMove(
                        move_type="drill", x0=x, y0=y, x1=x, y1=y,
                        z0=z, z1=dz, line_number=line_num, tool=current_tool,
                    ))
                    continue

            # Process tool change
            if 'T' in words:
                t = int(words['T'])
                if t != current_tool and t < 1000:
                    current_tool = t
                    data.tool_changes.append((x, y, current_tool))

            # Process feed
            if 'F' in words:
                current_feed = words['F']

            # Process motion
            has_motion = 'X' in words or 'Y' in words or 'Z' in words
            if has_motion:
                nx = words.get('X', x if is_absolute else 0)
                ny = words.get('Y', y if is_absolute else 0)
                nz = words.get('Z', z if is_absolute else 0)

                if is_absolute:
                    new_x, new_y, new_z = nx, ny, nz
                else:
                    new_x = x + nx
                    new_y = y + ny
                    new_z = z + nz

                if motion_mode == 0:
                    move_type = "rapid"
                elif motion_mode == 1:
                    move_type = "linear"
                elif motion_mode == 2:
                    move_type = "cw_arc"
                elif motion_mode == 3:
                    move_type = "ccw_arc"
                else:
                    move_type = "linear"

                move = PlotMove(
                    move_type=move_type,
                    x0=x, y0=y, x1=new_x, y1=new_y,
                    z0=z, z1=new_z,
                    line_number=line_num,
                    tool=current_tool,
                    feed=current_feed,
                )

                # For arcs, compute center
                if motion_mode in (2, 3):
                    ci = words.get('I', 0.0)
                    cj = words.get('J', 0.0)
                    move.cx = x + ci
                    move.cy = y + cj
                    move.radius = math.sqrt(ci * ci + cj * cj)

                data.moves.append(move)
                x, y, z = new_x, new_y, new_z

                # Track bounds
                x_min = min(x_min, x)
                x_max = max(x_max, x)
                y_min = min(y_min, y)
                y_max = max(y_max, y)
                z_min = min(z_min, z)
                z_max = max(z_max, z)

        data.x_min, data.x_max = x_min, x_max
        data.y_min, data.y_max = y_min, y_max
        data.z_min, data.z_max = z_min, z_max

        return data


# ── Plot Canvas ──────────────────────────────────────────────────

class PlotCanvas(QWidget):
    """QPainter-based 2D toolpath rendering canvas."""

    mouse_moved = pyqtSignal(float, float)  # machine X, Y coordinates

    # Colors
    COLOR_RAPID = QColor("#FF4444")
    COLOR_LINEAR = QColor("#4CAF50")
    COLOR_ARC_CW = QColor("#2196F3")
    COLOR_ARC_CCW = QColor("#00BCD4")
    COLOR_DRILL = QColor("#FF9800")
    COLOR_GRID = QColor("#333333")
    COLOR_GRID_MAJOR = QColor("#444444")
    COLOR_ORIGIN = QColor("#FFC107")
    COLOR_BOUND = QColor("#555555")
    COLOR_BG = QColor("#1a1a1a")
    COLOR_TOOL = QColor("#E91E63")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

        self._data: Optional[PlotData] = None
        self._scale = 1.0
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._drag_start = None
        self._drag_offset = None

        # Display options
        self.show_grid = True
        self.show_rapids = True
        self.show_bounds = True
        self.show_origin = True
        self.show_tools = True
        self.show_drills = True

    def set_data(self, data: PlotData):
        """Set plot data and auto-fit."""
        self._data = data
        self.fit_view()
        self.update()

    def clear(self):
        """Clear plot data."""
        self._data = None
        self.update()

    def fit_view(self):
        """Auto-fit the view to show all toolpaths."""
        if not self._data or not self._data.moves:
            self._scale = 1.0
            self._offset_x = self.width() / 2
            self._offset_y = self.height() / 2
            return

        d = self._data
        margin = 40
        w = self.width() - margin * 2
        h = self.height() - margin * 2

        if w <= 0 or h <= 0:
            return

        data_w = d.x_max - d.x_min
        data_h = d.y_max - d.y_min

        if data_w <= 0:
            data_w = 1.0
        if data_h <= 0:
            data_h = 1.0

        scale_x = w / data_w
        scale_y = h / data_h
        self._scale = min(scale_x, scale_y)

        center_x = (d.x_min + d.x_max) / 2
        center_y = (d.y_min + d.y_max) / 2
        self._offset_x = self.width() / 2 - center_x * self._scale
        self._offset_y = self.height() / 2 + center_y * self._scale

    def _to_screen(self, mx: float, my: float) -> QPointF:
        """Convert machine coords to screen coords."""
        sx = mx * self._scale + self._offset_x
        sy = -my * self._scale + self._offset_y  # Y is flipped
        return QPointF(sx, sy)

    def _to_machine(self, sx: float, sy: float) -> tuple[float, float]:
        """Convert screen coords to machine coords."""
        mx = (sx - self._offset_x) / self._scale
        my = -(sy - self._offset_y) / self._scale
        return mx, my

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), self.COLOR_BG)

        if self.show_grid:
            self._draw_grid(painter)

        if self.show_origin:
            self._draw_origin(painter)

        if self._data:
            if self.show_bounds:
                self._draw_bounds(painter)
            self._draw_moves(painter)
            if self.show_drills:
                self._draw_drill_markers(painter)
            if self.show_tools:
                self._draw_tool_markers(painter)

        painter.end()

    def _draw_grid(self, painter: QPainter):
        """Draw a coordinate grid."""
        # Determine grid spacing based on zoom
        pixels_per_unit = self._scale
        if pixels_per_unit <= 0:
            return

        # Choose grid spacing: 0.1, 0.5, 1, 5, 10, 50, 100...
        target_pixels = 50  # minimum pixels between grid lines
        spacing = 0.1
        for s in [0.1, 0.25, 0.5, 1, 2, 5, 10, 25, 50, 100, 250, 500]:
            if s * pixels_per_unit >= target_pixels:
                spacing = s
                break

        # Get visible range
        left, top_m = self._to_machine(0, self.height())
        right, bottom_m = self._to_machine(self.width(), 0)

        # Minor grid
        pen = QPen(self.COLOR_GRID, 1, Qt.PenStyle.DotLine)
        painter.setPen(pen)

        x = math.floor(left / spacing) * spacing
        while x <= right:
            p = self._to_screen(x, 0)
            painter.drawLine(QPointF(p.x(), 0), QPointF(p.x(), self.height()))
            x += spacing

        y = math.floor(top_m / spacing) * spacing
        while y <= bottom_m:
            p = self._to_screen(0, y)
            painter.drawLine(QPointF(0, p.y()), QPointF(self.width(), p.y()))
            y += spacing

        # Major grid (every 5x spacing)
        major = spacing * 5
        pen = QPen(self.COLOR_GRID_MAJOR, 1, Qt.PenStyle.SolidLine)
        painter.setPen(pen)

        x = math.floor(left / major) * major
        while x <= right:
            p = self._to_screen(x, 0)
            painter.drawLine(QPointF(p.x(), 0), QPointF(p.x(), self.height()))
            # Label
            painter.setFont(QFont("Consolas", 8))
            painter.setPen(QPen(QColor("#666666")))
            painter.drawText(QPointF(p.x() + 2, self.height() - 4), f"{x:.4g}")
            painter.setPen(pen)
            x += major

        y = math.floor(top_m / major) * major
        while y <= bottom_m:
            p = self._to_screen(0, y)
            painter.drawLine(QPointF(0, p.y()), QPointF(self.width(), p.y()))
            painter.setFont(QFont("Consolas", 8))
            painter.setPen(QPen(QColor("#666666")))
            painter.drawText(QPointF(4, p.y() - 4), f"{y:.4g}")
            painter.setPen(pen)
            y += major

    def _draw_origin(self, painter: QPainter):
        """Draw origin crosshair."""
        p = self._to_screen(0, 0)
        pen = QPen(self.COLOR_ORIGIN, 2)
        painter.setPen(pen)
        size = 15
        painter.drawLine(QPointF(p.x() - size, p.y()), QPointF(p.x() + size, p.y()))
        painter.drawLine(QPointF(p.x(), p.y() - size), QPointF(p.x(), p.y() + size))
        painter.drawEllipse(p, 4, 4)

    def _draw_bounds(self, painter: QPainter):
        """Draw work envelope bounding box."""
        if not self._data:
            return
        d = self._data
        tl = self._to_screen(d.x_min, d.y_max)
        br = self._to_screen(d.x_max, d.y_min)
        pen = QPen(self.COLOR_BOUND, 1, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.drawRect(QRectF(tl, br))

    def _draw_moves(self, painter: QPainter):
        """Draw all toolpath moves."""
        if not self._data:
            return

        for move in self._data.moves:
            if move.move_type == "rapid":
                if not self.show_rapids:
                    continue
                pen = QPen(self.COLOR_RAPID, 1, Qt.PenStyle.DashLine)
            elif move.move_type == "linear":
                pen = QPen(self.COLOR_LINEAR, 1.5, Qt.PenStyle.SolidLine)
            elif move.move_type == "cw_arc":
                pen = QPen(self.COLOR_ARC_CW, 1.5, Qt.PenStyle.SolidLine)
            elif move.move_type == "ccw_arc":
                pen = QPen(self.COLOR_ARC_CCW, 1.5, Qt.PenStyle.SolidLine)
            elif move.move_type == "drill":
                continue  # Handled separately
            else:
                pen = QPen(self.COLOR_LINEAR, 1, Qt.PenStyle.SolidLine)

            painter.setPen(pen)

            p0 = self._to_screen(move.x0, move.y0)
            p1 = self._to_screen(move.x1, move.y1)

            if move.move_type in ("cw_arc", "ccw_arc") and move.radius > 0:
                self._draw_arc(painter, move)
            else:
                painter.drawLine(p0, p1)

    def _draw_arc(self, painter: QPainter, move: PlotMove):
        """Draw a circular arc move."""
        # Compute arc parameters for QPainter
        cx, cy = move.cx, move.cy
        r = move.radius

        if r <= 0:
            # Fallback to line
            p0 = self._to_screen(move.x0, move.y0)
            p1 = self._to_screen(move.x1, move.y1)
            painter.drawLine(p0, p1)
            return

        # Start and end angles
        start_angle = math.atan2(move.y0 - cy, move.x0 - cx)
        end_angle = math.atan2(move.y1 - cy, move.x1 - cx)

        # Determine sweep
        if move.move_type == "cw_arc":
            sweep = start_angle - end_angle
            if sweep <= 0:
                sweep += 2 * math.pi
            sweep = -sweep  # CW is negative in Qt
        else:
            sweep = end_angle - start_angle
            if sweep <= 0:
                sweep += 2 * math.pi

        # Convert to screen coordinates
        sc = self._to_screen(cx, cy)
        sr = r * self._scale

        # Draw using arc approximation with line segments
        steps = max(16, int(abs(sweep) * r * self._scale / 5))
        points = []
        for i in range(steps + 1):
            t = i / steps
            angle = start_angle + sweep * t
            px = cx + r * math.cos(angle)
            py = cy + r * math.sin(angle)
            points.append(self._to_screen(px, py))

        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])

    def _draw_drill_markers(self, painter: QPainter):
        """Draw drill point markers."""
        if not self._data:
            return
        pen = QPen(self.COLOR_DRILL, 2)
        painter.setPen(pen)
        for dx, dy, dz in self._data.drill_points:
            p = self._to_screen(dx, dy)
            size = 5
            painter.drawLine(QPointF(p.x() - size, p.y() - size),
                             QPointF(p.x() + size, p.y() + size))
            painter.drawLine(QPointF(p.x() + size, p.y() - size),
                             QPointF(p.x() - size, p.y() + size))
            painter.drawEllipse(p, size, size)

    def _draw_tool_markers(self, painter: QPainter):
        """Draw tool change markers."""
        if not self._data:
            return
        for tx, ty, tnum in self._data.tool_changes:
            p = self._to_screen(tx, ty)
            # Triangle marker
            pen = QPen(self.COLOR_TOOL, 2)
            painter.setPen(pen)
            size = 8
            painter.drawLine(QPointF(p.x(), p.y() - size),
                             QPointF(p.x() - size, p.y() + size))
            painter.drawLine(QPointF(p.x() - size, p.y() + size),
                             QPointF(p.x() + size, p.y() + size))
            painter.drawLine(QPointF(p.x() + size, p.y() + size),
                             QPointF(p.x(), p.y() - size))
            # Label
            painter.setFont(QFont("Consolas", 8, QFont.Weight.Bold))
            painter.drawText(QPointF(p.x() + size + 2, p.y()), f"T{tnum}")

    # ── Mouse Interaction ────────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.pos()
            self._drag_offset = (self._offset_x, self._offset_y)
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        # Update coordinate display
        mx, my = self._to_machine(event.pos().x(), event.pos().y())
        self.mouse_moved.emit(mx, my)

        # Drag to pan
        if self._drag_start and self._drag_offset:
            dx = event.pos().x() - self._drag_start.x()
            dy = event.pos().y() - self._drag_start.y()
            self._offset_x = self._drag_offset[0] + dx
            self._offset_y = self._drag_offset[1] + dy
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = None
            self._drag_offset = None
            self.setCursor(Qt.CursorShape.CrossCursor)

    def wheelEvent(self, event: QWheelEvent):
        """Zoom with scroll wheel centered on cursor."""
        pos = event.position()
        old_mx, old_my = self._to_machine(pos.x(), pos.y())

        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        self._scale *= factor

        # Clamp scale
        self._scale = max(0.01, min(10000, self._scale))

        # Adjust offset to zoom toward cursor
        new_screen = self._to_screen(old_mx, old_my)
        self._offset_x += pos.x() - new_screen.x()
        self._offset_y += pos.y() - new_screen.y()

        self.update()

    def enterEvent(self, event):
        self.setCursor(Qt.CursorShape.CrossCursor)

    def leaveEvent(self, event):
        self.setCursor(Qt.CursorShape.ArrowCursor)


# ── Backplotter Panel (tab widget) ──────────────────────────────

class BackplotterPanel(QGroupBox):
    """G-code backplotter tab with canvas, controls, and legend."""

    def __init__(self, parent=None):
        super().__init__("Toolpath Backplotter", parent)
        self._parser = GCodePlotParser()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(4)

        # ── Toolbar ──
        toolbar = QHBoxLayout()

        self.load_btn = QPushButton("Open G-code")
        self.load_btn.clicked.connect(self._load_file)
        toolbar.addWidget(self.load_btn)

        self.fit_btn = QPushButton("Fit View")
        self.fit_btn.clicked.connect(self._fit_view)
        toolbar.addWidget(self.fit_btn)

        toolbar.addSpacing(10)

        # View toggles
        self.grid_check = QCheckBox("Grid")
        self.grid_check.setChecked(True)
        self.grid_check.toggled.connect(self._on_toggle_grid)
        toolbar.addWidget(self.grid_check)

        self.rapids_check = QCheckBox("Rapids")
        self.rapids_check.setChecked(True)
        self.rapids_check.toggled.connect(self._on_toggle_rapids)
        toolbar.addWidget(self.rapids_check)

        self.drills_check = QCheckBox("Drills")
        self.drills_check.setChecked(True)
        self.drills_check.toggled.connect(self._on_toggle_drills)
        toolbar.addWidget(self.drills_check)

        self.tools_check = QCheckBox("Tools")
        self.tools_check.setChecked(True)
        self.tools_check.toggled.connect(self._on_toggle_tools)
        toolbar.addWidget(self.tools_check)

        toolbar.addStretch()

        # Coordinate display
        self.coord_label = QLabel("X: —  Y: —")
        self.coord_label.setFont(QFont("Consolas", 10))
        self.coord_label.setStyleSheet("color: #FFC107;")
        toolbar.addWidget(self.coord_label)

        layout.addLayout(toolbar)

        # ── Canvas ──
        self.canvas = PlotCanvas()
        self.canvas.mouse_moved.connect(self._update_coords)
        layout.addWidget(self.canvas, 1)

        # ── Info bar ──
        info_bar = QHBoxLayout()

        # Legend
        legend_items = [
            ("━━ Rapid", "#FF4444"),
            ("━━ Linear", "#4CAF50"),
            ("━━ Arc CW", "#2196F3"),
            ("━━ Arc CCW", "#00BCD4"),
            ("✕ Drill", "#FF9800"),
            ("△ Tool", "#E91E63"),
            ("⊕ Origin", "#FFC107"),
        ]
        for text, color in legend_items:
            lbl = QLabel(text)
            lbl.setFont(QFont("Consolas", 8))
            lbl.setStyleSheet(f"color: {color};")
            info_bar.addWidget(lbl)

        info_bar.addStretch()

        self.stats_label = QLabel("")
        self.stats_label.setFont(QFont("Consolas", 9))
        self.stats_label.setStyleSheet("color: #888;")
        info_bar.addWidget(self.stats_label)

        layout.addLayout(info_bar)
        self.setLayout(layout)

    def _load_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open G-code File", "",
            "G-code Files (*.txt *.nc *.ngc *.gcode *.tap);;All Files (*)"
        )
        if filepath:
            self.load_file(filepath)

    def load_file(self, filepath: str):
        """Load and plot a G-code file."""
        try:
            from pathlib import Path
            with open(filepath, 'r', encoding='ascii', errors='replace') as f:
                text = f.read()
            self.load_text(text, Path(filepath).name)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load file: {e}")

    def load_text(self, text: str, name: str = ""):
        """Parse and plot G-code text."""
        data = self._parser.parse(text)
        self.canvas.set_data(data)

        # Update stats
        moves = len(data.moves)
        rapid = sum(1 for m in data.moves if m.move_type == "rapid")
        linear = sum(1 for m in data.moves if m.move_type == "linear")
        arcs = sum(1 for m in data.moves if m.move_type in ("cw_arc", "ccw_arc"))
        drills = len(data.drill_points)
        tools = len(data.tool_changes)

        parts = [f"{moves} moves"]
        if rapid:
            parts.append(f"{rapid} rapid")
        if linear:
            parts.append(f"{linear} linear")
        if arcs:
            parts.append(f"{arcs} arc")
        if drills:
            parts.append(f"{drills} drill")
        if tools:
            parts.append(f"{tools} tool chg")

        envelope = ""
        if data.x_max > data.x_min:
            w = data.x_max - data.x_min
            h = data.y_max - data.y_min
            envelope = f" | Envelope: {w:.3f}\" × {h:.3f}\""

        prefix = f"{name} — " if name else ""
        self.stats_label.setText(f"{prefix}{' | '.join(parts)}{envelope}")

    def _fit_view(self):
        self.canvas.fit_view()
        self.canvas.update()

    def _update_coords(self, x: float, y: float):
        self.coord_label.setText(f"X: {x:.4f}  Y: {y:.4f}")

    def _on_toggle_grid(self, checked):
        self.canvas.show_grid = checked
        self.canvas.update()

    def _on_toggle_rapids(self, checked):
        self.canvas.show_rapids = checked
        self.canvas.update()

    def _on_toggle_drills(self, checked):
        self.canvas.show_drills = checked
        self.canvas.update()

    def _on_toggle_tools(self, checked):
        self.canvas.show_tools = checked
        self.canvas.update()
