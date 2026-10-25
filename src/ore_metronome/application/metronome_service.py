from dataclasses import replace

from ore_metronome.application.ports import AudioOutput, SettingsStore
from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import BeatLevel, MetronomeSettings, PositionLevel


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

    def audio_now(self) -> float | None:
        return self._audio_output.now()

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
        levels = {
            index: level
            for index, level in self._settings.beat_levels.items()
            if index < meter.beats_per_bar
        }
        self._apply(replace(self._settings, meter=meter, beat_levels=levels))

    def set_beat_level(self, beat_index: int, level: BeatLevel) -> None:
        levels = dict(self._settings.beat_levels)
        levels[beat_index] = level
        self._apply(replace(self._settings, beat_levels=levels))

    def set_subdivision(self, subdivision: int) -> None:
        self._apply(replace(self._settings, subdivision=subdivision))

    def set_subdivision_mask(self, subdivision: int, mask: tuple[PositionLevel, ...]) -> None:
        masks = dict(self._settings.subdivision_masks)
        masks[subdivision] = mask
        self._apply(replace(self._settings, subdivision_masks=masks))

    def set_volume(self, volume: int) -> None:
        self._apply(replace(self._settings, volume=volume))

    def save_settings(self) -> None:
        self._settings_store.save(self._settings)

    def _apply(self, settings: MetronomeSettings) -> None:
        self._settings = settings
        self._audio_output.configure(settings)