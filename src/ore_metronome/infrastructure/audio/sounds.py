from enum import Enum
from pathlib import Path

import numpy as np
import soundfile as sf
from numpy.typing import NDArray


class SoundLoadError(RuntimeError):
    """Raised when an audio file cannot be loaded."""

DEFAULT_SAMPLE_RATE = 44100
DEFAULT_DURATION_MS = 35

AudioSamples = NDArray[np.float32]


class ClickKind(Enum):
    ACCENT = "accent"
    NORMAL = "normal"
    SUBDIVISION = "subdivision"


class SoundKit:
    def __init__(
        self,
        accent: AudioSamples,
        normal: AudioSamples,
        subdivision: AudioSamples,
    ) -> None:
        self.accent = accent
        self.normal = normal
        self.subdivision = subdivision

    def for_kind(self, kind: ClickKind) -> AudioSamples:
        if kind is ClickKind.ACCENT:
            return self.accent
        if kind is ClickKind.NORMAL:
            return self.normal
        if kind is ClickKind.SUBDIVISION:
            return self.subdivision
        raise ValueError(f"Unsupported click kind: {kind}")


def generate_click(
    *,
    frequency: float,
    amplitude: float,
    sample_rate: int,
    duration_ms: float = DEFAULT_DURATION_MS,
) -> AudioSamples:
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")
    if duration_ms <= 0:
        raise ValueError("duration_ms must be positive")
    if frequency <= 0:
        raise ValueError("frequency must be positive")
    if not 0 <= amplitude <= 1:
        raise ValueError("amplitude must be between 0 and 1")

    sample_count = round(sample_rate * duration_ms / 1000)
    time = np.arange(sample_count, dtype=np.float64) / sample_rate

    wave = np.sin(2 * np.pi * frequency * time)
    envelope = np.linspace(1.0, 0.0, sample_count, dtype=np.float64)

    return (amplitude * wave * envelope).astype(np.float32)


def generate_default_sounds(
    sample_rate: int = DEFAULT_SAMPLE_RATE,
) -> SoundKit:
    return SoundKit(
        accent=generate_click(
            frequency=1800,
            amplitude=0.9,
            sample_rate=sample_rate,
        ),
        normal=generate_click(
            frequency=1200,
            amplitude=0.7,
            sample_rate=sample_rate,
        ),
        subdivision=generate_click(
            frequency=800,
            amplitude=0.4,
            sample_rate=sample_rate,
        ),
    )

def load_audio_file(
    path: str | Path,
    *,
    target_sample_rate: int,
) -> AudioSamples:
    if target_sample_rate <= 0:
        raise ValueError("target_sample_rate must be positive")

    try:
        samples, source_sample_rate = sf.read(
            str(path),
            dtype="float32",
            always_2d=True,
        )
    except (OSError, RuntimeError) as exc:
        raise SoundLoadError(f"Could not load audio file: {path}") from exc

    if samples.shape[1] == 0:
        raise SoundLoadError(f"Audio file has no channels: {path}")

    mono = np.mean(samples, axis=1, dtype=np.float32)

    if source_sample_rate == target_sample_rate:
        return mono.astype(np.float32, copy=False)

    return _resample_linear(
        mono,
        source_sample_rate=source_sample_rate,
        target_sample_rate=target_sample_rate,
    )

def _resample_linear(
    samples: AudioSamples,
    *,
    source_sample_rate: int,
    target_sample_rate: int,
) -> AudioSamples:
    if source_sample_rate <= 0:
        raise SoundLoadError("source_sample_rate must be positive")

    if len(samples) == 0:
        return np.empty(0, dtype=np.float32)

    target_length = round(
        len(samples) * target_sample_rate / source_sample_rate
    )

    if target_length <= 0:
        raise SoundLoadError("target length must be positive")

    source_positions = np.arange(len(samples), dtype=np.float64)
    target_positions = np.linspace(
        0,
        len(samples) - 1,
        target_length,
    )

    resampled = np.interp(
        target_positions,
        source_positions,
        samples,
    )
    return resampled.astype(np.float32)