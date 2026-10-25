from PySide6.QtCore import QSize, Qt

from ore_metronome.application.metronome_service import MetronomeService
from ore_metronome.domain.models import BeatLevel
from ore_metronome.ui.controller import MAX_BPM, MetronomeController
from ore_metronome.ui.main_window import MainWindow


class FakeAudio:
    def __init__(self) -> None:
        self.is_running = False

    def start(self, settings) -> None:
        self.is_running = True

    def stop(self) -> None:
        self.is_running = False

    def configure(self, settings) -> None:
        pass


class FakeStore:
    def load(self):
        return None

    def save(self, settings) -> None:
        pass


def make_window(qtbot):
    service = MetronomeService(audio_output=FakeAudio(), settings_store=FakeStore())
    window = MainWindow(MetronomeController(service))
    qtbot.addWidget(window)
    return window, service


def test_initial_values_follow_settings(qtbot):
    window, _ = make_window(qtbot)

    assert window._spin.value() == 120
    assert window._slider.value() == 120


def test_spin_change_syncs_slider_and_service(qtbot):
    window, service = make_window(qtbot)

    window._spin.setValue(150)

    assert window._slider.value() == 150
    assert service.settings.bpm == 150


def test_slider_change_syncs_spin_and_service(qtbot):
    window, service = make_window(qtbot)

    window._slider.setValue(90)

    assert window._spin.value() == 90
    assert service.settings.bpm == 90


def test_bpm_is_limited_to_max(qtbot):
    window, service = make_window(qtbot)

    window._spin.setValue(MAX_BPM + 100)

    assert window._spin.value() == MAX_BPM
    assert service.settings.bpm == MAX_BPM


def test_toggle_button_starts_and_stops(qtbot):
    window, service = make_window(qtbot)

    window._toggle.click()
    assert service.is_running
    assert window._toggle.text() == "■ 停止"

    window._toggle.click()
    assert not service.is_running
    assert window._toggle.text() == "▶ 開始"


def test_toggle_button_does_not_take_focus(qtbot):
    window, _ = make_window(qtbot)

    assert window._toggle.focusPolicy() == Qt.FocusPolicy.NoFocus


def show_window(qtbot):
    window, service = make_window(qtbot)
    window.show()
    qtbot.waitExposed(window)
    window.activateWindow()
    qtbot.waitActive(window)
    window.setFocus()
    qtbot.wait(100)
    return window, service


def test_space_toggles_playback(qtbot):
    window, service = show_window(qtbot)

    qtbot.keyClick(window, Qt.Key.Key_Space)

    assert service.is_running


def test_up_and_down_change_bpm_by_one(qtbot):
    window, service = show_window(qtbot)

    qtbot.keyClick(window, Qt.Key.Key_Up)
    assert service.settings.bpm == 121

    qtbot.keyClick(window, Qt.Key.Key_Down)
    assert service.settings.bpm == 120


def test_volume_slider_syncs_service(qtbot):
    window, service = make_window(qtbot)

    window._volume_slider.setValue(30)

    assert service.settings.volume == 30


def test_initial_meter_values_follow_settings(qtbot):
    window, _ = make_window(qtbot)

    assert window._numerator_combo.currentData() == 4
    assert window._denominator_combo.currentData() == 4
    assert window._meter_label.text() == "4分の4拍子"


def test_numerator_change_updates_service_and_label(qtbot):
    window, service = make_window(qtbot)

    window._numerator_combo.setCurrentIndex(window._numerator_combo.findData(3))

    assert service.settings.meter.numerator == 3
    assert window._meter_label.text() == "4分の3拍子"


def test_denominator_change_updates_service_and_label(qtbot):
    window, service = make_window(qtbot)

    window._denominator_combo.setCurrentIndex(window._denominator_combo.findData(8))

    assert service.settings.meter.denominator == 8
    assert window._meter_label.text() == "8分の4拍子"


