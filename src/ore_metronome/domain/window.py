from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class WindowPosition:
    x: int
    y: int
