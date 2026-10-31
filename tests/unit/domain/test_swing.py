import pytest

from ore_metronome.domain.swing import (
    DEFAULT_SWING_PERCENT,
    is_swing_applicable,
    swing_offset_beats,
    validate_swing_percent,
)


def test_default_swing_is_straight():
    assert DEFAULT_SWING_PERCENT == 50


@pytest.mark.parametrize("percent", [49, 76])
def test_swing_percent_out_of_range_is_rejected(percent):
    with pytest.raises(ValueError):
        validate_swing_percent(percent)


@pytest.mark.parametrize("percent", [50, 62, 75])
def test_swing_percent_in_range_is_accepted(percent):
    validate_swing_percent(percent)


@pytest.mark.parametrize("subdivision", [2, 4, 6, 8, 32])
def test_even_subdivisions_are_swing_applicable(subdivision):
    assert is_swing_applicable(subdivision) is True


@pytest.mark.parametrize("subdivision", [1, 3, 5, 7, 9])
def test_odd_subdivisions_are_not_swing_applicable(subdivision):
    assert is_swing_applicable(subdivision) is False


def test_straight_swing_has_no_offset():
    for index in range(8):
        assert swing_offset_beats(index, 8, 50) == pytest.approx(0.0)


def test_downbeat_positions_never_move():
    assert swing_offset_beats(0, 2, 75) == 0.0
    assert swing_offset_beats(2, 4, 75) == 0.0


def test_eighth_note_offbeat_moves_to_two_thirds_at_66_percent():
    # 8分の裏は 0.5 拍の位置から、2 つ組の 2/3（0.667 拍）へずれる
    offset = swing_offset_beats(1, 2, 67)
    assert 0.5 + offset == pytest.approx(0.67)


def test_triplet_swing_offset_at_75_percent():
    # 16分（4分割）の裏 0.25 拍が、2 つ組の 75%（0.375 拍）へずれる
    offset = swing_offset_beats(1, 4, 75)
    assert 0.25 + offset == pytest.approx(0.375)


def test_odd_subdivision_offset_is_zero_even_when_swing_is_set():
    assert swing_offset_beats(1, 3, 75) == 0.0
