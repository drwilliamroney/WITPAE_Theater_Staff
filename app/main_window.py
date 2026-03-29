"""Primary PyQt5 application window."""

from __future__ import annotations

import time
import math
import logging
import subprocess
import shlex
from pathlib import Path

from PIL import Image
from PyQt5.QtCore import QPointF, QTimer, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PyQt5.QtWidgets import (
    QAction,
    QDialog,
    QDialogButtonBox,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
    QMainWindow,
    QProgressDialog,
    QSplitter,
    QLabel,
    QLineEdit,
    QTextEdit,
    QToolBar,
    QToolTip,
    QMessageBox,
    QVBoxLayout,
)

from app.map_assembly import MapAssembly
from app.regions_overlay import GAME_COLS, GAME_ROWS, REGION_DEFINITIONS


logger = logging.getLogger(__name__)


def pil_image_to_qpixmap(image: Image.Image) -> QPixmap:
    """Convert a PIL image to QPixmap without relying on Pillow's Qt adapters."""
    rgb_image = image.convert("RGB")
    image_bytes = rgb_image.tobytes("raw", "RGB")
    qimage = QImage(image_bytes, rgb_image.width, rgb_image.height, rgb_image.width * 3, QImage.Format_RGB888)
    return QPixmap.fromImage(qimage.copy())


def add_tiled_map_to_scene(scene: QGraphicsScene, image: Image.Image, tile_size: int = 1024) -> tuple[int, int]:
    """Add a full-resolution map image to the scene using tiled pixmap items."""
    width, height = image.size
    for top in range(0, height, tile_size):
        for left in range(0, width, tile_size):
            right = min(left + tile_size, width)
            bottom = min(top + tile_size, height)
            tile = image.crop((left, top, right, bottom))
            tile_item = QGraphicsPixmapItem(pil_image_to_qpixmap(tile))
            tile_item.setPos(left, top)
            tile_item.setZValue(0)
            scene.addItem(tile_item)
    return width, height


