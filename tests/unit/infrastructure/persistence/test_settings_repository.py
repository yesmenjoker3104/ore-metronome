import json
from pathlib import Path

import pytest

from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import BeatLevel, MetronomeSettings
from ore_metronome.infrastructure.persistence.settings_repository import (
    CURRENT_SCHEMA_VERSION,
    SettingsDataError,
    SettingsRepository,
)


def make_settings() -> MetronomeSettings:
    return MetronomeSettings(
        bpm=140,
        meter=Meter(7, 8),
        subdivision=5,
        subdivision_masks={
            5: (
                BeatLevel.ACCENT,
                BeatLevel.SILENT,
                BeatLevel.ACCENT,
                BeatLevel.NORMAL,
                BeatLevel.SILENT,
            ),
        },
        accent_enabled=False,
        volume=65,
        beat_levels={0: BeatLevel.SILENT, 2: BeatLevel.ACCENT},
    )


def test_load_returns_none_when_settings_file_does_not_exist(
    tmp_path: Path,
):
    repository = SettingsRepository(tmp_path / "settings.json")

    assert repository.load() is None


def test_save_and_load_round_trip(tmp_path: Path):
    path = tmp_path / "settings.json"
    repository = SettingsRepository(path)
    settings = make_settings()

    repository.save(settings)

    assert path.exists()
    assert repository.load() == settings


def test_saved_json_contains_schema_version(tmp_path: Path):
    path = tmp_path / "settings.json"
    repository = SettingsRepository(path)

    repository.save(make_settings())

    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["schema_version"] == CURRENT_SCHEMA_VERSION


def test_load_rejects_unsupported_schema_version(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 999,
                "bpm": 120,
                "meter": {
                    "numerator": 4,
                    "denominator": 4,
                },
                "subdivision": 1,
                "subdivision_masks": {},
                "accent_enabled": True,
                "volume": 100,
            }
        ),
        encoding="utf-8",
    )

    repository = SettingsRepository(path)

    with pytest.raises(SettingsDataError, match="Unsupported schema version"):
        repository.load()


def test_load_rejects_broken_json(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text("{broken", encoding="utf-8")

    repository = SettingsRepository(path)

    with pytest.raises(SettingsDataError, match="Could not read settings"):
        repository.load()


def test_load_rejects_invalid_settings(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "bpm": 999,
                "meter": {
                    "numerator": 4,
                    "denominator": 4,
                },
                "subdivision": 1,
                "subdivision_masks": {},
                "accent_enabled": True,
                "volume": 100,
            }
        ),
        encoding="utf-8",
    )

    repository = SettingsRepository(path)

    with pytest.raises(SettingsDataError, match="Invalid settings"):
        repository.load()


def test_save_creates_parent_directory(tmp_path: Path):
    path = tmp_path / "nested" / "settings.json"
    repository = SettingsRepository(path)

    repository.save(make_settings())

    assert path.exists()


def test_beat_levels_are_saved_as_names(tmp_path: Path):
    path = tmp_path / "settings.json"
    repository = SettingsRepository(path)

    repository.save(make_settings())

    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["beat_levels"] == {"0": "silent", "2": "accent"}


def test_position_levels_are_saved_as_names(tmp_path: Path):
    path = tmp_path / "settings.json"
    repository = SettingsRepository(path)

    repository.save(make_settings())

    data = json.loads(path.read_text(encoding="utf-8"))

    assert data["subdivision_masks"] == {
        "5": ["accent", "silent", "accent", "normal", "silent"],
    }


def test_load_converts_boolean_masks_saved_by_earlier_versions(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "bpm": 120,
                "meter": {
                    "numerator": 4,
                    "denominator": 4,
                },
                "subdivision": 3,
                "subdivision_masks": {"3": [False, True, False]},
                "accent_enabled": True,
                "volume": 100,
            }
        ),
        encoding="utf-8",
    )

    settings = SettingsRepository(path).load()

    assert settings is not None
    assert settings.mask_for(3) == (BeatLevel.ACCENT, BeatLevel.NORMAL, BeatLevel.SILENT)


def test_load_converts_null_positions_saved_by_earlier_versions(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "bpm": 120,
                "meter": {
                    "numerator": 4,
                    "denominator": 4,
                },
                "subdivision": 3,
                "subdivision_masks": {"3": [None, None, "silent"]},
                "accent_enabled": True,
                "volume": 100,
            }
        ),
        encoding="utf-8",
    )

    settings = SettingsRepository(path).load()

    assert settings is not None
    assert settings.mask_for(3) == (BeatLevel.ACCENT, BeatLevel.NORMAL, BeatLevel.SILENT)


def test_load_reads_settings_saved_before_beat_levels_existed(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "bpm": 120,
                "meter": {
                    "numerator": 4,
                    "denominator": 4,
                },
                "subdivision": 1,
                "subdivision_masks": {},
                "accent_enabled": True,
                "volume": 100,
            }
        ),
        encoding="utf-8",
    )

    settings = SettingsRepository(path).load()

    assert settings is not None
    assert dict(settings.beat_levels) == {}


def test_load_rejects_unknown_beat_level(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": CURRENT_SCHEMA_VERSION,
                "bpm": 120,
                "meter": {
                    "numerator": 4,
                    "denominator": 4,
                },
                "subdivision": 1,
                "subdivision_masks": {},
                "accent_enabled": True,
                "volume": 100,
                "beat_levels": {"0": "loud"},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(SettingsDataError, match="Invalid settings"):
        SettingsRepository(path).load()
