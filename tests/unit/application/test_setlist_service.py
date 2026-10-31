import pytest

from ore_metronome.application.metronome_service import MetronomeService
from ore_metronome.application.setlist_service import SetlistService
from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import MetronomeSettings
from ore_metronome.infrastructure.persistence.setlist_repository import SetlistRepository


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
        return MetronomeSettings(bpm=120, meter=Meter(4, 4), subdivision=1)

    def save(self, settings) -> None:
        pass


def make_service(tmp_path):
    metronome = MetronomeService(FakeAudio(), FakeSettingsStore())
    service = SetlistService(metronome, SetlistRepository(tmp_path / "setlists.json"))
    return service, metronome


def test_add_song_uses_current_settings_and_persists(tmp_path):
    path = tmp_path / "setlists.json"
    metronome = MetronomeService(FakeAudio(), FakeSettingsStore())
    service = SetlistService(metronome, SetlistRepository(path))
    service.add_playlist("練習")
    metronome.set_bpm(150)

    index = service.add_song(0, "曲A")

    assert index == 0
    assert service.library.playlists[0].items[0].settings.bpm == 150
    assert SetlistRepository(path).load() == service.library


def test_applying_songs_stays_within_current_playlist(tmp_path):
    service, metronome = make_service(tmp_path)
    service.add_playlist("A")
    service.add_playlist("B")
    metronome.set_bpm(100)
    service.add_song(0, "slow")
    metronome.set_bpm(180)
    service.add_song(0, "fast")
    metronome.set_bpm(200)
    service.add_song(1, "other")

    service.apply(0, 0)
    assert metronome.settings.bpm == 100
    assert service.next() is not None
    assert metronome.settings.bpm == 180
    assert service.next() is None
    assert metronome.settings.bpm == 180


def test_previous_moves_back_within_playlist(tmp_path):
    service, metronome = make_service(tmp_path)
    service.add_playlist("A")
    metronome.set_bpm(100)
    service.add_song(0, "slow")
    metronome.set_bpm(180)
    service.add_song(0, "fast")
    service.apply(0, 1)

    assert service.previous() is not None
    assert metronome.settings.bpm == 100
    assert service.previous() is None


def test_update_song_replaces_settings_and_marks_it_current(tmp_path):
    service, metronome = make_service(tmp_path)
    service.add_playlist("A")
    service.add_song(0, "A")
    metronome.set_bpm(160)

    service.update_song(0, 0, "A2")

    song = service.library.playlists[0].items[0]
    assert song.name == "A2"
    assert song.settings.bpm == 160
    assert service.current == (0, 0)


def test_add_playlist_rejects_duplicate_name(tmp_path):
    service, _ = make_service(tmp_path)
    service.add_playlist("A")

    with pytest.raises(ValueError, match="already exists"):
        service.add_playlist("A")
    assert len(service.library.playlists) == 1


def test_rename_playlist_persists(tmp_path):
    path = tmp_path / "setlists.json"
    service = SetlistService(
        MetronomeService(FakeAudio(), FakeSettingsStore()), SetlistRepository(path)
    )
    service.add_playlist("A")

    service.rename_playlist(0, "B")

    assert SetlistRepository(path).load().playlists[0].name == "B"


@pytest.mark.parametrize(
    ("current", "index", "new_index"),
    [(1, 0, 2), (1, 2, 0), (1, 1, 3), (2, 0, 3), (0, 3, 0), (3, 1, 0)],
)
def test_move_song_keeps_current_song_on_same_track(tmp_path, current, index, new_index):
    service, _ = make_service(tmp_path)
    service.add_playlist("P")
    names = ["A", "B", "C", "D"]
    for name in names:
        service.add_song(0, name)
    service.apply(0, current)

    service.move_song(0, index, new_index)

    playlist_index, song_index = service.current
    assert playlist_index == 0
    assert service.library.playlists[0].items[song_index].name == names[current]


def test_move_playlist_keeps_current_song_on_same_track(tmp_path):
    service, _ = make_service(tmp_path)
    for name in ("A", "B", "C"):
        service.add_playlist(name)
    service.add_song(1, "song")
    service.apply(1, 0)

    service.move_playlist(1, 0)

    assert service.current == (0, 0)
    assert service.library.playlists[0].name == "B"


def test_removing_current_playlist_clears_current(tmp_path):
    service, _ = make_service(tmp_path)
    service.add_playlist("A")
    service.add_song(0, "song")
    service.apply(0, 0)

    service.remove_playlist(0)

    assert service.current is None


def test_removing_earlier_playlist_shifts_current(tmp_path):
    service, _ = make_service(tmp_path)
    service.add_playlist("A")
    service.add_playlist("B")
    service.add_song(1, "song")
    service.apply(1, 0)

    service.remove_playlist(0)

    assert service.current == (0, 0)
    assert service.library.playlists[0].name == "B"


def test_removing_current_song_clears_current(tmp_path):
    service, _ = make_service(tmp_path)
    service.add_playlist("P")
    service.add_song(0, "A")
    service.add_song(0, "B")
    service.apply(0, 0)

    service.remove_song(0, 0)

    assert service.current is None


def test_removing_earlier_song_shifts_current(tmp_path):
    service, _ = make_service(tmp_path)
    service.add_playlist("P")
    for name in ("A", "B", "C"):
        service.add_song(0, name)
    service.apply(0, 2)

    service.remove_song(0, 0)

    assert service.current == (0, 1)
    assert service.library.playlists[0].items[1].name == "C"


def test_apply_keeps_current_volume(tmp_path):
    service, metronome = make_service(tmp_path)
    service.add_playlist("P")
    metronome.set_volume(30)
    service.add_song(0, "Quiet")
    metronome.set_volume(80)

    service.apply(0, 0)

    assert metronome.settings.volume == 80
