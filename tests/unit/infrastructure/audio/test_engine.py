import numpy as np

from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import MetronomeSettings
from ore_metronome.infrastructure.audio.engine import SoundDeviceEngine
from ore_metronome.infrastructure.audio.renderer import render_bar
from ore_metronome.infrastructure.audio.sounds import SoundKit

SAMPLE_RATE = 100


class FakeStream:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.started = False
        self.stopped = False
        self.closed = False
        self.time = 0.0

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def close(self):
        self.closed = True


class FakeStreamFactory:
    def __init__(self):
        self.streams: list[FakeStream] = []

    def __call__(self, **kwargs):
        stream = FakeStream(**kwargs)
        self.streams.append(stream)
        return stream


class FakeBeatSink:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


def make_sounds() -> SoundKit:
    return SoundKit(
        accent=np.array([0.25, 0.125], dtype=np.float32),
        normal=np.array([0.5, 0.25], dtype=np.float32),
        subdivision=np.array([0.75, 0.375], dtype=np.float32),
    )


def make_settings() -> MetronomeSettings:
    # 120 BPM, 2/4 → 1小節 = 1秒 = 100サンプル
    return MetronomeSettings(
        bpm=120,
        meter=Meter(2, 4),
        subdivision=1,
    )


def make_engine(factory: FakeStreamFactory) -> SoundDeviceEngine:
    return SoundDeviceEngine(
        make_sounds(),
        sample_rate=SAMPLE_RATE,
        stream_factory=factory,
    )


def expected_bar() -> np.ndarray:
    return render_bar(make_settings(), make_sounds(), sample_rate=SAMPLE_RATE)


class FakeTimeInfo:
    def __init__(self, dac_time: float) -> None:
        self.outputBufferDacTime = dac_time


def run_callback(stream: FakeStream, frames: int, dac_time: float | None = None) -> np.ndarray:
    outdata = np.full((frames, 1), -1.0, dtype=np.float32)
    time_info = None if dac_time is None else FakeTimeInfo(dac_time)
    stream.kwargs["callback"](outdata, frames, time_info, None)
    return outdata[:, 0]


def test_sample_rate_is_exposed_and_engine_starts_stopped():
    engine = make_engine(FakeStreamFactory())

    assert engine.sample_rate == SAMPLE_RATE
    assert engine.is_running is False


def test_start_opens_mono_float32_output_stream():
    factory = FakeStreamFactory()
    engine = make_engine(factory)

    engine.start(make_settings())

    assert len(factory.streams) == 1
    stream = factory.streams[0]
    assert stream.kwargs["samplerate"] == SAMPLE_RATE
    assert stream.kwargs["channels"] == 1
    assert stream.kwargs["dtype"] == "float32"
    assert callable(stream.kwargs["callback"])
    assert stream.started is True
    assert engine.is_running is True


def test_start_while_running_does_not_open_second_stream():
    factory = FakeStreamFactory()
    engine = make_engine(factory)

    engine.start(make_settings())
    engine.start(make_settings())

    assert len(factory.streams) == 1


def test_stop_stops_and_closes_stream():
    factory = FakeStreamFactory()
    engine = make_engine(factory)
    engine.start(make_settings())

    engine.stop()

    stream = factory.streams[0]
    assert stream.stopped is True
    assert stream.closed is True
    assert engine.is_running is False


def test_stop_when_not_running_does_nothing():
    factory = FakeStreamFactory()
    engine = make_engine(factory)

    engine.stop()

    assert factory.streams == []
    assert engine.is_running is False


def test_start_after_stop_opens_new_stream():
    factory = FakeStreamFactory()
    engine = make_engine(factory)
    engine.start(make_settings())
    engine.stop()

    engine.start(make_settings())

    assert len(factory.streams) == 2
    assert factory.streams[1].started is True
    assert engine.is_running is True


def test_callback_writes_one_bar_of_rendered_audio():
    factory = FakeStreamFactory()
    engine = make_engine(factory)
    engine.start(make_settings())
    bar = expected_bar()

    result = run_callback(factory.streams[0], len(bar))

    np.testing.assert_array_equal(result, bar)


def test_callback_loops_bar_across_buffers():
    factory = FakeStreamFactory()
    engine = make_engine(factory)
    engine.start(make_settings())
    bar = expected_bar()
    stream = factory.streams[0]

    # 60 + 60 = 120フレーム。100サンプルで先頭に戻るため、
    # 2回目のバッファは bar[60:] と bar[:20] が連結される
    first = run_callback(stream, 60)
    second = run_callback(stream, 60)

    result = np.concatenate([first, second])
    expected = np.tile(bar, 2)[:120]
    np.testing.assert_array_equal(result, expected)


