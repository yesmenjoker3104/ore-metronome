from dataclasses import replace

from ore_metronome.domain.models import MetronomeSettings


class Performance:
    """小節ごとに、テンポアップとチェンジアップを反映した設定を求める。"""

    def __init__(self, settings: MetronomeSettings) -> None:
        self._settings = settings
        self._bar_number = 0
        self._bpm = settings.bpm

    @property
    def settings(self) -> MetronomeSettings:
        return self._settings

    def set_settings(self, settings: MetronomeSettings) -> None:
        # 設定を変えたら、テンポは基準の BPM からやり直す。小節番号は続ける。
        self._settings = settings
        self._bpm = settings.bpm

    def next_bar(self) -> MetronomeSettings:
        self._bar_number += 1
        ramp = self._settings.tempo_ramp
        if ramp is not None and ramp.is_change_bar(self._bar_number):
            if ramp.reached_target(self._bpm):
                # 目標に達していたら、開始の BPM に戻して同じ変化を繰り返す。
                self._bpm = self._settings.bpm
            else:
                self._bpm = ramp.next_bpm(self._bpm, self._bar_number)
        return self.current()

    def current(self) -> MetronomeSettings:
        subdivision = self._settings.subdivision
        change_up = self._settings.change_up
        if change_up is not None and self._bar_number >= 1:
            subdivision = change_up.subdivision_for_bar(self._bar_number)
        return replace(self._settings, bpm=self._bpm, subdivision=subdivision)
