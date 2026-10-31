import pytest
from PySide6.QtCore import QRect, Qt
from PySide6.QtWidgets import QApplication, QGroupBox, QListWidget, QMenuBar

from ore_metronome.application.metronome_service import MetronomeService
from ore_metronome.application.ports import BeatEvent
from ore_metronome.application.setlist_service import SetlistService
from ore_metronome.application.update_service import UpdateService
from ore_metronome.domain.models import MAX_VOLUME, MIN_VOLUME, BeatLevel
from ore_metronome.domain.update import ReleaseInfo, UpdatePreferences
from ore_metronome.domain.window import WindowGeometry
from ore_metronome.infrastructure.persistence.setlist_repository import SetlistRepository
from ore_metronome.ui import main_window
from ore_metronome.ui.controller import MAX_BPM, MIN_BPM, MetronomeController
from ore_metronome.ui.main_window import PLAYLIST_FONT_POINT_SIZE, MainWindow


class FakeAudio:
    def __init__(self) -> None:
        self.is_running = False

    def start(self, settings) -> None:
        self.is_running = True

    def stop(self) -> None:
        self.is_running = False

    def now(self) -> float | None:
        return None

    def configure(self, settings) -> None:
        pass


class FakeStore:
    def load(self):
        return None

    def save(self, settings) -> None:
        pass


class FakeWindowStore:
    def __init__(self, geometry: WindowGeometry | None = None) -> None:
        self._geometry = geometry
        self.saved: list[WindowGeometry] = []

    def load(self) -> WindowGeometry | None:
        return self._geometry

    def save(self, geometry: WindowGeometry) -> None:
        self.saved.append(geometry)


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
    assert window._toggle.text() == "停止"

    window._toggle.click()
    assert not service.is_running
    assert window._toggle.text() == "開始"


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


def test_tempo_buttons_change_bpm_by_five_and_sync_slider(qtbot):
    window, service = make_window(qtbot)

    window._tempo_up.click()
    assert service.settings.bpm == 125
    assert window._slider.value() == 125

    window._tempo_down.click()
    window._tempo_down.click()
    assert service.settings.bpm == 115
    assert window._slider.value() == 115
    assert window._spin.value() == 115


def test_tempo_buttons_stop_at_bpm_limits(qtbot):
    window, service = make_window(qtbot)

    window._spin.setValue(MAX_BPM - 2)
    window._tempo_up.click()
    assert service.settings.bpm == MAX_BPM

    window._spin.setValue(MIN_BPM + 2)
    window._tempo_down.click()
    assert service.settings.bpm == MIN_BPM


def test_volume_slider_syncs_service(qtbot):
    window, service = make_window(qtbot)

    window._volume_slider.setValue(30)

    assert service.settings.volume == 30


def test_volume_buttons_change_volume_by_five_and_stop_at_limits(qtbot):
    window, service = make_window(qtbot)
    window._volume_slider.setValue(50)

    window._volume_up.click()
    assert service.settings.volume == 55
    assert window._volume_slider.value() == 55

    window._volume_down.click()
    window._volume_down.click()
    assert service.settings.volume == 45

    window._volume_slider.setValue(MAX_VOLUME - 2)
    window._volume_up.click()
    assert service.settings.volume == MAX_VOLUME

    window._volume_slider.setValue(MIN_VOLUME + 2)
    window._volume_down.click()
    assert service.settings.volume == MIN_VOLUME


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


def test_width_fits_six_dots_per_row_and_height_does_not_change_with_beats(qtbot):
    window, _ = make_window(qtbot)
    window.show()
    indicator = window._indicator

    window_heights = set()
    for beats in (1, 16):
        indicator.set_layout([BeatLevel.NORMAL] * beats)
        window_heights.add(window.height())

    assert window.width() == 496
    assert len(window_heights) == 1


