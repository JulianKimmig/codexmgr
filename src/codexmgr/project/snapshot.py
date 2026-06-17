"""Snapshot and restore project paths touched by ephemeral generated state."""

import shutil
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PathSnapshot:
    """In-memory snapshot of one filesystem path.

    Attributes:
        path: Filesystem path that was captured.
        existed: Whether the path existed at capture time.
        is_dir: Whether the original path was a directory.
        files: File contents keyed by relative POSIX path for directories, or
            by an empty key for single files.
        directories: Directory entries keyed by relative POSIX path.
    """

    path: Path
    existed: bool
    is_dir: bool
    files: dict[str, bytes]
    directories: list[str]


def snapshot_paths(paths: list[Path]) -> list[PathSnapshot]:
    """Capture unique paths before an ephemeral write.

    Args:
        paths: Filesystem paths that may be written or removed.

    Returns:
        Snapshots for each unique top-level path.
    """
    return [_snapshot_path(path) for path in _top_level_paths(paths)]


def restore_snapshots(snapshots: list[PathSnapshot]) -> None:
    """Restore captured paths to their previous state.

    Args:
        snapshots: Snapshots returned by ``snapshot_paths``.

    Returns:
        None. Filesystem paths are restored in place.
    """
    for snapshot in snapshots:
        _restore_snapshot(snapshot)


def _snapshot_path(path: Path) -> PathSnapshot:
    """Capture one path.

    Args:
        path: Filesystem path to capture.

    Returns:
        Snapshot data for the path.
    """
    if not path.exists():
        return PathSnapshot(path, existed=False, is_dir=False, files={}, directories=[])
    if path.is_dir():
        files = {
            child.relative_to(path).as_posix(): child.read_bytes()
            for child in sorted(path.rglob("*"))
            if child.is_file()
        }
        directories = [
            child.relative_to(path).as_posix()
            for child in sorted(path.rglob("*"))
            if child.is_dir()
        ]
        return PathSnapshot(path, True, True, files, directories)
    return PathSnapshot(path, True, False, {"": path.read_bytes()}, [])


def _restore_snapshot(snapshot: PathSnapshot) -> None:
    """Restore one captured path.

    Args:
        snapshot: Path snapshot to restore.
    """
    if not snapshot.existed:
        _remove_path(snapshot.path)
        return
    _remove_path(snapshot.path)
    if snapshot.is_dir:
        snapshot.path.mkdir(parents=True, exist_ok=True)
        for directory in snapshot.directories:
            (snapshot.path / directory).mkdir(parents=True, exist_ok=True)
        for relative_path, content in snapshot.files.items():
            target = snapshot.path / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        return
    snapshot.path.parent.mkdir(parents=True, exist_ok=True)
    snapshot.path.write_bytes(snapshot.files[""])


def _remove_path(path: Path) -> None:
    """Remove a file or directory if it exists.

    Args:
        path: Filesystem path to remove.
    """
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def _top_level_paths(paths: list[Path]) -> list[Path]:
    """Remove duplicate and nested paths from a snapshot request.

    Args:
        paths: Candidate paths.

    Returns:
        Sorted unique paths, omitting children whose parent is also captured.
    """
    resolved = sorted({path.resolve() for path in paths}, key=lambda item: len(item.parts))
    top_level: list[Path] = []
    for path in resolved:
        if not any(_is_relative_to(path, parent) for parent in top_level):
            top_level.append(path)
    return top_level


def _is_relative_to(path: Path, parent: Path) -> bool:
    """Return whether a path is contained by a parent path.

    Args:
        path: Candidate child path.
        parent: Candidate parent path.

    Returns:
        True when ``path`` is equal to or under ``parent``.
    """
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False
