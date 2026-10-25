import pytest

from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import BeatLevel, MetronomeSettings


def test_default_settings_are_created():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=1,
    )

    assert settings.bpm == 120
    assert settings.meter == Meter(4, 4)
    assert settings.subdivision == 1
    assert settings.accent_enabled is True
    assert settings.volume == 100


def test_mask_for_subdivision_defaults_to_normal_after_the_first_position():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=3,
    )

    assert settings.mask_for(3) == (None, BeatLevel.NORMAL, BeatLevel.NORMAL)


def test_configured_mask_is_returned():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=5,
        subdivision_masks={
            5: (None, BeatLevel.SILENT, BeatLevel.ACCENT, BeatLevel.NORMAL, BeatLevel.SILENT),
        },
    )

    assert settings.mask_for(5) == (
        None,
        BeatLevel.SILENT,
        BeatLevel.ACCENT,
        BeatLevel.NORMAL,
        BeatLevel.SILENT,
    )


def test_position_levels_are_stored_as_beat_level():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=2,
        subdivision_masks={2: (None, "silent")},
    )

    assert settings.mask_for(2) == (None, BeatLevel.SILENT)


@pytest.mark.parametrize("bpm", [19, 301])
def test_invalid_bpm_is_rejected(bpm):
    with pytest.raises(ValueError):
        MetronomeSettings(
            bpm=bpm,
            meter=Meter(4, 4),
            subdivision=1,
        )


@pytest.mark.parametrize("volume", [-1, 101])
def test_invalid_volume_is_rejected(volume):
    with pytest.raises(ValueError):
        MetronomeSettings(
            bpm=120,
            meter=Meter(4, 4),
            subdivision=1,
            volume=volume,
        )


@pytest.mark.parametrize("subdivision", [0, 10])
def test_invalid_subdivision_is_rejected(subdivision):
    with pytest.raises(ValueError):
        MetronomeSettings(
            bpm=120,
            meter=Meter(4, 4),
            subdivision=subdivision,
        )


def test_six_subdivision_is_kept_in_quarter_meter():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=6,
    )

    assert settings.subdivision == 6


def test_subdivision_is_kept_for_any_denominator():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(3, 8),
        subdivision=6,
    )

    assert settings.subdivision == 6


def test_position_one_must_follow_the_beat_level():
    with pytest.raises(ValueError):
        MetronomeSettings(
            bpm=120,
            meter=Meter(4, 4),
            subdivision=3,
            subdivision_masks={
                3: (BeatLevel.NORMAL, BeatLevel.NORMAL, BeatLevel.NORMAL),
            },
        )


def test_positions_after_the_first_must_have_a_level():
    with pytest.raises(ValueError):
        MetronomeSettings(
            bpm=120,
            meter=Meter(4, 4),
            subdivision=3,
            subdivision_masks={
                3: (None, None, BeatLevel.NORMAL),
            },
        )


def test_position_levels_can_all_be_silent():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=3,
        subdivision_masks={
            3: (None, BeatLevel.SILENT, BeatLevel.SILENT),
        },
    )

    assert settings.mask_for(3) == (None, BeatLevel.SILENT, BeatLevel.SILENT)


def test_invalid_mask_length_is_rejected():
    with pytest.raises(ValueError):
        MetronomeSettings(
            bpm=120,
            meter=Meter(4, 4),
            subdivision=3,
            subdivision_masks={
                3: (None, BeatLevel.NORMAL),
            },
        )


def test_effective_position_level_follows_beat_for_position_one():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=2,
        beat_levels={1: BeatLevel.SILENT},
    )

    assert settings.effective_position_level(0, 0) is BeatLevel.ACCENT
    assert settings.effective_position_level(1, 0) is BeatLevel.SILENT


def test_effective_position_level_downgrades_accent_when_disabled():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=2,
        subdivision_masks={2: (None, BeatLevel.ACCENT)},
        accent_enabled=False,
    )

    assert settings.effective_position_level(0, 0) is BeatLevel.NORMAL
    assert settings.effective_position_level(0, 1) is BeatLevel.NORMAL


def test_cycled_position_level_goes_accent_normal_silent():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=3,
        subdivision_masks={
            3: (None, BeatLevel.ACCENT, BeatLevel.NORMAL),
        },
    )

    assert settings.cycled_position_level(1) is BeatLevel.NORMAL
    assert settings.cycled_position_level(2) is BeatLevel.SILENT


def test_cycled_position_level_skips_accent_when_disabled():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=2,
        subdivision_masks={2: (None, BeatLevel.NORMAL)},
        accent_enabled=False,
    )

    assert settings.cycled_position_level(1) is BeatLevel.SILENT

    silent = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=2,
        subdivision_masks={2: (None, BeatLevel.SILENT)},
        accent_enabled=False,
    )

    assert silent.cycled_position_level(1) is BeatLevel.NORMAL


def test_settings_are_immutable():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=1,
    )

    with pytest.raises(AttributeError):
        settings.bpm = 140