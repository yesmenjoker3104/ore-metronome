import json
from pathlib import Path
from typing import Any

from ore_metronome.domain.setlist import Playlist, PlaylistItem, PlaylistLibrary
from ore_metronome.infrastructure.persistence.json_file import write_json_atomically
from ore_metronome.infrastructure.persistence.settings_repository import (
    SettingsDataError,
    SettingsRepository,
)

CURRENT_SCHEMA_VERSION = 2
LEGACY_SCHEMA_VERSION = 1
LEGACY_PLAYLIST_NAME = "デフォルト"


class SetlistDataError(RuntimeError):
    """Raised when a saved playlist cannot be read or decoded."""


class SetlistRepository:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def load(self) -> PlaylistLibrary:
        if not self._path.exists():
            return PlaylistLibrary()
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise TypeError("playlist must be an object")
            version = data.get("schema_version")
            if version == LEGACY_SCHEMA_VERSION:
                return self._load_legacy(data)
            if version != CURRENT_SCHEMA_VERSION:
                raise ValueError(f"Unsupported schema version: {version}")
            raw_playlists = data["playlists"]
            if not isinstance(raw_playlists, list):
                raise TypeError("playlists must be a list")
            return PlaylistLibrary(tuple(self._decode_playlist(raw) for raw in raw_playlists))
        except (OSError, json.JSONDecodeError) as exc:
            raise SetlistDataError(f"Could not read playlist: {self._path}") from exc
        except (KeyError, TypeError, ValueError, SettingsDataError) as exc:
            raise SetlistDataError(f"Invalid playlist: {self._path}") from exc

    def save(self, library: PlaylistLibrary) -> None:
        data: dict[str, Any] = {
            "schema_version": CURRENT_SCHEMA_VERSION,
            "playlists": [
                {
                    "name": playlist.name,
                    "items": [self._encode_item(item) for item in playlist.items],
                }
                for playlist in library.playlists
            ],
        }
        write_json_atomically(self._path, data)

    @classmethod
    def _load_legacy(cls, data: dict[str, Any]) -> PlaylistLibrary:
        # 旧形式は曲だけの単一リストだったため、それを既定のプレイリスト 1 件として読む。
        raw_items = data["items"]
        if not isinstance(raw_items, list):
            raise TypeError("items must be a list")
        items = tuple(cls._decode_item(raw) for raw in raw_items)
        if not items:
            return PlaylistLibrary()
        return PlaylistLibrary((Playlist(LEGACY_PLAYLIST_NAME, items),))

    @classmethod
    def _decode_playlist(cls, raw: Any) -> Playlist:
        if not isinstance(raw, dict):
            raise TypeError("playlist must be an object")
        name = raw["name"]
        raw_items = raw["items"]
        if not isinstance(name, str) or not isinstance(raw_items, list):
            raise TypeError("invalid playlist")
        return Playlist(name, tuple(cls._decode_item(item) for item in raw_items))

    @staticmethod
    def _encode_item(item: PlaylistItem) -> dict[str, Any]:
        return {
            "name": item.name,
            "settings": SettingsRepository.encode_settings(item.settings),
        }

    @staticmethod
    def _decode_item(raw: Any) -> PlaylistItem:
        if not isinstance(raw, dict):
            raise TypeError("playlist item must be an object")
        name = raw["name"]
        settings_data = raw["settings"]
        if not isinstance(name, str) or not isinstance(settings_data, dict):
            raise TypeError("invalid playlist item")
        return PlaylistItem(name, SettingsRepository.decode_settings(settings_data))
