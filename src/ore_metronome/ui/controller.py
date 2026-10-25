from ore_metronome.application.metronome_service import MetronomeService
from ore_metronome.application.ports import BeatEvent
from ore_metronome.domain.meter import MAX_NUMERATOR, MIN_NUMERATOR, Meter
from ore_metronome.domain.models import MAX_VOLUME, MIN_VOLUME, BeatLevel
from ore_metronome.domain.tap_tempo import TapTempo
from ore_metronome.infrastructure.audio.beat_queue import BeatQueue

MIN_BPM = 20
MAX_BPM = 300


class MetronomeController:
    def __init__(
        self,
        service: MetronomeService,
        beat_queue: BeatQueue | None = None,
    ) -> None:
        self._service = service
        self._beat_queue = beat_queue
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
        # 開始前に、前回の再生で残った拍イベントを捨てる
        if self._beat_queue is not None:
            self._beat_queue.clear()
        self._service.toggle()

    def tap(self, timestamp: float) -> None:
        bpm = self._tap_tempo.tap(timestamp)
        if bpm is not None:
            self.set_bpm(bpm)

    @property
    def beats_per_bar(self) -> int:
        return self._service.settings.meter.beats_per_bar

    @property
    def numerator(self) -> int:
        return self._service.settings.meter.numerator

    @property
    def denominator(self) -> int:
        return self._service.settings.meter.denominator

    def set_meter(self, numerator: int, denominator: int) -> None:
        numerator = max(MIN_NUMERATOR, min(MAX_NUMERATOR, numerator))
        self._service.set_meter(Meter(numerator, denominator))

    @property
    def accent_enabled(self) -> bool:
        return self._service.settings.accent_enabled

    def beat_level(self, beat_index: int) -> BeatLevel:
        return self._service.settings.effective_beat_level(beat_index)

    def cycle_beat_level(self, beat_index: int) -> None:
        settings = self._service.settings
        self._service.set_beat_level(beat_index, settings.cycled_beat_level(beat_index))

    @property
    def subdivision(self) -> int:
        return self._service.settings.subdivision

    def set_subdivision(self, subdivision: int) -> None:
        self._service.set_subdivision(subdivision)

    def subdivision_mask(self, subdivision: int) -> tuple[BeatLevel, ...]:
        return self._service.settings.mask_for(subdivision)

    def set_subdivision_mask(self, subdivision: int, mask: tuple[BeatLevel, ...]) -> None:
        self._service.set_subdivision_mask(subdivision, mask)

    def subdivision_position_level(self, position_index: int) -> BeatLevel:
        return self._service.settings.effective_mask_level(position_index)

    def cycle_subdivision_position(self, position_index: int) -> None:
        settings = self._service.settings
        count = settings.subdivision
        mask = list(settings.mask_for(count))
        mask[position_index] = settings.cycled_position_level(position_index)
        self._service.set_subdivision_mask(count, tuple(mask))

    @property
    def volume(self) -> int:
        return self._service.settings.volume

    def set_volume(self, volume: int) -> None:
        self._service.set_volume(max(MIN_VOLUME, min(MAX_VOLUME, volume)))

    def save_settings(self) -> None:
        self._service.save_settings()

    def drain_beats(self) -> list[BeatEvent]:
        if self._beat_queue is None:
            return []
        return self._beat_queue.drain(self._service.audio_now())