import os
import subprocess
import sys
import tempfile
from pathlib import Path


def update_script_path() -> Path:
    return Path(__file__).with_name("apply_update.ps1")


def start_update_process(
    staged_application: Path,
    current_application: Path,
    update_script: Path,
) -> None:
    """Starts the replacement script. It waits for this process to exit before replacing files."""
    if sys.platform != "win32":
        raise RuntimeError("In-app updates are supported on Windows only")
    environment = os.environ.copy()
    environment["ORE_METRONOME_PARENT_PID"] = str(os.getpid())
    subprocess.Popen(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(update_script),
            "-CurrentApplication",
            str(current_application),
            "-StagedApplication",
            str(staged_application),
        ],
        env=environment,
        cwd=tempfile.gettempdir(),
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
    )
