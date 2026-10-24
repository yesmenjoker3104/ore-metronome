from pathlib import Path

import pytest

from ore_metronome.infrastructure.persistence import paths


def test_app_data_dir_uses_appdata(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    assert paths.app_data_dir() == tmp_path / "ore-metronome"


def test_app_data_dir_falls_back_to_home_when_appdata_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("APPDATA", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    assert paths.app_data_dir() == tmp_path / "AppData" / "Roaming" / "ore-metronome"


def test_app_data_dir_falls_back_to_home_when_appdata_empty(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", "")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    assert paths.app_data_dir() == tmp_path / "AppData" / "Roaming" / "ore-metronome"


@pytest.mark.parametrize(
    ("func", "filename"),
    [
        (paths.settings_path, "settings.json"),
        (paths.presets_path, "presets.json"),
        (paths.setlists_path, "setlists.json"),
    ],
)
def test_file_paths_are_inside_app_dir(monkeypatch, tmp_path, func, filename):
    monkeypatch.setenv("APPDATA", str(tmp_path))

    assert func() == tmp_path / "ore-metronome" / filename