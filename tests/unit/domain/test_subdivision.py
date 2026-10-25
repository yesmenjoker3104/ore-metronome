import pytest

from ore_metronome.domain.subdivision import ALLOWED_COUNTS, validate_count


def test_allowed_count_is_returned():
    assert validate_count(5) == 5

@pytest.mark.parametrize("count", [0, 10, 32, 33])
def test_unsupported_count_is_rejected(count):
    with pytest.raises(ValueError):
        validate_count(count)

def test_six_tuplet_is_allowed():
    assert validate_count(6) == 6

def test_validate_count():
    for count in ALLOWED_COUNTS:
        assert validate_count(count) == count

    with pytest.raises(ValueError):
        validate_count(0)
