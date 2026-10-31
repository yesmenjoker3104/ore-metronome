from dataclasses import dataclass

from ore_metronome.domain.models import MetronomeSettings


@dataclass(frozen=True)
class PlaylistItem:
    name: str
    settings: MetronomeSettings

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Playlist item name must not be empty")


@dataclass(frozen=True)
class Playlist:
    name: str
    items: tuple[PlaylistItem, ...] = ()

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Playlist name must not be empty")
        if len({item.name for item in self.items}) != len(self.items):
            raise ValueError("Playlist item names must be unique")

    def renamed(self, name: str) -> "Playlist":
        return Playlist(name, self.items)

    def add(self, item: PlaylistItem) -> "Playlist":
        if any(existing.name == item.name for existing in self.items):
            raise ValueError(f"Playlist item already exists: {item.name}")
        return Playlist(self.name, self.items + (item,))

    def replace(self, index: int, item: PlaylistItem) -> "Playlist":
        self._check_index(index)
        if any(
            position != index and existing.name == item.name
            for position, existing in enumerate(self.items)
        ):
            raise ValueError(f"Playlist item already exists: {item.name}")
        items = list(self.items)
        items[index] = item
        return Playlist(self.name, tuple(items))

    def remove(self, index: int) -> "Playlist":
        self._check_index(index)
        return Playlist(self.name, self.items[:index] + self.items[index + 1 :])

    def move(self, index: int, new_index: int) -> "Playlist":
        self._check_index(index)
        if not 0 <= new_index < len(self.items):
            raise IndexError(new_index)
        items = list(self.items)
        item = items.pop(index)
        items.insert(new_index, item)
        return Playlist(self.name, tuple(items))

    def _check_index(self, index: int) -> None:
        if not 0 <= index < len(self.items):
            raise IndexError(index)


@dataclass(frozen=True)
class PlaylistLibrary:
    playlists: tuple[Playlist, ...] = ()

    def __post_init__(self) -> None:
        if len({playlist.name for playlist in self.playlists}) != len(self.playlists):
            raise ValueError("Playlist names must be unique")

    def add(self, playlist: Playlist) -> "PlaylistLibrary":
        if any(existing.name == playlist.name for existing in self.playlists):
            raise ValueError(f"Playlist already exists: {playlist.name}")
        return PlaylistLibrary(self.playlists + (playlist,))

    def replace(self, index: int, playlist: Playlist) -> "PlaylistLibrary":
        self._check_index(index)
        if any(
            position != index and existing.name == playlist.name
            for position, existing in enumerate(self.playlists)
        ):
            raise ValueError(f"Playlist already exists: {playlist.name}")
        playlists = list(self.playlists)
        playlists[index] = playlist
        return PlaylistLibrary(tuple(playlists))

    def remove(self, index: int) -> "PlaylistLibrary":
        self._check_index(index)
        return PlaylistLibrary(self.playlists[:index] + self.playlists[index + 1 :])

    def move(self, index: int, new_index: int) -> "PlaylistLibrary":
        self._check_index(index)
        if not 0 <= new_index < len(self.playlists):
            raise IndexError(new_index)
        playlists = list(self.playlists)
        playlist = playlists.pop(index)
        playlists.insert(new_index, playlist)
        return PlaylistLibrary(tuple(playlists))

    def _check_index(self, index: int) -> None:
        if not 0 <= index < len(self.playlists):
            raise IndexError(index)
