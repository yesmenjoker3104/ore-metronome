from queue import Empty, SimpleQueue

from ore_metronome.application.ports import BeatEvent


class BeatQueue:
    def __init__(self) -> None:
        self._queue: SimpleQueue[BeatEvent] = SimpleQueue()

    def publish(self, event: BeatEvent) -> None:
        self._queue.put(event)

    def drain(self) -> list[BeatEvent]:
        events: list[BeatEvent] = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except Empty:
                return events
