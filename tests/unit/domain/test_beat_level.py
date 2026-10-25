import pytest

from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import BeatLevel, MetronomeSettings


def make_settings(*, accent_enabled: bool = True, beat_levels=None) -> MetronomeSettings:
    return MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=1,
        accent_enabled=accent_enabled,
        beat_levels=beat_levels or {},
    )


def test_first_beat_defaults_to_accent_and_others_to_normal():
    settings = make_settings()

    assert settings.effective_beat_level(0) is BeatLevel.ACCENT
    assert settings.effective_beat_level(1) is BeatLevel.NORMAL
    assert settings.effective_beat_level(3) is BeatLevel.NORMAL


def test_cycle_with_accent_goes_accent_normal_silent():
    settings = make_settings()

    assert settings.cycled_beat_level(0) is BeatLevel.NORMAL
    assert settings.cycled_beat_level(1) is BeatLevel.SILENT

    silent_first = make_settings(beat_levels={1: BeatLevel.SILENT})
    assert silent_first.cycled_beat_level(1) is BeatLevel.ACCENT


def test_cycle_with_accent_off_skips_accent():
    settings = make_settings(accent_enabled=False)

    assert settings.effective_beat_level(0) is BeatLevel.NORMAL
    assert settings.cycled_beat_level(0) is BeatLevel.SILENT

    silent = make_settings(accent_enabled=False, beat_levels={0: BeatLevel.SILENT})
    assert silent.cycled_beat_level(0) is BeatLevel.NORMAL


def test_accent_level_shows_as_normal_while_accent_is_off():
    settings = make_settings(accent_enabled=False, beat_levels={2: BeatLevel.ACCENT})

    assert settings.effective_beat_level(2) is BeatLevel.NORMAL


def test_beat_level_outside_the_bar_is_rejected():
    with pytest.raises(ValueError, match="Beat index out of range"):
        make_settings(beat_levels={4: BeatLevel.SILENT})
