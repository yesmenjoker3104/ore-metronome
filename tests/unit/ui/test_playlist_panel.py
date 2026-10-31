from PySide6.QtCore import QMimeData, QPointF, Qt
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import QLabel, QPushButton

from ore_metronome.application.metronome_service import MetronomeService
from ore_metronome.application.setlist_service import SetlistService
from ore_metronome.infrastructure.persistence.setlist_repository import SetlistRepository
from ore_metronome.ui import playlist_panel
from ore_metronome.ui.playlist_panel import CURRENT_MARK, PlaylistPanel


class FakeAudio:
    is_running = False

    def start(self, settings) -> None:
        pass

    def stop(self) -> None:
        pass

    def now(self) -> None:
        return None

    def configure(self, settings) -> None:
        pass


class FakeSettingsStore:
    def load(self):
        return None

    def save(self, settings) -> None:
        pass


def make_panel(qtbot, tmp_path):
    metronome = MetronomeService(FakeAudio(), FakeSettingsStore())
    service = SetlistService(metronome, SetlistRepository(tmp_path / "setlists.json"))
    panel = PlaylistPanel(service)
    qtbot.addWidget(panel)
    return panel, service, metronome


def row_label(lst, row: int) -> str:
    return lst.itemWidget(lst.item(row)).findChild(QLabel).text()


def song_labels(panel: PlaylistPanel) -> list[str]:
    return [row_label(panel._song_list, row) for row in range(panel._song_list.count())]


def click_move(lst, row: int, tooltip: str) -> None:
    widget = lst.itemWidget(lst.item(row))
    next(
        button for button in widget.findChildren(QPushButton) if button.toolTip() == tooltip
    ).click()


