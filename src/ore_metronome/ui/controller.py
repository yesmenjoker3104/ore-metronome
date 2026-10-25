from ore_metronome.application.metronome_service import MetronomeService
from ore_metronome.domain.tap_tempo import TapTempo

MIN_BPM = 20
MAX_BPM = 300


class MetronomeController:
    def __init__(self, service: MetronomeService) -> None:
        self._service = service
        self._tap_tempo = TapTempo()

    @property
    def bpm(self) -> int:
        return self._service.settings.bpm

    @property
    def is_running(self) -> bool:
        return self._service.is_running

    def set_bpm(self, bpm: int) -> None:
        self._service.set_bpm(max(MIN_BPM, min(MAX_BPM, bpm)))

    def toggle(self) -> None:
        self._service.toggle()

    def tap(self, timestamp: float) -> None:
        bpm = self._tap_tempo.tap(timestamp)
        if bpm is not None:
            self.set_bpm(bpm)