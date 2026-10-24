import numpy as np

from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import MetronomeSettings
from ore_metronome.infrastructure.audio.renderer import render_bar
from ore_metronome.infrastructure.audio.sounds import SoundKit


def make_test_sounds() -> SoundKit:
    return SoundKit(
        accent=np.array([0.25, 0.125], dtype=np.float32),
        normal=np.array([0.5, 0.25], dtype=np.float32),
        subdivision=np.array([0.75, 0.375], dtype=np.float32),
    )


def test_render_bar_returns_one_bar_of_audio():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=1,
    )

    result = render_bar(
        settings,
        make_test_sounds(),
        sample_rate=100,
    )

    # 120 BPM = 0.5秒/拍
    # 4拍なので、1小節は2秒 = 200サンプル
    assert result.shape == (200,)
    assert result.dtype == np.float32


def test_first_beat_uses_accent_sound():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=1,
    )

    result = render_bar(
        settings,
        make_test_sounds(),
        sample_rate=100,
    )

    assert result[0] == 0.25
    assert result[50] == 0.5
    assert result[100] == 0.5
    assert result[150] == 0.5


def test_accent_can_be_disabled():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=1,
        accent_enabled=False,
    )

    result = render_bar(
        settings,
        make_test_sounds(),
        sample_rate=100,
    )

    assert result[0] == 0.5
    assert result[50] == 0.5


def test_subdivision_sounds_are_placed_at_equal_intervals():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(2, 4),
        subdivision=2,
    )

    result = render_bar(
        settings,
        make_test_sounds(),
        sample_rate=100,
    )

    # 1拍 = 50サンプル
    # 2分割なので、各拍の25サンプル目にも音が入る
    assert result[0] == 0.25
    assert result[25] == 0.75
    assert result[50] == 0.5
    assert result[75] == 0.75


def test_masked_subdivision_is_not_rendered():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(2, 4),
        subdivision=2,
        subdivision_masks={
            2: (True, False),
        },
    )

    result = render_bar(
        settings,
        make_test_sounds(),
        sample_rate=100,
    )

    assert result[0] == 0.25
    assert result[25] == 0.0
    assert result[50] == 0.5
    assert result[75] == 0.0


def test_downbeat_is_muted_when_position_one_is_off():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(2, 4),
        subdivision=2,
        subdivision_masks={
            2: (False, True),
        },
    )

    result = render_bar(
        settings,
        make_test_sounds(),
        sample_rate=100,
    )

    # 拍頭がOFFなので、強拍・通常拍は鳴らない
    assert result[0] == 0.0
    assert result[25] == 0.75
    assert result[50] == 0.0
    assert result[75] == 0.75


def test_volume_is_applied():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(1, 4),
        subdivision=1,
        volume=50,
    )

    result = render_bar(
        settings,
        make_test_sounds(),
        sample_rate=100,
    )

    assert result[0] == 0.125