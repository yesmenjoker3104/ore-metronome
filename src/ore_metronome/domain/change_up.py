from dataclasses import dataclass

from ore_metronome.domain.subdivision import validate_count


@dataclass(frozen=True)
class ChangeUpStep:
    subdivision: int
    bars: int

    def __post_init__(self) -> None:
        validate_count(self.subdivision)
        if self.bars < 1:
            raise ValueError("bars must be at least 1")


@dataclass(frozen=True)
class ChangeUp:
    """細分を段階的に切り替える。最後の段階の後は最初に戻って繰り返す。"""

    steps: tuple[ChangeUpStep, ...]

    def __post_init__(self) -> None:
        steps = tuple(self.steps)
        if not steps:
            raise ValueError("change-up needs at least one step")
        object.__setattr__(self, "steps", steps)

    @property
    def total_bars(self) -> int:
        return sum(step.bars for step in self.steps)

    def subdivision_for_bar(self, bar_number: int) -> int:
        """1 始まりの小節番号に対応する細分を返す。"""
        if bar_number < 1:
            raise ValueError("bar_number must be at least 1")
        position = (bar_number - 1) % self.total_bars
        for step in self.steps:
            if position < step.bars:
                return step.subdivision
            position -= step.bars
        raise AssertionError("unreachable: position is within total_bars")
