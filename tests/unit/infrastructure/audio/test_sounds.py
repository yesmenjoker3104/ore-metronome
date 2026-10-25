from pathlib import Path

import numpy as np
import pytest

from ore_metronome.infrastructure.audio.sounds import (
    ClickKind,
    SoundLoadError,
    generate_click,
    generate_default_sounds,
    load_audio_file,
)


def test_generate_click_returns_mono_float_array():
    sound = generate_click(
        frequency=1000,
        amplitude=0.5,
        sample_rate=44100,
        duration_ms=20,
    )

    assert isinstance(sound, np.ndarray)
    assert sound.ndim == 1
    assert sound.dtype == np.float32
    assert len(sound) == 882
    assert np.max(np.abs(sound)) <= 0.5


@pytest.mark.parametrize(
    ("kind", "expected_frequency", "expected_amplitude"),
    [
        (ClickKind.ACCENT, 1800, 0.9),
        (ClickKind.NORMAL, 1200, 0.7),
        (ClickKind.SUBDIVISION_ACCENT, 1000, 0.6),
        (ClickKind.SUBDIVISION_NORMAL, 800, 0.4),
    ],
)
def test_default_sound_has_expected_peak(
    kind,
    expected_frequency,
    expected_amplitude,
):
    sounds = generate_default_sounds(sample_rate=44100)

    sound = sounds.for_kind(kind)

    assert sound.ndim == 1
    assert sound.dtype == np.float32
    assert np.max(np.abs(sound)) <= expected_amplitude
    assert np.max(np.abs(sound)) > 0


def test_default_sounds_are_available_by_kind():
    sounds = generate_default_sounds(sample_rate=48000)

    assert sounds.for_kind(ClickKind.ACCENT) is sounds.accent
    assert sounds.for_kind(ClickKind.NORMAL) is sounds.normal
    assert sounds.for_kind(ClickKind.SUBDIVISION_ACCENT) is sounds.subdivision_accent
    assert sounds.for_kind(ClickKind.SUBDIVISION_NORMAL) is sounds.subdivision_normal


def test_subdivision_sounds_use_a_different_timbre_than_beat_sounds():
    # 連符は三角波、拍は正弦波。同じ周波数でも波形が一致しないことを確認する。
    sine = generate_click(frequency=800, amplitude=0.4, sample_rate=44100)
    triangle = generate_click(
        frequency=800,
        amplitude=0.4,
        sample_rate=44100,
        waveform="triangle",
    )

    assert not np.allclose(sine, triangle)
    assert 0.35 <= np.max(np.abs(triangle)) <= 0.4 + 1e-6


@pytest.mark.parametrize(
    ("sample_rate", "duration_ms"),
    [
        (0, 20),
        (-44100, 20),
        (44100, 0),
        (44100, -1),
    ],
)
def test_invalid_click_parameters_are_rejected(sample_rate, duration_ms):
    with pytest.raises(ValueError):
        generate_click(
            frequency=1000,
            amplitude=0.5,
            sample_rate=sample_rate,
            duration_ms=duration_ms,
        )


def test_invalid_amplitude_is_rejected():
    with pytest.raises(ValueError):
        generate_click(
            frequency=1000,
            amplitude=1.1,
            sample_rate=44100,
            duration_ms=20,
        )


def test_load_audio_file_returns_mono_float32(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    source = np.array(
        [
            [0.2, 0.4],
            [0.4, 0.6],
            [0.6, 0.8],
        ],
        dtype=np.float32,
    )

    def fake_read(path, *, dtype, always_2d):
        assert path == str(tmp_path / "click.wav")
        assert dtype == "float32"
        assert always_2d is True
        return source, 44100

    monkeypatch.setattr(
        "ore_metronome.infrastructure.audio.sounds.sf.read",
        fake_read,
    )

    result = load_audio_file(
        tmp_path / "click.wav",
        target_sample_rate=44100,
    )

    assert result.dtype == np.float32
    assert result.ndim == 1
    assert np.allclose(result, [0.3, 0.5, 0.7])


def test_load_audio_file_resamples_to_target_rate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    source = np.array(
        [
            [0.0],
            [1.0],
            [0.0],
            [-1.0],
        ],
        dtype=np.float32,
    )

    def fake_read(path, *, dtype, always_2d):
        return source, 22050

    monkeypatch.setattr(
        "ore_metronome.infrastructure.audio.sounds.sf.read",
        fake_read,
    )

    result = load_audio_file(
        tmp_path / "click.wav",
        target_sample_rate=44100,
    )

    assert result.dtype == np.float32
    assert result.ndim == 1
    assert len(result) == 8


def test_load_audio_file_wraps_soundfile_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    def fake_read(path, *, dtype, always_2d):
        raise RuntimeError("broken audio file")

    monkeypatch.setattr(
        "ore_metronome.infrastructure.audio.sounds.sf.read",
        fake_read,
    )

    with pytest.raises(SoundLoadError, match="Could not load audio file"):
        load_audio_file(
            tmp_path / "broken.wav",
            target_sample_rate=44100,
        )


@pytest.mark.parametrize("sample_rate", [0, -1])
def test_load_audio_file_rejects_invalid_sample_rate(
    tmp_path: Path,
    sample_rate: int,
):
    with pytest.raises(ValueError):
        load_audio_file(
            tmp_path / "click.wav",
            target_sample_rate=sample_rate,
        )