from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from ore_metronome.domain.meter import Meter
from ore_metronome.domain.subdivision import validate_count, validate_mask
from ore_metronome.domain.tempo import validate_bpm

MIN_VOLUME = 0
MAX_VOLUME = 100


@dataclass(frozen=True)
class MetronomeSettings:
    bpm: int
    meter: Meter
    subdivision: int
    subdivision_masks: Mapping[int, tuple[bool, ...]] = field(default_factory=dict)
    accent_enabled: bool = True
    volume: int = MAX_VOLUME

    def __post_init__(self) -> None:
        validate_bpm(self.bpm)
        validate_count(self.subdivision)

        if not MIN_VOLUME <= self.volume <= MAX_VOLUME:
            raise ValueError(f"Volume must be between {MIN_VOLUME} and {MAX_VOLUME}")

        normalized_masks: dict[int, tuple[bool, ...]] = {}

        for count, mask in self.subdivision_masks.items():
            validate_count(count)
            normalized_masks[count] = validate_mask(count, tuple(mask))

        object.__setattr__(
            self,
            "subdivision_masks",
            MappingProxyType(normalized_masks),
        )

    def mask_for(self, subdivision: int) -> tuple[bool, ...]:
        validate_count(subdivision)

        configured_mask = self.subdivision_masks.get(subdivision)
        if configured_mask is not None:
            return configured_mask

        return (True,) * subdivision