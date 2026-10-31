from collections.abc import Sequence

from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from ore_metronome.domain.meter import MAX_NUMERATOR
from ore_metronome.domain.models import BeatLevel

DOT_SIZE = 40
DOT_GAP = 14
DOT_PITCH = DOT_SIZE + DOT_GAP
SILENT_RING_WIDTH = 4
BEAT_ROWS = 3
# 最大拍数を BEAT_ROWS 行に収める列数（16 拍なら 6 列）。
BEAT_COLUMNS = -(-MAX_NUMERATOR // BEAT_ROWS)
TOP_MARGIN = 4

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
        self.setMinimumHeight(self._content_height(BEAT_ROWS) + TOP_MARGIN * 2)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_layout(self, levels: Sequence[BeatLevel]) -> None:
        self._levels = tuple(levels)
        self.update()

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
        for index, level in enumerate(self._levels):
            rect = self._dot_rect(index)
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

    def _dot_rect(self, index: int) -> QRect:
        row, column = divmod(index, BEAT_COLUMNS)
        beats = len(self._levels)
        rows_used = self._rows_used(beats)
        # 使っている行のブロックを、表示領域の縦の中央に置く。
        offset = (self.height() - self._content_height(rows_used)) // 2
        top = offset + row * DOT_PITCH
        # 各行に並ぶ点の数に合わせて、その行を横の中央に置く。
        dots_in_row = min(BEAT_COLUMNS, beats - row * BEAT_COLUMNS)
        left = (self.width() - self._span(dots_in_row)) // 2 + column * DOT_PITCH
        return QRect(left, top, DOT_SIZE, DOT_SIZE)

    def _beat_at(self, point: QPoint) -> int | None:
        for index in range(len(self._levels)):
            if self._dot_rect(index).contains(point):
                return index
        return None

    def _rows_used(self, beats: int) -> int:
        return max(1, -(-beats // BEAT_COLUMNS))

    def _content_height(self, rows: int) -> int:
        return rows * DOT_SIZE + (rows - 1) * DOT_GAP

    def _span(self, count: int) -> int:
        return count * DOT_SIZE + (count - 1) * DOT_GAP
