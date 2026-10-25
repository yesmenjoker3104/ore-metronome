import json
import urllib.error
import urllib.request

from ore_metronome.domain.update import ReleaseInfo, parse_version

GITHUB_API_URL = "https://api.github.com/repos/yesmenjoker3104/ore-metronome/releases/latest"
ARCHIVE_NAME = "ore-metronome-windows-x64.zip"
CHECKSUM_NAME = f"{ARCHIVE_NAME}.sha256"
USER_AGENT = "OreMetronome-Updater"


def fetch_latest_release(timeout_seconds: float = 10.0) -> ReleaseInfo | None:
    """Returns the latest stable release. Drafts and pre-releases are excluded by the API."""
    request = urllib.request.Request(
        GITHUB_API_URL,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            release = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise

    tag_name = str(release.get("tag_name", ""))
    major, minor, patch = parse_version(tag_name)

    assets = {
        item.get("name"): item.get("browser_download_url")
        for item in release.get("assets", [])
        if isinstance(item, dict)
    }
    archive_url = assets.get(ARCHIVE_NAME)
    checksum_url = assets.get(CHECKSUM_NAME)
    if not isinstance(archive_url, str) or not isinstance(checksum_url, str):
        raise RuntimeError(f"Release assets not found: {ARCHIVE_NAME}, {CHECKSUM_NAME}")

    return ReleaseInfo(
        version=f"{major}.{minor}.{patch}",
        notes=str(release.get("body") or ""),
        archive_url=archive_url,
        checksum_url=checksum_url,
    )
