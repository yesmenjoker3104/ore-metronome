from dataclasses import replace
from pathlib import Path

from ore_metronome.application.ports import UpdateGateway, UpdateStore
from ore_metronome.domain.update import ReleaseInfo, UpdatePreferences, is_newer_version


class UpdateService:
    def __init__(
        self,
        gateway: UpdateGateway,
        store: UpdateStore,
        current_version: str,
    ) -> None:
        self._gateway = gateway
        self._store = store
        self._current_version = current_version

    @property
    def current_version(self) -> str:
        return self._current_version

    def preferences(self) -> UpdatePreferences:
        return self._store.load()

    def set_check_on_startup(self, enabled: bool) -> None:
        self._store.save(replace(self._store.load(), check_on_startup=enabled))

    def skip_version(self, version: str) -> None:
        self._store.save(replace(self._store.load(), skipped_version=version))

    def find_newer_release(self, *, ignore_skipped: bool) -> ReleaseInfo | None:
        release = self._gateway.fetch_latest_release()
        if release is None or not is_newer_version(release.version, self._current_version):
            return None
        if ignore_skipped and release.version == self._store.load().skipped_version:
            return None
        return release

    def download(self, release: ReleaseInfo) -> Path:
        return self._gateway.download_release(release)

    def apply(self, staged_application: Path) -> None:
        self._gateway.start_update(staged_application)
