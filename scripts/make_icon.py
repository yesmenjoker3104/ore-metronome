"""data/app_icon.png から、exe・ウィンドウ用の icon.ico を作る。

ICO には PNG 形式の画像を複数サイズ入れる（Windows Vista 以降で使われる形式）。
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, Qt
from PySide6.QtGui import QImage

ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data" / "app_icon.png"
OUTPUT_PATH = ROOT / "src" / "ore_metronome" / "assets" / "icon.ico"
SIZES = (16, 24, 32, 48, 64, 128, 256)


def encode_png(image: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise SystemExit("Failed to encode PNG")
    return bytes(buffer.data())


def build_ico(source: QImage) -> bytes:
    images: list[bytes] = []
    for size in SIZES:
        scaled = source.scaled(
            size,
            size,
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        ).convertToFormat(QImage.Format.Format_RGBA8888)
        images.append(encode_png(scaled))

    header = struct.pack("<HHH", 0, 1, len(SIZES))
    offset = len(header) + 16 * len(SIZES)
    directory = bytearray()
    for size, data in zip(SIZES, images, strict=True):
        # ICO のサイズ欄は 1 バイトなので、256 は 0 で表す。
        dimension = 0 if size == 256 else size
        directory += struct.pack("<BBBBHHII", dimension, dimension, 0, 0, 1, 32, len(data), offset)
        offset += len(data)
    return header + bytes(directory) + b"".join(images)


def main() -> int:
    source = QImage(str(SOURCE_PATH))
    if source.isNull():
        print(f"Cannot load {SOURCE_PATH}", file=sys.stderr)
        return 1
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_bytes(build_ico(source))
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
