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

# 連符の各位置の状態。位置 1 は拍とは独立に設定し、拍が無音のときだけ無音になる。
def default_position_levels(count: int) -> tuple[BeatLevel, ...]:
    return (BeatLevel.ACCENT,) + (BeatLevel.NORMAL,) * (count - 1)


def _validate_position_levels(
    count: int,
    levels: tuple[BeatLevel, ...],
) -> tuple[BeatLevel, ...]:
    if len(levels) != count:
        raise ValueError(f"mask length {len(levels)} does not match count {count}")
    return tuple(BeatLevel(level) for level in levels)


@dataclass(frozen=True)
class MetronomeSettings:
    bpm: int
    meter: Meter
    subdivision: int
    subdivision_masks: Mapping[int, tuple[BeatLevel, ...]] = field(default_factory=dict)
    accent_enabled: bool = True
    volume: int = MAX_VOLUME
    # 未設定の拍は既定値（1 拍目はアクセント、それ以外は通常）になる。
    beat_levels: Mapping[int, BeatLevel] = field(default_factory=dict)

    def __post_init__(self) -> None:
        validate_bpm(self.bpm)
        validate_count(self.subdivision)

        if not MIN_VOLUME <= self.volume <= MAX_VOLUME:
            raise ValueError(f"Volume must be between {MIN_VOLUME} and {MAX_VOLUME}")

        normalized_masks: dict[int, tuple[BeatLevel, ...]] = {}

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

    def mask_for(self, subdivision: int) -> tuple[BeatLevel, ...]:
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

    def effective_mask_level(self, position_index: int) -> BeatLevel:
        level = self.mask_for(self.subdivision)[position_index]
        if level is BeatLevel.ACCENT and not self.accent_enabled:
            return BeatLevel.NORMAL
        return level

    def effective_position_level(self, beat_index: int, position_index: int) -> BeatLevel:
        # 連符の 1 は拍と独立に設定する。拍が無音のときだけ連符の 1 も無音になる。
        if position_index == 0 and self.effective_beat_level(beat_index) is BeatLevel.SILENT:
            return BeatLevel.SILENT
        return self.effective_mask_level(position_index)

    def cycled_beat_level(self, beat_index: int) -> BeatLevel:
        order = _CYCLE_WITH_ACCENT if self.accent_enabled else _CYCLE_WITHOUT_ACCENT
        current = self.effective_beat_level(beat_index)
        return order[(order.index(current) + 1) % len(order)]

    def cycled_position_level(self, position_index: int) -> BeatLevel:
        order = _CYCLE_WITH_ACCENT if self.accent_enabled else _CYCLE_WITHOUT_ACCENT
        current = self.effective_mask_level(position_index)
        return order[(order.index(current) + 1) % len(order)]


def _default_beat_level(beat_index: int) -> BeatLevel:
    return BeatLevel.ACCENT if beat_index == 0 else BeatLevel.NORMAL