from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QSlider, QSpinBox, QVBoxLayout, QWidget

from ore_metronome.ui.controller import MAX_BPM, MIN_BPM, MetronomeController


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
        self._toggle.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._update_toggle_text()

        self._spin.valueChanged.connect(self._on_bpm_changed)
        self._slider.valueChanged.connect(self._on_bpm_changed)
        self._toggle.clicked.connect(self._on_toggle)

        row = QHBoxLayout()
        row.addWidget(self._spin)
        layout = QVBoxLayout(self)
        layout.addLayout(row)
        layout.addWidget(self._slider)
        layout.addWidget(self._toggle)

    def _on_bpm_changed(self, bpm:int) -> None:
        self._controller.set_bpm(bpm)
        for widget in (self._spin, self._slider):
            widget.blockSignals(True)
            widget.setValue(bpm)
            widget.blockSignals(False)

    def _on_toggle(self) -> None:
        self._controller.toggle()
        self._update_toggle_text()

    def _update_toggle_text(self) -> None:
        self._toggle.setText("■ 停止" if self._controller.is_running else "▶ 開始")