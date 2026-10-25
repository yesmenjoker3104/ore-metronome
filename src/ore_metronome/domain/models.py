from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from ore_metronome.domain.meter import Meter
from ore_metronome.domain.subdivision import validate_count
from ore_metronome.domain.tempo import validate_bpm

MIN_VOLUME = 0
MAX_VOLUME = 100


class BeatLevel(StrEnum):
    ACCENT = "accent"
    NORMAL = "normal"
    SILENT = "silent"


# 循環の順序。アクセント OFF のときはアクセントを飛ばす。
_CYCLE_WITH_ACCENT = (BeatLevel.ACCENT, BeatLevel.NORMAL, BeatLevel.SILENT)
_CYCLE_WITHOUT_ACCENT = (BeatLevel.NORMAL, BeatLevel.SILENT)

# 位置マスクの要素。None は「拍インジケータの強弱に従う」（位置 1 のみ）。
PositionLevel = BeatLevel | None


def default_position_levels(count: int) -> tuple[PositionLevel, ...]:
    return (None,) + (BeatLevel.NORMAL,) * (count - 1)


def _validate_position_levels(
    count: int,
    levels: tuple[PositionLevel, ...],
) -> tuple[PositionLevel, ...]:
    if len(levels) != count:
        raise ValueError(f"mask length {len(levels)} does not match count {count}")
    if levels[0] is not None:
        raise ValueError("position 1 must follow the beat level")
    if any(level is None for level in levels[1:]):
        raise ValueError("only position 1 may follow the beat level")
    return tuple(BeatLevel(level) if level is not None else None for level in levels)


@dataclass(frozen=True)
class MetronomeSettings:
    bpm: int
    meter: Meter
    subdivision: int
    subdivision_masks: Mapping[int, tuple[PositionLevel, ...]] = field(default_factory=dict)
    accent_enabled: bool = True
    volume: int = MAX_VOLUME
    # 未設定の拍は既定値（1 拍目はアクセント、それ以外は通常）になる。
    beat_levels: Mapping[int, BeatLevel] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_bpm(self.bpm)
        validate_count(self.subdivision)

        if not MIN_VOLUME <= self.volume <= MAX_VOLUME:
            raise ValueError(f"Volume must be between {MIN_VOLUME} and {MAX_VOLUME}")

        normalized_masks: dict[int, tuple[PositionLevel, ...]] = {}

        for count, mask in self.subdivision_masks.items():
            validate_count(count)
            normalized_masks[count] = _validate_position_levels(count, tuple(mask))

        object.__setattr__(
            self,
            "subdivision_masks",
            MappingProxyType(normalized_masks),
        )

        normalized_levels: dict[int, BeatLevel] = {}

        for beat_index, level in self.beat_levels.items():
            if not 0 <= beat_index < self.meter.beats_per_bar:
                raise ValueError(f"Beat index out of range: {beat_index}")
            normalized_levels[beat_index] = BeatLevel(level)

        object.__setattr__(
            self,
            "beat_levels",
            MappingProxyType(normalized_levels),
        )

    def mask_for(self, subdivision: int) -> tuple[PositionLevel, ...]:
        validate_count(subdivision)

        configured_mask = self.subdivision_masks.get(subdivision)
        if configured_mask is not None:
            return configured_mask

        return default_position_levels(subdivision)

    def effective_beat_level(self, beat_index: int) -> BeatLevel:
        level = self.beat_levels.get(beat_index, _default_beat_level(beat_index))
        if level is BeatLevel.ACCENT and not self.accent_enabled:
            return BeatLevel.NORMAL
        return level

    def effective_position_level(self, beat_index: int, position_index: int) -> BeatLevel:
        if position_index == 0:
            return self.effective_beat_level(beat_index)

        level = self.mask_for(self.subdivision)[position_index]
        assert level is not None
        if level is BeatLevel.ACCENT and not self.accent_enabled:
            return BeatLevel.NORMAL
        return level

    def cycled_beat_level(self, beat_index: int) -> BeatLevel:
        order = _CYCLE_WITH_ACCENT if self.accent_enabled else _CYCLE_WITHOUT_ACCENT
        current = self.effective_beat_level(beat_index)
        return order[(order.index(current) + 1) % len(order)]

    def cycled_position_level(self, position_index: int) -> BeatLevel:
        order = _CYCLE_WITH_ACCENT if self.accent_enabled else _CYCLE_WITHOUT_ACCENT
        current = self.mask_for(self.subdivision)[position_index]
        assert current is not None
        if current is BeatLevel.ACCENT and not self.accent_enabled:
            current = BeatLevel.NORMAL
        return order[(order.index(current) + 1) % len(order)]


def _default_beat_level(beat_index: int) -> BeatLevel:
    return BeatLevel.ACCENT if beat_index == 0 else BeatLevel.NORMAL