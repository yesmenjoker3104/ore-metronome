"""assets/icons の SVG を、テーマ色で描いた QIcon にして読み込む。"""

import sys
from pathlib import Path

from PySide6.QtCore import QByteArray, QSize, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QPushButton

from ore_metronome.ui.theme import DISABLED_COLOR, TEXT_COLOR

ICON_SIZE = 24
ICON_PIXEL_SIZE = ICON_SIZE * 4


def _icons_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "ore_metronome" / "assets" / "icons"  # type: ignore[attr-defined]
    return Path(__file__).resolve().parents[1] / "assets" / "icons"


def _render(name: str, color: str) -> QPixmap:
    # SVG 内の currentColor を指定色に置き換えてから描く。高解像度でも崩れないよう4倍で描く。
    source = (_icons_dir() / f"{name}.svg").read_text(encoding="utf-8")
    renderer = QSvgRenderer(QByteArray(source.replace("currentColor", color).encode("utf-8")))
    pixmap = QPixmap(QSize(ICON_PIXEL_SIZE, ICON_PIXEL_SIZE))
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap


def svg_icon(name: str, color: str = TEXT_COLOR) -> QIcon:
    icon = QIcon(_render(name, color))
    # Qt の自動灰色化を避け、無効時も緑系で描く。
    icon.addPixmap(_render(name, DISABLED_COLOR), QIcon.Mode.Disabled)
    return icon


def set_button_icon(button: QPushButton, name: str, color: str = TEXT_COLOR) -> None:
    button.setIcon(svg_icon(name, color))
    button.setIconSize(QSize(ICON_SIZE, ICON_SIZE))
