import json
from pathlib import Path

import pytest

from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import MetronomeSettings
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
            5: (True, False, True, False, True),
        },
        accent_enabled=False,
        volume=65,
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