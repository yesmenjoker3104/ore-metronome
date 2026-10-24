from enum import Enum

MIN_BPM = 20
MAX_BPM = 300

class BaseNote(Enum):
    EIGHTH = 0.5
    QUARTER = 1.0
    DOTTED_QUARTER = 1.5
    HALF = 2.0

class TimeMode(Enum):
    NORMAL = 1.0
    HALF = 2.0
    DOUBLE = 0.5

def validate_bpm(bpm: int) -> int:
    if not MIN_BPM <= bpm <= MAX_BPM:
        raise ValueError(f"BPM must be between {MIN_BPM} and {MAX_BPM}")
    return bpm

def click_interval_seconds(
        bpm: int,
        base: BaseNote = BaseNote.QUARTER,
        mode: TimeMode = TimeMode.NORMAL
) -> float:
    validate_bpm(bpm)
    return (60.0 / bpm) * base.value * mode.value
