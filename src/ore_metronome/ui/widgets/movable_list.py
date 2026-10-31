from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QDropEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from ore_metronome.ui.icons import set_button_icon
from ore_metronome.ui.theme import ACCENT_COLOR

MOVE_BUTTON_WIDTH = 30
MOVE_BUTTON_HEIGHT = 26
MOVE_ICON_SIZE = 16


class MovableList(QListWidget):
    """ドラッグ＆ドロップと、行に埋め込んだ ↑↓ ボタンで順番を変えられるリスト。"""

    move_requested = Signal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(True)

    def dropEvent(self, event: QDropEvent) -> None:
        # Qt 標準の移動は項目を作り直すため、埋め込みの行ウィジェットが消える。
        # 移動は自前で行い、ボタンと同じ move_requested で通知する。
        source = self.currentRow()
        index = self.indexAt(event.position().toPoint())
        target = index.row() if index.isValid() else self.count() - 1
        event.setDropAction(Qt.DropAction.IgnoreAction)
        event.accept()
        if source >= 0 and target >= 0 and source != target:
            self.move_requested.emit(source, target)

    def add_row(self, text: str, highlight: bool = False) -> None:
        item = QListWidgetItem()
        self.addItem(item)
        row = self._row_widget(text, item, highlight)
        # 幅は表示領域に合わせる。本文の幅を要求すると、行がスクロールバーに重なる。
        item.setSizeHint(QSize(0, row.sizeHint().height()))
        self.setItemWidget(item, row)

    def _row_widget(self, text: str, item: QListWidgetItem, highlight: bool) -> QWidget:
        row = QWidget()
        row.setObjectName("playlistRow")
        # 行の背景を透明にして、リストの選択表示が隠れないようにする。
        row.setStyleSheet("QWidget#playlistRow, QLabel { background: transparent; }")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(6, 0, 2, 0)
        layout.setSpacing(4)
        label = QLabel(text)
        label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        if highlight:
            label.setObjectName("currentSong")
        layout.addWidget(label, 1)
        layout.addWidget(self._move_button("arrow_up", "上へ", item, -1))
        layout.addWidget(self._move_button("arrow_down", "下へ", item, 1))
        return row

    def _move_button(
        self, icon: str, tooltip: str, item: QListWidgetItem, delta: int
    ) -> QPushButton:
        button = QPushButton()
        set_button_icon(button, icon, ACCENT_COLOR)
        button.setIconSize(QSize(MOVE_ICON_SIZE, MOVE_ICON_SIZE))
        button.setToolTip(tooltip)
        button.setAccessibleName(tooltip)
        button.setFixedSize(MOVE_BUTTON_WIDTH, MOVE_BUTTON_HEIGHT)
        button.setStyleSheet("QPushButton { padding: 0px; border-radius: 4px; }")
        button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        button.clicked.connect(lambda: self._request_move(item, delta))
        return button

    def _request_move(self, item: QListWidgetItem, delta: int) -> None:
        row = self.row(item)
        new_row = row + delta
        if 0 <= new_row < self.count():
            self.move_requested.emit(row, new_row)