def test_extra_window_height_goes_to_beat_indicator_only(qtbot):
    window, _ = make_window(qtbot)
    window.show()
    QApplication.processEvents()
    controls = (window._slider, window._volume_slider, window._denominator_combo, window._toggle)
    before = [(w.mapTo(window, w.rect().topLeft()).y(), w.size()) for w in controls]
    indicator_height = window._indicator.height()

    window.resize(window.width(), window.height() + 150)
    QApplication.processEvents()

    after = [(w.mapTo(window, w.rect().topLeft()).y(), w.size()) for w in controls]
    assert window._indicator.height() == indicator_height + 150
    for (old_y, old_size), (new_y, new_size) in zip(before, after, strict=True):
        assert new_y - old_y == 150
        assert new_size == old_size


def test_tap_button_sits_right_of_bpm_display(qtbot):
    window, _ = make_window(qtbot)
    window.show()
    qtbot.waitExposed(window)

    spin_rect = window._spin.geometry()
    tap_rect = window._tap.geometry()

    assert tap_rect.left() > spin_rect.right()
    assert abs(tap_rect.center().y() - spin_rect.center().y()) < spin_rect.height() / 2


def test_tap_button_keeps_font_size_while_measuring(qtbot):
    window, _ = make_window(qtbot)
    window.show()
    qtbot.waitExposed(window)
    font_size = window._tap.font().pointSizeF()
    size = window._tap.size()

    window._on_tap()
    qtbot.wait(10)

    assert window._tap.font().pointSizeF() == font_size
    assert window._tap.size() == size


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
    shown = {index for index, button in window._mask_buttons.items() if not button.isHidden()}
    assert shown == {0, 1, 2, 3, 4}


def test_first_position_has_a_mask_button(qtbot):
    window, _ = make_window(qtbot)

    assert 0 in window._mask_buttons


def test_mask_container_is_hidden_without_subdivision(qtbot):
    window, _ = make_window(qtbot)

    window._subdivision_combo.setCurrentIndex(window._subdivision_combo.findData(1))

    assert window._mask_container.isHidden()


def test_mask_button_click_cycles_level(qtbot):
    window, service = make_window(qtbot)
    window._subdivision_combo.setCurrentIndex(window._subdivision_combo.findData(3))

    window._mask_buttons[1].click()

    assert service.settings.mask_for(3) == (
        BeatLevel.ACCENT,
        BeatLevel.SILENT,
        BeatLevel.NORMAL,
    )
    assert window._mask_buttons[1].property("level") == "silent"


def test_mask_button_click_visits_accent_normal_and_silent(qtbot):
    window, service = make_window(qtbot)
    window._subdivision_combo.setCurrentIndex(window._subdivision_combo.findData(2))
    button = window._mask_buttons[1]

    levels = []
    for _ in range(3):
        button.click()
        levels.append(service.settings.mask_for(2)[1])

    assert levels == [BeatLevel.SILENT, BeatLevel.ACCENT, BeatLevel.NORMAL]
    assert button.property("level") == "normal"


def test_mask_button_shows_level_for_accent(qtbot):
    window, service = make_window(qtbot)
    window._subdivision_combo.setCurrentIndex(window._subdivision_combo.findData(2))

    window._mask_buttons[1].click()
    window._mask_buttons[1].click()

    assert window._mask_buttons[1].property("level") == "accent"
    assert window._mask_buttons[1].toolTip() == "アクセント"


def test_first_position_button_defaults_to_accent(qtbot):
    window, _ = make_window(qtbot)
    window._subdivision_combo.setCurrentIndex(window._subdivision_combo.findData(3))

    assert window._mask_buttons[0].property("level") == "accent"
    assert window._mask_buttons[0].toolTip() == "アクセント"


def test_first_position_click_cycles_only_its_own_level(qtbot):
    window, service = make_window(qtbot)
    window._subdivision_combo.setCurrentIndex(window._subdivision_combo.findData(3))
    beat_levels_before = dict(service.settings.beat_levels)

    window._mask_buttons[0].click()

    assert service.settings.mask_for(3)[0] is BeatLevel.NORMAL
    assert dict(service.settings.beat_levels) == beat_levels_before
    assert window._mask_buttons[0].property("level") == "normal"


def test_beat_click_does_not_change_first_position_button(qtbot):
    window, _ = make_window(qtbot)
    window._subdivision_combo.setCurrentIndex(window._subdivision_combo.findData(3))

    window._indicator.beat_clicked.emit(0)

    assert window._mask_buttons[0].property("level") == "accent"


