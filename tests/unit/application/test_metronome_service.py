import pytest

from ore_metronome.application.metronome_service import (
    MetronomeService,
    default_settings,
)
from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import MetronomeSettings


class FakeAudioOutput:
    def __init__(self) -> None:
        self.is_running = False
        self.sample_rate = 44100
        self.started_settings: MetronomeSettings | None = None
        self.stopped_count = 0
        self.configured_settings: MetronomeSettings | None = None

    def start(self, settings: MetronomeSettings) -> None:
        self.started_settings = settings
        self.is_running = True

    def stop(self) -> None:
        self.is_running = False
        self.stopped_count += 1

    def configure(self, settings: MetronomeSettings) -> None:
        self.configured_settings = settings


class FakeSettingsStore:
    def __init__(
        self,
        settings: MetronomeSettings | None = None,
    ) -> None:
        self.settings = settings
        self.saved_settings: MetronomeSettings | None = None

    def load(self) -> MetronomeSettings | None:
        return self.settings

    def save(self, settings: MetronomeSettings) -> None:
        self.saved_settings = settings
        self.settings = settings


def make_settings(bpm: int = 120) -> MetronomeSettings:
    return MetronomeSettings(
        bpm=bpm,
        meter=Meter(4, 4),
        subdivision=1,
    )


def test_default_settings_are_120_bpm_four_four():
    settings = default_settings()

    assert settings.bpm == 120
    assert settings.meter == Meter(4, 4)
    assert settings.subdivision == 1
    assert settings.accent_enabled is True
    assert settings.volume == 100


def test_service_uses_default_settings_when_store_is_empty():
    audio = FakeAudioOutput()
    store = FakeSettingsStore()

    service = MetronomeService(audio, store)

    assert service.settings == default_settings()
    assert service.is_running is False


def test_service_loads_saved_settings():
    saved = make_settings(bpm=140)
    audio = FakeAudioOutput()
    store = FakeSettingsStore(saved)

    service = MetronomeService(audio, store)

    assert service.settings == saved


def test_start_starts_audio_with_current_settings():
    audio = FakeAudioOutput()
    store = FakeSettingsStore()
    service = MetronomeService(audio, store)

    service.start()

    assert service.is_running is True
    assert audio.started_settings == service.settings


def test_start_does_not_start_audio_twice():
    audio = FakeAudioOutput()
    store = FakeSettingsStore()
    service = MetronomeService(audio, store)

    service.start()
    service.start()

    assert service.is_running is True
    assert audio.started_settings == service.settings


def test_stop_stops_running_audio():
    audio = FakeAudioOutput()
    store = FakeSettingsStore()
    service = MetronomeService(audio, store)

    service.start()
    service.stop()

    assert service.is_running is False
    assert audio.stopped_count == 1


def test_stop_does_nothing_when_audio_is_not_running():
    audio = FakeAudioOutput()
    store = FakeSettingsStore()
    service = MetronomeService(audio, store)

    service.stop()

    assert audio.stopped_count == 0


def test_toggle_starts_stopped_audio():
    audio = FakeAudioOutput()
    store = FakeSettingsStore()
    service = MetronomeService(audio, store)

    service.toggle()

    assert service.is_running is True


def test_toggle_stops_running_audio():
    audio = FakeAudioOutput()
    store = FakeSettingsStore()
    service = MetronomeService(audio, store)

    service.start()
    service.toggle()

    assert service.is_running is False
    assert audio.stopped_count == 1


def test_update_settings_configures_audio_and_saves_settings():
    audio = FakeAudioOutput()
    store = FakeSettingsStore()
    service = MetronomeService(audio, store)
    updated = make_settings(bpm=160)

    service.update_settings(updated)

    assert service.settings == updated
    assert audio.configured_settings == updated
    assert store.saved_settings == updated


def test_set_bpm_updates_settings_and_configures_audio_without_saving():
    audio = FakeAudioOutput()
    store = FakeSettingsStore()
    service = MetronomeService(audio, store)

    service.set_bpm(150)

    assert service.settings.bpm == 150
    assert service.settings.meter == Meter(4, 4)
    assert audio.configured_settings == service.settings
    assert store.saved_settings is None


def test_set_bpm_while_running_keeps_audio_running():
    audio = FakeAudioOutput()
    store = FakeSettingsStore()
    service = MetronomeService(audio, store)
    service.start()

    service.set_bpm(150)

    assert service.is_running is True
    assert audio.configured_settings.bpm == 150


def test_set_bpm_rejects_out_of_range_and_changes_nothing():
    audio = FakeAudioOutput()
    store = FakeSettingsStore()
    service = MetronomeService(audio, store)
    before = service.settings

    with pytest.raises(ValueError):
        service.set_bpm(301)

    assert service.settings == before
    assert audio.configured_settings is None
    assert store.saved_settings is None


def test_set_meter_updates_settings_and_configures_audio_without_saving():
    audio = FakeAudioOutput()
    store = FakeSettingsStore()
    service = MetronomeService(audio, store)

    service.set_meter(Meter(3, 4))

    assert service.settings.meter == Meter(3, 4)
    assert service.settings.bpm == 120
    assert audio.configured_settings == service.settings
    assert store.saved_settings is None


def test_save_settings_saves_current_settings():
    audio = FakeAudioOutput()
    store = FakeSettingsStore()
    service = MetronomeService(audio, store)
    service.set_bpm(150)

    service.save_settings()

    assert store.saved_settings == service.settings
    assert store.saved_settings.bpm == 150


def test_set_volume_updates_settings():
    service = MetronomeService(FakeAudioOutput(), FakeSettingsStore())

    service.set_volume(40)

    assert service.settings.volume == 40