def test_meter_change_refreshes_beat_indicator(qtbot):
    window, _ = make_window(qtbot)
    calls: list[int] = []
    window._indicator.set_layout = lambda levels: calls.append(len(levels))

    window._numerator_combo.setCurrentIndex(window._numerator_combo.findData(12))
    window._denominator_combo.setCurrentIndex(window._denominator_combo.findData(8))

    assert calls[-1] == 12
    assert window._meter_label.text() == "8分の12拍子"


def test_clicking_beat_indicator_cycles_its_level(qtbot):
    window, service = make_window(qtbot)

    window._indicator.beat_clicked.emit(1)

    assert service.settings.effective_beat_level(1) is BeatLevel.SILENT
    assert window._indicator._levels[1] is BeatLevel.SILENT

    window._indicator.beat_clicked.emit(1)

    assert service.settings.effective_beat_level(1) is BeatLevel.ACCENT
    assert window._indicator._levels[1] is BeatLevel.ACCENT


def test_window_fits_sixteen_beats_in_two_rows(qtbot):
    window, _ = make_window(qtbot)
    window.show()
    window._indicator.set_layout([BeatLevel.NORMAL] * 16)

    assert window.size() == QSize(640, 480)
    assert window._indicator._rows(window._indicator._columns()) == 2


def test_tap_button_sits_right_of_bpm_display(qtbot):
    window, _ = make_window(qtbot)
    window.show()
    qtbot.waitExposed(window)

    spin_rect = window._spin.geometry()
    tap_rect = window._tap.geometry()

    assert tap_rect.left() > spin_rect.right()
    assert abs(tap_rect.center().y() - spin_rect.center().y()) < spin_rect.height() / 2


def test_tap_button_shows_measuring_state_until_reset(qtbot):
    window, _ = make_window(qtbot)
    window._tap_timer.setInterval(20)

    window._tap.click()

    assert window._tap.property("measuring")
    qtbot.waitUntil(lambda: not window._tap.property("measuring"), timeout=1000)


def test_denominator_combo_lists_values_in_ascending_order(qtbot):
    window, _ = make_window(qtbot)
    combo = window._denominator_combo

    values = [combo.itemData(index) for index in range(combo.count())]

    assert values == [2, 4, 8, 16]


def test_denominator_combo_does_not_take_focus(qtbot):
    window, _ = make_window(qtbot)

    assert window._denominator_combo.focusPolicy() == Qt.FocusPolicy.NoFocus


def test_subdivision_change_updates_service(qtbot):
    window, service = make_window(qtbot)

    window._subdivision_combo.setCurrentIndex(window._subdivision_combo.findData(6))

    assert service.settings.subdivision == 6


def test_mask_buttons_match_subdivision_count(qtbot):
    window, _ = make_window(qtbot)

    window._subdivision_combo.setCurrentIndex(window._subdivision_combo.findData(5))

    assert not window._mask_container.isHidden()
    shown = [not button.isHidden() for button in window._mask_buttons]
    assert shown == [True] * 5 + [False] * 4


def test_mask_container_is_hidden_without_subdivision(qtbot):
    window, _ = make_window(qtbot)

    window._subdivision_combo.setCurrentIndex(window._subdivision_combo.findData(1))

    assert window._mask_container.isHidden()


def test_mask_button_click_updates_service(qtbot):
    window, service = make_window(qtbot)
    window._subdivision_combo.setCurrentIndex(window._subdivision_combo.findData(3))

    window._mask_buttons[1].click()

    assert service.settings.mask_for(3) == (True, False, True)


def test_last_on_mask_position_cannot_be_turned_off(qtbot):
    window, service = make_window(qtbot)
    window._subdivision_combo.setCurrentIndex(window._subdivision_combo.findData(2))
    window._mask_buttons[0].click()

    window._mask_buttons[1].click()

    assert service.settings.mask_for(2) == (False, True)
    assert window._mask_buttons[1].isChecked()


def test_subdivision_is_enabled_for_any_denominator(qtbot):
    window, _ = make_window(qtbot)

    window._denominator_combo.setCurrentIndex(window._denominator_combo.findData(8))

    assert window._subdivision_combo.isEnabled()
    assert window._mask_container.isEnabled()

