import pytest

from ore_metronome.domain.tempo import MAX_BPM, MIN_BPM
from ore_metronome.domain.tempo_ramp import TempoRamp


def test_no_change_on_first_bar():
    ramp = TempoRamp(every_bars=4, delta_bpm=2)
    assert ramp.next_bpm(100, bar_number=1) == 100


def test_changes_only_every_n_bars():
    ramp = TempoRamp(every_bars=4, delta_bpm=2)
    assert ramp.next_bpm(100, bar_number=4) == 100
    assert ramp.next_bpm(100, bar_number=5) == 102


def test_negative_delta_decreases_tempo():
    ramp = TempoRamp(every_bars=1, delta_bpm=-5)
    assert ramp.next_bpm(100, bar_number=2) == 95


def test_stops_at_target_when_rising():
    ramp = TempoRamp(every_bars=4, delta_bpm=2, target_bpm=140)
    assert ramp.next_bpm(138, bar_number=5) == 140
    assert ramp.next_bpm(140, bar_number=9) == 140


def test_does_not_overshoot_target():
    ramp = TempoRamp(every_bars=1, delta_bpm=7, target_bpm=140)
    assert ramp.next_bpm(137, bar_number=2) == 140


def test_stops_at_target_when_falling():
    ramp = TempoRamp(every_bars=1, delta_bpm=-10, target_bpm=80)
    assert ramp.next_bpm(85, bar_number=2) == 80
    assert ramp.next_bpm(80, bar_number=3) == 80


def test_upper_limit_is_respected():
    ramp = TempoRamp(every_bars=1, delta_bpm=10, upper_bpm=120)
    assert ramp.next_bpm(115, bar_number=2) == 120
    assert ramp.next_bpm(120, bar_number=3) == 120


def test_lower_limit_is_respected():
    ramp = TempoRamp(every_bars=1, delta_bpm=-10, lower_bpm=90)
    assert ramp.next_bpm(95, bar_number=2) == 90


def test_default_limits_cover_full_range():
    ramp = TempoRamp(every_bars=1, delta_bpm=1)
    assert ramp.next_bpm(MAX_BPM, bar_number=2) == MAX_BPM
    assert ramp.next_bpm(MIN_BPM, bar_number=2) == MIN_BPM + 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"every_bars": 0, "delta_bpm": 2},
        {"every_bars": 4, "delta_bpm": 0},
        {"every_bars": 4, "delta_bpm": 2, "lower_bpm": 120, "upper_bpm": 100},
        {"every_bars": 4, "delta_bpm": 2, "lower_bpm": 90, "upper_bpm": 100, "target_bpm": 140},
        {"every_bars": 4, "delta_bpm": 2, "upper_bpm": 301},
    ],
)
def test_invalid_settings_are_rejected(kwargs):
    with pytest.raises(ValueError):
        TempoRamp(**kwargs)