class MapView(QGraphicsView):
    """Scrollable and zoomable map view."""

    def __init__(self, scene: QGraphicsScene, parent: QMainWindow | None = None) -> None:
        super().__init__(scene, parent)
        self._main_window = parent
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform, False)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setMouseTracking(True)

    def wheelEvent(self, event) -> None:  # noqa: N802
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else (1.0 / 1.15)
            self.scale(factor, factor)
            event.accept()
            return
        super().wheelEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        scene_pos = self.mapToScene(event.pos())
        if isinstance(self._main_window, MainWindow):
            self._main_window.on_map_hover(scene_pos)
            if self._main_window._show_mouse_pixel_debug:
                QToolTip.showText(
                    event.globalPos(),
                    f"px ({scene_pos.x():.1f}, {scene_pos.y():.1f})",
                    self.viewport(),
                )
        super().mouseMoveEvent(event)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton and isinstance(self._main_window, MainWindow):
            self._main_window.on_map_click(self.mapToScene(event.pos()))
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    """Main UI shell for map display (overlays intentionally omitted)."""

    GAME_EXECUTABLE = "War in the Pacific Admiral Edition.exe"
    GAME_START_ARGS = [
        "-altFont",
        "-skipVideo",
        "-archive",
        "-deepColor",
        "-dd_sw",
        "-px1600",
        "-py900",
        "-SingleCpuOrders",
        "-cpu3",
        "-fixedArt",
        "-multiaudio",
        "-w",
    ]
    # Locked calibration values.
    # These were finalized after WPEH00.bmp measurement (42x38 spacing) plus in-app spot checks
    # across multiple map locations, yielding typical residual error within ~1-2 px.
    # Do not tune these by eye; only change after rerunning the documented calibration workflow.
    HEX_CENTER_X_1_1 = 24.0
    HEX_CENTER_Y_1_1 = 8.0
    HEX_STEP_X = 42.0
    HEX_STEP_Y = 38.0
    HEX_ANCHOR_ADJUST_X = 19.0
    HEX_ANCHOR_ADJUST_Y = 17.0
    SHIFT_EVEN_ROWS_RIGHT = True

    def __init__(self, game_dir: Path, save_path: Path, side: str) -> None:
        super().__init__()
        self._game_dir = game_dir
        self._save_path = save_path
        self._side = side
        self._show_mouse_pixel_debug = True
        self._scene = QGraphicsScene(self)
        self._regions_visible = True
        self._region_items: list[object] = []
        self._hex_grid_visible = False
        self._hex_grid_items: list[object] = []
        self._selected_hex_item: QGraphicsPolygonItem | None = None
        self._regions_action: QAction | None = None
        self._hex_grid_action: QAction | None = None
        self._map_view: MapView | None = None
        self._detail_panel: QTextEdit | None = None
        self._map_width = 0
        self._map_height = 0
        self._hex_size_x = 0.0
        self._hex_size_y = 0.0
        self._hex_width = 0.0
        self._hex_origin_x = 0.0
        self._hex_origin_y = 0.0
        self._hover_hex: tuple[int, int] | None = None
        self._selected_hex: tuple[int, int] | None = None

        self._turn_progress_dialog: QProgressDialog | None = None
        self._turn_activity_deadline = 0.0
        self._turn_phase = "idle"
        self._pre_turn_signature = self._save_file_signature("wpae002.pws")
        self._end_turn_signature = self._save_file_signature("wpae000.pws")
        self._data_ready_deadline = 0.0
        self._data_signature = self._side_data_signature()
        self._turn_monitor_timer = QTimer(self)
        self._turn_monitor_timer.setInterval(1500)
        self._turn_monitor_timer.timeout.connect(self._poll_turn_file)
        self._turn_processing_timer = QTimer(self)
        self._turn_processing_timer.setInterval(500)
        self._turn_processing_timer.timeout.connect(self._poll_turn_processing)

        self.setWindowTitle("WITPAE Theater Staff")
        self.resize(1400, 900)

        self._init_toolbar()
        self._init_layout()
        self._load_map()
        self._refresh_detail_panel()
        self._turn_monitor_timer.start()

    def _init_toolbar(self) -> None:
        toolbar = QToolBar("Main", self)
        toolbar.setMovable(False)
        startup_action = QAction("Startup Game", self)
        startup_action.triggered.connect(self._startup_game)
        toolbar.addAction(startup_action)
        toolbar.addSeparator()
        toolbar.addAction(f"Side: {self._side}")
        toolbar.addAction(f"Game Dir: {self._game_dir}")
        self._regions_action = QAction("Regions", self)
        self._regions_action.setCheckable(True)
        self._regions_action.setChecked(True)
        self._regions_action.triggered.connect(self._set_regions_visible)
        toolbar.addAction(self._regions_action)

        self._hex_grid_action = QAction("HexGrid", self)
        self._hex_grid_action.setCheckable(True)
        self._hex_grid_action.setChecked(False)
        self._hex_grid_action.triggered.connect(self._set_hex_grid_visible)
        toolbar.addAction(self._hex_grid_action)
        self.addToolBar(toolbar)

    def _init_layout(self) -> None:
        map_view = MapView(self._scene, self)
        detail_panel = QTextEdit(self)
        detail_panel.setReadOnly(True)
        self._map_view = map_view
        self._detail_panel = detail_panel

        splitter = QSplitter(self)
        splitter.addWidget(map_view)
        splitter.addWidget(detail_panel)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        self.statusBar().showMessage("Map-only mode (no overlays)")

    def _load_map(self) -> None:
        assembly = MapAssembly(self._game_dir)

        self._scene.clear()
        self._map_width, self._map_height = add_tiled_map_to_scene(self._scene, assembly.image)
        self._scene.setSceneRect(0, 0, self._map_width, self._map_height)
        self._build_regions_overlay(self._map_width, self._map_height)
        self._build_hex_grid_overlay(self._map_width, self._map_height)
        self._set_regions_visible(self._regions_visible)
        self._set_hex_grid_visible(self._hex_grid_visible)
        self._selected_hex_item = None
        self._selected_hex = None

        map_source = "game tiles" if assembly.from_tiles else "placeholder"
        self.statusBar().showMessage(
            "Map loaded from "
            f"{map_source}; regions: {'on' if self._regions_visible else 'off'}; "
            f"hexgrid: {'on' if self._hex_grid_visible else 'off'}"
        )

        if self._map_view is not None:
            self._map_view.resetTransform()
            self._map_view.horizontalScrollBar().setValue(0)
            self._map_view.verticalScrollBar().setValue(0)

    def _build_regions_overlay(self, map_width: int, map_height: int) -> None:
        self._region_items.clear()

        step_x = map_width / (GAME_COLS - 1)
        step_y = map_height / (GAME_ROWS - 1)

        for region in REGION_DEFINITIONS:
            polygon = QPolygonF(
                [
                    QPointF((hx - 1) * step_x, (hy - 1) * step_y)
                    for (hx, hy) in region.polygon_hex
                ]
            )

            fill = QColor(*region.fill_rgba)
            stroke = QColor(*region.border_rgba)

            polygon_item = QGraphicsPolygonItem(polygon)
            polygon_item.setPen(QPen(stroke, 2))
            polygon_item.setBrush(QBrush(fill))
            polygon_item.setZValue(10)
            self._scene.addItem(polygon_item)
            self._region_items.append(polygon_item)

            center = polygon.boundingRect().center()
            label = QGraphicsSimpleTextItem(f"{region.abbr}  {region.name}")
            label.setBrush(QBrush(QColor(240, 248, 255)))
            label.setFont(QFont("Segoe UI", 10, QFont.Bold))
            label_rect = label.boundingRect()
            label.setPos(center.x() - label_rect.width() / 2, center.y() - label_rect.height() / 2)
            label.setZValue(11)
            self._scene.addItem(label)
            self._region_items.append(label)

    def _build_hex_grid_overlay(self, map_width: int, map_height: int) -> None:
        self._hex_grid_items.clear()

        cols = GAME_COLS
        rows = GAME_ROWS
        sqrt3 = math.sqrt(3.0)

        # Locked: measured center-to-center spacing from ART\WPEH00.bmp.
        hex_width = self.HEX_STEP_X
        hex_size_x = hex_width / sqrt3
        hex_size_y = self.HEX_STEP_Y / 1.5
        # Locked: calibrated anchor for hex (1,1), including legacy 19x17 anchor adjustment.
        origin_x = self.HEX_CENTER_X_1_1 + self.HEX_ANCHOR_ADJUST_X
        origin_y = self.HEX_CENTER_Y_1_1 + self.HEX_ANCHOR_ADJUST_Y
        self._hex_size_x = hex_size_x
        self._hex_size_y = hex_size_y
        self._hex_width = hex_width
        self._hex_origin_x = origin_x
        self._hex_origin_y = origin_y

        path = QPainterPath()
        for row in range(rows):
            row_offset = self._row_offset(row)
            center_y = origin_y + (1.5 * hex_size_y * row)
            for col in range(cols):
                center_x = origin_x + (hex_width * (col + row_offset))
                vertices = []
                for i in range(6):
                    angle = math.radians(60 * i - 90)
                    vx = center_x + hex_size_x * math.cos(angle)
                    vy = center_y + hex_size_y * math.sin(angle)
                    vertices.append(QPointF(vx, vy))

                path.moveTo(vertices[0])
                for vertex in vertices[1:]:
                    path.lineTo(vertex)
                path.closeSubpath()

        grid_item = QGraphicsPathItem(path)
        grid_item.setPen(QPen(QColor(255, 255, 255, 55), 0.35))
        grid_item.setBrush(QBrush(Qt.NoBrush))
        grid_item.setZValue(30)
        self._scene.addItem(grid_item)
        self._hex_grid_items.append(grid_item)

    def _row_offset(self, row_zero: int) -> float:
        if self.SHIFT_EVEN_ROWS_RIGHT:
            return 0.5 if (row_zero % 2 == 0) else 0.0
        return 0.5 if (row_zero % 2 == 1) else 0.0

    def _hex_center(self, col_zero: int, row_zero: int) -> QPointF:
        row_offset = self._row_offset(row_zero)
        x = self._hex_origin_x + (self._hex_width * (col_zero + row_offset))
        y = self._hex_origin_y + (1.5 * self._hex_size_y * row_zero)
        return QPointF(x, y)

    def _hex_polygon_for_game_hex(self, game_x: int, game_y: int) -> QPolygonF:
        center = self._hex_center(game_x - 1, game_y - 1)
        vertices: list[QPointF] = []
        for i in range(6):
            angle = math.radians(60 * i - 90)
            vx = center.x() + self._hex_size_x * math.cos(angle)
            vy = center.y() + self._hex_size_y * math.sin(angle)
            vertices.append(QPointF(vx, vy))
        return QPolygonF(vertices)

    @staticmethod
    def _cube_round(q: float, r: float) -> tuple[int, int]:
        x = q
        z = r
        y = -x - z

        rx = round(x)
        ry = round(y)
        rz = round(z)

        x_diff = abs(rx - x)
        y_diff = abs(ry - y)
        z_diff = abs(rz - z)

        if x_diff > y_diff and x_diff > z_diff:
            rx = -ry - rz
        elif y_diff > z_diff:
            ry = -rx - rz
        else:
            rz = -rx - ry

        return int(rx), int(rz)

    def _nearest_game_hex(self, scene_point: QPointF) -> tuple[int, int] | None:
        if self._hex_size_x <= 0.0 or self._hex_size_y <= 0.0 or self._hex_width <= 0.0:
            return None

        local_x = scene_point.x() - self._hex_origin_x
        local_y = scene_point.y() - self._hex_origin_y

        norm_x = local_x / self._hex_size_x
        norm_y = local_y / self._hex_size_y
        q = ((math.sqrt(3.0) / 3.0) * norm_x - (1.0 / 3.0) * norm_y)
        r = ((2.0 / 3.0) * norm_y)
        axial_q, axial_r = self._cube_round(q, r)

        row_zero = axial_r
        if self.SHIFT_EVEN_ROWS_RIGHT:
            col_zero = axial_q + ((row_zero + (row_zero & 1)) // 2)
        else:
            col_zero = axial_q + ((row_zero - (row_zero & 1)) // 2)

        col_zero = max(0, min(GAME_COLS - 1, col_zero))
        row_zero = max(0, min(GAME_ROWS - 1, row_zero))
        return (col_zero + 1, row_zero + 1)

    def on_map_hover(self, scene_point: QPointF) -> None:
        hex_xy = self._nearest_game_hex(scene_point)
        self._hover_hex = hex_xy
        if self._map_view is not None and hex_xy is not None:
            selection_text = (
                f" selected ({self._selected_hex[0]},{self._selected_hex[1]})"
                if self._selected_hex is not None
                else ""
            )
            self.statusBar().showMessage(
                f"Hover hex ({hex_xy[0]},{hex_xy[1]}){selection_text}; "
                f"regions: {'on' if self._regions_visible else 'off'}; "
                f"hexgrid: {'on' if self._hex_grid_visible else 'off'}"
            )

    def on_map_click(self, scene_point: QPointF) -> None:
        hex_xy = self._nearest_game_hex(scene_point)
        if hex_xy is None:
            return

        self._selected_hex = hex_xy
        polygon = self._hex_polygon_for_game_hex(hex_xy[0], hex_xy[1])

        if self._selected_hex_item is None:
            self._selected_hex_item = QGraphicsPolygonItem(polygon)
            self._selected_hex_item.setPen(QPen(QColor(255, 235, 59, 225), 2.0))
            self._selected_hex_item.setBrush(QBrush(QColor(255, 235, 59, 48)))
            self._selected_hex_item.setZValue(45)
            self._scene.addItem(self._selected_hex_item)
        else:
            self._selected_hex_item.setPolygon(polygon)
            self._selected_hex_item.setVisible(True)

        self._refresh_detail_panel()

    def _set_regions_visible(self, visible: bool) -> None:
        self._regions_visible = visible
        visibility = visible
        for item in self._region_items:
            item.setVisible(visibility)

    def _set_hex_grid_visible(self, visible: bool) -> None:
        self._hex_grid_visible = visible
        for item in self._hex_grid_items:
            item.setVisible(visible)

    def _save_file_signature(self, file_name: str) -> tuple[int, int]:
        save_file = self._save_path / file_name
        if not save_file.exists():
            return (-1, -1)
        stat = save_file.stat()
        return (int(stat.st_mtime_ns), int(stat.st_size))

    def _side_data_paths(self) -> list[Path]:
        side_folder = "ALLIED" if self._side.upper() == "ALLIED" else "JAPAN"
        data_root = self._save_path / side_folder
        return [
            data_root / "airgroups.json",
            data_root / "bases.json",
            data_root / "ground_units.json",
            data_root / "ships.json",
            data_root / "taskforces.json",
            data_root / "threats.json",
        ]

    def _side_data_signature(self) -> tuple[tuple[str, int, int], ...]:
        signature: list[tuple[str, int, int]] = []
        for path in self._side_data_paths():
            if path.exists():
                stat = path.stat()
                signature.append((path.name, int(stat.st_mtime_ns), int(stat.st_size)))
            else:
                signature.append((path.name, -1, -1))
        return tuple(signature)

    def _ensure_turn_progress_dialog(self) -> QProgressDialog:
        if self._turn_progress_dialog is None:
            self._turn_progress_dialog = QProgressDialog("", "", 0, 0, self)
            self._turn_progress_dialog.setCancelButton(None)
            self._turn_progress_dialog.setWindowTitle("WITPAE Theater Staff")
            self._turn_progress_dialog.setWindowModality(Qt.ApplicationModal)
            self._turn_progress_dialog.setMinimumDuration(0)
        return self._turn_progress_dialog

    def _show_turn_modal(self, text: str) -> None:
        dialog = self._ensure_turn_progress_dialog()
        dialog.setLabelText(text)
        dialog.show()

    def _poll_turn_file(self) -> None:
        pre_turn_signature = self._save_file_signature("wpae002.pws")
        end_turn_signature = self._save_file_signature("wpae000.pws")

        if self._turn_phase == "idle" and pre_turn_signature != self._pre_turn_signature:
            self._pre_turn_signature = pre_turn_signature
            self._turn_phase = "turn-running"
            self._show_turn_modal(
                "Pre-turn save activity detected (wpae002.pws).\n"
                "Turn is running. Waiting for end-of-turn save generation..."
            )
            self._turn_processing_timer.start()
            return

        if self._turn_phase in {"turn-running", "end-turn-writing"} and end_turn_signature != self._end_turn_signature:
            self._end_turn_signature = end_turn_signature
            self._turn_phase = "end-turn-writing"
            self._turn_activity_deadline = time.monotonic() + 4.0
            self._show_turn_modal(
                "End-of-turn save update detected (wpae000.pws).\n"
                "Waiting for file writes to finish before post-turn processing..."
            )

    def _poll_turn_processing(self) -> None:
        if self._turn_progress_dialog is None:
            self._turn_processing_timer.stop()
            return

        if self._turn_phase == "turn-running":
            self._show_turn_modal(
                "Pre-turn save activity detected (wpae002.pws).\n"
                "Turn is still running. Waiting for end-of-turn save generation..."
            )
            return

        if self._turn_phase != "end-turn-writing":
            self._turn_processing_timer.stop()
            return

        current_end_signature = self._save_file_signature("wpae000.pws")
        if current_end_signature != self._end_turn_signature:
            self._end_turn_signature = current_end_signature
            self._turn_activity_deadline = time.monotonic() + 4.0
            self._show_turn_modal(
                "End-of-turn save is still being written (wpae000.pws).\n"
                "Waiting for writes to stabilize before processing..."
            )
            return

        if time.monotonic() < self._turn_activity_deadline:
            return

        current_data_signature = self._side_data_signature()
        if current_data_signature != self._data_signature:
            self._data_signature = current_data_signature
            self._data_ready_deadline = time.monotonic() + 3.0
            self._show_turn_modal(
                "End-of-turn save is stable.\n"
                "Detected post-turn data export updates. Waiting for JSON files to stabilize..."
            )
            return

        if time.monotonic() < self._data_ready_deadline:
            self._show_turn_modal(
                "End-of-turn save is stable.\n"
                "Waiting for post-turn JSON exports to finish writing..."
            )
            return

        self._show_turn_modal(
            "Turn file stabilized.\n"
            "Running post-turn processing:\n"
            "- reloading base map\n"
            "- rebuilding overlays\n"
            "- refreshing data snapshot"
        )
        self._rebuild_presentable_state()
        self._data_signature = self._side_data_signature()
        self._turn_progress_dialog.hide()
        self._turn_processing_timer.stop()
        self._turn_phase = "idle"
        self.statusBar().showMessage("Post-turn processing complete; overlays/data are ready.")

    def _rebuild_presentable_state(self) -> None:
        self._load_map()
        self._refresh_detail_panel()

    def _refresh_detail_panel(self) -> None:
        if self._detail_panel is None:
            return

        data_files = [
            "airgroups.json",
            "bases.json",
            "ground_units.json",
            "ships.json",
            "taskforces.json",
            "threats.json",
        ]
        side_folder = "ALLIED" if self._side.upper() == "ALLIED" else "JAPAN"
        base_path = self._save_path / side_folder

        lines = [
            "Detail panel",
            "",
            "Overlays:",
            f"- Regions: {'ON' if self._regions_visible else 'OFF'}",
            f"- HexGrid: {'ON' if self._hex_grid_visible else 'OFF'}",
            "",
        ]

        if self._hover_hex is not None:
            lines.append(f"Hover hex: ({self._hover_hex[0]},{self._hover_hex[1]})")
        else:
            lines.append("Hover hex: -")

        if self._selected_hex is not None:
            lines.append(f"Selected hex: ({self._selected_hex[0]},{self._selected_hex[1]})")
        else:
            lines.append("Selected hex: -")

        lines.append(f"Turn detector state: {self._turn_phase}")

        lines.extend(["", "Data readiness:"])
        for file_name in data_files:
            full_path = base_path / file_name
            if full_path.exists():
                size_kb = max(1, int(full_path.stat().st_size / 1024))
                lines.append(f"- {file_name}: ready ({size_kb} KB)")
            else:
                lines.append(f"- {file_name}: missing")

        self._detail_panel.setPlainText("\n".join(lines))

    def _startup_game(self) -> None:
        command_parts = self._prompt_startup_command()
        if command_parts is None:
            self.statusBar().showMessage("Game launch canceled.")
            return

        launch_target = Path(command_parts[0])
        if not launch_target.is_absolute():
            launch_target = self._game_dir / launch_target
        if not launch_target.exists():
            message = f"Game executable not found: {launch_target}"
            self.statusBar().showMessage(message)
            QMessageBox.critical(self, "Startup Game", message)
            return

        launch_cmd = [str(launch_target), *command_parts[1:]]

        try:
            subprocess.Popen(
                launch_cmd,
                cwd=str(self._game_dir),
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
            self.statusBar().showMessage("Game launch requested.")
        except Exception as exc:
            logger.exception("Failed to launch game executable: %s", launch_target)
            message = f"Failed to launch game: {exc}"
            self.statusBar().showMessage(message)
            QMessageBox.critical(self, "Startup Game", message)

    def _prompt_startup_command(self) -> list[str] | None:
        default_command = " ".join([f'"{self.GAME_EXECUTABLE}"', *self.GAME_START_ARGS])

        dialog = QDialog(self)
        dialog.setWindowTitle("Startup Game")
        dialog.setModal(True)

        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Edit startup command line, then choose Launch or Cancel.", dialog))

        command_edit = QLineEdit(dialog)
        command_edit.setText(default_command)
        command_edit.selectAll()
        layout.addWidget(command_edit)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, parent=dialog)
        launch_button = button_box.button(QDialogButtonBox.Ok)
        if launch_button is not None:
            launch_button.setText("Launch")
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec_() != QDialog.Accepted:
            return None

        command_text = command_edit.text().strip()
        if not command_text:
            QMessageBox.warning(self, "Startup Game", "Command line is empty.")
            return None

        try:
            command_parts = shlex.split(command_text, posix=False)
        except ValueError as exc:
            QMessageBox.warning(self, "Startup Game", f"Invalid command line: {exc}")
            return None

        command_parts = [self._strip_wrapping_quotes(part) for part in command_parts]

        if not command_parts:
            QMessageBox.warning(self, "Startup Game", "Command line did not produce a launch target.")
            return None

        return command_parts

    @staticmethod
    def _strip_wrapping_quotes(token: str) -> str:
        if len(token) >= 2 and token[0] == token[-1] and token[0] in {'"', "'"}:
            return token[1:-1]
        return token
