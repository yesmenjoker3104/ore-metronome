import sys

from PySide6.QtWidgets import QApplication

from ore_metronome.bootstrap import build_service
from ore_metronome.infrastructure.audio.beat_queue import BeatQueue
from ore_metronome.ui.controller import MetronomeController
from ore_metronome.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
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

