from dataclasses import replace

from ore_metronome.application.ports import AudioOutput, SettingsStore
from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import MetronomeSettings


def default_settings() -> MetronomeSettings:
    return MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=1,
        accent_enabled=True,
        volume=100,
    )

class MetronomeService:
    def __init__(
        self,
        audio_output: AudioOutput,
        settings_store: SettingsStore,
    ) -> None:
        self._audio_output = audio_output
        self._settings_store = settings_store
        self._settings = settings_store.load() or default_settings()

    @property
    def settings(self) -> MetronomeSettings:
        return self._settings

    @property
    def is_running(self) -> bool:
        return self._audio_output.is_running

    def start(self) -> None:
        if self.is_running:
            return
        self._audio_output.start(self._settings)

    def stop(self) -> None:
        if not self.is_running:
            return

        self._audio_output.stop()

    def toggle(self) -> None:
        if self.is_running:
            self.stop()
        else:
            self.start()

    def update_settings(self, settings: MetronomeSettings) -> None:
        self._apply(settings)
        self._settings_store.save(settings)

    def set_bpm(self, bpm: int) -> None:
        self._apply(replace(self._settings, bpm=bpm))

    def set_meter(self, meter: Meter) -> None:
        self._apply(replace(self._settings, meter=meter))

    def set_volume(self, volume: int) -> None:
        self._apply(replace(self._settings, volume=volume))

    def save_settings(self) -> None:
        self._settings_store.save(self._settings)

    def _apply(self, settings: MetronomeSettings) -> None:
        self._settings = settings
        self._audio_output.configure(settings)