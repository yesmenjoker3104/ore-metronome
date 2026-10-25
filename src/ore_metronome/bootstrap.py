from pathlib import Path

import sounddevice as sd

from ore_metronome.application.metronome_service import MetronomeService
from ore_metronome.infrastructure.audio.engine import (
    DEFAULT_SAMPLE_RATE,
    SoundDeviceEngine,
    StreamFactory,
)
from ore_metronome.infrastructure.audio.sounds import generate_default_sounds
from ore_metronome.infrastructure.persistence.paths import settings_path
from ore_metronome.infrastructure.persistence.settings_repository import SettingsRepository


def build_service(
        *,
        settings_file: Path | None = None,
        stream_factory: StreamFactory = sd.OutputStream,
) -> MetronomeService:
    sounds = generate_default_sounds(sample_rate=DEFAULT_SAMPLE_RATE)
    engine = SoundDeviceEngine(
        sounds=sounds,
        sample_rate=DEFAULT_SAMPLE_RATE,
        stream_factory=stream_factory,
    )
    store = SettingsRepository(settings_file or settings_path())
    return MetronomeService(
        audio_output=engine,
        settings_store=store,
    )