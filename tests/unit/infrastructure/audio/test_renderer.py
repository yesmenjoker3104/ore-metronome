import numpy as np

from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import BeatLevel, MetronomeSettings
from ore_metronome.infrastructure.audio.renderer import render_bar
from ore_metronome.infrastructure.audio.sounds import SoundKit


def make_test_sounds() -> SoundKit:
    # 合算しても 1.0 を超えないよう小さめの値にする。
    return SoundKit(
        accent=np.array([0.125, 0.0625], dtype=np.float32),
        normal=np.array([0.25, 0.125], dtype=np.float32),
        subdivision_accent=np.array([0.5, 0.25], dtype=np.float32),
        subdivision_normal=np.array([0.0625, 0.03125], dtype=np.float32),
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

    assert result[0] == 0.125
    assert result[50] == 0.25
    assert result[100] == 0.25
    assert result[150] == 0.25


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

    assert result[0] == 0.25
    assert result[50] == 0.25


def test_subdivision_track_is_placed_at_equal_intervals_and_plays_with_the_beat():
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

    # 1拍 = 50サンプル。連符の 1 は拍と同時に鳴る（既定はアクセント）。
    # 位置 2 は通常音で 25 に鳴る。
    assert result[0] == 0.125 + 0.5
    assert result[25] == 0.0625
    assert result[50] == 0.25 + 0.5
    assert result[75] == 0.0625


def test_silent_subdivision_is_not_rendered():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(2, 4),
        subdivision=2,
        subdivision_masks={
            2: (BeatLevel.ACCENT, BeatLevel.SILENT),
        },
    )

    result = render_bar(
        settings,
        make_test_sounds(),
        sample_rate=100,
    )

    assert result[0] == 0.125 + 0.5
    assert result[25] == 0.0
    assert result[50] == 0.25 + 0.5
    assert result[75] == 0.0


def test_accent_subdivision_uses_subdivision_accent_sound():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(2, 4),
        subdivision=2,
        subdivision_masks={
            2: (BeatLevel.ACCENT, BeatLevel.ACCENT),
        },
    )

    result = render_bar(
        settings,
        make_test_sounds(),
        sample_rate=100,
    )

    assert result[25] == 0.5
    assert result[75] == 0.5


def test_accent_subdivision_falls_back_to_normal_when_accent_is_disabled():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(2, 4),
        subdivision=2,
        subdivision_masks={
            2: (BeatLevel.ACCENT, BeatLevel.ACCENT),
        },
        accent_enabled=False,
    )

    result = render_bar(
        settings,
        make_test_sounds(),
        sample_rate=100,
    )

    assert result[25] == 0.0625
    assert result[75] == 0.0625


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
    assert result[0] == 0.125 + 0.5
    assert result[8] == 0.0625
    assert result[16] == 0.0
    assert result[17] == 0.0625


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

    assert result[0] == 0.125 + 0.5
    assert result[6] == 0.0625
    assert result[19] == 0.0625


def test_silent_position_one_does_not_mute_the_main_beat():
    settings = MetronomeSettings(
        bpm=120,
        meter=Meter(2, 4),
        subdivision=2,
        subdivision_masks={
            2: (BeatLevel.SILENT, BeatLevel.NORMAL),
        },
    )

    result = render_bar(
        settings,
        make_test_sounds(),
        sample_rate=100,
    )

    # 連符の 1 を無音にしても、メインの拍はそのまま鳴る。
    assert result[0] == 0.125
    assert result[50] == 0.25


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

    assert result[0] == 0.0625


def test_silent_beat_mutes_subdivision_position_one_only():
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

    # 2拍目は拍が無音なので、連符の 1（50）も鳴らない。
    # 連符の 2 つ目（75）は拍とは独立しているので鳴る。
    assert result[0] == 0.125 + 0.5
    assert result[25] == 0.0625
    assert result[50] == 0.0
    assert result[75] == 0.0625


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

    assert result[0] == 0.25


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

    assert result[0] == 0.125
    assert result[100] == 0.125
    assert result[50] == 0.25
