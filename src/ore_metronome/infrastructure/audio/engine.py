import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
import sounddevice as sd

from ore_metronome.application.ports import BeatEvent, BeatEventSink
from ore_metronome.domain.models import MetronomeSettings
from ore_metronome.domain.tempo import beat_seconds_for_meter
from ore_metronome.infrastructure.audio.renderer import AudioBuffer, render_bar
from ore_metronome.infrastructure.audio.sounds import SoundKit

DEFAULT_SAMPLE_RATE = 44100

StreamFactory = Callable[..., Any]


@dataclass(frozen=True)
class _BarPlan:
    bar: AudioBuffer
    beat_seconds: float
    beats: int


class SoundDeviceEngine:
    def __init__(
            self,
            sounds: SoundKit,
            *,
            sample_rate: int = DEFAULT_SAMPLE_RATE,
            stream_factory: StreamFactory = sd.OutputStream,
            beat_sink: BeatEventSink | None = None,
    ) -> None:
        self._sounds = sounds
        self._sample_rate = sample_rate
        self._stream_factory = stream_factory
        self._beat_sink = beat_sink
        self._lock = threading.Lock()
        self._plan: _BarPlan | None = None
        self._pending: _BarPlan | None = None
        self._beat_index = 0
        self._position = 0
        self._announce_current = False
        self._stream: Any | None = None

    @property
    def is_running(self) -> bool:
        return self._stream is not None

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    def now(self) -> float | None:
        # 拍イベントの再生時刻と同じ時計（出力ストリームの時刻）を返す
        stream = self._stream
        if stream is None:
            return None
        return stream.time

    def start(self, settings: MetronomeSettings) -> None:
        if self.is_running:
            return
        self.configure(settings)
        self._announce_current = True
        stream = self._stream_factory(
            samplerate=self._sample_rate,
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

    def configure(self, settings: MetronomeSettings) -> None:
        plan = _BarPlan(
            bar=render_bar(settings, self._sounds, sample_rate=self._sample_rate),
            beat_seconds=beat_seconds_for_meter(settings.bpm, settings.meter),
            beats=settings.meter.beats_per_bar,
        )
        with self._lock:
            if self.is_running:
                self._pending = plan
            else:
                self._plan = plan
                self._pending = None
                self._beat_index = 0
                self._position = 0

    def _fill_buffer(self, outdata, frames, time, status) -> None:
        # time.outputBufferDacTime は、このブロックの先頭サンプルが実際に出力される時刻
        dac_time = None if time is None else time.outputBufferDacTime
        with self._lock:
            if self._plan is None:
                outdata.fill(0)
                return

            if self._announce_current:
                self._announce_current = False
                self._publish_beat(dac_time, offset_frames=0)

            chunks = []
            remaining = frames
            written = 0
            while remaining > 0:
                boundary = self._next_boundary(self._plan)
                end = min(self._position + remaining, boundary)
                chunks.append(self._plan.bar[self._position : end])
                length = end - self._position
                remaining -= length
                written += length
                self._position = end
                if end == boundary:
                    self._advance_beat(dac_time, offset_frames=written)

        outdata[:, 0] = np.concatenate(chunks)

    def _next_boundary(self, plan: _BarPlan) -> int:
        if self._beat_index + 1 < plan.beats:
            return self._beat_start(plan, self._beat_index + 1)
        return len(plan.bar)

    def _advance_beat(self, dac_time: float | None, offset_frames: int) -> None:
        # 拍子が変わるときは、切り替え前の拍の次を新しい拍子で数え直す
        next_index = (self._beat_index + 1) % self._plan.beats
        if self._pending is not None:
            self._plan, self._pending = self._pending, None
        self._beat_index = next_index % self._plan.beats
        self._position = self._beat_start(self._plan, self._beat_index)
        self._publish_beat(dac_time, offset_frames)

    def _publish_beat(self, dac_time: float | None, offset_frames: int) -> None:
        if self._beat_sink is None:
            return
        play_time = None
        if dac_time is not None:
            play_time = dac_time + offset_frames / self._sample_rate
        self._beat_sink.publish(
            BeatEvent(
                beat_index=self._beat_index,
                is_downbeat=self._beat_index == 0,
                is_subdivision=False,
                play_time=play_time,
            )
        )

    def _beat_start(self, plan: _BarPlan, beat_index: int) -> int:
        return round(beat_index * plan.beat_seconds * self._sample_rate)