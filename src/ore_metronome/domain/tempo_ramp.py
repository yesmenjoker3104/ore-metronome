from dataclasses import dataclass

from ore_metronome.domain.tempo import MAX_BPM, MIN_BPM, validate_bpm


@dataclass(frozen=True)
class TempoRamp:
    every_bars: int
    delta_bpm: int
    lower_bpm: int = MIN_BPM
    upper_bpm: int = MAX_BPM
    target_bpm: int | None = None

    def __post_init__(self) -> None:
        if self.every_bars < 1:
            raise ValueError("every_bars must be at least 1")
        if self.delta_bpm == 0:
            raise ValueError("delta_bpm must not be zero")
        validate_bpm(self.lower_bpm)
        validate_bpm(self.upper_bpm)
        if self.lower_bpm > self.upper_bpm:
            raise ValueError("lower_bpm must not be greater than upper_bpm")
        if self.target_bpm is not None:
            validate_bpm(self.target_bpm)
            if not (self.lower_bpm <= self.target_bpm <= self.upper_bpm):
                raise ValueError("target_bpm must be within the range of lower_bpm and upper_bpm")

    def is_change_bar(self, bar_number: int) -> bool:
        return bar_number > 1 and (bar_number - 1) % self.every_bars == 0

    def next_bpm(self, current_bpm: int, bar_number: int) -> int:
        if not self.is_change_bar(bar_number):
            return current_bpm
        if self.reached_target(current_bpm):
            return current_bpm
        stepped = current_bpm + self.delta_bpm
        if self.target_bpm is not None:
            if self.delta_bpm > 0:
                stepped = min(stepped, self.target_bpm)
            else:
                stepped = max(stepped, self.target_bpm)
        return max(self.lower_bpm, min(stepped, self.upper_bpm))

    def reached_target(self, current_bpm: int) -> bool:
        if self.target_bpm is None:
            return False
        if self.delta_bpm > 0:
            return current_bpm >= self.target_bpm
        else:
            return current_bpm <= self.target_bpm