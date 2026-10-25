import json
import os
import tempfile
from pathlib import Path
from typing import Any

from ore_metronome.domain.update import UpdatePreferences

CURRENT_SCHEMA_VERSION = 1


class JsonUpdateStore:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> UpdatePreferences:
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return UpdatePreferences()

        if not isinstance(data, dict) or data.get("schema_version") != CURRENT_SCHEMA_VERSION:
            return UpdatePreferences()

        check_on_startup = data.get("check_on_startup", True)
        skipped_version = data.get("skipped_version", "")
        if not isinstance(check_on_startup, bool) or not isinstance(skipped_version, str):
            return UpdatePreferences()
        return UpdatePreferences(
            check_on_startup=check_on_startup,
            skipped_version=skipped_version,
        )

    def save(self, preferences: UpdatePreferences) -> None:
        data: dict[str, Any] = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "check_on_startup": preferences.check_on_startup,
            "skipped_version": preferences.skipped_version,
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
                json.dump(data, temporary_file, ensure_ascii=False, indent=2)
                temporary_file.write("\n")
                temporary_path = Path(temporary_file.name)
            os.replace(temporary_path, self._path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