def test_start_resets_playback_to_first_beat():
    factory = FakeStreamFactory()
    engine = make_engine(factory)
    bar = expected_bar()

    engine.start(make_settings())
    run_callback(factory.streams[0], 30)
    engine.stop()

    engine.start(make_settings())
    result = run_callback(factory.streams[1], 10)

    np.testing.assert_array_equal(result, bar[:10])


def test_configure_while_running_applies_at_next_click():
    factory = FakeStreamFactory()
    engine = make_engine(factory)
    engine.start(make_settings())
    stream = factory.streams[0]
    old_bar = expected_bar()
    run_callback(stream, 30)

    # 60 BPM, 2/4 → 1拍 = 100サンプル。現在の拍は 50 で終わるので、
    # 50 のクリックは旧テンポのまま、その次の拍（新テンポの 1 拍目）から新テンポになる
    slower = MetronomeSettings(bpm=60, meter=Meter(2, 4), subdivision=1)
    engine.configure(slower)
    result = run_callback(stream, 30)

    new_bar = render_bar(slower, make_sounds(), sample_rate=SAMPLE_RATE)
    expected = np.concatenate([old_bar[30:50], new_bar[100:110]])
    np.testing.assert_array_equal(result, expected)


def test_configure_to_shorter_meter_applies_at_bar_end():
    factory = FakeStreamFactory()
    engine = make_engine(factory)
    engine.start(make_settings())
    stream = factory.streams[0]
    old_bar = expected_bar()
    run_callback(stream, 50)

    # 1/4 at 120 BPM → 1小節 = 50サンプル。2/4 の 2 拍目（50〜99）は鳴り切り、
    # 100 で小節が終わって新しい 1/4 の先頭（0）に戻る
    one_beat = MetronomeSettings(bpm=120, meter=Meter(1, 4), subdivision=1)
    engine.configure(one_beat)
    result = run_callback(stream, 60)

    new_bar = render_bar(one_beat, make_sounds(), sample_rate=SAMPLE_RATE)
    expected = np.concatenate([old_bar[50:100], new_bar[0:10]])
    np.testing.assert_array_equal(result, expected)


def test_configure_meter_change_waits_for_current_beat_to_finish():
    factory = FakeStreamFactory()
    engine = make_engine(factory)
    engine.start(make_settings())
    stream = factory.streams[0]
    old_bar = expected_bar()
    run_callback(stream, 60)

    # 3/4 at 120 BPM → 1拍 = 50サンプル、1小節 = 150サンプル。
    # 2/4 の 2 拍目（50〜99）は最後まで鳴らし、100 から 3/4 の 1 拍目（0）になる
    three_four = MetronomeSettings(bpm=120, meter=Meter(3, 4), subdivision=1)
    engine.configure(three_four)
    result = run_callback(stream, 100)

    new_bar = render_bar(three_four, make_sounds(), sample_rate=SAMPLE_RATE)
    expected = np.concatenate([old_bar[60:100], new_bar[0:60]])
    np.testing.assert_array_equal(result, expected)


def test_beat_sink_receives_beats_in_order():
    factory = FakeStreamFactory()
    sink = FakeBeatSink()
    engine = SoundDeviceEngine(
        make_sounds(),
        sample_rate=SAMPLE_RATE,
        stream_factory=factory,
        beat_sink=sink,
    )
    engine.start(make_settings())

    # 2/4 at 120 BPM, 100 サンプルで 1 小節。2 拍目は 50 サンプル目から
    run_callback(factory.streams[0], 60)

    assert [e.beat_index for e in sink.events] == [0, 1]
    assert [e.is_downbeat for e in sink.events] == [True, False]


def test_beats_carry_play_time_from_dac_clock():
    factory = FakeStreamFactory()
    sink = FakeBeatSink()
    engine = SoundDeviceEngine(
        make_sounds(),
        sample_rate=SAMPLE_RATE,
        stream_factory=factory,
        beat_sink=sink,
    )
    engine.start(make_settings())

    # start() では発行せず、最初のブロックで現在拍を再生時刻つきで発行する
    assert sink.events == []
    run_callback(factory.streams[0], 60, dac_time=10.0)

    assert [e.play_time for e in sink.events] == [10.0, 10.0 + 50 / SAMPLE_RATE]


def test_now_reports_stream_time_only_while_running():
    factory = FakeStreamFactory()
    engine = make_engine(factory)

    assert engine.now() is None

    engine.start(make_settings())
    factory.streams[0].time = 3.5
    assert engine.now() == 3.5

    engine.stop()
    assert engine.now() is None



