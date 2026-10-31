import json
from pathlib import Path
from typing import Any

from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import BeatLevel, MetronomeSettings
from ore_metronome.infrastructure.persistence.json_file import write_json_atomically

CURRENT_SCHEMA_VERSION = 1


def _decode_position_levels(raw: Any) -> tuple[BeatLevel, ...]:
    if not isinstance(raw, list):
        raise TypeError("subdivision mask must be a list")

    levels: list[BeatLevel] = []

    for position_index, item in enumerate(raw):
        if isinstance(item, bool):
            # 旧形式（ON/OFF のみ）。位置 1 は ON を通常、OFF を無音とする。
            if position_index == 0:
                levels.append(BeatLevel.ACCENT)
            else:
                levels.append(BeatLevel.NORMAL if item else BeatLevel.SILENT)
        elif item is None:
            # 旧形式の「拍に従う」。位置 1 は既定のアクセントにする。
            levels.append(BeatLevel.ACCENT if position_index == 0 else BeatLevel.NORMAL)
        else:
            levels.append(BeatLevel(item))

    return tuple(levels)


class SettingsDataError(RuntimeError):
    """Raised when saved settings cannot be read or decoded."""


class SettingsRepository:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> MetronomeSettings | None:
        if not self._path.exists():
            return None

        try:
            data = json.loads(
                self._path.read_text(encoding="utf-8"),
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise SettingsDataError(
                f"Could not read settings: {self._path}"
            ) from exc

        if not isinstance(data, dict):
            raise SettingsDataError(
                f"Settings must be a JSON object: {self._path}"
            )

        schema_version = data.get("schema_version")

        if schema_version != CURRENT_SCHEMA_VERSION:
            raise SettingsDataError(
                f"Unsupported schema version: {schema_version}"
            )

        try:
            return self.decode_settings(data)
        except (KeyError, TypeError, ValueError) as exc:
            raise SettingsDataError(
                f"Invalid settings: {self._path}"
            ) from exc

    def save(self, settings: MetronomeSettings) -> None:
        write_json_atomically(self._path, self.encode_settings(settings))

    @staticmethod
    def encode_settings(
        settings: MetronomeSettings,
    ) -> dict[str, Any]:
        return {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "bpm": settings.bpm,
            "meter": {
                "numerator": settings.meter.numerator,
                "denominator": settings.meter.denominator,
            },
            "subdivision": settings.subdivision,
            "subdivision_masks": {
                str(count): [level.value for level in mask]
                for count, mask in settings.subdivision_masks.items()
            },
            "accent_enabled": settings.accent_enabled,
            "volume": settings.volume,
            "beat_levels": {
                str(index): level.value
                for index, level in settings.beat_levels.items()
            },
        }

    @staticmethod
    def decode_settings(
        data: dict[str, Any],
    ) -> MetronomeSettings:
        meter_data = data["meter"]

        if not isinstance(meter_data, dict):
            raise TypeError("meter must be an object")

        masks_data = data["subdivision_masks"]

        if not isinstance(masks_data, dict):
            raise TypeError("subdivision_masks must be an object")

        masks = {
            int(count): _decode_position_levels(mask)
            for count, mask in masks_data.items()
        }

        # 拍の状態は後から追加したため、無い設定ファイルも読めるようにする。
        levels_data = data.get("beat_levels", {})

        if not isinstance(levels_data, dict):
            raise TypeError("beat_levels must be an object")

        levels = {
            int(index): BeatLevel(level)
            for index, level in levels_data.items()
        }

        return MetronomeSettings(
            bpm=data["bpm"],
            meter=Meter(
                numerator=meter_data["numerator"],
                denominator=meter_data["denominator"],
            ),
            subdivision=data["subdivision"],
            subdivision_masks=masks,
            accent_enabled=data["accent_enabled"],
            volume=data["volume"],
            beat_levels=levels,
        )