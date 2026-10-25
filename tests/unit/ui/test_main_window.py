from PySide6.QtCore import Qt

from ore_metronome.application.metronome_service import MetronomeService
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