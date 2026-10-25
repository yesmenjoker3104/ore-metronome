import numpy as np
from numpy.typing import NDArray

from ore_metronome.domain.models import BeatLevel, MetronomeSettings
from ore_metronome.domain.tempo import beat_seconds_for_meter
from ore_metronome.infrastructure.audio.sounds import SoundKit

AudioBuffer = NDArray[np.float32]


def render_bar(
    settings: MetronomeSettings,
    sounds: SoundKit,
    *,
    sample_rate: int,
) -> AudioBuffer:
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")

    beat_seconds = beat_seconds_for_meter(settings.bpm, settings.meter)

    bar_seconds = beat_seconds * settings.meter.beats_per_bar
    buffer_length = round(bar_seconds * sample_rate)

    output = np.zeros(buffer_length, dtype=np.float32)
    subdivision = settings.subdivision
    mask = settings.mask_for(subdivision)

    for beat_index in range(settings.meter.beats_per_bar):
        level = settings.effective_beat_level(beat_index)
        if level is BeatLevel.SILENT:
            continue

        for subdivision_index, enabled in enumerate(mask):
            if not enabled:
                continue
            position = beat_index + subdivision_index / subdivision
            start_sample = round(position * beat_seconds * sample_rate)

            if subdivision_index == 0:
                sound = sounds.accent if level is BeatLevel.ACCENT else sounds.normal
            else:
                sound = sounds.subdivision

            _mix_into(output, sound, start_sample)

    output *= settings.volume / 100
    return np.clip(output, -1.0, 1.0).astype(np.float32)


def _mix_into(
    output: AudioBuffer,
    sound: AudioBuffer,
    start_sample: int,
) -> None:
    if start_sample >= len(output):
        return

    if start_sample < 0:
        raise ValueError("start_sample must be non-negative")

    available_length = len(output) - start_sample
    copy_length = min(len(sound), available_length)

    output[start_sample : start_sample + copy_length] += sound[:copy_length]