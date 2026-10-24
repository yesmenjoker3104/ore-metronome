import pytest

from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import MetronomeSettings


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


def test_mask_for_subdivision_defaults_to_all_on():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=3,
    )

    assert settings.mask_for(3) == (True, True, True)


def test_configured_mask_is_returned():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=5,
        subdivision_masks={
            5: (True, False, True, False, True),
        },
    )

    assert settings.mask_for(5) == (True, False, True, False, True)


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


@pytest.mark.parametrize("subdivision", [0, 6, 10])
def test_invalid_subdivision_is_rejected(subdivision):
    with pytest.raises(ValueError):
        MetronomeSettings(
            bpm=120,
            meter=Meter(4, 4),
            subdivision=subdivision,
        )


def test_all_off_mask_is_rejected():
    with pytest.raises(ValueError):
        MetronomeSettings(
            bpm=120,
            meter=Meter(4, 4),
            subdivision=3,
            subdivision_masks={
                3: (False, False, False),
            },
        )


def test_invalid_mask_length_is_rejected():
    with pytest.raises(ValueError):
        MetronomeSettings(
            bpm=120,
            meter=Meter(4, 4),
            subdivision=3,
            subdivision_masks={
                3: (True, False),
            },
        )


def test_settings_are_immutable():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=1,
    )

    with pytest.raises(AttributeError):
        settings.bpm = 140