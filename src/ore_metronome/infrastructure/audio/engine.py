import threading
from collections.abc import Callable
from typing import Any

import numpy as np
import sounddevice as sd

from ore_metronome.domain.models import MetronomeSettings
from ore_metronome.infrastructure.audio.renderer import AudioBuffer, render_bar
from ore_metronome.infrastructure.audio.sounds import SoundKit

DEFAULT_SAMPLE_RATE = 44100

StreamFactory = Callable[..., Any]

class SoundDeviceEngine:
    def __init__(
            self,
            sounds: SoundKit,
            *,
            sample_rate: int = DEFAULT_SAMPLE_RATE,
            stream_factory: StreamFactory = sd.OutputStream,
    ) -> None:
        self._sounds = sounds
        self._sample_rate = sample_rate
        self._stream_factory = stream_factory
        self._lock = threading.Lock()
        self._bar: AudioBuffer | None = None
        self._position = 0
        self._stream: Any | None = None

    @property
    def is_running(self) -> bool:
        return self._stream is not None

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def start(self, settings: MetronomeSettings) -> None:
        if self.is_running:
            return
        self.configure(settings)
        stream = self._stream_factory(
            samplerate=self._stream_factory,
            channels=1,
            dtype='float32',
            callback=self._fill_buffer,
        )
        stream.start()
        self._stream = stream

    def stop(self) -> None:
        if self._stream is None:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None

    def configure(self, outdata, frames, time, status) -> None:
        with self._lock:
            bar = self._bar
            if bar is None:
                outdata.fill(0)
                return

            chunks = []
            remaining = frames
            while remaining > 0:
                end = min(self._position + remaining, len(bar))
                chunk = bar[self._position : end]
                chunks.append(chunk)
                remaining -= len(chunk)
                self._position = end % len(bar)

        outdata[:, 0] = np.concatenate(chunks)