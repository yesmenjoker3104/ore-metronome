from enum import StrEnum


class PlaylistFontSize(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


PLAYLIST_FONT_POINT_SIZES = {
    PlaylistFontSize.SMALL: 16.0,
    PlaylistFontSize.MEDIUM: 20.0,
    PlaylistFontSize.LARGE: 24.0,
}
