import pytest

from ore_metronome.domain.change_up import ChangeUp, ChangeUpStep


def test_step_rejects_invalid_subdivision():
    with pytest.raises(ValueError):
        ChangeUpStep(subdivision=10, bars=4)


def test_step_rejects_zero_bars():
    with pytest.raises(ValueError):
        ChangeUpStep(subdivision=2, bars=0)


def test_change_up_rejects_empty_steps():
    with pytest.raises(ValueError):
        ChangeUp(steps=())


def test_change_up_total_bars_sums_steps():
    change_up = ChangeUp(
        steps=(ChangeUpStep(1, 4), ChangeUpStep(2, 2), ChangeUpStep(5, 3)),
    )

    assert change_up.total_bars == 9


def test_subdivision_follows_steps_in_order():
    change_up = ChangeUp(
        steps=(ChangeUpStep(1, 2), ChangeUpStep(2, 1), ChangeUpStep(7, 2)),
    )

    assert [change_up.subdivision_for_bar(n) for n in range(1, 6)] == [1, 1, 2, 7, 7]


def test_subdivision_loops_back_to_first_step():
    change_up = ChangeUp(steps=(ChangeUpStep(1, 2), ChangeUpStep(3, 1)))

    # 1 → 1 → 3 → 1 → 1 → 3 ...
    assert [change_up.subdivision_for_bar(n) for n in range(1, 8)] == [
        1,
        1,
        3,
        1,
        1,
        3,
        1,
    ]


def test_default_style_chain_matches_four_steps_of_four_bars():
    change_up = ChangeUp(
        steps=(
            ChangeUpStep(1, 4),
            ChangeUpStep(2, 4),
            ChangeUpStep(3, 4),
            ChangeUpStep(4, 4),
        ),
    )

    assert change_up.subdivision_for_bar(4) == 1
    assert change_up.subdivision_for_bar(5) == 2
    assert change_up.subdivision_for_bar(12) == 3
    assert change_up.subdivision_for_bar(13) == 4
    assert change_up.subdivision_for_bar(16) == 4
    assert change_up.subdivision_for_bar(17) == 1


def test_bar_number_must_start_at_one():
    change_up = ChangeUp(steps=(ChangeUpStep(1, 1),))

    with pytest.raises(ValueError):
        change_up.subdivision_for_bar(0)
