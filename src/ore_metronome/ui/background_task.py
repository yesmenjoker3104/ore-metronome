from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QThread, Signal


class BackgroundTask(QThread):
    """Runs blocking work off the UI thread and reports the outcome via signals."""

    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, work: Callable[[], Any]) -> None:
        super().__init__()
        self._work = work

    def run(self) -> None:
        try:
            result = self._work()
        except Exception as error:
            self.failed.emit(str(error) or type(error).__name__)
            return
        self.succeeded.emit(result)
