import os
from pathlib import Path

import sounddevice as sd

from ore_metronome.application.metronome_service import MetronomeService
from ore_metronome.application.ports import BeatEventSink
from ore_metronome.domain.models import MetronomeSettings
from ore_metronome.infrastructure.audio.engine import (
    DEFAULT_SAMPLE_RATE,
    SoundDeviceEngine,
    StreamFactory,
)
from ore_metronome.infrastructure.audio.sounds import generate_default_sounds
from ore_metronome.infrastructure.persistence.paths import settings_path
from ore_metronome.infrastructure.persistence.settings_repository import (
    SettingsDataError,
    SettingsRepository,
)


class _FallbackSettingsStore:
    def __init__(self, repository: SettingsRepository, path: Path) -> None:
        self._repository = repository
        self._path = path

    def load(self) -> MetronomeSettings | None:
        try:
            return self._repository.load()
        except SettingsDataError:
            os.replace(self._path, self._path.with_name(self._path.name + ".bak"))
            return None

    def save(self, settings: MetronomeSettings) -> None:
        self._repository.save(settings)


def build_service(
        *,
        settings_file: Path | None = None,
        stream_factory: StreamFactory = sd.OutputStream,
        beat_sink: BeatEventSink | None = None,
) -> MetronomeService:
    sounds = generate_default_sounds(sample_rate=DEFAULT_SAMPLE_RATE)
    engine = SoundDeviceEngine(
        sounds=sounds,
        sample_rate=DEFAULT_SAMPLE_RATE,
        stream_factory=stream_factory,
        beat_sink=beat_sink,
    )
    path = settings_file or settings_path()
    store = _FallbackSettingsStore(SettingsRepository(path), path)
    return MetronomeService(
        audio_output=engine,
        settings_store=store,
    )