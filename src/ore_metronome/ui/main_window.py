import time
from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ore_metronome.ui.controller import MAX_BPM, MIN_BPM, MetronomeController
from ore_metronome.ui.widgets.beat_indicator import BeatIndicator

TICK_INTERVAL_MS = 15

STYLE_SHEET = """
QWidget {
    background-color: #0B0B0B;
    color: #F2F2F2;
}
QSpinBox {
    background-color: #161616;
    border: 1px solid #1F3D2C;
    border-radius: 4px;
    padding: 4px;
}
QPushButton {
    background-color: #161616;
    border: 1px solid #1F3D2C;
    border-radius: 6px;
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
QSlider::groove:horizontal {
    background: #1F3D2C;
    height: 6px;
    border-radius: 3px;
}
QSlider::sub-page:horizontal {
    background: #00E676;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #F2F2F2;
    width: 16px;
    margin: -6px 0;
    border-radius: 8px;
}
"""


class MainWindow(QWidget):
    def __init__(self, controller: MetronomeController) -> None:
        super().__init__()
        self._controller = controller
        self.setWindowTitle("Ore Metronome")

        self._spin = QSpinBox()
        self._spin.setRange(MIN_BPM, MAX_BPM)
        self._spin.setValue(controller.bpm)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(MIN_BPM, MAX_BPM)
        self._slider.setValue(controller.bpm)

        self._toggle = QPushButton()
        self._toggle.setObjectName("toggle")
        self._toggle.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._update_toggle_text()

        self._tap = QPushButton("タップ")
        self._tap.setFocusPolicy(Qt.FocusPolicy.NoFocus)

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
        self._refresh_indicator()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)
        self._timer.start(TICK_INTERVAL_MS)

        row = QHBoxLayout()
        row.addWidget(self._spin)
        layout = QVBoxLayout(self)
        layout.addWidget(self._indicator)
        layout.addLayout(row)
        layout.addWidget(self._slider)
        layout.addWidget(self._toggle)
        layout.addWidget(self._tap)
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

    def _on_toggle(self) -> None:
        self._controller.toggle()
        self._update_toggle_text()

    def _on_tap(self) -> None:
        self._controller.tap(time.monotonic())
        self._spin.setValue(self._controller.bpm)

    def _update_toggle_text(self) -> None:
        self._toggle.setText("■ 停止" if self._controller.is_running else "▶ 開始")

    def _refresh_indicator(self) -> None:
        self._indicator.set_layout(
            self._controller.beats_per_bar,
            self._controller.accent_enabled,
        )

    def _on_tick(self) -> None:
        if not self._controller.is_running:
            return
        for event in self._controller.drain_beats():
            self._indicator.set_active_beat(event.beat_index)

        if not self._controller.is_running:
            self._indicator.set_active_beat(None)