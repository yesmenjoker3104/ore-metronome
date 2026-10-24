import pytest

from ore_metronome.domain.session import MuteCycle, Session


def run_bars(session, count, bar_seconds=2.0):
    results = []
    for _ in range(count):
        plan = session.begin_bar()
        stop = session.end_bar(plan, bar_seconds)
        results.append((plan, stop))
    return results


def test_bar_numbers_start_at_one_without_count_in():
    session = Session()
    (plan, _), = run_bars(session, 1)
    assert plan.bar_number == 1
    assert plan.is_count_in is False


def test_count_in_bars_have_no_bar_number():
    session = Session(count_in_bars=2)
    results = run_bars(session, 3)
    assert [plan.is_count_in for plan, _ in results] == [True, True, False]
    assert [plan.bar_number for plan, _ in results] == [None, None, 1]


def test_count_in_does_not_count_toward_stop_condition():
    session = Session(count_in_bars=1, stop_after_bars=1)
    results = run_bars(session, 2)
    assert [stop for _, stop in results] == [False, True]


def test_mute_cycle_plays_then_mutes():
    session = Session(mute=MuteCycle(play_bars=2, mute_bars=1))
    results = run_bars(session, 6)
    assert [plan.is_muted for plan, _ in results] == [False, False, True, False, False, True]


def test_mute_cycle_with_zero_mute_bars_never_mutes():
    session = Session(mute=MuteCycle(play_bars=2, mute_bars=0))
    results = run_bars(session, 4)
    assert not any(plan.is_muted for plan, _ in results)


def test_muted_bars_still_count():
    session = Session(mute=MuteCycle(play_bars=1, mute_bars=1), stop_after_bars=4)
    results = run_bars(session, 4)
    assert [stop for _, stop in results] == [False, False, False, True]


def test_stop_after_bars():
    session = Session(stop_after_bars=3)
    results = run_bars(session, 3)
    assert [stop for _, stop in results] == [False, False, True]


def test_stop_after_minutes():
    session = Session(stop_after_minutes=1.0)
    results = run_bars(session, 2, bar_seconds=30.0)
    assert [stop for _, stop in results] == [False, True]


def test_stops_at_whichever_condition_comes_first():
    session = Session(stop_after_bars=10, stop_after_minutes=0.5)
    results = run_bars(session, 3, bar_seconds=10.0)
    assert [stop for _, stop in results] == [False, False, True]


def test_reset_counter_restarts_bars_and_time():
    session = Session(stop_after_bars=2)
    run_bars(session, 1)
    session.reset_counter()
    results = run_bars(session, 2)
    assert [stop for _, stop in results] == [False, True]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"count_in_bars": -1},
        {"count_in_bars": 3},
        {"stop_after_bars": 0},
        {"stop_after_minutes": 0},
    ],
)
def test_invalid_session_settings_are_rejected(kwargs):
    with pytest.raises(ValueError):
        Session(**kwargs)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"play_bars": 0, "mute_bars": 1},
        {"play_bars": 2, "mute_bars": -1},
    ],
)
def test_invalid_mute_cycle_is_rejected(kwargs):
    with pytest.raises(ValueError):
        MuteCycle(**kwargs)