def test_window_geometry_is_saved_on_close(qtbot):
    store = FakeWindowStore()
    service = MetronomeService(audio_output=FakeAudio(), settings_store=FakeStore())
    window = MainWindow(MetronomeController(service), window_store=store)
    qtbot.addWidget(window)
    window.setGeometry(60, 70, 520, 460)

    window.close()

    assert store.saved == [WindowGeometry(60, 70, 520, 460)]


def make_window_with_playlists(qtbot, tmp_path, store=None):
    metronome = MetronomeService(audio_output=FakeAudio(), settings_store=FakeStore())
    setlist = SetlistService(metronome, SetlistRepository(tmp_path / "setlists.json"))
    window = MainWindow(MetronomeController(metronome), window_store=store, setlist_service=setlist)
    qtbot.addWidget(window)
    return window


def test_playlist_button_opens_panel_on_the_right(qtbot, tmp_path):
    window = make_window_with_playlists(qtbot, tmp_path)
    window.show()
    QApplication.processEvents()
    window.resize(800, window.height())
    QApplication.processEvents()
    width = window.width()

    window._playlist_button.click()
    QApplication.processEvents()

    assert not window._playlist_panel.isHidden()
    assert window.width() == width + main_window.PLAYLIST_PANEL_WIDTH

    window._playlist_button.click()
    QApplication.processEvents()

    assert window._playlist_panel.isHidden()
    assert window.width() == width


@pytest.mark.parametrize("show", ["showMaximized", "showFullScreen"])
def test_playlist_panel_stays_on_screen_when_window_is_maximized(qtbot, tmp_path, show):
    window = make_window_with_playlists(qtbot, tmp_path)
    getattr(window, show)()
    QApplication.processEvents()
    size = window.size()

    window._playlist_button.click()
    QApplication.processEvents()

    if window.minimumSizeHint().width() > window.screen().availableGeometry().width():
        pytest.skip("画面幅が開いた状態のレイアウト最小幅より狭いので、全画面状態は検証できない")
    panel = window._playlist_panel
    assert panel.isVisible()
    assert window.isMaximized() or window.isFullScreen()
    # 幅は、レイアウトの最小幅が要求する分だけ広がる（それ以上は広げない）。
    assert window.width() == max(size.width(), window.minimumSizeHint().width())
    assert window.rect().contains(panel.geometry())
    opened_size = window.size()

    window._playlist_button.click()
    QApplication.processEvents()

    assert panel.isHidden()
    assert window.size() == opened_size
    assert window.isMaximized() or window.isFullScreen()


def test_window_geometry_saved_without_panel_width(qtbot, tmp_path):
    store = FakeWindowStore()
    window = make_window_with_playlists(qtbot, tmp_path, store)
    window.setGeometry(60, 70, 520, 460)
    window._playlist_button.click()

    window.close()

    assert store.saved == [WindowGeometry(60, 70, 520, 460)]


def test_closing_playlist_panel_restores_window_size(qtbot, tmp_path):
    window = make_window_with_playlists(qtbot, tmp_path)
    window.show()
    QApplication.processEvents()
    window.resize(600, window.height())
    QApplication.processEvents()
    size = (window.width(), window.height())

    window._playlist_button.click()
    QApplication.processEvents()
    window._playlist_button.click()
    QApplication.processEvents()

    assert (window.width(), window.height()) == size


def test_opening_playlist_panel_keeps_controls_in_place(qtbot, tmp_path):
    window = make_window_with_playlists(qtbot, tmp_path)
    window.show()
    QApplication.processEvents()
    controls = (window._indicator, window._slider, window._volume_slider, window._denominator_combo)

    def geometries():
        return [(w.mapTo(window, w.rect().topLeft()), w.size()) for w in controls]

    before = geometries()
    window._playlist_button.click()
    QApplication.processEvents()
    assert geometries() == before

    window._playlist_button.click()
    QApplication.processEvents()
    assert geometries() == before


def test_window_has_no_playlist_menu(qtbot, tmp_path):
    window = make_window_with_playlists(qtbot, tmp_path)

    assert [action.text() for action in window.findChild(QMenuBar).actions()] == ["ヘルプ"]


