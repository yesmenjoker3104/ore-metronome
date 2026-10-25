"""exe のファイルプロパティに出す version_info.txt を version.py から作る。"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "src" / "ore_metronome" / "version.py"
OUTPUT_FILE = ROOT / "build" / "version_info.txt"
PRODUCT_NAME = "Ore Metronome"
EXECUTABLE_NAME = "ore-metronome.exe"


def read_version() -> str:
    match = re.search(r'__version__\s*=\s*"([^"]+)"', VERSION_FILE.read_text(encoding="utf-8"))
    if match is None:
        raise SystemExit(f"__version__ not found in {VERSION_FILE}")
    return match.group(1)


def version_tuple(version: str) -> tuple[int, int, int, int]:
    numbers = [int(part) for part in version.split(".")]
    if len(numbers) > 4:
        raise SystemExit(f"Unsupported version format: {version}")
    numbers += [0] * (4 - len(numbers))
    return (numbers[0], numbers[1], numbers[2], numbers[3])


def render(version: str) -> str:
    numbers = version_tuple(version)
    return f"""# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={numbers},
    prodvers={numbers},
    mask=0x3F,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'041104B0',
          [
            StringStruct(u'CompanyName', u''),
            StringStruct(u'FileDescription', u'{PRODUCT_NAME}'),
            StringStruct(u'FileVersion', u'{version}'),
            StringStruct(u'InternalName', u'ore-metronome'),
            StringStruct(u'OriginalFilename', u'{EXECUTABLE_NAME}'),
            StringStruct(u'ProductName', u'{PRODUCT_NAME}'),
            StringStruct(u'ProductVersion', u'{version}')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [1041, 1200])])
  ]
)
"""


def main() -> None:
    version = read_version()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(render(version), encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE} for version {version}")


if __name__ == "__main__":
    main()
