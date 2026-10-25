import sys
import time
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLayout,
    QMenuBar,
    QMessageBox,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ore_metronome.application.ports import WindowStateStore
from ore_metronome.application.update_service import UpdateService
from ore_metronome.domain.meter import ALLOWED_DENOMINATORS, MAX_NUMERATOR, MIN_NUMERATOR
from ore_metronome.domain.models import MAX_VOLUME, MIN_VOLUME, BeatLevel
from ore_metronome.domain.subdivision import ALLOWED_COUNTS
from ore_metronome.domain.tap_tempo import RESET_SECONDS
from ore_metronome.domain.update import ReleaseInfo
from ore_metronome.domain.window import WindowPosition
from ore_metronome.ui.background_task import BackgroundTask
from ore_metronome.ui.controller import MAX_BPM, MIN_BPM, MetronomeController
from ore_metronome.ui.dialogs.update_dialog import UpdateChoice, UpdateDialog
from ore_metronome.ui.widgets.beat_indicator import BeatIndicator
from ore_metronome.version import __version__

TICK_INTERVAL_MS = 15

WINDOW_WIDTH = 496
WINDOW_HEIGHT = 480

MASK_BUTTON_SIZE = 28

MASK_LEVEL_LABELS = {
    BeatLevel.ACCENT: "アクセント",
    BeatLevel.NORMAL: "通常音",
    BeatLevel.SILENT: "音なし",
}

SUBDIVISION_LABELS = {
    1: "なし",
    2: "8分",
    3: "3連符",
    4: "16分",
    5: "5連符",
    6: "6連符",
    7: "7連符",
    8: "32分",
    9: "9連符",
}

STYLE_SHEET = """
QWidget {
    background-color: #0B0B0B;
    color: #F2F2F2;
}
QSpinBox {
    background-color: #161616;
    border: 1px solid #1F3D2C;
    border-radius: 8px;
    padding: 4px 8px;
}
QPushButton {
    background-color: #161616;
    border: 1px solid #1F3D2C;
    border-radius: 12px;
    padding: 8px;
}
QPushButton:hover {
    border-color: #00E676;
}
QPushButton:pressed {
    background-color: #1F3D2C;
}
QPushButton#toggle {
    background-color: #00E676;
    color: #0B0B0B;
    font-weight: bold;
    border: none;
}
QPushButton#mask {
    padding: 4px;
    border-radius: 8px;
    border: 1px solid #3A3A3A;
    color: #6B6B6B;
}
QPushButton#mask[level="normal"] {
    background-color: #1F3D2C;
    border-color: #1F3D2C;
    color: #00E676;
}
QPushButton#mask[level="accent"] {
    background-color: #00E676;
    border-color: #00E676;
    color: #0B0B0B;
    font-weight: bold;
}
QPushButton#tap[measuring="true"] {
    background-color: #1F3D2C;
    border: 1px solid #00E676;
    color: #00E676;
    font-weight: bold;
}
QSlider::groove:horizontal {
    background: #1F3D2C;
    height: 12px;
    border-radius: 6px;
}
QSlider::sub-page:horizontal {
    background: #00E676;
    border-radius: 6px;
}
QSlider::handle:horizontal {
    background: #F2F2F2;
    width: 32px;
    margin: -12px 0;
    border-radius: 16px;
}
QGroupBox {
    border: 1px solid #1F3D2C;
    border-radius: 12px;
    margin-top: 12px;
    padding: 6px 8px 6px 8px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #00E676;
}
"""


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _framed(title: str, content: QWidget | QLayout) -> QGroupBox:
    box = QGroupBox(title)
    layout = QVBoxLayout(box)
    if isinstance(content, QLayout):
        layout.addLayout(content)
    else:
        layout.addWidget(content)
    return box


