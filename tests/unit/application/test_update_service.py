from pathlib import Path

from ore_metronome.application.update_service import UpdateService
from ore_metronome.domain.update import ReleaseInfo, UpdatePreferences


class FakeStore:
    def __init__(self, preferences: UpdatePreferences | None = None) -> None:
        self.preferences = preferences or UpdatePreferences()

    def load(self) -> UpdatePreferences:
        return self.preferences

    def save(self, preferences: UpdatePreferences) -> None:
        self.preferences = preferences


class FakeGateway:
    def __init__(self, release: ReleaseInfo | None = None) -> None:
        self.release = release
        self.started_with: Path | None = None

    def fetch_latest_release(self) -> ReleaseInfo | None:
        return self.release

    def download_release(self, release: ReleaseInfo) -> Path:
        return Path("staged")

    def start_update(self, staged_application: Path) -> None:
        self.started_with = staged_application


def make_release(version: str) -> ReleaseInfo:
    return ReleaseInfo(
        version=version,
        notes="",
        archive_url="https://example.invalid/app.zip",
        checksum_url="https://example.invalid/app.zip.sha256",
    )


def test_newer_release_is_returned():
    service = UpdateService(FakeGateway(make_release("0.2.0")), FakeStore(), "0.1.0")

    release = service.find_newer_release(ignore_skipped=True)

    assert release is not None
    assert release.version == "0.2.0"


def test_same_or_older_release_is_ignored():
    service = UpdateService(FakeGateway(make_release("0.1.0")), FakeStore(), "0.1.0")

    assert service.find_newer_release(ignore_skipped=True) is None


def test_skipped_version_is_hidden_only_from_automatic_check():
    store = FakeStore(UpdatePreferences(skipped_version="0.2.0"))
    service = UpdateService(FakeGateway(make_release("0.2.0")), store, "0.1.0")

    assert service.find_newer_release(ignore_skipped=True) is None
    manual = service.find_newer_release(ignore_skipped=False)
    assert manual is not None
    assert manual.version == "0.2.0"


def test_skip_and_startup_toggle_are_persisted():
    store = FakeStore()
    service = UpdateService(FakeGateway(), store, "0.1.0")

    service.skip_version("0.2.0")
    service.set_check_on_startup(False)

    assert store.preferences == UpdatePreferences(check_on_startup=False, skipped_version="0.2.0")


def test_apply_passes_staged_application_to_gateway():
    gateway = FakeGateway()
    service = UpdateService(gateway, FakeStore(), "0.1.0")

    service.apply(Path("staged"))

    assert gateway.started_with == Path("staged")
