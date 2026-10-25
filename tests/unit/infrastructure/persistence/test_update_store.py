import pytest

from ore_metronome.domain.update import UpdatePreferences
from ore_metronome.infrastructure.persistence.update_store import JsonUpdateStore


def test_missing_file_returns_defaults(tmp_path):
    assert JsonUpdateStore(tmp_path / "update.json").load() == UpdatePreferences()


def test_save_then_load_round_trips_and_leaves_no_temporary_files(tmp_path):
    path = tmp_path / "nested" / "update.json"
    preferences = UpdatePreferences(check_on_startup=False, skipped_version="0.2.0")

    JsonUpdateStore(path).save(preferences)

    assert JsonUpdateStore(path).load() == preferences
    assert list(path.parent.glob("*.tmp")) == []


@pytest.mark.parametrize(
    "content",
    [
        "not json",
        "[]",
        '{"schema_version": 2}',
        '{"schema_version": 1, "check_on_startup": "yes"}',
    ],
)
def test_broken_data_falls_back_to_defaults(tmp_path, content):
    path = tmp_path / "update.json"
    path.write_text(content, encoding="utf-8")

    assert JsonUpdateStore(path).load() == UpdatePreferences()
