from ore_metronome.application.ports import BeatEvent
from ore_metronome.infrastructure.audio.beat_queue import BeatQueue


def event(index: int, play_time: float | None) -> BeatEvent:
    return BeatEvent(
        beat_index=index,
        is_downbeat=index == 0,
        is_subdivision=False,
        play_time=play_time,
    )


def test_drain_returns_only_events_whose_play_time_has_arrived():
    queue = BeatQueue()
    queue.publish(event(0, 1.0))
    queue.publish(event(1, 2.0))

    assert [e.beat_index for e in queue.drain(now=1.5)] == [0]
    assert [e.beat_index for e in queue.drain(now=1.6)] == []
    assert [e.beat_index for e in queue.drain(now=2.0)] == [1]


def test_untimed_events_are_returned_immediately():
    queue = BeatQueue()
    queue.publish(event(0, None))

    assert [e.beat_index for e in queue.drain(now=0.0)] == [0]


def test_drain_without_clock_drops_timed_events():
    queue = BeatQueue()
    queue.publish(event(0, 1.0))

    assert queue.drain(now=None) == []
    assert queue.drain(now=5.0) == []


def test_clear_discards_pending_events():
    queue = BeatQueue()
    queue.publish(event(0, 1.0))
    queue.drain(now=0.0)
    queue.publish(event(1, 2.0))

    queue.clear()

    assert queue.drain(now=10.0) == []
