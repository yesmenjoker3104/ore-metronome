from PySide6.QtCore import QPoint, QSize, Qt

from ore_metronome.domain.models import BeatLevel
from ore_metronome.ui.widgets.beat_indicator import DOT_GAP, DOT_SIZE, BeatIndicator


def _height_for_rows(rows: int) -> int:
    return rows * DOT_SIZE + (rows - 1) * DOT_GAP + 8


def test_indicator_stays_one_row_when_all_beats_fit(qtbot):
    indicator = BeatIndicator()
    qtbot.addWidget(indicator)
    indicator.resize(QSize(496, 300))

    indicator.set_layout([BeatLevel.ACCENT, BeatLevel.NORMAL, BeatLevel.NORMAL, BeatLevel.NORMAL])

    assert indicator.minimumHeight() == _height_for_rows(1)


def test_indicator_wraps_into_rows_when_beats_do_not_fit(qtbot):
    indicator = BeatIndicator()
    qtbot.addWidget(indicator)
    indicator.resize(QSize(496, 300))

    indicator.set_layout([BeatLevel.NORMAL] * 16)

    assert indicator.minimumHeight() == _height_for_rows(3)


def test_clicking_a_dot_emits_its_beat_index(qtbot):
    indicator = BeatIndicator()
    qtbot.addWidget(indicator)
    indicator.show()
    indicator.resize(QSize(496, 300))
    indicator.set_layout([BeatLevel.NORMAL] * 4)
    clicked: list[int] = []
    indicator.beat_clicked.connect(clicked.append)

    # 4 dots in one row: the second dot is centered near x=208, y=150.
    qtbot.mouseClick(indicator, Qt.MouseButton.LeftButton, pos=QPoint(208, 150))

    assert clicked == [1]


def test_clicking_between_dots_emits_nothing(qtbot):
    indicator = BeatIndicator()
    qtbot.addWidget(indicator)
    indicator.show()
    indicator.resize(QSize(496, 300))
    indicator.set_layout([BeatLevel.NORMAL] * 4)
    clicked: list[int] = []
    indicator.beat_clicked.connect(clicked.append)

    qtbot.mouseClick(indicator, Qt.MouseButton.LeftButton, pos=QPoint(168, 150))

    assert clicked == []
