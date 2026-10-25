from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QSizePolicy, QWidget

DOT_SIZE = 28
DOT_GAP = 12

NORMAL_COLOR = QColor("#2A2A2A")
NORMAL_ACTIVE_COLOR = QColor("#F2F2F2")
DOWNBEAT_COLOR = QColor("#1F3D2C")
DOWNBEAT_ACTIVE_COLOR = QColor("#00E676")


class BeatIndicator(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._beats = 0
        self._accent_enabled = False
        self._active_beat: int | None = None
        self.setMinimumHeight(DOT_SIZE + 8)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_layout(self, beats: int, accent_enabled: bool) -> None:
        self._beats = beats
        self._accent_enabled = accent_enabled
        self._active_beat = None
        self.update()

    def set_active_beat(self, beat_index: int | None) -> None:
        self._active_beat = beat_index
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        top = (self.height() - DOT_SIZE) // 2
        left = (self.width() - self._total_width()) // 2
        for index in range(self._beats):
            painter.setBrush(self._color_for(index))
            x = left + index * (DOT_SIZE + DOT_GAP)
            painter.drawEllipse(x, top, DOT_SIZE, DOT_SIZE)
        painter.end()

    def _total_width(self) -> int:
        if self._beats == 0:
            return 0
        return self._beats * DOT_SIZE + (self._beats - 1) * DOT_GAP

    def _color_for(self, index: int) -> QColor:
        is_active = index == self._active_beat
        is_downbeat = self._accent_enabled and index == 0
        if is_downbeat:
            return DOWNBEAT_ACTIVE_COLOR if is_active else DOWNBEAT_COLOR
        return NORMAL_ACTIVE_COLOR if is_active else NORMAL_COLOR