from dataclasses import dataclass

MIN_NUMERATOR = 1
MAX_NUMERATOR = 16

ALLOWED_DENOMINATORS = frozenset([2, 4, 8, 16])


@dataclass(frozen=True)
class Meter:
    numerator: int
    denominator: int

    def __post_init__(self):
        if not MIN_NUMERATOR <= self.numerator <= MAX_NUMERATOR:
            raise ValueError(f"Numerator must be between {MIN_NUMERATOR} and {MAX_NUMERATOR}")
        if self.denominator not in ALLOWED_DENOMINATORS:
            raise ValueError(f"Denominator must be one of {ALLOWED_DENOMINATORS}")


    @property
    def beats_per_bar(self) -> int:
        return self.numerator

def beat_in_bar(meter:Meter, beat_count: int) -> int:
    return beat_count % meter.beats_per_bar

def is_downbeat(meter: Meter, beat_count: int) -> bool:
    return beat_in_bar(meter, beat_count) == 0