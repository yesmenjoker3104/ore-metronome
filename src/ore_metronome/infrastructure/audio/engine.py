import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np
import sounddevice as sd

from ore_metronome.application.ports import BeatEvent, BeatEventSink
from ore_metronome.domain.models import MetronomeSettings
from ore_metronome.domain.performance import Performance
from ore_metronome.domain.session import BarPlan, Session
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
    bpm: int
    subdivision: int
    session_bar: BarPlan


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
        self._performance: Performance | None = None
        self._session = Session()
        self._plan: _BarPlan | None = None
        self._pending: MetronomeSettings | None = None
        self._finished = False
        self._beat_index = 0
        self._position = 0
        self._announce_current = False
        self._stream: Any | None = None

    @property
    def is_running(self) -> bool:
        return self._stream is not None

    @property
    def finished(self) -> bool:
        with self._lock:
            return self._finished

    @property
    def bars_done(self) -> int:
        with self._lock:
            return self._session.bars_done

    def reset_counter(self) -> None:
        with self._lock:
            self._session.reset_counter()

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
        if self.is_running:
            # 次の拍から反映する。小節をまたぐ変更は次の小節の先頭で反映される。
            with self._lock:
                self._pending = settings
            return

        # 小節カウンタは再生開始ごとに作り直す。
        performance = Performance(settings)
        session = Session(
            count_in_bars=settings.count_in_bars,
            mute=settings.mute_cycle,
            stop_after_bars=settings.stop_after_bars,
            stop_after_minutes=settings.stop_after_minutes,
        )
        plan = self._plan_for(performance.next_bar(), session.begin_bar())
        with self._lock:
            self._performance = performance
            self._session = session
            self._plan = plan
            self._pending = None
            self._finished = False
            self._beat_index = 0
            self._position = 0

    def _plan_for(self, settings: MetronomeSettings, session_bar: BarPlan) -> _BarPlan:
        bar = render_bar(
            settings,
            self._sounds,
            sample_rate=self._sample_rate,
            count_in=session_bar.is_count_in,
        )
        if session_bar.is_muted:
            bar = np.zeros_like(bar)
        return _BarPlan(
            bar=bar,
            beat_seconds=beat_seconds_for_meter(settings.bpm, settings.meter),
            beats=settings.meter.beats_per_bar,
            bpm=settings.bpm,
            subdivision=settings.subdivision,
            session_bar=session_bar,
        )

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
            # 自動停止すると _plan が None になり、残りは無音で埋める。
            while remaining > 0 and self._plan is not None:
                boundary = self._next_boundary(self._plan)
                end = min(self._position + remaining, boundary)
                chunks.append(self._plan.bar[self._position : end])
                length = end - self._position
                remaining -= length
                written += length
                self._position = end
                if end == boundary:
                    self._advance_beat(dac_time, offset_frames=written)
            if remaining > 0:
                chunks.append(np.zeros(remaining, dtype=np.float32))

        outdata[:, 0] = np.concatenate(chunks)

    def _next_boundary(self, plan: _BarPlan) -> int:
        if self._beat_index + 1 < plan.beats:
            return self._beat_start(plan, self._beat_index + 1)
        return len(plan.bar)

    def _advance_beat(self, dac_time: float | None, offset_frames: int) -> None:
        next_index = self._beat_index + 1
        new_bar = next_index >= self._plan.beats
        if new_bar:
            next_index = 0

        pending = self._pending
        if pending is not None:
            self._pending = None
            self._performance.set_settings(pending)
            self._session.set_rules(
                pending.mute_cycle,
                pending.stop_after_bars,
                pending.stop_after_minutes,
            )
            # 拍子が縮んで次の拍が収まらないときは、この拍で小節が変わる
            if not new_bar and next_index >= pending.meter.beats_per_bar:
                new_bar = True
                next_index = 0

        if new_bar:
            bar_seconds = self._plan.beat_seconds * self._plan.beats
            if self._session.end_bar(self._plan.session_bar, bar_seconds):
                self._plan = None
                self._finished = True
                return
            self._plan = self._plan_for(
                self._performance.next_bar(),
                self._session.begin_bar(),
            )
        elif pending is not None:
            self._plan = self._plan_for(
                self._performance.current(),
                self._plan.session_bar,
            )

        self._beat_index = next_index
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
                bpm=self._plan.bpm,
                subdivision=self._plan.subdivision,
            )
        )

    def _beat_start(self, plan: _BarPlan, beat_index: int) -> int:
        return round(beat_index * plan.beat_seconds * self._sample_rate)