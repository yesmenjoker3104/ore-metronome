from ore_metronome.domain.tap_tempo import TapTempo


def test_single_tap_gives_no_bpm():
    tap = TapTempo()
    assert tap.tap(0.0) is None


def test_two_taps_half_second_apart_is_120_bpm():
    tap = TapTempo()
    tap.tap(0.0)
    assert tap.tap(0.5) == 120


def test_intervals_are_averaged():
    tap = TapTempo()
    tap.tap(0.0)
    tap.tap(0.5)
    assert tap.tap(1.1) == 109  # 間隔 0.5 と 0.6 の平均 0.55 → 60 / 0.55 ≈ 109.09


def test_only_last_eight_intervals_are_used():
    tap = TapTempo()
    tap.tap(0.0)
    tap.tap(1.0)  # 間隔 1.0（古い）
    for i in range(1, 9):
        last = tap.tap(1.0 + 0.5 * i)  # 間隔 0.5 を 8 回
    assert last == 120


def test_gap_of_two_seconds_resets_measurement():
    tap = TapTempo()
    tap.tap(0.0)
    tap.tap(0.5)
    assert tap.tap(2.5) is None  # 2.0 秒以上空いたのでリセット
    assert tap.tap(3.0) == 120


def test_same_timestamp_is_ignored():
    tap = TapTempo()
    tap.tap(0.0)
    assert tap.tap(0.0) is None


def test_bpm_is_clamped_to_maximum():
    tap = TapTempo()
    tap.tap(0.0)
    assert tap.tap(0.1) == 300