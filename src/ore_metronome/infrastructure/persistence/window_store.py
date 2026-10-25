import json
import os
import tempfile
from pathlib import Path
from typing import Any

from ore_metronome.domain.window import WindowPosition

CURRENT_SCHEMA_VERSION = 1


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


class JsonWindowStore:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> WindowPosition | None:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(data, dict) or data.get("schema_version") != CURRENT_SCHEMA_VERSION:
            return None

        x = data.get("x")
        y = data.get("y")
        if not _is_int(x) or not _is_int(y):
            return None
        return WindowPosition(x=x, y=y)

    def save(self, position: WindowPosition) -> None:
        data: dict[str, Any] = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "x": position.x,
            "y": position.y,
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self._path.parent,
                prefix=f".{self._path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                json.dump(data, temporary_file, indent=2)
                temporary_file.write("\n")
                temporary_path = Path(temporary_file.name)
            os.replace(temporary_path, self._path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
