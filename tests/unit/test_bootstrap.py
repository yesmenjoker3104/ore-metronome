from dataclasses import replace

from ore_metronome.application.metronome_service import MetronomeService
from ore_metronome.bootstrap import build_service


class FakeStream:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def close(self) -> None:
        pass


def fake_factory(**kwargs) -> FakeStream:
    return FakeStream(**kwargs)


def test_build_service_returns_metronome_service(tmp_path):
    service = build_service(
        settings_file=tmp_path / "settings.json",
        stream_factory=fake_factory,
    )

    assert isinstance(service, MetronomeService)
    assert not service.is_running


def test_build_service_toggle_starts_and_stops(tmp_path):
    service = build_service(
        settings_file=tmp_path / "settings.json",
        stream_factory=fake_factory,
    )

    service.toggle()
    assert service.is_running

    service.toggle()
    assert not service.is_running


def test_build_service_restores_saved_settings(tmp_path):
    path = tmp_path / "settings.json"
    service = build_service(settings_file=path, stream_factory=fake_factory)
    service.update_settings(replace(service.settings, bpm=150))

    reloaded = build_service(settings_file=path, stream_factory=fake_factory)

    assert reloaded.settings.bpm == 150

def test_build_service_falls_back_when_settings_file_is_broken(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("{ broken", encoding="utf-8")

    service = build_service(settings_file=path, stream_factory=fake_factory)

    assert service.settings.bpm == 120
    assert not path.exists()
    assert (tmp_path / "settings.json.bak").exists()