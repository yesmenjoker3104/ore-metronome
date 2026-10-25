import os
import subprocess
import sys
import time

import pytest

from ore_metronome.infrastructure.update.apply_update import update_script_path

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows PowerShell only")


def _script_command(current, staged) -> list[str]:
    return [
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
    ]


def _script_environment(tmp_path, parent_pid: int = 0) -> dict[str, str]:
    environment = os.environ.copy()
    environment["ORE_METRONOME_PARENT_PID"] = str(parent_pid)
    environment["TEMP"] = str(tmp_path)
    return environment


def start_update_script(tmp_path, current, staged) -> subprocess.Popen:
    return subprocess.Popen(
        _script_command(current, staged),
        env=_script_environment(tmp_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def run_update_script(tmp_path, current, staged, parent_pid: int = 0):
    return subprocess.run(
        _script_command(current, staged),
        env=_script_environment(tmp_path, parent_pid),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_replaces_only_the_executable_in_current_application(tmp_path):
    current = tmp_path / "app"
    current.mkdir()
    (current / "ore-metronome.exe").write_bytes(b"old-exe")
    (current / "settings.txt").write_text("keep", encoding="utf-8")
    staged = tmp_path / "staged" / "app"
    staged.mkdir(parents=True)
    (staged / "ore-metronome.exe").write_bytes(b"new-exe")

    result = run_update_script(tmp_path, current, staged)

    assert result.returncode == 0, result.stderr
    assert (current / "ore-metronome.exe").read_bytes() == b"new-exe"
    assert (current / "settings.txt").read_text(encoding="utf-8") == "keep"
    assert not (current / "ore-metronome.exe.bak").exists()


def test_restores_previous_executable_when_staged_is_missing(tmp_path):
    current = tmp_path / "app"
    current.mkdir()
    (current / "ore-metronome.exe").write_bytes(b"old-exe")

    result = run_update_script(tmp_path, current, tmp_path / "missing")

    assert result.returncode == 1
    assert (current / "ore-metronome.exe").read_bytes() == b"old-exe"
    assert not (current / "ore-metronome.exe.bak").exists()


def test_waits_for_locked_executable_to_be_released(tmp_path):
    current = tmp_path / "app"
    current.mkdir()
    (current / "ore-metronome.exe").write_bytes(b"old-exe")
    staged = tmp_path / "staged" / "app"
    staged.mkdir(parents=True)
    (staged / "ore-metronome.exe").write_bytes(b"new-exe")

    lock = open(current / "ore-metronome.exe", "rb")
    try:
        process = start_update_script(tmp_path, current, staged)
        time.sleep(2)
    finally:
        lock.close()
    stdout, stderr = process.communicate(timeout=120)

    assert process.returncode == 0, stderr
    assert (current / "ore-metronome.exe").read_bytes() == b"new-exe"
