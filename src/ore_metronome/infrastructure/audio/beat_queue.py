from collections import deque
from queue import Empty, SimpleQueue

from ore_metronome.application.ports import BeatEvent


class BeatQueue:
    def __init__(self) -> None:
        self._incoming: SimpleQueue[BeatEvent] = SimpleQueue()
        self._waiting: deque[BeatEvent] = deque()

    def publish(self, event: BeatEvent) -> None:
        self._incoming.put(event)

    def drain(self, now: float | None) -> list[BeatEvent]:
        """Returns the events whose playback time has arrived.

        With now=None the audio is not running, so timed events are stale and dropped.
        """
        self._collect()
        if now is None:
            self._waiting.clear()
            return []
        due: list[BeatEvent] = []
        while self._waiting:
            event = self._waiting[0]
            if event.play_time is not None and event.play_time > now:
                break
            due.append(self._waiting.popleft())
        return due

    def clear(self) -> None:
        self._collect()
        self._waiting.clear()

    def _collect(self) -> None:
        while True:
            try:
                self._waiting.append(self._incoming.get_nowait())
            except Empty:
                return
