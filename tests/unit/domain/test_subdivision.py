import pytest

from ore_metronome.domain.subdivision import ALLOWED_COUNTS, validate_count, validate_mask


def test_allowed_count_is_returned():
    assert validate_count(5) == 5

@pytest.mark.parametrize("count", [0, 6, 10, 32, 33])
def test_unsupported_count_is_rejected(count):
    with pytest.raises(ValueError):
        validate_count(count)

def test_validate_count():
    for count in ALLOWED_COUNTS:
        assert validate_count(count) == count

    with pytest.raises(ValueError):
        validate_count(0)

def test_validate_mask():
    assert validate_mask(3, (True, False, True)) == (True, False, True)

    with pytest.raises(ValueError):
        validate_mask(3, (True, False))

    with pytest.raises(ValueError):
        validate_mask(3, (False, False, False))

def test_all_off_mask_is_rejected():
    with pytest.raises(ValueError):
        validate_mask(3, (False, False, False))

def test_5_tuplet_mask_1_3_5():
    mask = (True, False, True, False, True)
    assert validate_mask(5, mask) == mask