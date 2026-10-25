import shutil
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

EXECUTABLE_NAME = "ore-metronome.exe"


def extract_application(archive_path: Path, staging_directory: Path) -> Path:
    """Extracts the single application folder from the archive and returns its path.

    All entries are checked before anything is written, so a bad archive leaves no files behind.
    """
    with ZipFile(archive_path) as archive:
        infos = archive.infolist()
        for info in infos:
            _check_entry_name(info.filename)

        roots = {PurePosixPath(info.filename).parts[0] for info in infos if info.filename}
        if len(roots) != 1:
            raise RuntimeError("Update archive must contain one application directory")
        root = next(iter(roots))
        if f"{root}/{EXECUTABLE_NAME}" not in {info.filename for info in infos}:
            raise RuntimeError(f"Update archive does not contain {EXECUTABLE_NAME}")

        if staging_directory.exists():
            shutil.rmtree(staging_directory)
        destination_root = staging_directory.resolve()
        destination_root.mkdir(parents=True)

        for info in infos:
            target = (destination_root / info.filename).resolve()
            if not target.is_relative_to(destination_root):
                raise RuntimeError("Update archive contains an unsafe path")
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)

    return destination_root / root


def _check_entry_name(name: str) -> None:
    if not name or name.startswith(("/", "\\")) or "\\" in name or ":" in name:
        raise RuntimeError("Update archive contains an unsafe path")
    if ".." in PurePosixPath(name).parts:
        raise RuntimeError("Update archive contains an unsafe path")
