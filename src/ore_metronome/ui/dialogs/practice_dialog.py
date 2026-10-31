from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ore_metronome.domain.change_up import ChangeUp, ChangeUpStep
from ore_metronome.domain.subdivision import ALLOWED_COUNTS
from ore_metronome.domain.swing import MAX_SWING_PERCENT, MIN_SWING_PERCENT
from ore_metronome.domain.tempo_ramp import TempoRamp
from ore_metronome.ui.controller import MAX_BPM, MIN_BPM, MetronomeController
from ore_metronome.ui.icons import set_button_icon
from ore_metronome.ui.labels import SUBDIVISION_LABELS
from ore_metronome.ui.theme import ACCENT_COLOR
from ore_metronome.ui.widgets.movable_list import MovableList

DEFAULT_EVERY_BARS = 4
DEFAULT_DELTA_BPM = 5
DEFAULT_STEP_BARS = 4
DEFAULT_CHANGE_UP_STEPS = (
    ChangeUpStep(1, DEFAULT_STEP_BARS),
    ChangeUpStep(2, DEFAULT_STEP_BARS),
    ChangeUpStep(3, DEFAULT_STEP_BARS),
    ChangeUpStep(4, DEFAULT_STEP_BARS),
)
# チェンジアップでは細分 1 を「なし」ではなく4分の意味で表示する。
STEP_LABELS = {
    1: "4分",
    **{count: label for count, label in SUBDIVISION_LABELS.items() if count > 1},
}


def _spin(minimum: int, maximum: int, value: int, suffix: str = "") -> QSpinBox:
    spin = QSpinBox()
    spin.setRange(minimum, maximum)
    spin.setValue(value)
    spin.setSuffix(suffix)
    return spin


