import pytest

from ore_metronome.domain.tempo import (
    BaseNote,
    TimeMode,
    click_interval_seconds,
    validate_bpm,
)


@pytest.mark.parametrize("bpm", [20, 120, 300])
def test_valid_bpm_is_returned(bpm):
    assert validate_bpm(bpm) == bpm


@pytest.mark.parametrize("bpm", [0, 19, 301])
def test_out_of_range_bpm_raises_value_error(bpm):
    with pytest.raises(ValueError):
        validate_bpm(bpm)


def test_quarter_note_at_120_is_half_second():
    assert click_interval_seconds(120, BaseNote.QUARTER) == 0.5

def test_dotted_quarter_base_at_120_is_three_quarters_second():
    assert click_interval_seconds(120, BaseNote.DOTTED_QUARTER) == 0.75

def test_double_time_halves_interval():
    assert click_interval_seconds(120, mode=TimeMode.DOUBLE) == pytest.approx(0.25)

def test_invalid_bpm_is_rejected_when_computing_interval():
    with pytest.raises(ValueError):
        click_interval_seconds(10)