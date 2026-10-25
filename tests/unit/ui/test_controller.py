import pytest

from ore_metronome.application.metronome_service import MetronomeService
from ore_metronome.domain.meter import MAX_NUMERATOR, MIN_NUMERATOR
from ore_metronome.domain.models import BeatLevel
from ore_metronome.ui.controller import MAX_BPM, MIN_BPM, MetronomeController


class FakeAudio:
    def __init__(self) -> None:
        self.is_running = False

    def start(self, settings) -> None:
        self.is_running = True

    def stop(self) -> None:
        self.is_running = False

    def now(self) -> float | None:
        return None

    def configure(self, settings) -> None:
        pass


class FakeStore:
    def load(self):
        return None

    def save(self, settings) -> None:
        pass


@pytest.fixture
def controller_and_service():
    service = MetronomeService(audio_output=FakeAudio(), settings_store=FakeStore())
    return MetronomeController(service), service


def test_bpm_reflects_service_settings(controller_and_service):
    controller, _ = controller_and_service

    assert controller.bpm == 120


def test_set_bpm_updates_service(controller_and_service):
    controller, service = controller_and_service

    controller.set_bpm(140)

    assert service.settings.bpm == 140
    assert controller.bpm == 140


@pytest.mark.parametrize(
    ("requested", "expected"),
    [(MIN_BPM - 10, MIN_BPM), (MAX_BPM + 50, MAX_BPM)],
)
def test_set_bpm_clamps_to_range(controller_and_service, requested, expected):
    controller, _ = controller_and_service

    controller.set_bpm(requested)

    assert controller.bpm == expected


def test_toggle_starts_and_stops(controller_and_service):
    controller, _ = controller_and_service

    assert not controller.is_running

    controller.toggle()
    assert controller.is_running

    controller.toggle()
    assert not controller.is_running


def test_tap_sets_bpm_from_interval(controller_and_service):
    controller, _ = controller_and_service

    controller.tap(10.0)
    controller.tap(10.4)  # 0.4 秒間隔 = 150 BPM

    assert controller.bpm == 150


def test_set_meter_updates_service(controller_and_service):
    controller, service = controller_and_service

    controller.set_meter(12, 8)

    assert service.settings.meter.numerator == 12
    assert service.settings.meter.denominator == 8
    assert controller.beats_per_bar == 12


@pytest.mark.parametrize(
    ("requested", "expected"),
    [(MIN_NUMERATOR - 5, MIN_NUMERATOR), (MAX_NUMERATOR + 5, MAX_NUMERATOR)],
)
def test_set_meter_clamps_numerator(controller_and_service, requested, expected):
    controller, _ = controller_and_service

    controller.set_meter(requested, 4)

    assert controller.numerator == expected


def test_set_subdivision_updates_service(controller_and_service):
    controller, service = controller_and_service

    controller.set_subdivision(6)

    assert service.settings.subdivision == 6
    assert controller.subdivision == 6


def test_set_subdivision_mask_updates_service(controller_and_service):
    controller, _ = controller_and_service
    controller.set_subdivision(5)

    controller.set_subdivision_mask(
        5,
        (
            BeatLevel.ACCENT,
            BeatLevel.SILENT,
            BeatLevel.ACCENT,
            BeatLevel.NORMAL,
            BeatLevel.SILENT,
        ),
    )

    assert controller.subdivision_mask(5) == (
        BeatLevel.ACCENT,
        BeatLevel.SILENT,
        BeatLevel.ACCENT,
        BeatLevel.NORMAL,
        BeatLevel.SILENT,
    )


def test_cycle_subdivision_position_updates_current_subdivision(controller_and_service):
    controller, _ = controller_and_service
    controller.set_subdivision(3)

    controller.cycle_subdivision_position(2)

    assert controller.subdivision_mask(3) == (
        BeatLevel.ACCENT,
        BeatLevel.NORMAL,
        BeatLevel.SILENT,
    )
    assert controller.subdivision_position_level(2) is BeatLevel.SILENT
