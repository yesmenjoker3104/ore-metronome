from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ore_metronome.application.setlist_service import SetlistService
from ore_metronome.ui.icons import set_button_icon
from ore_metronome.ui.theme import ACCENT_COLOR
from ore_metronome.ui.widgets.movable_list import MovableList

CURRENT_MARK = "▶ "


def _section_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("sectionTitle")
    return label


class PlaylistPanel(QWidget):
    settings_applied = Signal()

    def __init__(self, service: SetlistService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._playlist_list = MovableList()
        self._song_list = MovableList()
        self._playlist_list.currentRowChanged.connect(lambda _row: self._populate_songs())
        self._playlist_list.move_requested.connect(self._on_playlist_moved)
        self._song_list.currentRowChanged.connect(lambda _row: self._sync_buttons())
        self._song_list.itemDoubleClicked.connect(lambda _item: self._apply_selected_song())
        self._song_list.move_requested.connect(self._on_song_moved)

        self._playlist_required: list[QPushButton] = []
        self._song_add: list[QPushButton] = []
        self._song_required: list[QPushButton] = []

        playlist_add = self._button("追加", self._add_playlist, icon="plus")
        playlist_rename = self._button(
            "名前変更", self._rename_playlist, self._playlist_required, icon="rename"
        )
        playlist_remove = self._button(
            "削除", self._remove_playlist, self._playlist_required, icon="delete"
        )

        song_add = self._button("追加", self._add_song, self._song_add, icon="plus")
        song_update = self._button("更新", self._update_song, self._song_required, icon="update")
        song_remove = self._button("削除", self._remove_song, self._song_required, icon="delete")

        layout = QVBoxLayout(self)
        layout.addWidget(_section_title("プレイリスト"))
        layout.addWidget(self._playlist_list)
        layout.addLayout(_row(playlist_add, playlist_rename, playlist_remove))
        layout.addWidget(_section_title("曲"))
        layout.addWidget(self._song_list)
        layout.addLayout(_row(song_add, song_update, song_remove))
        self.refresh()

    def refresh(self) -> None:
        self._populate_playlists(self._playlist_list.currentRow())
        self._populate_songs()

    def _button(
        self,
        text: str,
        slot: Callable[[], None],
        group: list[QPushButton] | None = None,
        *,
        icon: str,
    ) -> QPushButton:
        button = QPushButton(text)
        button.clicked.connect(slot)
        set_button_icon(button, icon, ACCENT_COLOR)
        button.setProperty("variant", "primary")
        if group is not None:
            group.append(button)
        return button

    def _populate_playlists(self, select: int) -> None:
        self._playlist_list.clear()
        for playlist in self._service.library.playlists:
            self._playlist_list.add_row(playlist.name)
        count = self._playlist_list.count()
        self._playlist_list.setCurrentRow(_clamp(select, count))
        self._sync_buttons()

    def _populate_songs(self, select: int | None = None) -> None:
        playlist_index = self._selected_playlist_index()
        current = self._service.current
        if select is None:
            select = 0
            if current is not None and current[0] == playlist_index:
                select = current[1]
        self._song_list.clear()
        if playlist_index is not None:
            playlist = self._service.library.playlists[playlist_index]
            for song_index, song in enumerate(playlist.items):
                marked = current == (playlist_index, song_index)
                self._song_list.add_row(f"{CURRENT_MARK if marked else ''}{song.name}", marked)
        self._song_list.setCurrentRow(_clamp(select, self._song_list.count()))
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        has_playlist = self._selected_playlist_index() is not None
        has_song = self._selected_song_index() is not None
        for button in self._playlist_required:
            button.setEnabled(has_playlist)
        for button in self._song_add:
            button.setEnabled(has_playlist)
        for button in self._song_required:
            button.setEnabled(has_song)

    def _selected_playlist_index(self) -> int | None:
        row = self._playlist_list.currentRow()
        return row if row >= 0 else None

    def _selected_song_index(self) -> int | None:
        row = self._song_list.currentRow()
        return row if row >= 0 else None

    def _ask_name(self, title: str, initial: str = "") -> str | None:
        name, accepted = QInputDialog.getText(self, title, "名前:", text=initial)
        return name if accepted else None

    def _warn(self, error: ValueError) -> None:
        QMessageBox.warning(self, "プレイリスト", str(error))

    def _add_playlist(self) -> None:
        name = self._ask_name("プレイリストを追加")
        if name is None:
            return
        try:
            index = self._service.add_playlist(name)
        except ValueError as error:
            self._warn(error)
            return
        self._populate_playlists(index)

    def _rename_playlist(self) -> None:
        index = self._selected_playlist_index()
        if index is None:
            return
        name = self._ask_name("プレイリスト名を変更", self._service.library.playlists[index].name)
        if name is None:
            return
        try:
            self._service.rename_playlist(index, name)
        except ValueError as error:
            self._warn(error)
            return
        self._populate_playlists(index)

    def _remove_playlist(self) -> None:
        index = self._selected_playlist_index()
        if index is None:
            return
        if (
            QMessageBox.question(self, "プレイリスト", "選択したプレイリストを削除しますか？")
            != QMessageBox.StandardButton.Yes
        ):
            return
        self._service.remove_playlist(index)
        self._populate_playlists(index)

    def _on_playlist_moved(self, index: int, new_index: int) -> None:
        self._service.move_playlist(index, new_index)
        self._populate_playlists(new_index)

    def _on_song_moved(self, index: int, new_index: int) -> None:
        playlist_index = self._selected_playlist_index()
        if playlist_index is None:
            return
        self._service.move_song(playlist_index, index, new_index)
        self._populate_songs(new_index)

    def _add_song(self) -> None:
        playlist_index = self._selected_playlist_index()
        if playlist_index is None:
            return
        name = self._ask_name("曲を追加")
        if name is None:
            return
        try:
            song_index = self._service.add_song(playlist_index, name)
        except ValueError as error:
            self._warn(error)
            return
        self._populate_songs(song_index)

    def _update_song(self) -> None:
        playlist_index = self._selected_playlist_index()
        song_index = self._selected_song_index()
        if playlist_index is None or song_index is None:
            return
        song = self._service.library.playlists[playlist_index].items[song_index]
        name = self._ask_name("曲を更新", song.name)
        if name is None:
            return
        try:
            self._service.update_song(playlist_index, song_index, name)
        except ValueError as error:
            self._warn(error)
            return
        self._populate_songs(song_index)

    def _apply_selected_song(self) -> None:
        playlist_index = self._selected_playlist_index()
        song_index = self._selected_song_index()
        if playlist_index is None or song_index is None:
            return
        self._service.apply(playlist_index, song_index)
        self._populate_songs(song_index)
        self.settings_applied.emit()

    def _remove_song(self) -> None:
        playlist_index = self._selected_playlist_index()
        song_index = self._selected_song_index()
        if playlist_index is None or song_index is None:
            return
        if (
            QMessageBox.question(self, "プレイリスト", "選択した曲を削除しますか？")
            != QMessageBox.StandardButton.Yes
        ):
            return
        self._service.remove_song(playlist_index, song_index)
        self._populate_songs(song_index)


def _row(*buttons: QPushButton) -> QHBoxLayout:
    row = QHBoxLayout()
    for button in buttons:
        row.addWidget(button)
    return row


def _clamp(index: int, count: int) -> int:
    if count == 0:
        return -1
    return min(max(index, 0), count - 1)