class MainWindow(QWidget):
    def __init__(
        self,
        controller: MetronomeController,
        update_service: UpdateService | None = None,
        window_store: WindowStateStore | None = None,
    ) -> None:
        super().__init__()
        self._controller = controller
        self._update_service = update_service
        self._window_store = window_store
        self._active_task: BackgroundTask | None = None
        self._manual_check = False
        self.setWindowTitle(f"Ore Metronome v{__version__}")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
        self._restore_window_position()
        font = self.font()
        font.setPointSizeF(font.pointSizeF() * 2)
        self.setFont(font)

        self._spin = QSpinBox()
        self._spin.setRange(MIN_BPM, MAX_BPM)
        self._spin.setValue(controller.bpm)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(MIN_BPM, MAX_BPM)
        self._slider.setValue(controller.bpm)

        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(MIN_VOLUME, MAX_VOLUME)
        self._volume_slider.setValue(controller.volume)
        self._volume_slider.valueChanged.connect(self._controller.set_volume)

        self._toggle = QPushButton()
        self._toggle.setObjectName("toggle")
        self._toggle.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._update_toggle_text()

        self._tap = QPushButton("タップ")
        self._tap.setObjectName("tap")
        self._tap.setFont(self.font())
        self._tap.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._tap_timer = QTimer(self)
        self._tap_timer.setSingleShot(True)
        self._tap_timer.setInterval(round(RESET_SECONDS * 1000))
        self._tap_timer.timeout.connect(self._end_tap_measuring)

        self._numerator_combo = QComboBox()
        self._numerator_combo.setMinimumWidth(110)
        self._numerator_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for numerator in range(MIN_NUMERATOR, MAX_NUMERATOR + 1):
            self._numerator_combo.addItem(str(numerator), numerator)
        self._numerator_combo.setCurrentIndex(
            self._numerator_combo.findData(controller.numerator)
        )

        self._denominator_combo = QComboBox()
        self._denominator_combo.setMinimumWidth(110)
        self._denominator_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for denominator in sorted(ALLOWED_DENOMINATORS):
            self._denominator_combo.addItem(str(denominator), denominator)
        self._denominator_combo.setCurrentIndex(
            self._denominator_combo.findData(controller.denominator)
        )

        self._meter_label = QLabel()
        self._update_meter_label()
        self._numerator_combo.currentIndexChanged.connect(self._on_meter_changed)
        self._denominator_combo.currentIndexChanged.connect(self._on_meter_changed)

        self._subdivision_combo = QComboBox()
        self._subdivision_combo.setMinimumWidth(100)
        self._subdivision_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for count in sorted(ALLOWED_COUNTS):
            self._subdivision_combo.addItem(SUBDIVISION_LABELS[count], count)
        self._subdivision_combo.setCurrentIndex(
            self._subdivision_combo.findData(controller.subdivision)
        )

        self._mask_container = QWidget()
        mask_layout = QHBoxLayout(self._mask_container)
        mask_layout.setContentsMargins(0, 0, 0, 0)
        mask_layout.setSpacing(2)
        # 位置 1 は全拍インジケータに連動し、クリックで全拍の状態を一括で切り替える。
        self._mask_buttons: dict[int, QPushButton] = {}
        for position_index in range(max(ALLOWED_COUNTS)):
            button = QPushButton(str(position_index + 1))
            button.setObjectName("mask")
            button.setFixedSize(MASK_BUTTON_SIZE, MASK_BUTTON_SIZE)
            button.setFont(self.font())
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.clicked.connect(
                lambda _checked=False, i=position_index: self._on_mask_clicked(i)
            )
            mask_layout.addWidget(button)
            self._mask_buttons[position_index] = button
        self._subdivision_combo.currentIndexChanged.connect(self._on_subdivision_changed)
        self._refresh_mask_buttons()

        self._spin.valueChanged.connect(self._on_bpm_changed)
        self._slider.valueChanged.connect(self._on_bpm_changed)
        self._toggle.clicked.connect(self._on_toggle)
        self._tap.clicked.connect(self._on_tap)

        self._bind_shortcut("Space", self._on_toggle)
        self._bind_shortcut("Up", lambda: self._nudge(1))
        self._bind_shortcut("Down", lambda: self._nudge(-1))
        self._bind_shortcut("PgUp", lambda: self._nudge(10))
        self._bind_shortcut("PgDown", lambda: self._nudge(-10))
        self._bind_shortcut("T", self._on_tap)

        self._indicator = BeatIndicator()
        self._indicator.beat_clicked.connect(self._on_beat_clicked)
        self._refresh_indicator()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(TICK_INTERVAL_MS)

        row = QHBoxLayout()
        row.addWidget(self._spin)
        row.addWidget(self._tap)
        meter_row = QHBoxLayout()
        meter_row.addWidget(self._numerator_combo)
        meter_row.addWidget(QLabel("/"))
        meter_row.addWidget(self._denominator_combo)
        meter_row.addWidget(self._meter_label)
        subdivision_row = QHBoxLayout()
        subdivision_row.addWidget(QLabel("連符"))
        subdivision_row.addWidget(self._subdivision_combo)
        subdivision_row.addWidget(self._mask_container)
        subdivision_row.addStretch()
        layout = QVBoxLayout(self)
        layout.setMenuBar(self._build_menu_bar())
        layout.addWidget(_framed("", self._indicator))
        layout.addWidget(_framed("テンポ", row))
        slider_row = QHBoxLayout()
        slider_row.addWidget(_framed("テンポ調整", self._slider), 1)
        slider_row.addWidget(_framed("音量", self._volume_slider), 1)
        layout.addLayout(slider_row)
        layout.addWidget(_framed("拍子", meter_row))
        layout.addWidget(_framed("連符", subdivision_row))
        layout.addWidget(self._toggle)
        layout.addStretch()
        self.setStyleSheet(STYLE_SHEET)
        if (
            update_service is not None
            and _is_frozen()
            and update_service.preferences().check_on_startup
        ):
            self._start_update_check(manual=False)

    def _build_menu_bar(self) -> QMenuBar:
        menu_bar = QMenuBar(self)
        help_menu = menu_bar.addMenu("ヘルプ")
        check_action = help_menu.addAction("更新を確認...")
        startup_action = help_menu.addAction("起動時に更新を確認")
        startup_action.setCheckable(True)
        about_action = help_menu.addAction("バージョン情報")
        check_action.triggered.connect(lambda: self._start_update_check(manual=True))
        about_action.triggered.connect(self._show_about)
        service = self._update_service
        if service is None:
            check_action.setEnabled(False)
            startup_action.setEnabled(False)
        else:
            startup_action.setChecked(service.preferences().check_on_startup)
            startup_action.toggled.connect(service.set_check_on_startup)
        return menu_bar

    def _show_about(self) -> None:
        QMessageBox.about(self, "バージョン情報", f"Ore Metronome\nv{__version__}")

    def _is_task_running(self) -> bool:
        return self._active_task is not None and self._active_task.isRunning()

    def _run_task(
        self,
        work: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_failure: Callable[[str], None],
    ) -> None:
        task = BackgroundTask(work)
        task.succeeded.connect(on_success)
        task.failed.connect(on_failure)
        self._active_task = task
        task.start()

    def _start_update_check(self, *, manual: bool) -> None:
        service = self._update_service
        if service is None or self._is_task_running():
            return
        if not _is_frozen():
            if manual:
                QMessageBox.information(
                    self, "アップデート", "開発実行中はアップデートを適用できません。"
                )
            return
        self._manual_check = manual
        ignore_skipped = not manual
        self._run_task(
            lambda: service.find_newer_release(ignore_skipped=ignore_skipped),
            self._on_check_succeeded,
            self._on_check_failed,
        )

    def _on_check_succeeded(self, release: ReleaseInfo | None) -> None:
        if release is None:
            if self._manual_check:
                QMessageBox.information(
                    self, "アップデート", f"現在のバージョン v{__version__} は最新です。"
                )
            return
        dialog = UpdateDialog(__version__, release, self)
        dialog.exec()
        service = self._update_service
        if service is None:
            return
        if dialog.choice is UpdateChoice.SKIP:
            service.skip_version(release.version)
        elif dialog.choice is UpdateChoice.INSTALL:
            self._start_download(release)

    def _on_check_failed(self, message: str) -> None:
        if self._manual_check:
            QMessageBox.warning(self, "アップデート", f"更新の確認に失敗しました。\n{message}")

    def _start_download(self, release: ReleaseInfo) -> None:
        service = self._update_service
        if service is None:
            return
        self._run_task(
            lambda: service.download(release),
            self._on_download_succeeded,
            self._on_download_failed,
        )

    def _on_download_succeeded(self, staged: Any) -> None:
        service = self._update_service
        if service is None:
            return
        try:
            service.apply(staged)
        except Exception as error:
            QMessageBox.warning(self, "アップデート", f"更新を開始できませんでした。\n{error}")
            return
        self.close()

    def _on_download_failed(self, message: str) -> None:
        QMessageBox.warning(self, "アップデート", f"ダウンロードに失敗しました。\n{message}")

    def _bind_shortcut(self, key: str, handler: Callable[[], None]) -> None:
        shortcut = QShortcut(QKeySequence(key), self)
        shortcut.activated.connect(handler)

    def _nudge(self, delta: int) -> None:
        self._spin.setValue(self._spin.value() + delta)

    def _on_bpm_changed(self, bpm: int) -> None:
        self._controller.set_bpm(bpm)
        for widget in (self._spin, self._slider):
            widget.blockSignals(True)
            widget.setValue(bpm)
            widget.blockSignals(False)

    def _on_meter_changed(self) -> None:
        self._controller.set_meter(
            self._numerator_combo.currentData(),
            self._denominator_combo.currentData(),
        )
        self._update_meter_label()
        self._refresh_indicator()

    def _on_subdivision_changed(self) -> None:
        self._controller.set_subdivision(self._subdivision_combo.currentData())
        self._refresh_mask_buttons()

    def _refresh_mask_buttons(self) -> None:
        count = self._controller.subdivision
        self._mask_container.setVisible(count > 1)
        for position_index, button in self._mask_buttons.items():
            button.setVisible(position_index < count)
            if position_index < count:
                level = self._controller.subdivision_position_level(position_index)
                self._set_mask_level(button, level)

    def _set_mask_level(self, button: QPushButton, level: BeatLevel) -> None:
        button.setProperty("level", level.value)
        button.setToolTip(MASK_LEVEL_LABELS[level])
        button.style().unpolish(button)
        button.style().polish(button)

    def _on_mask_clicked(self, position_index: int) -> None:
        self._controller.cycle_subdivision_position(position_index)
        self._refresh_mask_buttons()

    def _update_meter_label(self) -> None:
        self._meter_label.setText(
            f"{self._controller.denominator}分の{self._controller.numerator}拍子"
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        self._controller.save_settings()
        if self._window_store is not None:
            position = self.pos()
            self._window_store.save(WindowPosition(position.x(), position.y()))
        super().closeEvent(event)

    def _restore_window_position(self) -> None:
        if self._window_store is None:
            return
        position = self._window_store.load()
        if position is None:
            return
        # 画面外や画面をまたぐ位置は、外したモニターに取り残されないよう既定位置のままにする。
        rect = QRect(position.x, position.y, WINDOW_WIDTH, WINDOW_HEIGHT)
        if any(screen.availableGeometry().contains(rect) for screen in QApplication.screens()):
            self.move(position.x, position.y)

    def _on_toggle(self) -> None:
        self._controller.toggle()
        self._update_toggle_text()

    def _on_tap(self) -> None:
        self._controller.tap(time.monotonic())
        self._spin.setValue(self._controller.bpm)
        self._set_tap_measuring(True)
        self._tap_timer.start()

    def _end_tap_measuring(self) -> None:
        self._set_tap_measuring(False)

    def _set_tap_measuring(self, measuring: bool) -> None:
        self._tap.setProperty("measuring", measuring)
        self._tap.style().unpolish(self._tap)
        self._tap.style().polish(self._tap)

    def _update_toggle_text(self) -> None:
        self._toggle.setText("■ 停止" if self._controller.is_running else "▶ 開始")

    def _refresh_indicator(self) -> None:
        beats = self._controller.beats_per_bar
        levels = [self._controller.beat_level(index) for index in range(beats)]
        self._indicator.set_layout(levels)

    def _on_beat_clicked(self, beat_index: int) -> None:
        self._controller.cycle_beat_level(beat_index)
        self._refresh_indicator()

    def _on_tick(self) -> None:
        if not self._controller.is_running:
            return
        for event in self._controller.drain_beats():
            self._indicator.set_active_beat(event.beat_index)

        if not self._controller.is_running:
            self._indicator.set_active_beat(None)