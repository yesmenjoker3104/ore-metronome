from PySide6.QtWidgets import QPushButton

from ore_metronome.application.metronome_service import MetronomeService
from ore_metronome.domain.change_up import ChangeUp, ChangeUpStep
from ore_metronome.domain.swing import DEFAULT_SWING_PERCENT
from ore_metronome.domain.tempo_ramp import TempoRamp
from ore_metronome.ui.controller import MetronomeController
from ore_metronome.ui.dialogs.practice_dialog import DEFAULT_CHANGE_UP_STEPS, PracticeDialog


class FakeAudio:
    is_running = False

    def start(self, settings) -> None:
        self.is_running = True

    def stop(self) -> None:
        self.is_running = False

    def now(self) -> None:
        return None

    def configure(self, settings) -> None:
        pass


class FakeSettingsStore:
    def load(self):
        return None

    def save(self, settings) -> None:
        pass


def make_dialog(qtbot):
    service = MetronomeService(audio_output=FakeAudio(), settings_store=FakeSettingsStore())
    controller = MetronomeController(service)
    dialog = PracticeDialog(controller)
    qtbot.addWidget(dialog)
    return dialog, controller


def test_close_button_hides_practice_dialog(qtbot):
    dialog, _ = make_dialog(qtbot)
    dialog.show()
    close_button = next(b for b in dialog.findChildren(QPushButton) if b.text() == "閉じる")

    close_button.click()

    assert not dialog.isVisible()


def test_practice_dialog_delete_button_uses_accent_style(qtbot):
    dialog, _ = make_dialog(qtbot)

    delete_button = next(b for b in dialog.findChildren(QPushButton) if b.text() == "削除")

    assert delete_button.property("variant") == "primary"


def select_subdivision(dialog: PracticeDialog, count: int) -> None:
    dialog._step_subdivision_combo.setCurrentIndex(dialog._step_subdivision_combo.findData(count))


def test_controls_start_in_the_controller_state(qtbot):
    dialog, controller = make_dialog(qtbot)

    assert controller.tempo_ramp is None
    assert controller.change_up is None
    assert not dialog._ramp_enabled.isChecked()
    assert not dialog._change_up_enabled.isChecked()
    assert dialog._swing_slider.value() == DEFAULT_SWING_PERCENT
    assert dialog._swing_label.text() == f"{DEFAULT_SWING_PERCENT}%"


def test_enabling_tempo_ramp_applies_default_ramp(qtbot):
    dialog, controller = make_dialog(qtbot)

    dialog._ramp_enabled.setChecked(True)

    assert controller.tempo_ramp == TempoRamp(every_bars=4, delta_bpm=5)


def test_downward_direction_makes_negative_delta(qtbot):
    dialog, controller = make_dialog(qtbot)
    dialog._ramp_enabled.setChecked(True)

    dialog._direction_combo.setCurrentIndex(1)

    assert controller.tempo_ramp.delta_bpm == -5


def test_lower_bound_above_upper_pulls_upper_up(qtbot):
    dialog, controller = make_dialog(qtbot)
    dialog._ramp_enabled.setChecked(True)

    dialog._upper_spin.setValue(100)
    dialog._lower_spin.setValue(150)

    assert dialog._upper_spin.value() == 150
    assert controller.tempo_ramp.lower_bpm == 150
    assert controller.tempo_ramp.upper_bpm == 150


def test_upper_bound_below_lower_pulls_lower_down(qtbot):
    dialog, controller = make_dialog(qtbot)
    dialog._ramp_enabled.setChecked(True)

    dialog._lower_spin.setValue(120)
    dialog._upper_spin.setValue(80)

    assert dialog._lower_spin.value() == 80
    assert controller.tempo_ramp.lower_bpm == 80
    assert controller.tempo_ramp.upper_bpm == 80


def test_target_is_kept_within_the_ramp_range(qtbot):
    dialog, controller = make_dialog(qtbot)
    dialog._ramp_enabled.setChecked(True)

    dialog._upper_spin.setValue(120)
    dialog._target_check.setChecked(True)
    dialog._target_spin.setValue(200)

    assert controller.tempo_ramp.target_bpm == 120


