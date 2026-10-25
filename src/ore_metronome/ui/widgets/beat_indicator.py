from collections.abc import Sequence

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ore_metronome.domain.models import BeatLevel

DOT_SIZE = 56
DOT_GAP = 24
DOT_PITCH = DOT_SIZE + DOT_GAP
SILENT_RING_WIDTH = 4

# アクセントは濃く、アクセントなしは薄く、無音は輪郭だけで示す。
ACCENT_COLOR = QColor("#1F7A4A")
ACCENT_ACTIVE_COLOR = QColor("#00E676")
NORMAL_COLOR = QColor("#2A2A2A")
NORMAL_ACTIVE_COLOR = QColor("#F2F2F2")
SILENT_COLOR = QColor("#3A3A3A")
SILENT_ACTIVE_COLOR = QColor("#F2F2F2")


class BeatIndicator(QWidget):
    beat_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._levels: tuple[BeatLevel, ...] = ()
        self._active_beat: int | None = None
        self._update_minimum_height()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_layout(self, levels: Sequence[BeatLevel]) -> None:
        self._levels = tuple(levels)
        self._update_minimum_height()
        self.update()

    def resizeEvent(self, event) -> None:
        self._update_minimum_height()
        super().resizeEvent(event)

    def set_active_beat(self, beat_index: int | None) -> None:
        self._active_beat = beat_index
        self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            beat_index = self._beat_at(event.position().toPoint())
            if beat_index is not None:
                self.beat_clicked.emit(beat_index)
        super().mousePressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        columns = self._columns()
        for index, level in enumerate(self._levels):
            rect = self._dot_rect(index, columns)
            self._paint_dot(painter, rect, level, index == self._active_beat)
        painter.end()

    def _paint_dot(
        self,
        painter: QPainter,
        rect: QRect,
        level: BeatLevel,
        is_active: bool,
    ) -> None:
        if level is BeatLevel.SILENT:
            color = SILENT_ACTIVE_COLOR if is_active else SILENT_COLOR
            painter.setPen(QPen(color, SILENT_RING_WIDTH))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            inset = SILENT_RING_WIDTH // 2
            painter.drawEllipse(rect.adjusted(inset, inset, -inset, -inset))
            return

        painter.setPen(Qt.PenStyle.NoPen)
        if level is BeatLevel.ACCENT:
            color = ACCENT_ACTIVE_COLOR if is_active else ACCENT_COLOR
        else:
            color = NORMAL_ACTIVE_COLOR if is_active else NORMAL_COLOR
        painter.setBrush(color)
        painter.drawEllipse(rect)

    def _dot_rect(self, index: int, columns: int) -> QRect:
        beats = len(self._levels)
        rows = self._rows(columns)
        top = (self.height() - self._content_height(rows)) // 2
        row, column = divmod(index, columns)
        row_count = min(columns, beats - row * columns)
        left = (self.width() - self._row_width(row_count)) // 2
        return QRect(left + column * DOT_PITCH, top + row * DOT_PITCH, DOT_SIZE, DOT_SIZE)

    def _beat_at(self, point: QPoint) -> int | None:
        columns = self._columns()
        for index in range(len(self._levels)):
            if self._dot_rect(index, columns).contains(point):
                return index
        return None

    def _columns(self) -> int:
        # Fit as many dots as the current width allows, at least one.
        return max(1, (self.width() + DOT_GAP) // DOT_PITCH)

    def _rows(self, columns: int) -> int:
        beats = len(self._levels)
        if beats == 0:
            return 1
        return -(-beats // columns)

    def _content_height(self, rows: int) -> int:
        return rows * DOT_SIZE + (rows - 1) * DOT_GAP

    def _row_width(self, count: int) -> int:
        return count * DOT_SIZE + (count - 1) * DOT_GAP

    def _update_minimum_height(self) -> None:
        rows = self._rows(self._columns())
        self.setMinimumHeight(self._content_height(rows) + 8)
