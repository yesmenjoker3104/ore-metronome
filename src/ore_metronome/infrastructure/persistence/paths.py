import os
from pathlib import Path

APP_DIR_NAME = "ore-metronome"


def app_data_dir() -> Path:
    appdata = os.getenv("APPDATA")
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base / APP_DIR_NAME


def settings_path() -> Path:
    return app_data_dir() / "settings.json"


def presets_path() -> Path:
    return app_data_dir() / "presets.json"


def setlists_path() -> Path:
    return app_data_dir() / "setlists.json"