from dataclasses import dataclass

MAX_COUNT_IN_BARS = 2


@dataclass(frozen=True)
class MuteCycle:
    play_bars: int
    mute_bars: int

    def __post_init__(self) -> None:
        if self.play_bars < 1:
            raise ValueError("play_bars must be at least 1")
        if self.mute_bars < 0:
            raise ValueError("mute_bars must not be negative")

    def is_muted(self, bar_index: int) -> bool:
        if self.mute_bars == 0:
            return False
        return (bar_index % (self.play_bars + self.mute_bars)) >= self.play_bars


@dataclass(frozen=True)
class BarPlan:
    is_count_in: bool
    is_muted: bool
    bar_number: int | None


class Session:
    def __init__(
            self,
            count_in_bars: int = 0,
            mute: MuteCycle | None = None,
            stop_after_bars: int | None = None,
            stop_after_minutes: float | None = None,
    ) -> None:
        if not 0 <= count_in_bars <= MAX_COUNT_IN_BARS:
            raise ValueError(f"count_in_bars must be between 0 and {MAX_COUNT_IN_BARS}")
        if stop_after_bars is not None and stop_after_bars < 1:
            raise ValueError("stop_after_bars must be at least 1")
        if stop_after_minutes is not None and stop_after_minutes <= 0:
            raise ValueError("stop_after_minutes must be positive")
        self._count_in_remaining = count_in_bars
        self._mute = mute
        self._stop_after_bars = stop_after_bars
        self._stop_after_minutes = stop_after_minutes
        self._bar_done = 0
        self._elapsed_seconds = 0.0

    @property
    def bars_done(self) -> int:
        return self._bar_done

    def begin_bar(self) -> BarPlan:
        if self._count_in_remaining > 0:
            self._count_in_remaining -= 1
            return BarPlan(
                is_count_in=True,
                is_muted=False,
                bar_number=None
            )
        is_muted = self._mute is not None and self._mute.is_muted(self._bar_done)
        return BarPlan(
            is_count_in=False,
            is_muted=is_muted,
            bar_number=self._bar_done + 1
        )

    def end_bar(self, plan: BarPlan, bar_seconds: float) -> bool:
        if plan.is_count_in:
            return False
        self._bar_done += 1
        self._elapsed_seconds += bar_seconds
        return self._reached_stop()

    def reset_counter(self) -> None:
        self._bar_done = 0
        self._elapsed_seconds = 0.0

    def _reached_stop(self) -> bool:
        if self._stop_after_bars is not None and self._bar_done >= self._stop_after_bars:
            return True
        if self._stop_after_minutes is None:
            return False
        stop_seconds = self._stop_after_minutes * 60
        if self._elapsed_seconds >= stop_seconds:
            return True
        return False
