import pytest

from ore_metronome.domain.playlist_font import PlaylistFontSize
from ore_metronome.infrastructure.persistence.playlist_font_store import JsonPlaylistFontStore


def test_missing_file_returns_small(tmp_path):
    assert JsonPlaylistFontStore(tmp_path / "playlist_font.json").load() == PlaylistFontSize.SMALL


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "nested" / "playlist_font.json"

    JsonPlaylistFontStore(path).save(PlaylistFontSize.LARGE)

    assert JsonPlaylistFontStore(path).load() == PlaylistFontSize.LARGE


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        '{"schema_version": 2, "size": "large"}',
        '{"schema_version": 1, "size": "huge"}',
        '{"schema_version": 1}',
    ],
)
def test_broken_data_returns_small(tmp_path, content):
    path = tmp_path / "playlist_font.json"
    path.write_text(content, encoding="utf-8")

    assert JsonPlaylistFontStore(path).load() == PlaylistFontSize.SMALL
