"""Primary PyQt5 application window."""

from __future__ import annotations

import time
import math
import logging
import subprocess
import shlex
import re
from pathlib import Path

from PIL import Image
from PyQt5.QtCore import QPointF, QTimer, Qt
from PyQt5.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap, QPolygonF
from PyQt5.QtWidgets import (
    QAction,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QGraphicsEllipseItem,
    QGraphicsPathItem,
    QGraphicsPolygonItem,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
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
    QToolButton,
    QToolTip,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from app.map_assembly import MapAssembly
from app.regions_overlay import GAME_COLS, GAME_ROWS, REGION_DEFINITIONS, RegionDefinition
from app.runtime_scraper import scrape_snapshot


logger = logging.getLogger(__name__)


def pil_image_to_qpixmap(image: Image.Image) -> QPixmap:
    """Convert a PIL image to QPixmap without relying on Pillow's Qt adapters."""
    rgb_image = image.convert("RGB")
    image_bytes = rgb_image.tobytes("raw", "RGB")
    qimage = QImage(image_bytes, rgb_image.width, rgb_image.height, rgb_image.width * 3, QImage.Format_RGB888)
    return QPixmap.fromImage(qimage.copy())


class TFLegendOverlay(QWidget):
    """Fixed-position overlay legend widget for task force type/color mapping."""

    _SWATCH_W: int = 20
    _SWATCH_H: int = 12
    _PAD: int = 8
    _ROW_H: int = 22
    _TEXT_W: int = 170

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._entries: list[tuple[QColor, str]] = []
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setVisible(False)

    def set_entries(self, entries: list[tuple[QColor, str]]) -> None:
        self._entries = list(entries)
        if entries:
            w = self._PAD * 2 + self._SWATCH_W + 6 + self._TEXT_W
            h = self._PAD + self._ROW_H * len(entries) + self._PAD
            self.resize(w, h)
        self.setVisible(bool(entries))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        if not self._entries:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 175))
        painter.setPen(QPen(QColor(200, 200, 200, 100), 1))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))
        font = QFont("Segoe UI", 8)
        painter.setFont(font)
        y = self._PAD
        for color, label in self._entries:
            swatch_y = y + (self._ROW_H - self._SWATCH_H) // 2
            painter.fillRect(self._PAD, swatch_y, self._SWATCH_W, self._SWATCH_H, color)
            painter.setPen(QPen(QColor(255, 255, 255, 100), 1))
            painter.drawRect(self._PAD, swatch_y, self._SWATCH_W, self._SWATCH_H)
            painter.setPen(QColor(240, 240, 240))
            painter.drawText(self._PAD + self._SWATCH_W + 6, y + self._ROW_H - 5, label)
            y += self._ROW_H
        painter.end()


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
        self._legend_overlay: TFLegendOverlay | None = None
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform, False)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setMouseTracking(True)

    def set_legend_overlay(self, overlay: TFLegendOverlay) -> None:
        self._legend_overlay = overlay

    def reposition_legend_overlay(self) -> None:
        if self._legend_overlay is None or not self._legend_overlay.isVisible():
            return
        margin = 10
        x = self.width() - self._legend_overlay.width() - margin
        y = self.height() - self._legend_overlay.height() - margin
        self._legend_overlay.move(max(0, x), max(0, y))

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self.reposition_legend_overlay()

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

    HEX_COORDINATE_PATTERN = re.compile(r"\((?P<x>\d{1,3})\s*,\s*(?P<y>\d{1,3})\)")
    HEX_COORDINATE_AT_PATTERN = re.compile(r"\bat\s+(?P<x>\d{1,3})\s*,\s*(?P<y>\d{1,3})\b", re.IGNORECASE)
    SUB_WORD_PATTERN = re.compile(r"\bsub\b")
    ALLIED_TEXT_LOG_NAMES = frozenset({"combatreport.txt", "operationsreport.txt", "sigintreport.txt"})
    JAPAN_TEXT_LOG_NAMES = frozenset({"jcombatreport.txt", "joperationsreport.txt", "jsigintreport.txt"})

    COMMON_OVERLAY_LAYERS: list[tuple[str, str]] = [
        ("hexgrid", "HexGrid"),
        ("regions", "Regions"),
        ("invasions", "Invasions"),
        ("threats", "Threats"),
        ("combat", "Combat"),
    ]
    MODE_OVERLAY_LAYERS: dict[str, list[tuple[str, str]]] = {
        "Surface": [
            ("cv_tfs", "CV TFs"),
            ("other_tfs", "Other TF"),
        ],
        "Submarine": [
            ("submarine_patrols", "Patrols"),
            ("submarine_threats", "Threats"),
        ],
        "Air": [],
        "Ground": [],
        "Logistics": [
            ("logistics_taskforces", "Task Forces"),
            ("logistics_bases", "Bases"),
        ],
    }

    # CV TF missions (air-combat carrier task forces).
    CV_TF_MISSIONS: frozenset[str] = frozenset({"AIRCOMBAT"})

    # Missions excluded from the "Other TF" overlay (covered by dedicated layers or not surface).
    OTHER_TF_EXCLUDED_MISSIONS: frozenset[str] = frozenset(
        {"AIRCOMBAT", "CARGO", "REPLENISHMENT", "TANKER", "SUBPATROL"}
    )

    # Color (R, G, B) per mission type for task force line rendering.
    TF_MISSION_COLORS: dict[str, tuple[int, int, int]] = {
        "AIRCOMBAT":         (255, 235,  59),
        "SURFACE":           (220,  50,  50),
        "BOMBARDMENT":       (255, 140,   0),
        "FASTTRANSPORT":     (  0, 210, 210),
        "TRANSPORT":         (100, 160, 255),
        "MINELAYING":        (200, 190,   0),
        "SUBMINELAYING":     (120,  40, 180),
        "SUBTRANSPORT":      ( 60,  80, 200),
        "AIRTRANSPORT":      ( 80, 220, 100),
        "CVESCORT":          (200, 100, 210),
        "AMPHIB":            (255, 100, 190),
        "ASWCOMBAT":         (180,  60,  60),
        "PTBOAT":            (  0, 190, 160),
        "MINESWEEPING":      (180, 180, 180),
        "LANDINGCRAFT":      (210, 150,  80),
        "SUPPORT":           (160, 180, 210),
        "LOCALMINESWEEPING": (200, 220,  50),
        "ESCORT":            (255, 170, 100),
    }

    # Human-readable display names for legend labels.
    TF_MISSION_DISPLAY_NAMES: dict[str, str] = {
        "AIRCOMBAT":         "Air Combat (CV TF)",
        "SURFACE":           "Surface",
        "BOMBARDMENT":       "Bombardment",
        "FASTTRANSPORT":     "Fast Transport",
        "TRANSPORT":         "Transport",
        "MINELAYING":        "Mine Laying",
        "SUBMINELAYING":     "Sub Mine Laying",
        "SUBTRANSPORT":      "Sub Transport",
        "AIRTRANSPORT":      "Air Transport",
        "CVESCORT":          "CV Escort",
        "AMPHIB":            "Amphibious",
        "ASWCOMBAT":         "ASW Combat",
        "PTBOAT":            "PT Boat",
        "MINESWEEPING":      "Mine Sweeping",
        "LANDINGCRAFT":      "Landing Craft",
        "SUPPORT":           "Support",
        "LOCALMINESWEEPING": "Local Mine Sweeping",
        "ESCORT":            "Escort",
    }

    # Arrow geometry constants for task force movement lines.
    # ARROW_SIZE_RATIO: fraction of line length used for arrowhead wings (clamped).
    # ARROW_WING_ANGLE_DEG: half-angle of the arrowhead spread in degrees.
    TF_ARROW_SIZE_RATIO: float = 0.18
    TF_ARROW_SIZE_MIN_PX: float = 6.0
    TF_ARROW_SIZE_MAX_PX: float = 16.0
    TF_ARROW_WING_ANGLE_DEG: float = 28.0
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
        side_token = str(side or "").strip().upper()
        self._side = "JAPAN" if side_token.startswith("JAP") else "ALLIED"
        self._show_mouse_pixel_debug = True
        self._scene = QGraphicsScene(self)
        self._regions_visible = True
        self._region_items: list[object] = []
        self._hex_grid_visible = True
        self._hex_grid_items: list[object] = []
        self._selected_hex_item: QGraphicsPolygonItem | None = None
        self._overlays_dock: QDockWidget | None = None
        self._regions_checkbox: QCheckBox | None = None
        self._hex_grid_checkbox: QCheckBox | None = None
        self._overlay_layer_visibility: dict[str, bool] = {
            "hexgrid": self._hex_grid_visible,
            "regions": self._regions_visible,
            "invasions": False,
            "threats": False,
            "combat": False,
            "cv_tfs": False,
            "other_tfs": False,
            "submarine_patrols": False,
            "submarine_threats": False,
            "logistics_taskforces": False,
            "logistics_bases": False,
        }
        self._map_view: MapView | None = None
        self._detail_panel: QTextEdit | None = None
        self._tf_legend_overlay: TFLegendOverlay | None = None
        self._cv_tf_legend_entries: list[tuple[QColor, str]] = []
        self._other_tf_legend_entries: list[tuple[QColor, str]] = []
        self._map_width = 0
        self._map_height = 0
        self._hex_size_x = 0.0
        self._hex_size_y = 0.0
        self._hex_width = 0.0
        self._hex_origin_x = 0.0
        self._hex_origin_y = 0.0
        self._hover_hex: tuple[int, int] | None = None
        self._selected_hex: tuple[int, int] | None = None
        self._scraper_records_cache: dict[str, list[dict]] = {}
        self._scraper_object_cache: dict[str, dict] = {}
        self._overlay_items: dict[str, list[object]] = {
            "invasions": [],
            "threats": [],
            "combat": [],
            "cv_tfs": [],
            "other_tfs": [],
            "submarine_patrols": [],
            "submarine_threats": [],
            "logistics_taskforces": [],
            "logistics_bases": [],
        }

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
        self._init_overlays_dock()
        self._init_layout()
        self._refresh_scraper_snapshot_from_game(reason="startup")
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
        self.addToolBar(toolbar)

    def _init_overlays_dock(self) -> None:
        dock = QDockWidget("Overlays", self)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)

        content = QWidget(dock)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        map_view_combo = QComboBox(content)
        map_view_combo.addItem("Full Map")
        for region in REGION_DEFINITIONS:
            map_view_combo.addItem(region.name)
        map_view_combo.currentIndexChanged.connect(self._on_map_view_selection_changed)
        layout.addWidget(map_view_combo)

        common_checkboxes: list[QCheckBox] = []
        common_toggle, common_body, common_layout = self._create_overlay_section(
            content, "Common", checkboxes_ref=common_checkboxes, expanded=True
        )
        layout.addWidget(common_toggle)
        layout.addWidget(common_body)

        for layer_key, label in self.COMMON_OVERLAY_LAYERS:
            default_on = layer_key in {"hexgrid", "regions"}
            checkbox = QCheckBox(label, common_body)
            checkbox.setChecked(default_on)
            self._overlay_layer_visibility[layer_key] = default_on
            if layer_key == "regions":
                checkbox.stateChanged.connect(lambda state: self._set_regions_visible(state == Qt.Checked))
                self._regions_checkbox = checkbox
            elif layer_key == "hexgrid":
                checkbox.stateChanged.connect(lambda state: self._set_hex_grid_visible(state == Qt.Checked))
                self._hex_grid_checkbox = checkbox
            else:
                checkbox.stateChanged.connect(
                    lambda state, key=layer_key: self._set_overlay_layer_visible(key, state == Qt.Checked)
                )
            common_layout.addWidget(checkbox)
            common_checkboxes.append(checkbox)

        for group_name, layers in self.MODE_OVERLAY_LAYERS.items():
            group_checkboxes: list[QCheckBox] = []
            group_toggle, group_body, group_layout = self._create_overlay_section(
                content, group_name, checkboxes_ref=group_checkboxes, expanded=False
            )
            layout.addWidget(group_toggle)
            layout.addWidget(group_body)
            for layer_key, label in layers:
                checkbox = QCheckBox(label, group_body)
                checkbox.setChecked(self._overlay_layer_visibility.get(layer_key, False))
                checkbox.stateChanged.connect(
                    lambda state, key=layer_key: self._set_overlay_layer_visible(key, state == Qt.Checked)
                )
                group_layout.addWidget(checkbox)
                group_checkboxes.append(checkbox)

        layout.addStretch(1)
        dock.setWidget(content)
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        self._overlays_dock = dock

    def _create_overlay_section(
        self,
        parent: QWidget,
        title: str,
        *,
        checkboxes_ref: list[QCheckBox],
        expanded: bool,
    ) -> tuple[QToolButton, QWidget, QVBoxLayout]:
        toggle = QToolButton(parent)
        toggle.setText(title)
        toggle.setCheckable(True)
        toggle.setChecked(expanded)
        toggle.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)

        body = QWidget(parent)
        body.setVisible(expanded)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 2, 2, 6)
        body_layout.setSpacing(6)

        def _toggle_section(checked: bool) -> None:
            body.setVisible(checked)
            toggle.setArrowType(Qt.DownArrow if checked else Qt.RightArrow)
            if not checked:
                for cb in checkboxes_ref:
                    cb.setChecked(False)

        toggle.toggled.connect(_toggle_section)
        return toggle, body, body_layout

    def _set_overlay_layer_visible(self, layer_key: str, visible: bool) -> None:
        self._overlay_layer_visibility[layer_key] = bool(visible)
        for item in self._overlay_items.get(layer_key, []):
            item.setVisible(bool(visible))
        if layer_key in {"cv_tfs", "other_tfs"}:
            self._update_tf_legend()
        self._refresh_detail_panel()

    def _set_initial_map_view(self) -> None:
        if self._map_view is None or self._map_width <= 0:
            return

        viewport_width = self._map_view.viewport().width()
        if viewport_width <= 0:
            return

        scale_factor = viewport_width / float(self._map_width)
        self._map_view.resetTransform()
        self._map_view.scale(scale_factor, scale_factor)
        self._map_view.horizontalScrollBar().setValue(0)
        self._map_view.verticalScrollBar().setValue(0)

    def _on_map_view_selection_changed(self, index: int) -> None:
        """Handle map view dropdown selection changes."""
        if index == 0:
            self._set_initial_map_view()
        elif 1 <= index <= len(REGION_DEFINITIONS):
            self._zoom_to_region(REGION_DEFINITIONS[index - 1])

    def _zoom_to_region(self, region: RegionDefinition) -> None:
        """Zoom the map so the region's top-left is at the canvas top-left and its width fills the canvas."""
        if self._map_view is None or self._map_width <= 0 or self._map_height <= 0:
            return

        viewport = self._map_view.viewport()
        viewport_width = viewport.width()
        viewport_height = viewport.height()
        if viewport_width <= 0:
            return

        step_x = self._map_width / (GAME_COLS - 1)
        step_y = self._map_height / (GAME_ROWS - 1)

        xs = [(hx - 1) * step_x for (hx, _hy) in region.polygon_hex]
        ys = [(hy - 1) * step_y for (_hx, hy) in region.polygon_hex]
        min_x = min(xs)
        min_y = min(ys)
        max_x = max(xs)
        region_width = max_x - min_x
        if region_width <= 0:
            return

        scale_factor = viewport_width / region_width
        self._map_view.resetTransform()
        self._map_view.scale(scale_factor, scale_factor)

        center_x = min_x + viewport_width / (2.0 * scale_factor)
        center_y = min_y + viewport_height / (2.0 * scale_factor)
        self._map_view.centerOn(center_x, center_y)

    def _init_layout(self) -> None:
        map_view = MapView(self._scene, self)
        detail_panel = QTextEdit(self)
        detail_panel.setReadOnly(True)
        self._map_view = map_view
        self._detail_panel = detail_panel

        legend_overlay = TFLegendOverlay(map_view)
        self._tf_legend_overlay = legend_overlay
        map_view.set_legend_overlay(legend_overlay)

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
        self._build_submarine_patrols_overlay()
        self._build_submarine_threats_overlay()
        self._build_invasions_overlay()
        self._build_threats_overlay()
        self._build_combat_overlay()
        self._build_cv_tfs_overlay()
        self._build_other_tfs_overlay()
        self._build_logistics_taskforces_overlay()
        self._build_base_status_overlay()
        self._set_regions_visible(self._regions_visible)
        self._set_hex_grid_visible(self._hex_grid_visible)
        for layer_key in self._overlay_items:
            self._set_overlay_layer_visible(layer_key, self._overlay_layer_visibility.get(layer_key, False))
        self._update_tf_legend()
        self._selected_hex_item = None
        self._selected_hex = None

        map_source = "game tiles" if assembly.from_tiles else "placeholder"
        self.statusBar().showMessage(
            "Map loaded from "
            f"{map_source}; regions: {'on' if self._regions_visible else 'off'}; "
            f"hexgrid: {'on' if self._hex_grid_visible else 'off'}"
        )

        if self._map_view is not None:
            QTimer.singleShot(0, self._set_initial_map_view)

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

    def set_scraper_snapshot(
        self,
        *,
        records: dict[str, list[dict]] | None = None,
        objects: dict[str, dict] | None = None,
    ) -> None:
        """Receive in-memory scraper dataset snapshot for overlay rendering."""
        for dataset_name, payload in (records or {}).items():
            key = str(dataset_name).strip().lower()
            if isinstance(payload, list):
                self._scraper_records_cache[key] = [
                    item for item in payload
                    if isinstance(item, dict) and self._record_matches_selected_side(item)
                ]
        for dataset_name, payload in (objects or {}).items():
            key = str(dataset_name).strip().lower()
            if isinstance(payload, dict):
                self._scraper_object_cache[key] = dict(payload)
        logger.info(
            "Scraper snapshot received: %s record datasets, %s object datasets",
            len(records or {}),
            len(objects or {}),
        )

    def _refresh_scraper_snapshot_from_game(self, *, reason: str) -> None:
        """Refresh in-memory snapshot directly from legacy DLL scraper logic."""
        try:
            records, objects = scrape_snapshot(self._game_dir, self._save_path, self._side)
        except Exception as exc:
            logger.warning(
                "In-process scraper refresh failed (%s): %s. "
                "Sub patrols from wpae000 require legacy scraper availability.",
                reason,
                exc,
            )
            return

        self.set_scraper_snapshot(records=records, objects=objects)
        logger.info("In-process scraper refresh complete (%s)", reason)

    def _record_matches_selected_side(self, record: dict) -> bool:
        """Check if a record belongs to the selected side."""
        for field in ("nation", "side", "nationality"):
            if field in record:
                nation = str(record.get(field, "")).lower()
                is_japanese = ("japan" in nation) or ("ijn" in nation)
                return is_japanese if self._side.upper() == "JAPAN" else (not is_japanese)
        return True

    def _get_scraper_records(self, dataset_name: str) -> list[dict]:
        """Get filtered records from scraper cache."""
        key = str(dataset_name).strip().lower()
        return list(self._scraper_records_cache.get(key, []))

    def _get_scraper_object(self, dataset_name: str) -> dict:
        """Get object from scraper cache."""
        key = str(dataset_name).strip().lower()
        return dict(self._scraper_object_cache.get(key, {}))

    @staticmethod
    def _safe_int(value, default: int = 0) -> int:
        """Safely convert value to int."""
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _extract_xy_from_position(payload) -> tuple[int, int] | None:
        """Extract x,y hex coordinates from position dict."""
        if not isinstance(payload, dict):
            return None
        x = MainWindow._safe_int(payload.get("x"), 0)
        y = MainWindow._safe_int(payload.get("y"), 0)
        if x < 1 or y < 1 or x > GAME_COLS or y > GAME_ROWS:
            return None
        return (x, y)

    def _text_log_candidates(self) -> list[Path]:
        allowed_names = self.ALLIED_TEXT_LOG_NAMES if self._side.upper() == "ALLIED" else self.JAPAN_TEXT_LOG_NAMES
        side_folder = "ALLIED" if self._side.upper() == "ALLIED" else "JAPAN"
        search_folders = [self._save_path, self._save_path / side_folder]
        paths: list[Path] = []
        seen: set[Path] = set()

        for folder in search_folders:
            if not folder.exists():
                continue
            for suffix in ("*.txt", "*.log"):
                for path in sorted(folder.glob(suffix)):
                    if not path.is_file():
                        continue
                    if path.name.lower() not in allowed_names:
                        continue
                    if path in seen:
                        continue
                    seen.add(path)
                    paths.append(path)
        return paths

    def _extract_hex_from_text(self, line: str) -> tuple[int, int] | None:
        match = self.HEX_COORDINATE_PATTERN.search(line)
        if match is None:
            match = self.HEX_COORDINATE_AT_PATTERN.search(line)
        if match is None:
            return None

        x = self._safe_int(match.group("x"), 0)
        y = self._safe_int(match.group("y"), 0)
        if x < 1 or y < 1 or x > GAME_COLS or y > GAME_ROWS:
            return None
        return (x, y)

    def _line_is_submarine_patrol(self, line: str) -> bool:
        text = line.lower()
        has_sub = ("submarine" in text) or (self.SUB_WORD_PATTERN.search(text) is not None)
        if not has_sub:
            return False
        if "submarine tf" in text and ("reports having been sighted" in text or "reports sighted" in text):
            return True
        return (
            "sub patrol" in text
            or "subpatrol" in text
            or "on patrol" in text
            or "patrolling" in text
            or "patrol area" in text
        )

    def _line_is_submarine_threat(self, line: str) -> bool:
        text = line.lower()
        has_sub = ("submarine" in text) or (self.SUB_WORD_PATTERN.search(text) is not None)
        if not has_sub:
            return False

        return (
            "sub attack" in text
            or "submarine attack" in text
            or "enemy sub" in text
            or "sub sighted" in text
            or "submarine sighted" in text
            or "sub spotted" in text
            or "submarine spotted" in text
            or "asw attack" in text
        )

    def _collect_submarine_hexes_from_logs(self, *, mode: str) -> set[tuple[int, int]]:
        result: set[tuple[int, int]] = set()
        for log_path in self._text_log_candidates():
            parsed_file = False
            for encoding in ("utf-8", "utf-8-sig", "utf-16", "cp1252"):
                try:
                    log_text = log_path.read_text(encoding=encoding)
                except (OSError, UnicodeError):
                    continue

                parsed_file = True
                before_count = len(result)
                for line in log_text.splitlines():
                    is_match = (
                        self._line_is_submarine_patrol(line)
                        if mode == "patrol"
                        else self._line_is_submarine_threat(line)
                    )
                    if not is_match:
                        continue
                    game_hex = self._extract_hex_from_text(line)
                    if game_hex is not None:
                        result.add(game_hex)

                logger.info(
                    "Parsed log for submarine %s markers: path=%s encoding=%s new=%s total=%s",
                    mode,
                    log_path,
                    encoding,
                    len(result) - before_count,
                    len(result),
                )
                break

            if not parsed_file:
                logger.info("Skipping text log; unable to decode with supported encodings: path=%s", log_path)

        return result

    def _hex_center_for_game_hex(self, game_x: int, game_y: int) -> QPointF | None:
        """Get pixel center for a game hex coordinate."""
        if game_x < 1 or game_y < 1 or game_x > GAME_COLS or game_y > GAME_ROWS:
            return None
        return self._hex_center(game_x - 1, game_y - 1)

    def _draw_hex_radius_circle(
        self,
        layer_key: str,
        game_hex: tuple[int, int],
        *,
        radius_hexes: float = 2.0,
        stroke: QColor,
        fill: QColor,
        width: float = 1.4,
        z_value: float = 34.0,
    ) -> None:
        """Draw a circular marker centered on a hex."""
        center = self._hex_center_for_game_hex(game_hex[0], game_hex[1])
        if center is None:
            return
        radius_px = max(2.0, float(radius_hexes) * self._hex_width)
        marker = QGraphicsEllipseItem(
            center.x() - radius_px,
            center.y() - radius_px,
            radius_px * 2.0,
            radius_px * 2.0,
        )
        marker.setPen(QPen(stroke, width))
        marker.setBrush(QBrush(fill))
        marker.setZValue(z_value)
        self._scene.addItem(marker)
        self._overlay_items[layer_key].append(marker)

    def _build_submarine_patrols_overlay(self) -> None:
        """Build overlay for submarine patrol targets hexes."""
        layer_key = "submarine_patrols"
        self._overlay_items[layer_key].clear()

        patrol_targets: set[tuple[int, int]] = set()
        taskforce_records = self._get_scraper_records("taskforces")
        if not taskforce_records:
            logger.warning(
                "No in-memory taskforces snapshot is loaded for side=%s. "
                "Submarine patrol markers from wpae000 require a scraper snapshot via set_scraper_snapshot().",
                self._side,
            )
        
        for record in taskforce_records:
            mission = str(record.get("mission", "")).strip().upper()
            if mission != "SUBPATROL":
                continue
            target_x = self._safe_int(record.get("target_x"), 0)
            target_y = self._safe_int(record.get("target_y"), 0)
            if target_x < 1 or target_y < 1 or target_x > GAME_COLS or target_y > GAME_ROWS:
                continue
            patrol_targets.add((target_x, target_y))

        patrol_targets_from_logs = self._collect_submarine_hexes_from_logs(mode="patrol")
        patrol_targets.update(patrol_targets_from_logs)

        logger.info(
            "Submarine patrol overlay: side=%s taskforce_records=%d patrol_targets=%d (log-derived=%d)",
            self._side,
            len(taskforce_records),
            len(patrol_targets),
            len(patrol_targets_from_logs),
        )

        for game_hex in sorted(patrol_targets):
            self._draw_hex_radius_circle(
                layer_key,
                game_hex,
                radius_hexes=2.0,
                stroke=QColor(70, 220, 120, 220),
                fill=QColor(70, 220, 120, 48),
                width=1.4,
                z_value=34.0,
            )

    def _build_submarine_threats_overlay(self) -> None:
        """Build overlay for submarine threat areas."""
        layer_key = "submarine_threats"
        self._overlay_items[layer_key].clear()

        threat_hexes: set[tuple[int, int]] = set()
        threat_payload = self._get_scraper_object("threats")
        
        sub_threat_areas = threat_payload.get("sub_threat_areas", [])
        if isinstance(sub_threat_areas, list):
            for record in sub_threat_areas:
                if isinstance(record, dict):
                    pos = self._extract_xy_from_position(record.get("position"))
                    if pos is not None:
                        threat_hexes.add(pos)

        threat_areas = threat_payload.get("threat_areas", [])
        if isinstance(threat_areas, list):
            for record in threat_areas:
                if not isinstance(record, dict):
                    continue
                threat_types = record.get("threat_types", [])
                has_sub = False
                if isinstance(threat_types, list):
                    for tt in threat_types:
                        if "SUB" in str(tt).upper():
                            has_sub = True
                            break
                elif isinstance(threat_types, str) and "SUB" in threat_types.upper():
                    has_sub = True
                
                if has_sub:
                    pos = self._extract_xy_from_position(record.get("position"))
                    if pos is not None:
                        threat_hexes.add(pos)

        threat_hexes_from_logs = self._collect_submarine_hexes_from_logs(mode="threat")
        threat_hexes.update(threat_hexes_from_logs)

        logger.info(
            "Submarine threat overlay: side=%s threat_hexes=%d (log-derived=%d)",
            self._side,
            len(threat_hexes),
            len(threat_hexes_from_logs),
        )

        for game_hex in sorted(threat_hexes):
            self._draw_hex_radius_circle(
                layer_key,
                game_hex,
                radius_hexes=2.0,
                stroke=QColor(232, 82, 82, 230),
                fill=QColor(232, 82, 82, 45),
                width=1.4,
                z_value=34.0,
            )

    def _build_invasions_overlay(self) -> None:
        """Build overlay for invasion landing zones."""
        layer_key = "invasions"
        self._overlay_items[layer_key].clear()

        invasion_hexes: set[tuple[int, int]] = set()
        invasion_records = self._get_scraper_records("invasions")

        for record in invasion_records:
            pos = self._extract_xy_from_position(record.get("position"))
            if pos is None:
                pos = self._extract_xy_from_position(record.get("threat_base_position"))
            if pos is not None:
                invasion_hexes.add(pos)

        logger.info(
            "Invasions overlay: side=%s invasion_records=%d unique_hexes=%d",
            self._side,
            len(invasion_records),
            len(invasion_hexes),
        )

        for game_hex in sorted(invasion_hexes):
            self._draw_hex_radius_circle(
                layer_key,
                game_hex,
                radius_hexes=2.5,
                stroke=QColor(255, 102, 0, 220),
                fill=QColor(255, 102, 0, 50),
                width=2.0,
                z_value=33.0,
            )

    def _build_threats_overlay(self) -> None:
        """Build overlay for general air/naval threats (non-submarine)."""
        layer_key = "threats"
        self._overlay_items[layer_key].clear()

        threat_hexes: set[tuple[int, int]] = set()
        threat_payload = self._get_scraper_object("threats")

        threat_areas = threat_payload.get("threat_areas", [])
        if isinstance(threat_areas, list):
            for record in threat_areas:
                if not isinstance(record, dict):
                    continue
                threat_types = record.get("threat_types", [])
                has_sub = False
                if isinstance(threat_types, list):
                    for tt in threat_types:
                        if "SUB" in str(tt).upper():
                            has_sub = True
                            break
                elif isinstance(threat_types, str) and "SUB" in threat_types.upper():
                    has_sub = True
                
                if not has_sub:
                    pos = self._extract_xy_from_position(record.get("position"))
                    if pos is not None:
                        threat_hexes.add(pos)

        logger.info(
            "General threats overlay: side=%s threat_hexes=%d",
            self._side,
            len(threat_hexes),
        )

        for game_hex in sorted(threat_hexes):
            self._draw_hex_radius_circle(
                layer_key,
                game_hex,
                radius_hexes=2.0,
                stroke=QColor(200, 100, 200, 220),
                fill=QColor(200, 100, 200, 48),
                width=1.4,
                z_value=32.0,
            )

    def _build_combat_overlay(self) -> None:
        """Build overlay for active combat zones."""
        layer_key = "combat"
        self._overlay_items[layer_key].clear()

        combat_hexes: set[tuple[int, int]] = set()
        combat_records = self._get_scraper_records("combats")
        if not combat_records:
            combat_records = self._get_scraper_records("combat_zones")

        for record in combat_records:
            pos = self._extract_xy_from_position(record.get("position"))
            if pos is not None:
                combat_hexes.add(pos)

        logger.info(
            "Combat overlay: side=%s combat_zones=%d unique_hexes=%d",
            self._side,
            len(combat_records),
            len(combat_hexes),
        )

        for game_hex in sorted(combat_hexes):
            self._draw_hex_radius_circle(
                layer_key,
                game_hex,
                radius_hexes=1.8,
                stroke=QColor(255, 0, 0, 240),
                fill=QColor(255, 0, 0, 60),
                width=1.8,
                z_value=35.0,
            )

    def _draw_taskforce_line(
        self,
        layer_key: str,
        start_xy: tuple[int, int],
        end_xy: tuple[int, int],
        target_xy: tuple[int, int] | None,
        *,
        color: QColor,
        width: float = 1.8,
        z_value: float = 36.0,
    ) -> None:
        """Draw a movement line for a task force (start→end solid, end→target dashed)."""
        start_center = self._hex_center_for_game_hex(start_xy[0], start_xy[1])
        end_center = self._hex_center_for_game_hex(end_xy[0], end_xy[1])
        if start_center is None or end_center is None:
            return

        # Build the solid movement line with arrowhead (start → end).
        path = QPainterPath()
        path.moveTo(start_center)
        path.lineTo(end_center)

        dx = end_center.x() - start_center.x()
        dy = end_center.y() - start_center.y()
        length = math.hypot(dx, dy)
        if length > 1e-3:
            angle = math.atan2(dy, dx)
            arrow_size = max(
                self.TF_ARROW_SIZE_MIN_PX,
                min(self.TF_ARROW_SIZE_MAX_PX, length * self.TF_ARROW_SIZE_RATIO),
            )
            wing_angle = math.radians(self.TF_ARROW_WING_ANGLE_DEG)
            path.moveTo(end_center)
            path.lineTo(QPointF(
                end_center.x() - arrow_size * math.cos(angle - wing_angle),
                end_center.y() - arrow_size * math.sin(angle - wing_angle),
            ))
            path.moveTo(end_center)
            path.lineTo(QPointF(
                end_center.x() - arrow_size * math.cos(angle + wing_angle),
                end_center.y() - arrow_size * math.sin(angle + wing_angle),
            ))

        line_item = QGraphicsPathItem(path)
        pen = QPen(color, width)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        line_item.setPen(pen)
        line_item.setBrush(QBrush(Qt.NoBrush))
        line_item.setZValue(z_value)
        self._scene.addItem(line_item)
        self._overlay_items[layer_key].append(line_item)

        # Dashed line from end position to target destination (if different).
        if target_xy is not None and target_xy != end_xy:
            target_center = self._hex_center_for_game_hex(target_xy[0], target_xy[1])
            if target_center is not None:
                target_path = QPainterPath()
                target_path.moveTo(end_center)
                target_path.lineTo(target_center)
                target_item = QGraphicsPathItem(target_path)
                dash_pen = QPen(color, width * 0.75)
                dash_pen.setStyle(Qt.DashLine)
                dash_pen.setCapStyle(Qt.RoundCap)
                target_item.setPen(dash_pen)
                target_item.setBrush(QBrush(Qt.NoBrush))
                target_item.setZValue(z_value - 0.5)
                self._scene.addItem(target_item)
                self._overlay_items[layer_key].append(target_item)

    def _build_cv_tfs_overlay(self) -> None:
        """Build overlay lines for CV (air-combat) task forces."""
        layer_key = "cv_tfs"
        self._overlay_items[layer_key].clear()
        self._cv_tf_legend_entries.clear()

        taskforce_records = self._get_scraper_records("taskforces")
        color_rgb = self.TF_MISSION_COLORS.get("AIRCOMBAT", (255, 235, 59))
        color = QColor(*color_rgb, 220)
        drawn = 0

        for record in taskforce_records:
            mission = str(record.get("mission", "")).strip().upper()
            if mission not in self.CV_TF_MISSIONS:
                continue
    # Mission label → (line RGB, dot RGBA)
    LOGISTICS_TF_MISSION_STYLE: list[tuple[str, tuple[int, int, int], tuple[int, int, int, int]]] = [
        ("CARGO",         (80,  200, 255),  (80,  200, 255, 180)),
        ("TANKER",        (255, 200,  60),  (255, 200,  60, 180)),
        ("REPLENISHMENT", (120, 240, 120),  (120, 240, 120, 180)),
    ]

    def _build_logistics_taskforces_overlay(self) -> None:
        """Draw movement lines for cargo, tanker, and replenishment task forces with a legend."""
        layer_key = "logistics_taskforces"
        self._overlay_items[layer_key].clear()

        taskforce_records = self._get_scraper_records("taskforces")
        if not taskforce_records:
            logger.info(
                "Logistics TF overlay: no taskforces snapshot loaded for side=%s", self._side
            )

        # Build a lookup of mission name → style (line color, dot color)
        mission_style: dict[str, tuple[QColor, QColor, QColor]] = {}
        for mission_name, rgb_line, rgba_dot in self.LOGISTICS_TF_MISSION_STYLE:
            line_color = QColor(*rgb_line)
            dot_color = QColor(*rgba_dot)
            dot_border = QColor(rgb_line[0], rgb_line[1], rgb_line[2], 220)
            mission_style[mission_name] = (line_color, dot_color, dot_border)

        logistics_missions = {m for m, _, _ in self.LOGISTICS_TF_MISSION_STYLE}
        drawn_by_mission: dict[str, int] = {m: 0 for m in logistics_missions}

        for record in taskforce_records:
            mission = str(record.get("mission", "")).strip().upper()
            if mission not in logistics_missions:
                continue

            style = mission_style[mission]
            line_color, dot_color, dot_border = style

            start_x = self._safe_int(record.get("start_of_day_x"), 0)
            start_y = self._safe_int(record.get("start_of_day_y"), 0)
            end_x = self._safe_int(record.get("end_of_day_x"), 0)
            end_y = self._safe_int(record.get("end_of_day_y"), 0)
            if start_x < 1 or start_y < 1 or end_x < 1 or end_y < 1:
                continue
            target_x = self._safe_int(record.get("target_x"), 0)
            target_y = self._safe_int(record.get("target_y"), 0)
            target_xy = (target_x, target_y) if target_x >= 1 and target_y >= 1 else None
            self._draw_taskforce_line(
                layer_key,
                (start_x, start_y),
                (end_x, end_y),
                target_xy,
                color=color,
            )
            drawn += 1

        if drawn > 0:
            display = self.TF_MISSION_DISPLAY_NAMES.get("AIRCOMBAT", "Air Combat (CV TF)")
            self._cv_tf_legend_entries.append((color, display))

        logger.info("CV TFs overlay: side=%s drawn=%d", self._side, drawn)

    def _build_other_tfs_overlay(self) -> None:
        """Build overlay lines for surface task forces (excluding CV, cargo, replenishment, tanker, sub patrol)."""
        layer_key = "other_tfs"
        self._overlay_items[layer_key].clear()
        self._other_tf_legend_entries.clear()

        taskforce_records = self._get_scraper_records("taskforces")
        mission_colors: dict[str, QColor] = {}

        for record in taskforce_records:
            mission = str(record.get("mission", "")).strip().upper()
            if mission in self.OTHER_TF_EXCLUDED_MISSIONS:
                continue
            start_x = self._safe_int(record.get("start_of_day_x"), 0)
            start_y = self._safe_int(record.get("start_of_day_y"), 0)
            end_x = self._safe_int(record.get("end_of_day_x"), 0)
            end_y = self._safe_int(record.get("end_of_day_y"), 0)
            if start_x < 1 or start_y < 1 or end_x < 1 or end_y < 1:
                continue
            color_rgb = self.TF_MISSION_COLORS.get(mission, (180, 180, 180))
            color = QColor(*color_rgb, 220)
            if mission not in mission_colors:
                mission_colors[mission] = color
            target_x = self._safe_int(record.get("target_x"), 0)
            target_y = self._safe_int(record.get("target_y"), 0)
            target_xy = (target_x, target_y) if target_x >= 1 and target_y >= 1 else None
            self._draw_taskforce_line(
                layer_key,
                (start_x, start_y),
                (end_x, end_y),
                target_xy,
                color=color,
            )

        for mission, color in sorted(mission_colors.items()):
            if mission in self.TF_MISSION_DISPLAY_NAMES:
                display = self.TF_MISSION_DISPLAY_NAMES[mission]
            else:
                display = mission.replace("_", " ").title()
                logger.warning(
                    "Other TFs overlay: no display name for mission type %r; using fallback %r",
                    mission,
                    display,
                )
            self._other_tf_legend_entries.append((color, display))

        logger.info(
            "Other TFs overlay: side=%s drawn=%d missions=%s",
            self._side,
            len(self._overlay_items[layer_key]),
            sorted(mission_colors.keys()),
        )

    def _update_tf_legend(self) -> None:
        """Rebuild legend content based on currently visible surface TF overlay layers."""
        if self._tf_legend_overlay is None:
            return
        entries: list[tuple[QColor, str]] = []
        if self._overlay_layer_visibility.get("cv_tfs", False):
            entries.extend(self._cv_tf_legend_entries)
        if self._overlay_layer_visibility.get("other_tfs", False):
            entries.extend(self._other_tf_legend_entries)
        self._tf_legend_overlay.set_entries(entries)
        if self._map_view is not None:
            self._map_view.reposition_legend_overlay()


            start_valid = 1 <= start_x <= GAME_COLS and 1 <= start_y <= GAME_ROWS
            end_valid = 1 <= end_x <= GAME_COLS and 1 <= end_y <= GAME_ROWS

            # Draw movement line start→end when both coordinates are known.
            if start_valid and end_valid:
                start_pt = self._hex_center_for_game_hex(start_x, start_y)
                end_pt = self._hex_center_for_game_hex(end_x, end_y)
                if start_pt is not None and end_pt is not None:
                    pen = QPen(line_color, 1.6, Qt.SolidLine)
                    pen.setCapStyle(Qt.RoundCap)
                    path = QPainterPath()
                    path.moveTo(start_pt)
                    path.lineTo(end_pt)
                    line_item = QGraphicsPathItem(path)
                    line_item.setPen(pen)
                    line_item.setZValue(36.0)
                    self._scene.addItem(line_item)
                    self._overlay_items[layer_key].append(line_item)

            # Draw a dot at the end-of-day position (current location).
            if end_valid:
                center = self._hex_center_for_game_hex(end_x, end_y)
                if center is not None:
                    dot_r = max(3.0, self._hex_width * 0.35)
                    dot_item = QGraphicsEllipseItem(
                        center.x() - dot_r,
                        center.y() - dot_r,
                        dot_r * 2.0,
                        dot_r * 2.0,
                    )
                    dot_item.setPen(QPen(dot_border, 1.2))
                    dot_item.setBrush(QBrush(dot_color))
                    dot_item.setZValue(37.0)
                    self._scene.addItem(dot_item)
                    self._overlay_items[layer_key].append(dot_item)

            drawn_by_mission[mission] = drawn_by_mission.get(mission, 0) + 1

        # Draw a compact legend in the top-left corner of the scene.
        self._draw_logistics_tf_legend(layer_key, mission_style, drawn_by_mission)

        logger.info(
            "Logistics TF overlay: side=%s drawn=%s",
            self._side,
            drawn_by_mission,
        )

    def _draw_logistics_tf_legend(
        self,
        layer_key: str,
        mission_style: dict[str, tuple[QColor, QColor, QColor]],
        drawn_by_mission: dict[str, int],
    ) -> None:
        """Render a small map legend for logistics task force mission colors."""
        legend_x = 40.0
        legend_y = 40.0
        row_height = 22.0
        swatch_w = 30.0
        swatch_h = 10.0
        font = QFont("Segoe UI", 8)

        # Background rectangle — sized to fit all rows.
        rows_shown = [m for m, _, _ in self.LOGISTICS_TF_MISSION_STYLE if drawn_by_mission.get(m, 0) > 0]
        if not rows_shown:
            return

        bg_w = 170.0
        bg_h = row_height * len(rows_shown) + 10.0
        bg = QGraphicsRectItem(legend_x - 6, legend_y - 6, bg_w, bg_h)
        bg.setBrush(QBrush(QColor(20, 20, 20, 170)))
        bg.setPen(QPen(QColor(180, 180, 180, 120), 0.8))
        bg.setZValue(50.0)
        self._scene.addItem(bg)
        self._overlay_items[layer_key].append(bg)

        for i, mission_name in enumerate(rows_shown):
            line_color, dot_color, dot_border = mission_style[mission_name]
            row_y = legend_y + i * row_height

            # Color swatch line.
            sw_path = QPainterPath()
            sw_path.moveTo(legend_x, row_y + swatch_h / 2.0)
            sw_path.lineTo(legend_x + swatch_w, row_y + swatch_h / 2.0)
            sw_item = QGraphicsPathItem(sw_path)
            sw_item.setPen(QPen(line_color, 2.5))
            sw_item.setZValue(51.0)
            self._scene.addItem(sw_item)
            self._overlay_items[layer_key].append(sw_item)

            # Dot at end of swatch.
            dot_r = 4.0
            dot_item = QGraphicsEllipseItem(
                legend_x + swatch_w - dot_r,
                row_y + swatch_h / 2.0 - dot_r,
                dot_r * 2.0,
                dot_r * 2.0,
            )
            dot_item.setPen(QPen(dot_border, 1.0))
            dot_item.setBrush(QBrush(dot_color))
            dot_item.setZValue(52.0)
            self._scene.addItem(dot_item)
            self._overlay_items[layer_key].append(dot_item)

            # Label: mission name + count.
            count = drawn_by_mission.get(mission_name, 0)
            label = QGraphicsSimpleTextItem(f"{mission_name.capitalize()} ({count})")
            label.setFont(font)
            label.setBrush(QBrush(QColor(240, 240, 240)))
            label.setPos(legend_x + swatch_w + 8.0, row_y)
            label.setZValue(52.0)
            self._scene.addItem(label)
            self._overlay_items[layer_key].append(label)

    def _build_base_status_overlay(self) -> None:
        """Draw base status markers color-coded by port level and damage state."""
        layer_key = "logistics_bases"
        self._overlay_items[layer_key].clear()

        base_records = self._get_scraper_records("bases")
        if not base_records:
            logger.info(
                "Base status overlay: no bases snapshot loaded for side=%s", self._side
            )

        drawn = 0
        for record in base_records:
            # Position from the record's position dict or direct x/y fields.
            pos = self._extract_xy_from_position(record.get("position"))
            if pos is None:
                x = self._safe_int(record.get("x"), 0)
                y = self._safe_int(record.get("y"), 0)
                if 1 <= x <= GAME_COLS and 1 <= y <= GAME_ROWS:
                    pos = (x, y)
            if pos is None:
                continue

            port = self._safe_int(record.get("port"), 0)
            airfield = self._safe_int(record.get("airfield"), 0)
            port_damage = self._safe_int(record.get("port_damage"), 0)
            runway_damage = self._safe_int(record.get("runway_damage"), 0)
            airfield_damage = self._safe_int(record.get("airfield_damage"), 0)
            supply = self._safe_int(record.get("supply"), 0)

            # Color coding follows pywitpui conventions:
            # - Major bases (port >= 6) → gold
            # - Large bases (port 4-5 or airfield >= 5) → blue
            # - Medium bases (port 2-3) → green
            # - Minor bases (port 1 or airfield >= 1) → dim grey
            # - Damage present → shift toward red tint
            # - Supply < 1000 at significant base → orange tint warning
            base_level = max(port, airfield)
            if port >= 6:
                stroke = QColor(255, 215, 0, 220)   # gold
                fill = QColor(255, 215, 0, 60)
            elif port >= 4 or airfield >= 5:
                stroke = QColor(100, 160, 255, 220)  # blue
                fill = QColor(100, 160, 255, 50)
            elif port >= 2:
                stroke = QColor(80, 200, 120, 220)   # green
                fill = QColor(80, 200, 120, 45)
            elif base_level >= 1:
                stroke = QColor(180, 180, 180, 180)  # grey
                fill = QColor(180, 180, 180, 35)
            else:
                continue  # skip locations with no port or airfield

            # Apply red tint when significant damage is present.
            total_damage = port_damage + runway_damage + airfield_damage
            if total_damage >= 30:
                stroke = QColor(
                    min(255, stroke.red() + 80),
                    max(0, stroke.green() - 60),
                    max(0, stroke.blue() - 60),
                    stroke.alpha(),
                )
                fill = QColor(
                    min(255, fill.red() + 60),
                    max(0, fill.green() - 40),
                    max(0, fill.blue() - 40),
                    fill.alpha(),
                )

            # Apply orange tint when supply is critically low at a significant base.
            if port >= 2 and supply < 1000:
                stroke = QColor(
                    min(255, stroke.red() + 40),
                    min(255, stroke.green() + 20),
                    max(0, stroke.blue() - 80),
                    stroke.alpha(),
                )

            radius = max(0.6, 0.35 + 0.12 * base_level)
            self._draw_hex_radius_circle(
                layer_key,
                pos,
                radius_hexes=radius,
                stroke=stroke,
                fill=fill,
                width=1.2,
                z_value=31.0,
            )
            drawn += 1

        logger.info(
            "Base status overlay: side=%s total_records=%d drawn=%d",
            self._side,
            len(base_records),
            drawn,
        )

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
        visibility = bool(visible)
        self._regions_visible = visibility
        self._overlay_layer_visibility["regions"] = visibility
        for item in self._region_items:
            item.setVisible(visibility)
        if self._regions_checkbox is not None and self._regions_checkbox.isChecked() != visibility:
            self._regions_checkbox.blockSignals(True)
            self._regions_checkbox.setChecked(visibility)
            self._regions_checkbox.blockSignals(False)
        self._refresh_detail_panel()

    def _set_hex_grid_visible(self, visible: bool) -> None:
        visibility = bool(visible)
        self._hex_grid_visible = visibility
        self._overlay_layer_visibility["hexgrid"] = visibility
        for item in self._hex_grid_items:
            item.setVisible(visibility)
        if self._hex_grid_checkbox is not None and self._hex_grid_checkbox.isChecked() != visibility:
            self._hex_grid_checkbox.blockSignals(True)
            self._hex_grid_checkbox.setChecked(visibility)
            self._hex_grid_checkbox.blockSignals(False)
        self._refresh_detail_panel()

    def _save_file_signature(self, file_name: str) -> tuple[int, int]:
        save_file = self._save_path / file_name
        if not save_file.exists():
            return (-1, -1)
        stat = save_file.stat()
        return (int(stat.st_mtime_ns), int(stat.st_size))

    def _side_data_paths(self) -> list[Path]:
        paths = [self._save_path / "wpae000.pws", self._save_path / "wpae002.pws"]
        paths.extend(self._text_log_candidates())
        return paths

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
            "- refreshing in-process scraper snapshot\n"
            "- reloading base map\n"
            "- rebuilding overlays\n"
            "- refreshing data snapshot"
        )
        self._refresh_scraper_snapshot_from_game(reason="end-turn")
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

        lines.extend(["", "Overlay marker counts:"])
        for layer_key in ["cv_tfs", "other_tfs", "submarine_patrols", "submarine_threats", "invasions", "threats", "combat"]:
        for layer_key in ["submarine_patrols", "submarine_threats", "invasions", "threats", "combat", "logistics_taskforces", "logistics_bases"]:
            marker_count = len(self._overlay_items.get(layer_key, []))
            is_visible = "ON" if marker_count > 0 else "OFF"
            lines.append(f"- {layer_key}: {is_visible} (markers: {marker_count})")

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
