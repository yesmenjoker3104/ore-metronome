import numpy as np

from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import BeatLevel, MetronomeSettings
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


def test_bar_length_follows_denominator():
    sounds = make_test_sounds()

    quarter_bar = render_bar(
        MetronomeSettings(bpm=120, meter=Meter(9, 4), subdivision=1),
        sounds,
        sample_rate=100,
    )
    eighth_bar = render_bar(
        MetronomeSettings(bpm=120, meter=Meter(9, 8), subdivision=1),
        sounds,
        sample_rate=100,
    )

    # 120 BPM の八分音符基準は 0.25秒/拍。9拍で 2.25秒 = 225サンプル
    assert eighth_bar.shape == (225,)
    # 四分音符基準は 0.5秒/拍。9拍で 4.5秒 = 450サンプル
    assert quarter_bar.shape == (450,)


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


def test_six_tuplet_places_clicks_at_sixths_of_a_quarter_beat():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(1, 4),
        subdivision=6,
    )

    result = render_bar(
        settings,
        make_test_sounds(),
        sample_rate=100,
    )

    # 1拍 = 50サンプル。6連符の打点は 8.33, 16.67, ... → 8, 17, 25, 33, 42
    assert result[0] == 0.25
    assert result[8] == 0.75
    assert result[16] == 0.0
    assert result[17] == 0.75


def test_subdivision_applies_to_the_denominator_beat():
    # 8分の1拍子、120 BPM → 1拍 = 0.25秒 = 25サンプル。4分割で 0, 6.25, 12.5, 18.75 に打点
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(1, 8),
        subdivision=4,
    )

    result = render_bar(
        settings,
        make_test_sounds(),
        sample_rate=100,
    )

    assert result[0] == 0.25
    assert result[6] == 0.75
    assert result[19] == 0.75


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


def test_silent_beat_mutes_its_subdivision_clicks():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(2, 4),
        subdivision=2,
        beat_levels={1: BeatLevel.SILENT},
    )

    result = render_bar(
        settings,
        make_test_sounds(),
        sample_rate=100,
    )

    # 2拍目（サンプル 50 以降）は無音。細分音の 75 も鳴らない
    assert result[0] == 0.25
    assert result[25] == 0.75
    assert result[50] == 0.0
    assert result[75] == 0.0


def test_normal_level_on_first_beat_uses_normal_sound():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=1,
        beat_levels={0: BeatLevel.NORMAL},
    )

    result = render_bar(
        settings,
        make_test_sounds(),
        sample_rate=100,
    )

    assert result[0] == 0.5


def test_accent_level_can_be_set_on_any_beat():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=1,
        beat_levels={2: BeatLevel.ACCENT},
    )

    result = render_bar(
        settings,
        make_test_sounds(),
        sample_rate=100,
    )

    assert result[0] == 0.25
    assert result[100] == 0.25
    assert result[50] == 0.5
