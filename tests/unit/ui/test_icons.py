import pytest
from PySide6.QtGui import QColor, QIcon
from PySide6.QtWidgets import QPushButton

from ore_metronome.ui.icons import ICON_PIXEL_SIZE, _icons_dir, set_button_icon, svg_icon
from ore_metronome.ui.theme import ACCENT_COLOR, DISABLED_COLOR

USED_ICON_NAMES = [
    "play",
    "stop",
    "tap",
    "plus",
    "minus",
    "arrow_up",
    "arrow_down",
    "update",
    "delete",
    "rename",
    "close",
    "practice",
    "playlist",
]


@pytest.mark.parametrize("name", USED_ICON_NAMES)
def test_used_icon_file_exists_and_renders(qapp, name):
    assert (_icons_dir() / f"{name}.svg").is_file()
    assert not svg_icon(name).isNull()


def test_every_svg_in_icons_dir_is_used_or_listed():
    on_disk = {path.stem for path in _icons_dir().glob("*.svg")}
    assert on_disk == set(USED_ICON_NAMES)


def test_svg_files_have_no_hardcoded_colour():
    for path in _icons_dir().glob("*.svg"):
        text = path.read_text(encoding="utf-8")
        assert "currentColor" in text, path.name
        assert "#" not in text, path.name


def test_set_button_icon_sets_icon_and_size(qapp):
    button = QPushButton("テスト")

    set_button_icon(button, "plus")

    assert not button.icon().isNull()
    assert button.iconSize().width() == 24
    assert button.iconSize().height() == 24


def test_disabled_icon_uses_dim_accent_not_grey(qapp):
    icon = svg_icon("delete", ACCENT_COLOR)

    image = icon.pixmap(ICON_PIXEL_SIZE, ICON_PIXEL_SIZE, QIcon.Mode.Disabled).toImage()
    opaque_colours = {
        image.pixelColor(x, y).name()
        for x in range(image.width())
        for y in range(image.height())
        if image.pixelColor(x, y).alpha() == 255
    }

    assert opaque_colours == {QColor(DISABLED_COLOR).name()}