def _row(*widgets: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    for widget in widgets:
        row.addWidget(widget)
    return row


class PracticeDialog(QDialog):
    """テンポアップ・チェンジアップ・スウィングを設定する。変更は即時に反映する。"""

    def __init__(self, controller: MetronomeController, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self._controller = controller
        self._steps: list[ChangeUpStep] = list(DEFAULT_CHANGE_UP_STEPS)
        self._syncing = False
        self.setWindowTitle("練習設定")
        self._build_ui()
        self.refresh()

    def refresh(self) -> None:
        """コントローラの現在値を画面に反映する。画面操作は再適用しない。"""
        self._quietly(self._load)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(self._build_tempo_ramp_group())
        layout.addWidget(self._build_change_up_group())
        layout.addWidget(self._build_swing_group())
        close_button = QPushButton("閉じる")
        set_button_icon(close_button, "close")
        close_button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        close_button.clicked.connect(self.close)
        bottom_row = QHBoxLayout()
        bottom_row.addStretch()
        bottom_row.addWidget(close_button)
        layout.addLayout(bottom_row)
        self.setMinimumWidth(460)

    def _build_tempo_ramp_group(self) -> QGroupBox:
        group = QGroupBox("テンポアップ")
        layout = QVBoxLayout(group)

        self._ramp_enabled = QCheckBox("有効")
        self._every_spin = _spin(1, 99, DEFAULT_EVERY_BARS, " 小節ごと")
        self._direction_combo = QComboBox()
        self._direction_combo.addItem("上昇", 1)
        self._direction_combo.addItem("下降", -1)
        self._delta_spin = _spin(1, 50, DEFAULT_DELTA_BPM, " BPM")
        self._lower_spin = _spin(MIN_BPM, MAX_BPM, MIN_BPM, " BPM")
        self._upper_spin = _spin(MIN_BPM, MAX_BPM, MAX_BPM, " BPM")
        self._target_check = QCheckBox("目標BPMに達したら戻して繰り返す")
        self._target_spin = _spin(MIN_BPM, MAX_BPM, MAX_BPM, " BPM")

        layout.addWidget(self._ramp_enabled)
        layout.addLayout(_row(self._every_spin, self._direction_combo, self._delta_spin))
        layout.addLayout(_row(QLabel("下限"), self._lower_spin, QLabel("上限"), self._upper_spin))
        layout.addLayout(_row(self._target_check, self._target_spin))

        self._ramp_enabled.toggled.connect(self._apply_ramp)
        self._every_spin.valueChanged.connect(self._apply_ramp)
        self._direction_combo.currentIndexChanged.connect(self._apply_ramp)
        self._delta_spin.valueChanged.connect(self._apply_ramp)
        self._lower_spin.valueChanged.connect(self._on_lower_changed)
        self._upper_spin.valueChanged.connect(self._on_upper_changed)
        self._target_check.toggled.connect(self._apply_ramp)
        self._target_spin.valueChanged.connect(self._apply_ramp)
        return group

    def _build_change_up_group(self) -> QGroupBox:
        group = QGroupBox("チェンジアップ")
        layout = QVBoxLayout(group)

        self._change_up_enabled = QCheckBox("有効")
        self._steps_list = MovableList()
        self._step_subdivision_combo = QComboBox()
        for count in ALLOWED_COUNTS:
            self._step_subdivision_combo.addItem(STEP_LABELS[count], count)
        self._step_bars_spin = _spin(1, 99, DEFAULT_STEP_BARS, " 小節")
        self._add_button = QPushButton("追加")
        self._update_button = QPushButton("更新")
        self._delete_button = QPushButton("削除")
        set_button_icon(self._add_button, "plus", ACCENT_COLOR)
        set_button_icon(self._update_button, "update", ACCENT_COLOR)
        set_button_icon(self._delete_button, "delete", ACCENT_COLOR)
        self._add_button.setProperty("variant", "primary")
        self._update_button.setProperty("variant", "primary")
        self._delete_button.setProperty("variant", "primary")

        layout.addWidget(self._change_up_enabled)
        layout.addWidget(self._steps_list)
        layout.addLayout(_row(self._step_subdivision_combo, self._step_bars_spin))
        layout.addLayout(_row(self._add_button, self._update_button, self._delete_button))

        self._change_up_enabled.toggled.connect(self._apply_change_up)
        self._steps_list.currentRowChanged.connect(self._on_step_selected)
        self._steps_list.move_requested.connect(self._on_step_moved)
        self._add_button.clicked.connect(self._on_add_step)
        self._update_button.clicked.connect(self._on_update_step)
        self._delete_button.clicked.connect(self._on_delete_step)
        return group

    def _build_swing_group(self) -> QGroupBox:
        group = QGroupBox("スウィング")
        layout = QVBoxLayout(group)

        self._swing_slider = QSlider(Qt.Orientation.Horizontal)
        self._swing_slider.setRange(MIN_SWING_PERCENT, MAX_SWING_PERCENT)
        self._swing_label = QLabel()
        hint = QLabel(
            "偶数の細分（8分・16分・6連符・32分）にだけかかります。50%が通常のリズムです。"
        )
        hint.setWordWrap(True)

        layout.addLayout(_row(self._swing_slider, self._swing_label))
        layout.addWidget(hint)

        self._swing_slider.valueChanged.connect(self._on_swing_changed)
        return group

    def _quietly(self, action: Callable[[], None]) -> None:
        previous = self._syncing
        self._syncing = True
        try:
            action()
        finally:
            self._syncing = previous

    def _load(self) -> None:
        ramp = self._controller.tempo_ramp
        self._ramp_enabled.setChecked(ramp is not None)
        if ramp is not None:
            self._every_spin.setValue(ramp.every_bars)
            self._direction_combo.setCurrentIndex(0 if ramp.delta_bpm > 0 else 1)
            self._delta_spin.setValue(abs(ramp.delta_bpm))
            self._lower_spin.setValue(ramp.lower_bpm)
            self._upper_spin.setValue(ramp.upper_bpm)
            self._target_check.setChecked(ramp.target_bpm is not None)
            if ramp.target_bpm is not None:
                self._target_spin.setValue(ramp.target_bpm)

        change_up = self._controller.change_up
        self._change_up_enabled.setChecked(change_up is not None)
        if change_up is not None:
            self._steps = list(change_up.steps)
        self._render_steps()

        swing = self._controller.swing_percent
        self._swing_slider.setValue(swing)
        self._swing_label.setText(f"{swing}%")

    def _apply_ramp(self) -> None:
        if self._syncing:
            return
        self._controller.set_tempo_ramp(self._build_ramp())

    def _build_ramp(self) -> TempoRamp | None:
        if not self._ramp_enabled.isChecked():
            return None
        lower = self._lower_spin.value()
        upper = self._upper_spin.value()
        target = None
        if self._target_check.isChecked():
            target = min(max(self._target_spin.value(), lower), upper)
        direction = int(self._direction_combo.currentData())
        return TempoRamp(
            every_bars=self._every_spin.value(),
            delta_bpm=direction * self._delta_spin.value(),
            lower_bpm=lower,
            upper_bpm=upper,
            target_bpm=target,
        )

    def _on_lower_changed(self, value: int) -> None:
        if self._syncing:
            return
        if value > self._upper_spin.value():
            self._quietly(lambda: self._upper_spin.setValue(value))
        self._apply_ramp()

    def _on_upper_changed(self, value: int) -> None:
        if self._syncing:
            return
        if value < self._lower_spin.value():
            self._quietly(lambda: self._lower_spin.setValue(value))
        self._apply_ramp()

    def _render_steps(self, selected: int = -1) -> None:
        self._steps_list.clear()
        for index, step in enumerate(self._steps):
            label = STEP_LABELS[step.subdivision]
            self._steps_list.add_row(f"{index + 1}. {label} × {step.bars}小節")
        if 0 <= selected < len(self._steps):
            self._steps_list.setCurrentRow(selected)
        self._update_step_buttons()

    def _update_step_buttons(self) -> None:
        selected = self._steps_list.currentRow() >= 0
        self._update_button.setEnabled(selected)
        self._delete_button.setEnabled(selected and len(self._steps) > 1)

    def _on_step_selected(self, row: int) -> None:
        if 0 <= row < len(self._steps):
            step = self._steps[row]
            self._quietly(lambda: self._load_step_editor(step))
        self._update_step_buttons()

    def _load_step_editor(self, step: ChangeUpStep) -> None:
        index = self._step_subdivision_combo.findData(step.subdivision)
        self._step_subdivision_combo.setCurrentIndex(index)
        self._step_bars_spin.setValue(step.bars)

    def _current_step(self) -> ChangeUpStep:
        return ChangeUpStep(
            subdivision=int(self._step_subdivision_combo.currentData()),
            bars=self._step_bars_spin.value(),
        )

    def _on_add_step(self) -> None:
        self._steps.append(self._current_step())
        self._render_steps(selected=len(self._steps) - 1)
        self._apply_change_up()

    def _on_update_step(self) -> None:
        row = self._steps_list.currentRow()
        if row < 0:
            return
        self._steps[row] = self._current_step()
        self._render_steps(selected=row)
        self._apply_change_up()

    def _on_delete_step(self) -> None:
        row = self._steps_list.currentRow()
        if row < 0 or len(self._steps) <= 1:
            return
        del self._steps[row]
        self._render_steps(selected=min(row, len(self._steps) - 1))
        self._apply_change_up()

    def _on_step_moved(self, source: int, target: int) -> None:
        step = self._steps.pop(source)
        self._steps.insert(target, step)
        self._render_steps(selected=target)
        self._apply_change_up()

    def _apply_change_up(self) -> None:
        if self._syncing:
            return
        enabled = self._change_up_enabled.isChecked()
        self._controller.set_change_up(ChangeUp(tuple(self._steps)) if enabled else None)

    def _on_swing_changed(self, value: int) -> None:
        self._swing_label.setText(f"{value}%")
        if self._syncing:
            return
        self._controller.set_swing_percent(value)
