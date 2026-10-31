from dataclasses import replace

from ore_metronome.application.metronome_service import MetronomeService
from ore_metronome.domain.models import MetronomeSettings
from ore_metronome.domain.setlist import Playlist, PlaylistItem, PlaylistLibrary
from ore_metronome.infrastructure.persistence.setlist_repository import SetlistRepository


def _moved_index(current: int, index: int, new_index: int) -> int:
    if current == index:
        return new_index
    if index < current <= new_index:
        return current - 1
    if new_index <= current < index:
        return current + 1
    return current


class SetlistService:
    def __init__(
        self,
        metronome_service: MetronomeService,
        repository: SetlistRepository,
        library: PlaylistLibrary | None = None,
    ) -> None:
        self._metronome_service = metronome_service
        self._repository = repository
        self._library = repository.load() if library is None else library
        # (プレイリストの位置, 曲の位置) の組。最後に適用した曲を表す。
        self._current: tuple[int, int] | None = None

    @property
    def library(self) -> PlaylistLibrary:
        return self._library

    @property
    def current(self) -> tuple[int, int] | None:
        return self._current

    def add_playlist(self, name: str) -> int:
        self._library = self._library.add(Playlist(name))
        self.save()
        return len(self._library.playlists) - 1

    def rename_playlist(self, index: int, name: str) -> None:
        playlist = self._library.playlists[index].renamed(name)
        self._library = self._library.replace(index, playlist)
        self.save()

    def remove_playlist(self, index: int) -> None:
        self._library = self._library.remove(index)
        if self._current is not None:
            playlist_index, song_index = self._current
            if playlist_index == index:
                self._current = None
            elif playlist_index > index:
                self._current = (playlist_index - 1, song_index)
        self.save()

    def move_playlist(self, index: int, new_index: int) -> None:
        self._library = self._library.move(index, new_index)
        if self._current is not None:
            playlist_index, song_index = self._current
            self._current = (_moved_index(playlist_index, index, new_index), song_index)
        self.save()

    def add_song(self, playlist_index: int, name: str) -> int:
        playlist = self._library.playlists[playlist_index]
        song = PlaylistItem(name=name, settings=self._metronome_service.settings)
        self._library = self._library.replace(playlist_index, playlist.add(song))
        self.save()
        return len(playlist.items)

    def update_song(self, playlist_index: int, song_index: int, name: str) -> None:
        playlist = self._library.playlists[playlist_index]
        song = PlaylistItem(name=name, settings=self._metronome_service.settings)
        self._library = self._library.replace(
            playlist_index, playlist.replace(song_index, song)
        )
        self._current = (playlist_index, song_index)
        self.save()

    def remove_song(self, playlist_index: int, song_index: int) -> None:
        playlist = self._library.playlists[playlist_index]
        self._library = self._library.replace(playlist_index, playlist.remove(song_index))
        if self._current is not None and self._current[0] == playlist_index:
            current_song = self._current[1]
            if current_song == song_index:
                self._current = None
            elif current_song > song_index:
                self._current = (playlist_index, current_song - 1)
        self.save()

    def move_song(self, playlist_index: int, index: int, new_index: int) -> None:
        playlist = self._library.playlists[playlist_index]
        self._library = self._library.replace(
            playlist_index, playlist.move(index, new_index)
        )
        if self._current is not None and self._current[0] == playlist_index:
            self._current = (playlist_index, _moved_index(self._current[1], index, new_index))
        self.save()

    def apply(self, playlist_index: int, song_index: int) -> MetronomeSettings:
        item = self._library.playlists[playlist_index].items[song_index]
        # 音量はプリセットに含めず、適用時も現在の音量を維持する。
        settings = replace(item.settings, volume=self._metronome_service.settings.volume)
        self._current = (playlist_index, song_index)
        self._metronome_service.update_settings(settings)
        return settings

    def previous(self) -> MetronomeSettings | None:
        if self._current is None or self._current[1] <= 0:
            return None
        playlist_index, song_index = self._current
        return self.apply(playlist_index, song_index - 1)

    def next(self) -> MetronomeSettings | None:
        if self._current is None:
            return None
        playlist_index, song_index = self._current
        if song_index >= len(self._library.playlists[playlist_index].items) - 1:
            return None
        return self.apply(playlist_index, song_index + 1)

    def save(self) -> None:
        self._repository.save(self._library)
