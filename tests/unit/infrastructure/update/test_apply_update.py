import os
import subprocess
import sys

import pytest

from ore_metronome.infrastructure.update.apply_update import update_script_path

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell only")


def run_update_script(tmp_path, current, staged, parent_pid: int = 0):
    environment = os.environ.copy()
    environment["ORE_METRONOME_PARENT_PID"] = str(parent_pid)
    environment["TEMP"] = str(tmp_path)
    return subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(update_script_path()),
            "-CurrentApplication",
            str(current),
            "-StagedApplication",
            str(staged),
            "-SkipLaunch",
        ],
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_replaces_current_application_with_staged_one(tmp_path):
    current = tmp_path / "app"
    current.mkdir()
    (current / "old.txt").write_text("old", encoding="utf-8")
    staged = tmp_path / "staged" / "app"
    staged.mkdir(parents=True)
    (staged / "ore-metronome.exe").write_bytes(b"exe")

    result = run_update_script(tmp_path, current, staged)

    assert result.returncode == 0, result.stderr
    assert (current / "ore-metronome.exe").exists()
    assert not (current / "old.txt").exists()
    assert not (tmp_path / "app.bak").exists()


def test_restores_previous_application_when_staged_is_missing(tmp_path):
    current = tmp_path / "app"
    current.mkdir()
    (current / "old.txt").write_text("old", encoding="utf-8")

    result = run_update_script(tmp_path, current, tmp_path / "missing")

    assert result.returncode == 1
    assert (current / "old.txt").read_text(encoding="utf-8") == "old"
    assert not (tmp_path / "app.bak").exists()
