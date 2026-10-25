import os
import re
import tomllib
from pathlib import Path

import pytest

from ore_metronome.version import __version__

ROOT = Path(__file__).resolve().parents[2]


def test_changelog_top_entry_matches_version():
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    match = re.search(r"^## \[(\d+\.\d+\.\d+)\]", text, re.MULTILINE)

    assert match is not None
    assert match[1] == __version__


def test_pyproject_reads_version_from_package():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "version" in data["project"]["dynamic"]
    assert data["tool"]["setuptools"]["dynamic"]["version"]["attr"] == (
        "ore_metronome.version.__version__"
    )


def test_release_tag_matches_version():
    if os.environ.get("GITHUB_REF_TYPE") != "tag":
        pytest.skip("only checked when building a release tag")

    assert os.environ["GITHUB_REF_NAME"] == f"v{__version__}"
