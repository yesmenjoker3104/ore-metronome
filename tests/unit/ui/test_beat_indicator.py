import pytest
from PySide6.QtCore import QPoint, QSize, Qt

from ore_metronome.domain.models import BeatLevel
from ore_metronome.ui.widgets.beat_indicator import (
    BEAT_ROWS,
    DOT_GAP,
    DOT_PITCH,
    DOT_SIZE,
    TOP_MARGIN,
    BeatIndicator,
)

WIDTH = 496


def _reserved_height() -> int:
    return BEAT_ROWS * DOT_SIZE + (BEAT_ROWS - 1) * DOT_GAP + TOP_MARGIN * 2


def _make_indicator(qtbot, beats: int) -> tuple[BeatIndicator, list[int]]:
    indicator = BeatIndicator()
    qtbot.addWidget(indicator)
    indicator.show()
    indicator.resize(QSize(WIDTH, _reserved_height()))
    indicator.set_layout([BeatLevel.NORMAL] * beats)
    clicked: list[int] = []
    indicator.beat_clicked.connect(clicked.append)
    return indicator, clicked


def test_height_is_reserved_for_the_maximum_number_of_rows(qtbot):
    indicator = BeatIndicator()
    qtbot.addWidget(indicator)

    for beats in (1, 4, 16):
        indicator.set_layout([BeatLevel.NORMAL] * beats)
        assert indicator.minimumHeight() == _reserved_height()
        assert indicator.maximumHeight() == _reserved_height()


def test_clicking_a_dot_emits_its_beat_index(qtbot):
    indicator, clicked = _make_indicator(qtbot, beats=4)

    qtbot.mouseClick(
        indicator, Qt.MouseButton.LeftButton, pos=indicator._dot_rect(0).center()
    )
    qtbot.mouseClick(
        indicator, Qt.MouseButton.LeftButton, pos=indicator._dot_rect(3).center()
    )

    assert clicked == [0, 3]


def test_clicking_between_dots_emits_nothing(qtbot):
    indicator, clicked = _make_indicator(qtbot, beats=4)
    gap_center = (indicator._dot_rect(0).right() + indicator._dot_rect(1).left()) // 2 + 1
    y = indicator._dot_rect(0).center().y()

    qtbot.mouseClick(indicator, Qt.MouseButton.LeftButton, pos=QPoint(gap_center, y))

    assert clicked == []


def test_last_beats_of_sixteen_are_clickable_inside_reserved_height(qtbot):
    indicator, clicked = _make_indicator(qtbot, beats=16)

    # 16 beats fill rows of 6, 6, 4. The last row of 4 is centered.
    qtbot.mouseClick(
        indicator, Qt.MouseButton.LeftButton, pos=indicator._dot_rect(14).center()
    )
    qtbot.mouseClick(
        indicator, Qt.MouseButton.LeftButton, pos=indicator._dot_rect(15).center()
    )

    assert clicked == [14, 15]
    assert TOP_MARGIN + 2 * DOT_PITCH + DOT_SIZE <= _reserved_height()


@pytest.mark.parametrize("beats", [1, 2, 4, 5, 6, 7, 11, 16])
def test_each_row_is_centered_horizontally(qtbot, beats):
    indicator, _ = _make_indicator(qtbot, beats=beats)
    rects = [indicator._dot_rect(i) for i in range(beats)]

    for row_top in sorted({rect.top() for rect in rects}):
        row = [rect for rect in rects if rect.top() == row_top]
        left_margin = min(rect.left() for rect in row)
        right_margin = indicator.width() - max(rect.right() + 1 for rect in row)
        assert left_margin == right_margin

