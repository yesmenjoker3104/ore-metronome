import pytest

from ore_metronome.domain.window import WindowPosition
from ore_metronome.infrastructure.persistence.window_store import JsonWindowStore


def test_missing_file_returns_none(tmp_path):
    assert JsonWindowStore(tmp_path / "window.json").load() is None


def test_save_then_load_round_trips_and_leaves_no_temporary_files(tmp_path):
    path = tmp_path / "nested" / "window.json"
    position = WindowPosition(x=-1200, y=340)

    JsonWindowStore(path).save(position)

    assert JsonWindowStore(path).load() == position
    assert list(path.parent.glob("*.tmp")) == []


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[]",
        '{"schema_version": 2, "x": 1, "y": 2}',
        '{"schema_version": 1, "x": "1", "y": 2}',
        '{"schema_version": 1, "x": 1}',
        '{"schema_version": 1, "x": true, "y": 2}',
    ],
)
def test_broken_data_returns_none(tmp_path, content):
    path = tmp_path / "window.json"
    path.write_text(content, encoding="utf-8")

    assert JsonWindowStore(path).load() is None
