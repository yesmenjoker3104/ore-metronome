from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from ore_metronome.domain.models import MetronomeSettings


@dataclass(frozen=True)
class BeatEvent:
    """A beat notification sent from the audio layer to the UI layer."""

    beat_index: int
    is_downbeat: bool
    is_subdivision: bool


@runtime_checkable
class AudioOutput(Protocol):
    @property
    def is_running(self) -> bool:
        """Indicates whether the audio output is currently running."""
        ...

    @property
    def sample_rate(self) -> int:
        """Returns the sample rate of the audio output."""
        ...

    def start(self, settings: MetronomeSettings) -> None:
        """Starts the audio output with the given metronome settings."""
        ...

    def stop(self) -> None:
        """Stops the audio output."""
        ...

    def configure(self, settings: MetronomeSettings) -> None:
        """Configures the audio output with the given metronome settings."""
        ...

@runtime_checkable
class SettingsStore(Protocol):
    def load(self) -> MetronomeSettings | None:
        """Loads the metronome settings from the store, or returns None if not found."""
        ...

    def save(self, settings: MetronomeSettings) -> None:
        """Saves the metronome settings to the store."""
        ...

@runtime_checkable
class BeatEventSink(Protocol):
    def publish(self, event: BeatEvent) -> None:
        """Publishes a beat event to the sink."""
        ...

BeatEventCallback = Callable[[BeatEvent], None]