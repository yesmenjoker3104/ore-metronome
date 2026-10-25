from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable

from ore_metronome.domain.models import MetronomeSettings
from ore_metronome.domain.update import ReleaseInfo, UpdatePreferences


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

@runtime_checkable
class UpdateGateway(Protocol):
    def fetch_latest_release(self) -> ReleaseInfo | None:
        """Returns the latest stable release, or None if no release exists."""
        ...

    def download_release(self, release: ReleaseInfo) -> Path:
        """Downloads and verifies the release, and returns the extracted application folder."""
        ...

    def start_update(self, staged_application: Path) -> None:
        """Starts a separate process that replaces the running application."""
        ...


@runtime_checkable
class UpdateStore(Protocol):
    def load(self) -> UpdatePreferences:
        """Loads the update preferences, or returns the defaults if they are missing."""
        ...

    def save(self, preferences: UpdatePreferences) -> None:
        """Saves the update preferences."""
        ...


BeatEventCallback = Callable[[BeatEvent], None]