def drop_on_row(lst, source: int, target: int) -> None:
    lst.setCurrentRow(source)
    point = lst.visualItemRect(lst.item(target)).center()
    event = QDropEvent(
        QPointF(point),
        Qt.DropAction.MoveAction,
        QMimeData(),
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    lst.dropEvent(event)


def test_adding_duplicate_playlist_shows_warning_instead_of_raising(qtbot, monkeypatch, tmp_path):
    panel, service, _ = make_panel(qtbot, tmp_path)
    service.add_playlist("A")
    warnings: list[tuple] = []

    class FakeInputDialog:
        @staticmethod
        def getText(*args, **kwargs):
            return ("A", True)

    class FakeMessageBox:
        @staticmethod
        def warning(*args, **kwargs):
            warnings.append(args)

    monkeypatch.setattr(playlist_panel, "QInputDialog", FakeInputDialog)
    monkeypatch.setattr(playlist_panel, "QMessageBox", FakeMessageBox)

    panel._add_playlist()

    assert len(warnings) == 1
    assert len(service.library.playlists) == 1


def test_selecting_playlist_lists_its_songs(qtbot, tmp_path):
    panel, service, _ = make_panel(qtbot, tmp_path)
    service.add_playlist("A")
    service.add_song(0, "a1")
    service.add_playlist("B")
    service.add_song(1, "b1")
    service.add_song(1, "b2")
    panel.refresh()

    panel._playlist_list.setCurrentRow(1)

    assert song_labels(panel) == ["b1", "b2"]


def test_current_song_is_marked(qtbot, tmp_path):
    panel, service, _ = make_panel(qtbot, tmp_path)
    service.add_playlist("P")
    service.add_song(0, "A")
    service.add_song(0, "B")
    service.apply(0, 1)

    panel.refresh()

    assert song_labels(panel) == ["A", f"{CURRENT_MARK}B"]


def test_current_song_row_is_highlighted(qtbot, tmp_path):
    panel, service, _ = make_panel(qtbot, tmp_path)
    service.add_playlist("P")
    service.add_song(0, "A")
    service.add_song(0, "B")
    service.apply(0, 1)

    panel.refresh()

    current_label = panel._song_list.itemWidget(panel._song_list.item(1)).findChild(QLabel)
    other_label = panel._song_list.itemWidget(panel._song_list.item(0)).findChild(QLabel)
    assert current_label.objectName() == "currentSong"
    assert other_label.objectName() == ""


def test_song_buttons_follow_selection(qtbot, tmp_path):
    panel, service, _ = make_panel(qtbot, tmp_path)
    assert not any(button.isEnabled() for button in panel._song_add)

    service.add_playlist("P")
    panel.refresh()
    assert all(button.isEnabled() for button in panel._song_add)
    assert not any(button.isEnabled() for button in panel._song_required)

    service.add_song(0, "A")
    panel.refresh()
    assert all(button.isEnabled() for button in panel._song_required)


def test_double_clicking_song_applies_it_and_emits_signal(qtbot, tmp_path):
    panel, service, metronome = make_panel(qtbot, tmp_path)
    service.add_playlist("P")
    metronome.set_bpm(150)
    service.add_song(0, "fast")
    metronome.set_bpm(120)
    panel.refresh()

    with qtbot.waitSignal(panel.settings_applied):
        panel._song_list.itemDoubleClicked.emit(panel._song_list.item(0))

    assert metronome.settings.bpm == 150


def button_named(panel: PlaylistPanel, text: str) -> QPushButton:
    return next(button for button in panel.findChildren(QPushButton) if button.text() == text)


def test_panel_has_no_apply_or_song_step_buttons(qtbot, tmp_path):
    panel, _, _ = make_panel(qtbot, tmp_path)

    labels = {button.text() for button in panel.findChildren(QPushButton)}

    assert {"適用", "前の曲", "次の曲"}.isdisjoint(labels)


def test_panel_action_buttons_use_accent_style(qtbot, tmp_path):
    panel, _, _ = make_panel(qtbot, tmp_path)

    for text in ("追加", "名前変更", "更新", "削除"):
        for button in panel.findChildren(QPushButton):
            if button.text() == text:
                assert button.property("variant") == "primary", text


def test_moving_songs_with_buttons_reorders_playlist_and_keeps_current_song(qtbot, tmp_path):
    panel, service, _ = make_panel(qtbot, tmp_path)
    service.add_playlist("P")
    for name in ("A", "B", "C"):
        service.add_song(0, name)
    service.apply(0, 0)
    panel.refresh()

    click_move(panel._song_list, 0, "下へ")
    click_move(panel._song_list, 1, "下へ")

    assert [song.name for song in service.library.playlists[0].items] == ["B", "C", "A"]
    assert service.current == (0, 2)
    assert song_labels(panel) == ["B", "C", f"{CURRENT_MARK}A"]
    assert panel._song_list.currentRow() == 2


def test_moving_playlists_with_buttons_reorders_them(qtbot, tmp_path):
    panel, service, _ = make_panel(qtbot, tmp_path)
    for name in ("A", "B", "C"):
        service.add_playlist(name)
    panel.refresh()

    click_move(panel._playlist_list, 0, "下へ")
    click_move(panel._playlist_list, 1, "下へ")

    assert [playlist.name for playlist in service.library.playlists] == ["B", "C", "A"]
    assert panel._playlist_list.currentRow() == 2


def test_move_buttons_at_the_ends_do_nothing(qtbot, tmp_path):
    panel, service, _ = make_panel(qtbot, tmp_path)
    for name in ("A", "B"):
        service.add_playlist(name)
    panel.refresh()

    click_move(panel._playlist_list, 0, "上へ")
    click_move(panel._playlist_list, 1, "下へ")

    assert [playlist.name for playlist in service.library.playlists] == ["A", "B"]


def test_dragging_songs_reorders_playlist_and_keeps_current_song(qtbot, tmp_path):
    panel, service, _ = make_panel(qtbot, tmp_path)
    panel.resize(300, 600)
    panel.show()
    service.add_playlist("P")
    for name in ("A", "B", "C"):
        service.add_song(0, name)
    service.apply(0, 0)
    panel.refresh()

    drop_on_row(panel._song_list, 0, 2)

    assert [song.name for song in service.library.playlists[0].items] == ["B", "C", "A"]
    assert service.current == (0, 2)
    assert song_labels(panel) == ["B", "C", f"{CURRENT_MARK}A"]
    assert panel._song_list.currentRow() == 2


def test_dragging_playlists_reorders_them(qtbot, tmp_path):
    panel, service, _ = make_panel(qtbot, tmp_path)
    panel.resize(300, 600)
    panel.show()
    for name in ("A", "B", "C"):
        service.add_playlist(name)
    panel.refresh()

    drop_on_row(panel._playlist_list, 2, 0)

    assert [playlist.name for playlist in service.library.playlists] == ["C", "A", "B"]
    assert panel._playlist_list.currentRow() == 0


def test_dropping_on_the_same_row_changes_nothing(qtbot, tmp_path):
    panel, service, _ = make_panel(qtbot, tmp_path)
    panel.resize(300, 600)
    panel.show()
    for name in ("A", "B"):
        service.add_playlist(name)
    panel.refresh()

    drop_on_row(panel._playlist_list, 1, 1)

    assert [playlist.name for playlist in service.library.playlists] == ["A", "B"]
