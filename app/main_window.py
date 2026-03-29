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
from PyQt5.QtGui import QBrush, QColor, QFont, QImage, QPainterPath, QPen, QPixmap, QPolygonF
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
    QMessageBox,
    QVBoxLayout,
)

from app.map_assembly import MapAssembly
from app.regions_overlay import GAME_COLS, GAME_ROWS, REGION_DEFINITIONS


logger = logging.getLogger(__name__)


def pil_image_to_qpixmap(image: Image.Image) -> QPixmap:
    """Convert a PIL image to QPixmap without relying on Pillow's Qt adapters."""
    rgba_image = image.convert("RGBA")
    image_bytes = rgba_image.tobytes("raw", "RGBA")
    qimage = QImage(image_bytes, rgba_image.width, rgba_image.height, rgba_image.width * 4, QImage.Format_RGBA8888)
    return QPixmap.fromImage(qimage.copy())


def prepare_display_image(image: Image.Image, max_dimension: int = 4096) -> Image.Image:
    """Scale oversized maps down to a Qt-friendly display size for 32-bit processes."""
    width, height = image.size
    largest_dimension = max(width, height)
    if largest_dimension <= max_dimension:
        return image

    scale = max_dimension / float(largest_dimension)
    display_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    logger.info("Scaling display map from %sx%s to %sx%s for Qt rendering", width, height, display_size[0], display_size[1])
    return image.resize(display_size, Image.Resampling.LANCZOS)


class MapView(QGraphicsView):
    """Scrollable and zoomable map view."""

    def __init__(self, scene: QGraphicsScene, parent: QMainWindow | None = None) -> None:
        super().__init__(scene, parent)
        self._main_window = parent
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHints(self.renderHints())
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setMouseTracking(True)

    def wheelEvent(self, event) -> None:  # noqa: N802
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else (1.0 / 1.15)
            self.scale(factor, factor)
            event.accept()
            return
        super().wheelEvent(event)

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        if isinstance(self._main_window, MainWindow):
            self._main_window.on_map_hover(self.mapToScene(event.pos()))
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

    def __init__(self, game_dir: Path, save_path: Path, side: str) -> None:
        super().__init__()
        self._game_dir = game_dir
        self._save_path = save_path
        self._side = side
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
        self._hex_size = 0.0
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
        display_image = prepare_display_image(assembly.image)
        pixmap = pil_image_to_qpixmap(display_image)
        self._map_width = pixmap.width()
        self._map_height = pixmap.height()

        self._scene.clear()
        self._scene.addItem(QGraphicsPixmapItem(pixmap))
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

        size_from_width = map_width / (sqrt3 * (cols + 0.5))
        size_from_height = map_height / (1.5 * rows + 0.5)
        hex_size = min(size_from_width, size_from_height)

        hex_width = sqrt3 * hex_size
        grid_width = hex_width * (cols + 0.5)
        grid_height = hex_size * (1.5 * rows + 0.5)
        origin_x = (map_width - grid_width) / 2.0 + (hex_width / 2.0)
        origin_y = (map_height - grid_height) / 2.0 + hex_size
        self._hex_size = hex_size
        self._hex_width = hex_width
        self._hex_origin_x = origin_x
        self._hex_origin_y = origin_y

        path = QPainterPath()
        for row in range(rows):
            row_offset = 0.5 if (row % 2 == 1) else 0.0
            center_y = origin_y + (1.5 * hex_size * row)
            for col in range(cols):
                center_x = origin_x + (hex_width * (col + row_offset))
                vertices = []
                for i in range(6):
                    angle = math.radians(60 * i - 90)
                    vx = center_x + hex_size * math.cos(angle)
                    vy = center_y + hex_size * math.sin(angle)
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

    def _hex_center(self, col_zero: int, row_zero: int) -> QPointF:
        row_offset = 0.5 if (row_zero % 2 == 1) else 0.0
        x = self._hex_origin_x + (self._hex_width * (col_zero + row_offset))
        y = self._hex_origin_y + (1.5 * self._hex_size * row_zero)
        return QPointF(x, y)

    def _hex_polygon_for_game_hex(self, game_x: int, game_y: int) -> QPolygonF:
        center = self._hex_center(game_x - 1, game_y - 1)
        vertices: list[QPointF] = []
        for i in range(6):
            angle = math.radians(60 * i - 90)
            vx = center.x() + self._hex_size * math.cos(angle)
            vy = center.y() + self._hex_size * math.sin(angle)
            vertices.append(QPointF(vx, vy))
        return QPolygonF(vertices)

    def _nearest_game_hex(self, scene_point: QPointF) -> tuple[int, int] | None:
        if self._hex_size <= 0.0 or self._hex_width <= 0.0:
            return None

        px = scene_point.x()
        py = scene_point.y()

        approx_row = int(round((py - self._hex_origin_y) / (1.5 * self._hex_size)))
        best: tuple[int, int] | None = None
        best_dist2 = float("inf")

        for row_zero in range(max(0, approx_row - 2), min(GAME_ROWS - 1, approx_row + 2) + 1):
            offset = 0.5 if (row_zero % 2 == 1) else 0.0
            approx_col = int(round((px - self._hex_origin_x) / self._hex_width - offset))
            for col_zero in range(max(0, approx_col - 2), min(GAME_COLS - 1, approx_col + 2) + 1):
                center = self._hex_center(col_zero, row_zero)
                dx = center.x() - px
                dy = center.y() - py
                dist2 = dx * dx + dy * dy
                if dist2 < best_dist2:
                    best_dist2 = dist2
                    best = (col_zero + 1, row_zero + 1)

        return best

    def on_map_hover(self, scene_point: QPointF) -> None:
        hex_xy = self._nearest_game_hex(scene_point)
        self._hover_hex = hex_xy
        if self._map_view is not None and hex_xy is not None:
            self._map_view.setToolTip(f"Hex ({hex_xy[0]},{hex_xy[1]})")
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
