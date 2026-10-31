from ore_metronome.domain.change_up import ChangeUp, ChangeUpStep
from ore_metronome.domain.meter import Meter
from ore_metronome.domain.models import MetronomeSettings
from ore_metronome.domain.performance import Performance
from ore_metronome.domain.tempo_ramp import TempoRamp


def make_settings(**overrides) -> MetronomeSettings:
    values = {"bpm": 100, "meter": Meter(4, 4), "subdivision": 1}
    values.update(overrides)
    return MetronomeSettings(**values)


def test_plain_settings_resolve_to_base_every_bar():
    performance = Performance(make_settings())

    for _ in range(3):
        resolved = performance.next_bar()
        assert resolved.bpm == 100
        assert resolved.subdivision == 1


def test_tempo_ramp_steps_bpm_at_bar_boundaries():
    ramp = TempoRamp(every_bars=2, delta_bpm=5)
    performance = Performance(make_settings(tempo_ramp=ramp))

    bpms = [performance.next_bar().bpm for _ in range(5)]

    # 1小節目は基準のまま。2 小節ごとに +5
    assert bpms == [100, 100, 105, 105, 110]


def test_change_up_sets_subdivision_per_bar():
    change_up = ChangeUp(steps=(ChangeUpStep(1, 1), ChangeUpStep(4, 2)))
    performance = Performance(make_settings(change_up=change_up))

    subdivisions = [performance.next_bar().subdivision for _ in range(4)]

    assert subdivisions == [1, 4, 4, 1]


def test_tempo_and_change_up_combine():
    ramp = TempoRamp(every_bars=1, delta_bpm=10)
    change_up = ChangeUp(steps=(ChangeUpStep(2, 1), ChangeUpStep(3, 1)))
    performance = Performance(make_settings(tempo_ramp=ramp, change_up=change_up))

    resolved = [performance.next_bar() for _ in range(3)]

    assert [(s.bpm, s.subdivision) for s in resolved] == [
        (100, 2),
        (110, 3),
        (120, 2),
    ]


def test_current_does_not_advance_the_bar():
    ramp = TempoRamp(every_bars=1, delta_bpm=5)
    performance = Performance(make_settings(tempo_ramp=ramp))
    performance.next_bar()

    assert performance.current().bpm == 100
    assert performance.current().bpm == 100
    assert performance.next_bar().bpm == 105


def test_set_settings_restarts_tempo_from_new_base_and_keeps_bar_count():
    ramp = TempoRamp(every_bars=1, delta_bpm=5)
    performance = Performance(make_settings(tempo_ramp=ramp))
    performance.next_bar()
    performance.next_bar()

    performance.set_settings(make_settings(bpm=80, tempo_ramp=ramp))

    # 小節番号は 2 のまま続くので、次の小節で 1 段階上がる
    assert performance.current().bpm == 80
    assert performance.next_bar().bpm == 85


def test_reaching_target_returns_to_base_bpm_and_repeats():
    ramp = TempoRamp(every_bars=1, delta_bpm=10, target_bpm=130)
    performance = Performance(make_settings(tempo_ramp=ramp))

    bpms = [performance.next_bar().bpm for _ in range(6)]

    # 130 に達したら、次の変化の小節で 100 に戻して繰り返す
    assert bpms == [100, 110, 120, 130, 100, 110]


def test_resolved_settings_keep_meter_and_masks():
    change_up = ChangeUp(steps=(ChangeUpStep(3, 1),))
    performance = Performance(
        make_settings(meter=Meter(3, 4), change_up=change_up, swing_percent=60)
    )

    resolved = performance.next_bar()

    assert resolved.meter == Meter(3, 4)
    assert resolved.swing_percent == 60
    assert resolved.subdivision == 3
