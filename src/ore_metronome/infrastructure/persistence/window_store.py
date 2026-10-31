import json
from pathlib import Path
from typing import Any

from ore_metronome.domain.window import WindowGeometry
from ore_metronome.infrastructure.persistence.json_file import write_json_atomically

CURRENT_SCHEMA_VERSION = 2


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


class JsonWindowStore:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> WindowGeometry | None:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(data, dict) or data.get("schema_version") != CURRENT_SCHEMA_VERSION:
            return None

        x = data.get("x")
        y = data.get("y")
        width = data.get("width")
        height = data.get("height")
        if not _is_int(x) or not _is_int(y):
            return None
        if not _is_int(width) or not _is_int(height) or width <= 0 or height <= 0:
            return None
        return WindowGeometry(x=x, y=y, width=width, height=height)

    def save(self, geometry: WindowGeometry) -> None:
        data: dict[str, Any] = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "x": geometry.x,
            "y": geometry.y,
            "width": geometry.width,
            "height": geometry.height,
        }
        write_json_atomically(self._path, data)
