import pytest

from ore_metronome.domain.meter import Meter, beat_in_bar, is_downbeat


@pytest.mark.parametrize(("numerator", "denominator"), [(1, 2), (4, 4), (7, 8), (16, 16)])
def test_valid_meter_is_created(numerator, denominator):
    meter = Meter(numerator, denominator)
    assert meter.beats_per_bar == numerator


@pytest.mark.parametrize("numerator", [0, 17])
def test_out_of_range_numerator_is_rejected(numerator):
    with pytest.raises(ValueError):
        Meter(numerator, 4)


@pytest.mark.parametrize("denominator", [1, 3, 32])
def test_unsupported_denominator_is_rejected(denominator):
    with pytest.raises(ValueError):
        Meter(4, denominator)


def test_beat_in_bar_wraps_at_numerator():
    meter = Meter(4, 4)
    assert [beat_in_bar(meter, n) for n in range(6)] == [0, 1, 2, 3, 0, 1]


def test_downbeat_repeats_every_bar():
    meter = Meter(3, 4)
    downbeats = [n for n in range(7) if is_downbeat(meter, n)]
    assert downbeats == [0, 3, 6]