def test_disabling_tempo_ramp_clears_it(qtbot):
    dialog, controller = make_dialog(qtbot)
    dialog._ramp_enabled.setChecked(True)

    dialog._ramp_enabled.setChecked(False)

    assert controller.tempo_ramp is None


def test_enabling_change_up_applies_default_steps(qtbot):
    dialog, controller = make_dialog(qtbot)

    dialog._change_up_enabled.setChecked(True)

    assert controller.change_up == ChangeUp(steps=DEFAULT_CHANGE_UP_STEPS)


def test_disabled_change_up_keeps_steps_for_next_enable(qtbot):
    dialog, controller = make_dialog(qtbot)
    dialog._change_up_enabled.setChecked(True)
    dialog._steps_list.setCurrentRow(0)
    dialog._delete_button.click()

    dialog._change_up_enabled.setChecked(False)
    assert controller.change_up is None

    dialog._change_up_enabled.setChecked(True)
    assert len(controller.change_up.steps) == len(DEFAULT_CHANGE_UP_STEPS) - 1


def test_add_step_appends_to_change_up(qtbot):
    dialog, controller = make_dialog(qtbot)
    dialog._change_up_enabled.setChecked(True)
    select_subdivision(dialog, 5)
    dialog._step_bars_spin.setValue(2)

    dialog._add_button.click()

    assert dialog._steps_list.count() == len(DEFAULT_CHANGE_UP_STEPS) + 1
    assert controller.change_up.steps[-1] == ChangeUpStep(5, 2)


def test_update_replaces_the_selected_step(qtbot):
    dialog, controller = make_dialog(qtbot)
    dialog._change_up_enabled.setChecked(True)
    dialog._steps_list.setCurrentRow(0)
    select_subdivision(dialog, 9)
    dialog._step_bars_spin.setValue(3)

    dialog._update_button.click()

    assert controller.change_up.steps[0] == ChangeUpStep(9, 3)
    assert dialog._steps_list.currentRow() == 0


def test_delete_removes_the_selected_step(qtbot):
    dialog, controller = make_dialog(qtbot)
    dialog._change_up_enabled.setChecked(True)
    dialog._steps_list.setCurrentRow(1)

    dialog._delete_button.click()

    assert [step.subdivision for step in controller.change_up.steps] == [1, 3, 4]


def test_last_remaining_step_cannot_be_deleted(qtbot):
    dialog, controller = make_dialog(qtbot)
    dialog._change_up_enabled.setChecked(True)
    while dialog._steps_list.count() > 1:
        dialog._steps_list.setCurrentRow(0)
        dialog._delete_button.click()
    dialog._steps_list.setCurrentRow(0)

    assert not dialog._delete_button.isEnabled()
    assert len(controller.change_up.steps) == 1


def test_update_and_delete_need_a_selection(qtbot):
    dialog, _ = make_dialog(qtbot)
    dialog._change_up_enabled.setChecked(True)

    assert dialog._steps_list.currentRow() == -1
    assert not dialog._update_button.isEnabled()
    assert not dialog._delete_button.isEnabled()


def test_moving_a_step_reorders_and_applies(qtbot):
    dialog, controller = make_dialog(qtbot)
    dialog._change_up_enabled.setChecked(True)

    dialog._steps_list.move_requested.emit(0, 2)

    assert [step.subdivision for step in controller.change_up.steps] == [2, 3, 1, 4]


def test_swing_slider_applies_to_controller(qtbot):
    dialog, controller = make_dialog(qtbot)

    dialog._swing_slider.setValue(66)

    assert controller.swing_percent == 66
    assert dialog._swing_label.text() == "66%"


def test_refresh_reflects_controller_without_writing_back(qtbot):
    dialog, controller = make_dialog(qtbot)
    change_up = ChangeUp(steps=(ChangeUpStep(2, 2),))
    controller.set_swing_percent(70)
    controller.set_change_up(change_up)

    dialog.refresh()

    assert dialog._swing_slider.value() == 70
    assert dialog._change_up_enabled.isChecked()
    assert dialog._steps_list.count() == 1
    assert controller.change_up is change_up
