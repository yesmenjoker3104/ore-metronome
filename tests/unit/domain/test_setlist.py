import pytest

from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import MetronomeSettings
from ore_metronome.domain.setlist import Playlist, PlaylistItem, PlaylistLibrary


def item(name: str) -> PlaylistItem:
    return PlaylistItem(
        name,
        MetronomeSettings(bpm=120, meter=Meter(4, 4), subdivision=1),
    )


def test_playlist_rejects_duplicate_names():
    with pytest.raises(ValueError, match="unique"):
        Playlist("P", (item("A"), item("A")))


def test_playlist_rejects_empty_name():
    with pytest.raises(ValueError, match="must not be empty"):
        Playlist("  ")


def test_playlist_moves_and_removes_items():
    playlist = Playlist("P", (item("A"), item("B"), item("C")))

    moved = playlist.move(0, 2)

    assert [entry.name for entry in moved.items] == ["B", "C", "A"]
    assert [entry.name for entry in moved.remove(1).items] == ["B", "A"]


def test_playlist_rename_keeps_items():
    playlist = Playlist("P", (item("A"),))

    renamed = playlist.renamed("Q")

    assert renamed.name == "Q"
    assert renamed.items == playlist.items


def test_library_rejects_duplicate_playlist_names():
    with pytest.raises(ValueError, match="unique"):
        PlaylistLibrary((Playlist("P"), Playlist("P")))


def test_library_add_rejects_existing_name():
    library = PlaylistLibrary((Playlist("P"),))

    with pytest.raises(ValueError, match="already exists"):
        library.add(Playlist("P"))


def test_library_moves_and_removes_playlists():
    library = PlaylistLibrary((Playlist("A"), Playlist("B"), Playlist("C")))

    moved = library.move(0, 2)

    assert [entry.name for entry in moved.playlists] == ["B", "C", "A"]
    assert [entry.name for entry in moved.remove(1).playlists] == ["B", "A"]
