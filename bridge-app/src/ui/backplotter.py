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
    QFrame, QSizePolicy, QSlider,
)
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QFont, QBrush, QPainterPath,
    QMouseEvent, QWheelEvent, QPaintEvent, QTransform, QImage,
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
        self.show_heat_map = False  # Feed-rate heat map coloring

        # Animation state
        self._anim_index = -1  # -1 = show all; >= 0 = show up to index
        self._max_feed = 0.0   # For heat map normalization

    def set_data(self, data: PlotData):
        """Set plot data and auto-fit."""
        self._data = data
        self._anim_index = -1  # Show all
        # Compute max feed for heat map
        self._max_feed = max((m.feed for m in data.moves if m.feed > 0), default=1.0)
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

        max_idx = self._anim_index if self._anim_index >= 0 else len(self._data.moves)

        for i, move in enumerate(self._data.moves):
            if i >= max_idx:
                break

            if move.move_type == "rapid":
                if not self.show_rapids:
                    continue
                pen = QPen(self.COLOR_RAPID, 1, Qt.PenStyle.DashLine)
            elif move.move_type in ("linear", "cw_arc", "ccw_arc"):
                if self.show_heat_map and move.feed > 0:
                    # Heat map: blue (slow) → green → yellow → red (fast)
                    ratio = min(1.0, move.feed / self._max_feed) if self._max_feed > 0 else 0.5
                    color = self._feed_to_color(ratio)
                    pen = QPen(color, 1.5, Qt.PenStyle.SolidLine)
                elif move.move_type == "linear":
                    pen = QPen(self.COLOR_LINEAR, 1.5, Qt.PenStyle.SolidLine)
                elif move.move_type == "cw_arc":
                    pen = QPen(self.COLOR_ARC_CW, 1.5, Qt.PenStyle.SolidLine)
                else:
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

        # Draw animation cursor (tool position indicator)
        if self._anim_index > 0 and self._anim_index <= len(self._data.moves):
            last = self._data.moves[self._anim_index - 1]
            tp = self._to_screen(last.x1, last.y1)
            pen = QPen(QColor("#FFFFFF"), 2)
            painter.setPen(pen)
            painter.drawEllipse(tp, 5, 5)
            painter.drawLine(QPointF(tp.x() - 7, tp.y()), QPointF(tp.x() + 7, tp.y()))
            painter.drawLine(QPointF(tp.x(), tp.y() - 7), QPointF(tp.x(), tp.y() + 7))

    @staticmethod
    def _feed_to_color(ratio: float) -> QColor:
        """Convert feed ratio (0-1) to heat map color (blue→green→yellow→red)."""
        if ratio < 0.25:
            t = ratio / 0.25
            r, g, b = 0, int(255 * t), 255
        elif ratio < 0.5:
            t = (ratio - 0.25) / 0.25
            r, g, b = 0, 255, int(255 * (1 - t))
        elif ratio < 0.75:
            t = (ratio - 0.5) / 0.25
            r, g, b = int(255 * t), 255, 0
        else:
            t = (ratio - 0.75) / 0.25
            r, g, b = 255, int(255 * (1 - t)), 0
        return QColor(r, g, b)

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

    # ── Export ────────────────────────────────────────────────────

    def render_to_image(self, width: int = 1920, height: int = 1080) -> QImage:
        """Render the canvas to a QImage for export."""
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(QColor(self.COLOR_BG))

        # Save current state
        old_w, old_h = self.width(), self.height()
        old_scale = self._scale
        old_ox, old_oy = self._offset_x, self._offset_y

        # Temporarily resize for rendering
        self.resize(width, height)
        self.fit_view()

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

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

        # Restore
        self.resize(old_w, old_h)
        self._scale = old_scale
        self._offset_x = old_ox
        self._offset_y = old_oy

        return image


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

        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self._clear_plot)
        toolbar.addWidget(self.clear_btn)

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

        self.heat_check = QCheckBox("Heat Map")
        self.heat_check.setChecked(False)
        self.heat_check.setToolTip("Color toolpath by feed rate")
        self.heat_check.toggled.connect(self._on_toggle_heat_map)
        toolbar.addWidget(self.heat_check)

        toolbar.addStretch()

        # Coordinate display
        self.coord_label = QLabel("X: —  Y: —")
        self.coord_label.setFont(QFont("Consolas", 10))
        self.coord_label.setStyleSheet("color: #FFC107;")
        toolbar.addWidget(self.coord_label)

        layout.addLayout(toolbar)

        # ── Animation Controls ──
        anim_bar = QHBoxLayout()

        self.play_btn = QPushButton("▶ Play")
        self.play_btn.setFixedWidth(70)
        self.play_btn.clicked.connect(self._anim_play_pause)
        anim_bar.addWidget(self.play_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setFixedWidth(70)
        self.stop_btn.clicked.connect(self._anim_stop)
        anim_bar.addWidget(self.stop_btn)

        self.step_btn = QPushButton("Step ▶|")
        self.step_btn.setFixedWidth(70)
        self.step_btn.clicked.connect(self._anim_step)
        anim_bar.addWidget(self.step_btn)

        self.anim_slider = QSlider(Qt.Orientation.Horizontal)
        self.anim_slider.setMinimum(0)
        self.anim_slider.setMaximum(100)
        self.anim_slider.setValue(100)
        self.anim_slider.valueChanged.connect(self._on_slider_changed)
        anim_bar.addWidget(self.anim_slider, 1)

        self.anim_label = QLabel("100%")
        self.anim_label.setFont(QFont("Consolas", 9))
        self.anim_label.setFixedWidth(50)
        anim_bar.addWidget(self.anim_label)

        anim_bar.addSpacing(10)

        self.export_btn = QPushButton("Export PNG/PDF")
        self.export_btn.clicked.connect(self._export_image)
        anim_bar.addWidget(self.export_btn)

        layout.addLayout(anim_bar)

        # Animation timer
        self._anim_timer = QTimer()
        self._anim_timer.setInterval(30)  # ~33 fps
        self._anim_timer.timeout.connect(self._anim_tick)
        self._anim_playing = False

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

        # Reset animation
        self._anim_stop()

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

    def _clear_plot(self):
        """Clear the backplotter display."""
        self.canvas.clear()
        self.canvas.update()
        self.stats_label.setText("")
        self.coord_label.setText("X: —  Y: —")

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

    def _on_toggle_heat_map(self, checked):
        self.canvas.show_heat_map = checked
        self.canvas.update()

    # ── Animation ─────────────────────────────────────────────

    def _anim_play_pause(self):
        """Toggle play/pause for toolpath animation."""
        if not self.canvas._data or not self.canvas._data.moves:
            return

        if self._anim_playing:
            self._anim_timer.stop()
            self._anim_playing = False
            self.play_btn.setText("▶ Play")
        else:
            # If at end, restart
            total = len(self.canvas._data.moves)
            if self.canvas._anim_index < 0 or self.canvas._anim_index >= total:
                self.canvas._anim_index = 0
            self._anim_playing = True
            self.play_btn.setText("⏸ Pause")
            self._anim_timer.start()

    def _anim_stop(self):
        """Stop animation and show all moves."""
        self._anim_timer.stop()
        self._anim_playing = False
        self.play_btn.setText("▶ Play")
        self.canvas._anim_index = -1  # Show all
        self.anim_slider.setValue(100)
        self.anim_label.setText("100%")
        self.canvas.update()

    def _anim_step(self):
        """Advance animation by one move."""
        if not self.canvas._data or not self.canvas._data.moves:
            return
        total = len(self.canvas._data.moves)
        if self.canvas._anim_index < 0:
            self.canvas._anim_index = 1
        elif self.canvas._anim_index < total:
            self.canvas._anim_index += 1
        self._update_anim_slider()
        self.canvas.update()

    def _anim_tick(self):
        """Timer callback — advance animation frame."""
        if not self.canvas._data or not self.canvas._data.moves:
            self._anim_timer.stop()
            return
        total = len(self.canvas._data.moves)
        # Advance by ~1-5 moves per tick depending on total moves
        step = max(1, total // 300)
        self.canvas._anim_index = min(self.canvas._anim_index + step, total)
        self._update_anim_slider()
        self.canvas.update()

        if self.canvas._anim_index >= total:
            self._anim_timer.stop()
            self._anim_playing = False
            self.play_btn.setText("▶ Play")

    def _on_slider_changed(self, value):
        """Slider moved — set animation position."""
        if not self.canvas._data or not self.canvas._data.moves:
            return
        total = len(self.canvas._data.moves)
        if value >= 100:
            self.canvas._anim_index = -1  # Show all
            self.anim_label.setText("100%")
        else:
            self.canvas._anim_index = max(0, int(total * value / 100))
            self.anim_label.setText(f"{value}%")
        self.canvas.update()

    def _update_anim_slider(self):
        """Update slider to match current animation position."""
        if not self.canvas._data or not self.canvas._data.moves:
            return
        total = len(self.canvas._data.moves)
        if self.canvas._anim_index < 0:
            pct = 100
        else:
            pct = int(self.canvas._anim_index * 100 / total)
        self.anim_slider.blockSignals(True)
        self.anim_slider.setValue(pct)
        self.anim_slider.blockSignals(False)
        self.anim_label.setText(f"{pct}%")

    # ── Export ────────────────────────────────────────────────

    def _export_image(self):
        """Export the backplot as PNG or PDF."""
        if not self.canvas._data or not self.canvas._data.moves:
            QMessageBox.information(self, "No Data", "Load a G-code file first.")
            return

        filepath, selected = QFileDialog.getSaveFileName(
            self, "Export Backplot", "",
            "PNG Image (*.png);;PDF Document (*.pdf);;All Files (*)"
        )
        if not filepath:
            return

        try:
            if filepath.lower().endswith('.pdf'):
                self._export_pdf(filepath)
            else:
                if not filepath.lower().endswith('.png'):
                    filepath += '.png'
                self._export_png(filepath)
            QMessageBox.information(self, "Exported",
                                    f"Backplot saved to:\n{filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def _export_png(self, filepath: str):
        """Export backplot as PNG image."""
        image = self.canvas.render_to_image(1920, 1080)
        image.save(filepath, "PNG")

    def _export_pdf(self, filepath: str):
        """Export backplot as PDF document."""
        from PyQt6.QtGui import QPdfWriter, QPageLayout, QPageSize
        from PyQt6.QtCore import QMarginsF

        writer = QPdfWriter(filepath)
        writer.setPageSize(QPageSize(QPageSize.PageSizeId.Letter))
        writer.setPageMargins(QMarginsF(20, 20, 20, 20))
        writer.setResolution(300)

        painter = QPainter(writer)

        # Render at PDF resolution
        w = writer.width()
        h = writer.height()

        # Save canvas state
        old_scale = self.canvas._scale
        old_ox, old_oy = self.canvas._offset_x, self.canvas._offset_y
        old_w, old_h = self.canvas.width(), self.canvas.height()

        self.canvas.resize(w, h)
        self.canvas.fit_view()

        # Paint
        painter.fillRect(0, 0, w, h, self.canvas.COLOR_BG)
        if self.canvas.show_grid:
            self.canvas._draw_grid(painter)
        if self.canvas.show_origin:
            self.canvas._draw_origin(painter)
        if self.canvas._data:
            if self.canvas.show_bounds:
                self.canvas._draw_bounds(painter)
            self.canvas._draw_moves(painter)
            if self.canvas.show_drills:
                self.canvas._draw_drill_markers(painter)
            if self.canvas.show_tools:
                self.canvas._draw_tool_markers(painter)

        # Title
        painter.setPen(QPen(QColor("#d4d4d4")))
        painter.setFont(QFont("Consolas", 12))
        painter.drawText(50, 50, f"CNC Bridge Backplot — {self.stats_label.text()}")

        painter.end()

        # Restore
        self.canvas.resize(old_w, old_h)
        self.canvas._scale = old_scale
        self.canvas._offset_x = old_ox
        self.canvas._offset_y = old_oy
