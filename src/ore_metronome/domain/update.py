import re
from dataclasses import dataclass

_VERSION_PATTERN = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


@dataclass(frozen=True, slots=True)
class ReleaseInfo:
    version: str
    notes: str
    archive_url: str
    checksum_url: str


@dataclass(frozen=True, slots=True)
class UpdatePreferences:
    check_on_startup: bool = True
    skipped_version: str = ""


def parse_version(text: str) -> tuple[int, int, int]:
    match = _VERSION_PATTERN.fullmatch(text.strip())
    if match is None:
        raise ValueError(f"Unsupported version: {text}")
    return int(match[1]), int(match[2]), int(match[3])


def is_newer_version(candidate: str, current: str) -> bool:
    return parse_version(candidate) > parse_version(current)
