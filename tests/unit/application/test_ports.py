from ore_metronome.application.ports import (
    AudioOutput,
    BeatEvent,
    BeatEventSink,
    SettingsStore,
)
from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import MetronomeSettings


def make_settings() -> MetronomeSettings:
    return MetronomeSettings(
        bpm=120,
        meter=Meter(4, 4),
        subdivision=1,
    )


class FakeAudioOutput:
    def __init__(self) -> None:
        self.is_running = False
        self.sample_rate = 44100
        self.started_settings = None
        self.configured_settings = None

    def start(self, settings: MetronomeSettings) -> None:
        self.started_settings = settings
        self.is_running = True

    def stop(self) -> None:
        self.is_running = False

    def configure(self, settings: MetronomeSettings) -> None:
        self.configured_settings = settings


class FakeSettingsStore:
    def __init__(self) -> None:
        self.settings = None

    def load(self) -> MetronomeSettings | None:
        return self.settings

    def save(self, settings: MetronomeSettings) -> None:
        self.settings = settings


class FakeBeatEventSink:
    def __init__(self) -> None:
        self.events: list[BeatEvent] = []

    def publish(self, event: BeatEvent) -> None:
        self.events.append(event)


def test_fake_audio_output_matches_protocol():
    output = FakeAudioOutput()

    assert isinstance(output, AudioOutput)


def test_audio_output_can_start_and_stop():
    output = FakeAudioOutput()
    settings = make_settings()

    output.start(settings)

    assert output.is_running is True
    assert output.started_settings == settings

    output.stop()

    assert output.is_running is False


def test_audio_output_can_be_reconfigured():
    output = FakeAudioOutput()
    settings = make_settings()
    updated = MetronomeSettings(
        bpm=140,
        meter=Meter(4, 4),
        subdivision=1,
    )

    output.start(settings)
    output.configure(updated)

    assert output.configured_settings == updated


def test_fake_settings_store_matches_protocol():
    store = FakeSettingsStore()

    assert isinstance(store, SettingsStore)


def test_settings_store_saves_and_loads_settings():
    store = FakeSettingsStore()
    settings = make_settings()

    assert store.load() is None

    store.save(settings)

    assert store.load() == settings


def test_fake_event_sink_matches_protocol():
    sink = FakeBeatEventSink()

    assert isinstance(sink, BeatEventSink)


def test_event_sink_receives_beat_event():
    sink = FakeBeatEventSink()
    event = BeatEvent(
        beat_index=0,
        is_downbeat=True,
        is_subdivision=False,
    )

    sink.publish(event)

    assert sink.events == [event]