import ctypes
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from ore_metronome.bootstrap import build_service
from ore_metronome.infrastructure.audio.beat_queue import BeatQueue
from ore_metronome.ui.controller import MetronomeController
from ore_metronome.ui.main_window import MainWindow

ICON_PATH = Path(__file__).resolve().parents[2] / "data" / "app_icon.png"
APP_USER_MODEL_ID = "ore-metronome"


def main() -> int:
    if sys.platform == "win32":
        # Without an explicit ID, Windows groups the taskbar button under python.exe.
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    beats = BeatQueue()
    service = build_service(beat_sink=beats)
    window = MainWindow(MetronomeController(service, beats))
    window.show()
    try:
        return app.exec()
    finally:
        service.stop()

if __name__ == "__main__":
    sys.exit(main())

