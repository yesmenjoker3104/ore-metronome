import shutil
import sys
import tempfile
from pathlib import Path

from ore_metronome.domain.update import ReleaseInfo
from ore_metronome.infrastructure.update.apply_update import (
    start_update_process,
    update_script_path,
)
from ore_metronome.infrastructure.update.downloader import download_release_archive
from ore_metronome.infrastructure.update.extractor import extract_application
from ore_metronome.infrastructure.update.github_releases import (
    ARCHIVE_NAME,
    fetch_latest_release,
)


class GitHubUpdateGateway:
    def __init__(self, current_application: Path | None = None) -> None:
        self._current_application = current_application or Path(sys.executable).resolve().parent

    def fetch_latest_release(self) -> ReleaseInfo | None:
        return fetch_latest_release()

    def download_release(self, release: ReleaseInfo) -> Path:
        workspace = Path(tempfile.mkdtemp(prefix="ore-metronome-update-"))
        try:
            archive = download_release_archive(release, workspace / ARCHIVE_NAME)
            staged = extract_application(archive, workspace / "staged")
            archive.unlink()
            return staged
        except Exception:
            shutil.rmtree(workspace, ignore_errors=True)
            raise

    def start_update(self, staged_application: Path) -> None:
        start_update_process(staged_application, self._current_application, update_script_path())
