from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QMenuBar

from ore_metronome.application.metronome_service import MetronomeService
from ore_metronome.application.update_service import UpdateService
from ore_metronome.domain.models import BeatLevel
from ore_metronome.domain.update import ReleaseInfo, UpdatePreferences
from ore_metronome.ui import main_window
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


def make_window(qtbot, update_service=None):
    service = MetronomeService(audio_output=FakeAudio(), settings_store=FakeStore())
    window = MainWindow(MetronomeController(service), update_service)
    qtbot.addWidget(window)
    return window, service


class FakeUpdateGateway:
    def __init__(self) -> None:
        self.fetch_count = 0

    def fetch_latest_release(self) -> ReleaseInfo | None:
        self.fetch_count += 1
        return None

    def download_release(self, release):
        raise AssertionError("download must not run in these tests")

    def start_update(self, staged_application) -> None:
        raise AssertionError("update must not start in these tests")


class FakeUpdateStore:
    def __init__(self, check_on_startup: bool) -> None:
        self.preferences = UpdatePreferences(check_on_startup=check_on_startup)

    def load(self) -> UpdatePreferences:
        return self.preferences

    def save(self, preferences: UpdatePreferences) -> None:
        self.preferences = preferences


def make_update_service(check_on_startup: bool = True):
    gateway = FakeUpdateGateway()
    service = UpdateService(gateway, FakeUpdateStore(check_on_startup), "0.1.0")
    return service, gateway


def help_menu_actions(window):
    menu_bar = window.findChild(QMenuBar)
    return {action.text(): action for action in menu_bar.actions()[0].menu().actions()}


def test_startup_check_is_skipped_outside_frozen_build(qtbot):
    update_service, gateway = make_update_service()

    make_window(qtbot, update_service)

    assert gateway.fetch_count == 0


def test_startup_check_runs_in_frozen_build_when_enabled(qtbot, monkeypatch):
    monkeypatch.setattr(main_window, "_is_frozen", lambda: True)
    update_service, gateway = make_update_service(check_on_startup=True)

    window, _ = make_window(qtbot, update_service)

    qtbot.waitUntil(lambda: gateway.fetch_count == 1)
    window._active_task.wait()


def test_manual_check_reports_latest_version(qtbot, monkeypatch):
    monkeypatch.setattr(main_window, "_is_frozen", lambda: True)
    shown = []
    monkeypatch.setattr(main_window.QMessageBox, "information", lambda *args: shown.append(args))
    update_service, gateway = make_update_service(check_on_startup=False)
    window, _ = make_window(qtbot, update_service)

    window._start_update_check(manual=True)

    qtbot.waitUntil(lambda: len(shown) == 1)
    window._active_task.wait()
    assert gateway.fetch_count == 1


def test_startup_toggle_reflects_saved_preference(qtbot):
    update_service, _ = make_update_service(check_on_startup=False)
    window, _ = make_window(qtbot, update_service)

    assert help_menu_actions(window)["起動時に更新を確認"].isChecked() is False


def test_initial_values_follow_settings(qtbot):
    window, _ = make_window(qtbot)

    assert window._spin.value() == 120
    assert window._slider.value() == 120


def test_spin_change_syncs_slider_and_service(qtbot):
    window, service = make_window(qtbot)

    window._spin.setValue(150)

    assert window._slider.value() == 150
    assert service.settings.bpm == 150


def test_closing_window_saves_current_settings(qtbot):
    saved = []

    class RecordingStore(FakeStore):
        def save(self, settings) -> None:
            saved.append(settings)

    service = MetronomeService(audio_output=FakeAudio(), settings_store=RecordingStore())
    window = MainWindow(MetronomeController(service))
    qtbot.addWidget(window)
    window._spin.setValue(150)
    saved.clear()

    window.close()

    assert saved[-1].bpm == 150


def test_beat_indicator_frame_has_no_title(qtbot):
    window, _ = make_window(qtbot)

    titles = [box.title() for box in window.findChildren(QGroupBox)]

    assert "拍" not in titles
    assert window._indicator.parentWidget().title() == ""


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


def test_window_width_fits_six_dots_per_row_and_height_does_not_change_with_beats(qtbot):
    window, _ = make_window(qtbot)
    window.show()
    indicator = window._indicator
    assert indicator.minimumHeight() == indicator.maximumHeight()

    window_heights = set()
    for beats in (1, 16):
        indicator.set_layout([BeatLevel.NORMAL] * beats)
        window_heights.add(window.height())

    assert window.width() == 496
    assert len(window_heights) == 1


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

