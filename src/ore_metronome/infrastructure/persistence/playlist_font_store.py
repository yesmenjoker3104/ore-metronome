import json
from pathlib import Path
from typing import Any

from ore_metronome.domain.playlist_font import PlaylistFontSize
from ore_metronome.infrastructure.persistence.json_file import write_json_atomically

CURRENT_SCHEMA_VERSION = 1


class JsonPlaylistFontStore:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> PlaylistFontSize:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return PlaylistFontSize.SMALL

        if not isinstance(data, dict) or data.get("schema_version") != CURRENT_SCHEMA_VERSION:
            return PlaylistFontSize.SMALL
        try:
            return PlaylistFontSize(data.get("size"))
        except ValueError:
            return PlaylistFontSize.SMALL

    def save(self, size: PlaylistFontSize) -> None:
        data: dict[str, Any] = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "size": size.value,
        }
        write_json_atomically(self._path, data)