def test_playlist_panel_uses_larger_font_than_default(qtbot, tmp_path):
    window = make_window_with_playlists(qtbot, tmp_path)

    assert window._playlist_panel.font().pointSizeF() == main_window.PLAYLIST_FONT_POINT_SIZE
    assert main_window.PLAYLIST_FONT_POINT_SIZE > QApplication.font().pointSizeF()


def test_saved_window_geometry_is_restored_when_on_screen(qtbot):
    store = FakeWindowStore(WindowGeometry(60, 70, 520, 460))
    service = MetronomeService(audio_output=FakeAudio(), settings_store=FakeStore())
    window = MainWindow(MetronomeController(service), window_store=store)
    qtbot.addWidget(window)

    assert window.geometry() == QRect(60, 70, 520, 460)


def test_saved_window_geometry_off_screen_falls_back_to_default(qtbot):
    default_window, _ = make_window(qtbot)
    store = FakeWindowStore(WindowGeometry(100000, 100000, 520, 460))
    service = MetronomeService(audio_output=FakeAudio(), settings_store=FakeStore())
    window = MainWindow(MetronomeController(service), window_store=store)
    qtbot.addWidget(window)

    assert window.pos() == default_window.pos()
    assert window.size() == default_window.size()


def test_saved_window_size_smaller_than_layout_minimum_is_clamped(qtbot):
    store = FakeWindowStore(WindowGeometry(60, 70, 50, 50))
    service = MetronomeService(audio_output=FakeAudio(), settings_store=FakeStore())
    window = MainWindow(MetronomeController(service), window_store=store)
    qtbot.addWidget(window)

    window.show()

    assert window.width() >= window.minimumSizeHint().width()
    assert window.height() >= window.minimumSizeHint().height()


def test_saved_window_size_larger_than_screen_falls_back_to_default(qtbot):
    default_window, _ = make_window(qtbot)
    store = FakeWindowStore(WindowGeometry(60, 70, 100000, 100000))
    service = MetronomeService(audio_output=FakeAudio(), settings_store=FakeStore())
    window = MainWindow(MetronomeController(service), window_store=store)
    qtbot.addWidget(window)

    assert window.geometry() == default_window.geometry()


def test_subdivision_is_enabled_for_any_denominator(qtbot):
    window, _ = make_window(qtbot)

    window._denominator_combo.setCurrentIndex(window._denominator_combo.findData(8))

    assert window._subdivision_combo.isEnabled()
    assert window._mask_container.isEnabled()


def test_bpm_widgets_follow_the_running_tempo(qtbot, monkeypatch):
    window, _ = make_window(qtbot)
    window._controller.set_bpm(120)
    window._controller.toggle()
    event = BeatEvent(beat_index=0, is_downbeat=True, is_subdivision=False, bpm=140)
    monkeypatch.setattr(window._controller, "drain_beats", lambda: [event])

    window._on_tick()

    assert window._spin.value() == 140
    assert window._slider.value() == 140
    assert window._controller.bpm == 120


def test_stopping_restores_the_base_tempo_on_the_bpm_widgets(qtbot, monkeypatch):
    window, _ = make_window(qtbot)
    window._controller.set_bpm(120)
    window._controller.toggle()
    event = BeatEvent(beat_index=0, is_downbeat=True, is_subdivision=False, bpm=140)
    monkeypatch.setattr(window._controller, "drain_beats", lambda: [event])
    window._on_tick()

    window._on_toggle()

    assert window._spin.value() == 120
    assert window._slider.value() == 120


def test_practice_button_reuses_one_dialog(qtbot):
    window, _ = make_window(qtbot)
    window.show()

    window._practice_button.click()
    first = window._practice_dialog
    window._practice_button.click()

    assert first is window._practice_dialog
    assert first.isVisible()


def test_playlist_lists_use_the_playlist_font_size(qtbot, tmp_path):
    window = make_window_with_playlists(qtbot, tmp_path)

    lists = window._playlist_panel.findChildren(QListWidget)

    assert lists
    for playlist_list in lists:
        assert playlist_list.font().pointSizeF() == PLAYLIST_FONT_POINT_SIZE

