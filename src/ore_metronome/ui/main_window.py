import time
from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ore_metronome.domain.meter import ALLOWED_DENOMINATORS, MAX_NUMERATOR, MIN_NUMERATOR
from ore_metronome.domain.models import MAX_VOLUME, MIN_VOLUME
from ore_metronome.domain.subdivision import ALLOWED_COUNTS
from ore_metronome.domain.tap_tempo import RESET_SECONDS
from ore_metronome.ui.controller import MAX_BPM, MIN_BPM, MetronomeController
from ore_metronome.ui.widgets.beat_indicator import BeatIndicator

TICK_INTERVAL_MS = 15

WINDOW_WIDTH = 640
WINDOW_HEIGHT = 480

MASK_BUTTON_SIZE = 44

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
    padding: 8px;
}
QPushButton {
    background-color: #161616;
    border: 1px solid #1F3D2C;
    border-radius: 12px;
    padding: 16px;
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
}
QPushButton#mask:checked {
    background-color: #00E676;
    color: #0B0B0B;
    font-weight: bold;
}
QPushButton#tap[measuring="true"] {
    background-color: #1F3D2C;
    border: 2px solid #00E676;
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
"""


class MainWindow(QWidget):
    def __init__(self, controller: MetronomeController) -> None:
        super().__init__()
        self._controller = controller
        self.setWindowTitle("Ore Metronome")
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)
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
        self._subdivision_combo.setMinimumWidth(160)
        self._subdivision_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        for count in sorted(ALLOWED_COUNTS):
            self._subdivision_combo.addItem(SUBDIVISION_LABELS[count], count)
        self._subdivision_combo.setCurrentIndex(
            self._subdivision_combo.findData(controller.subdivision)
        )

        self._mask_container = QWidget()
        mask_layout = QHBoxLayout(self._mask_container)
        mask_layout.setContentsMargins(0, 0, 0, 0)
        mask_layout.setSpacing(4)
        self._mask_buttons: list[QPushButton] = []
        for index in range(max(ALLOWED_COUNTS)):
            button = QPushButton(str(index + 1))
            button.setObjectName("mask")
            button.setCheckable(True)
            button.setFixedSize(MASK_BUTTON_SIZE, MASK_BUTTON_SIZE)
            button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            button.clicked.connect(lambda checked, i=index: self._on_mask_clicked(i, checked))
            mask_layout.addWidget(button)
            self._mask_buttons.append(button)
        mask_layout.addStretch()
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
        subdivision_row.addStretch()
        layout = QVBoxLayout(self)
        layout.addWidget(self._indicator)
        layout.addLayout(row)
        layout.addWidget(self._slider)
        layout.addLayout(meter_row)
        layout.addLayout(subdivision_row)
        layout.addWidget(self._mask_container)
        layout.addWidget(self._toggle)
        layout.addWidget(self._volume_slider)
        layout.addStretch()
        self.setStyleSheet(STYLE_SHEET)

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
        mask = self._controller.subdivision_mask(count)
        self._mask_container.setVisible(count > 1)
        for index, button in enumerate(self._mask_buttons):
            button.setVisible(index < count)
            button.setChecked(index < count and mask[index])

    def _on_mask_clicked(self, index: int, checked: bool) -> None:
        count = self._controller.subdivision
        mask = list(self._controller.subdivision_mask(count))
        mask[index] = checked
        if not any(mask):
            self._mask_buttons[index].setChecked(True)
            return
        self._controller.set_subdivision_mask(count, tuple(mask))

    def _update_meter_label(self) -> None:
        self._meter_label.setText(
            f"{self._controller.denominator}分の{self._controller.numerator}拍子"
        )

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