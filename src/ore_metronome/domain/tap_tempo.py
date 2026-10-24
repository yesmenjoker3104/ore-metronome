from collections import deque

from ore_metronome.domain.tempo import MAX_BPM, MIN_BPM

RESET_SECONDS = 2.0
MAX_INTERVALS = 8


class TapTempo:
    def __init__(self) -> None:
        self._last_tap: float | None = None
        self._intervals: deque[float] = deque(maxlen=MAX_INTERVALS)

    def tap(self, timestamp: float) -> int | None:
        if self._last_tap is not None:
            gap = timestamp - self._last_tap
            if gap >= RESET_SECONDS:
                self._intervals.clear()
            elif gap > 0:
                self._intervals.append(gap)
        self._last_tap = timestamp

        if not self._intervals:
            return None
        average = sum(self._intervals) / len(self._intervals)
        tempo = round(60.0 / average)
        return max(MIN_BPM, min(MAX_BPM, tempo))