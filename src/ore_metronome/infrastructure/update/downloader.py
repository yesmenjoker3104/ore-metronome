import hashlib
import re
import shutil
import urllib.request
from http.client import HTTPResponse
from pathlib import Path
from urllib.parse import urlparse

from ore_metronome.domain.update import ReleaseInfo
from ore_metronome.infrastructure.update.github_releases import USER_AGENT

_SHA256_PATTERN = re.compile(r"[0-9a-fA-F]{64}")


class ChecksumMismatchError(RuntimeError):
    """Raised when a downloaded archive does not match its published SHA-256."""


def _open_https(url: str, timeout_seconds: float) -> HTTPResponse:
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError("Release download URL must use HTTPS")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return urllib.request.urlopen(request, timeout=timeout_seconds)


def read_expected_sha256(checksum_url: str) -> str:
    with _open_https(checksum_url, timeout_seconds=10.0) as response:
        text = response.read().decode("utf-8")
    match = _SHA256_PATTERN.search(text)
    if match is None:
        raise ValueError("Checksum file does not contain a SHA-256 value")
    return match[0].lower()


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download_release_archive(release: ReleaseInfo, destination: Path) -> Path:
    """Downloads the archive and verifies it. Deletes the file when the checksum does not match."""
    expected = read_expected_sha256(release.checksum_url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with _open_https(release.archive_url, timeout_seconds=60.0) as response:
        with destination.open("wb") as output:
            shutil.copyfileobj(response, output)

    actual = sha256_of(destination)
    if actual != expected:
        destination.unlink(missing_ok=True)
        raise ChecksumMismatchError("Downloaded update does not match its SHA-256 checksum")
    return destination
