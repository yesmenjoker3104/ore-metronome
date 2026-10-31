import json
from pathlib import Path

import pytest

from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import MetronomeSettings
from ore_metronome.domain.setlist import Playlist, PlaylistItem, PlaylistLibrary
from ore_metronome.infrastructure.persistence.setlist_repository import (
    CURRENT_SCHEMA_VERSION,
    LEGACY_PLAYLIST_NAME,
    SetlistDataError,
    SetlistRepository,
)
from ore_metronome.infrastructure.persistence.settings_repository import SettingsRepository


def test_save_and_load_round_trip(tmp_path: Path):
    repository = SetlistRepository(tmp_path / "setlists.json")
    library = PlaylistLibrary(
        (
            Playlist(
                "練習",
                (
                    PlaylistItem(
                        "曲A",
                        MetronomeSettings(bpm=140, meter=Meter(3, 4), subdivision=2),
                    ),
                ),
            ),
            Playlist("空"),
        )
    )

    repository.save(library)

    assert repository.load() == library


def test_saved_json_has_schema_version(tmp_path: Path):
    path = tmp_path / "setlists.json"
    SetlistRepository(path).save(PlaylistLibrary())

    assert json.loads(path.read_text(encoding="utf-8"))["schema_version"] == CURRENT_SCHEMA_VERSION


def test_load_rejects_invalid_playlist(tmp_path: Path):
    path = tmp_path / "setlists.json"
    path.write_text(json.dumps({"schema_version": 999, "playlists": []}), encoding="utf-8")

    with pytest.raises(SetlistDataError, match="Invalid playlist"):
        SetlistRepository(path).load()


def test_load_migrates_schema_1_items_into_default_playlist(tmp_path: Path):
    path = tmp_path / "setlists.json"
    settings = MetronomeSettings(bpm=100, meter=Meter(4, 4), subdivision=1)
    legacy = {
        "schema_version": 1,
        "items": [{"name": "旧曲", "settings": SettingsRepository.encode_settings(settings)}],
    }
    path.write_text(json.dumps(legacy), encoding="utf-8")

    library = SetlistRepository(path).load()

    assert library.playlists == (Playlist(LEGACY_PLAYLIST_NAME, (PlaylistItem("旧曲", settings),)),)


def test_load_migrates_empty_schema_1_to_empty_library(tmp_path: Path):
    path = tmp_path / "setlists.json"
    path.write_text(json.dumps({"schema_version": 1, "items": []}), encoding="utf-8")

    assert SetlistRepository(path).load() == PlaylistLibrary()


def test_load_rejects_schema_1_with_malformed_item(tmp_path: Path):
    path = tmp_path / "setlists.json"
    path.write_text(json.dumps({"schema_version": 1, "items": [{"name": "x"}]}), encoding="utf-8")

    with pytest.raises(SetlistDataError, match="Invalid playlist"):
        SetlistRepository(path).load()
