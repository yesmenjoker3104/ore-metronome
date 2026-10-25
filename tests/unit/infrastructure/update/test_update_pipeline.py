import hashlib
import io
import urllib.error
import zipfile

import pytest

from ore_metronome.domain.update import ReleaseInfo
from ore_metronome.infrastructure.update import downloader, extractor, github_releases


def make_archive(path, entries: dict[str, bytes]):
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return path


def test_extracts_single_root_folder(tmp_path):
    archive = make_archive(
        tmp_path / "app.zip",
        {
            "ore-metronome/ore-metronome.exe": b"exe",
            "ore-metronome/_internal/lib.dll": b"dll",
        },
    )

    staged = extractor.extract_application(archive, tmp_path / "staged")

    assert staged.name == "ore-metronome"
    assert (staged / "ore-metronome.exe").read_bytes() == b"exe"
    assert (staged / "_internal" / "lib.dll").read_bytes() == b"dll"


@pytest.mark.parametrize(
    "name",
    ["ore-metronome/../evil.txt", "/evil.txt", "ore-metronome/C:evil.txt"],
)
def test_unsafe_entry_names_are_rejected_before_writing(tmp_path, name):
    archive = make_archive(
        tmp_path / "app.zip",
        {"ore-metronome/ore-metronome.exe": b"exe", name: b"x"},
    )

    with pytest.raises(RuntimeError):
        extractor.extract_application(archive, tmp_path / "staged")

    assert not (tmp_path / "staged").exists()
    assert not (tmp_path / "evil.txt").exists()


def test_archive_without_executable_is_rejected(tmp_path):
    archive = make_archive(tmp_path / "app.zip", {"ore-metronome/readme.txt": b"x"})

    with pytest.raises(RuntimeError, match="ore-metronome.exe"):
        extractor.extract_application(archive, tmp_path / "staged")


def test_archive_with_two_roots_is_rejected(tmp_path):
    archive = make_archive(
        tmp_path / "app.zip",
        {"a/ore-metronome.exe": b"exe", "b/readme.txt": b"x"},
    )

    with pytest.raises(RuntimeError, match="one application directory"):
        extractor.extract_application(archive, tmp_path / "staged")


def fake_urlopen_for(payloads: dict[str, bytes]):
    def _open(url, timeout_seconds):
        return io.BytesIO(payloads[url])

    return _open


def make_release() -> ReleaseInfo:
    return ReleaseInfo(
        version="0.2.0",
        notes="",
        archive_url="https://example.invalid/app.zip",
        checksum_url="https://example.invalid/app.zip.sha256",
    )


def test_download_keeps_archive_when_checksum_matches(tmp_path, monkeypatch):
    data = b"zip-bytes"
    digest = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(
        downloader,
        "_open_https",
        fake_urlopen_for(
            {
                "https://example.invalid/app.zip": data,
                "https://example.invalid/app.zip.sha256": f"{digest}  app.zip\n".encode(),
            }
        ),
    )

    result = downloader.download_release_archive(make_release(), tmp_path / "app.zip")

    assert result.read_bytes() == data


def test_download_deletes_archive_when_checksum_mismatches(tmp_path, monkeypatch):
    wrong = hashlib.sha256(b"other").hexdigest()
    monkeypatch.setattr(
        downloader,
        "_open_https",
        fake_urlopen_for(
            {
                "https://example.invalid/app.zip": b"zip-bytes",
                "https://example.invalid/app.zip.sha256": wrong.encode(),
            }
        ),
    )

    with pytest.raises(downloader.ChecksumMismatchError):
        downloader.download_release_archive(make_release(), tmp_path / "app.zip")

    assert not (tmp_path / "app.zip").exists()


def test_non_https_urls_are_rejected():
    with pytest.raises(ValueError, match="HTTPS"):
        downloader._open_https("http://example.invalid/app.zip", timeout_seconds=1.0)


def fake_github_response(body: bytes):
    def _open(request, timeout):
        return io.BytesIO(body)

    return _open


def test_fetch_latest_release_reads_tag_and_assets(monkeypatch):
    payload = (
        b'{"tag_name": "v0.2.0", "body": "notes", "assets": ['
        b'{"name": "ore-metronome-windows-x64.zip", "browser_download_url": "https://h/a.zip"},'
        b'{"name": "ore-metronome-windows-x64.zip.sha256", "browser_download_url": "https://h/a.sha256"}'
        b"]}"
    )
    monkeypatch.setattr(github_releases.urllib.request, "urlopen", fake_github_response(payload))

    release = github_releases.fetch_latest_release()

    assert release == ReleaseInfo(
        version="0.2.0",
        notes="notes",
        archive_url="https://h/a.zip",
        checksum_url="https://h/a.sha256",
    )


def test_fetch_latest_release_returns_none_when_no_release_exists(monkeypatch):
    def _not_found(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 404, "Not Found", None, None)

    monkeypatch.setattr(github_releases.urllib.request, "urlopen", _not_found)

    assert github_releases.fetch_latest_release() is None


def test_fetch_latest_release_requires_both_assets(monkeypatch):
    payload = b'{"tag_name": "v0.2.0", "assets": []}'
    monkeypatch.setattr(github_releases.urllib.request, "urlopen", fake_github_response(payload))

    with pytest.raises(RuntimeError, match="assets"):
        github_releases.fetch_latest_release()
