"""Manage project-local copies of reusable guide files."""

import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from ..core.errors import CommandError
from ..core.paths import CODEXMGR_HOME_SOURCE
from ..core.toml_io import plain_toml_value
from .sources import project_guides_dir, guides_source_root, safe_guide_path


@dataclass(frozen=True)
class GuideCopy:
    """One managed reusable guide file copy.

    Attributes:
        relative_path: POSIX path under the source and target guides roots.
        source: Source file under CODEXMGR_HOME/guides.
        target: Project-local target file under `.guides`.
    """

    relative_path: str
    source: Path
    target: Path


@dataclass(frozen=True)
class GuideCopyFile:
    """Expected content for one managed guide copy.

    Attributes:
        source: Canonical reusable guide file.
        path: Project-local target file.
        content: Expected bytes read from the source file.
        resource_kind: Resource family used for conflict validation.
    """

    source: Path
    path: Path
    content: bytes
    resource_kind: str = "guide"


def validate_guide_copy_targets(
    copies: list[GuideCopy],
    previous_lock: Mapping[str, Any],
    cwd: Path,
    codexmgr_home: Path,
) -> None:
    """Reject first-time copies over unmanaged target files.

    Args:
        copies: Current managed guide copies.
        previous_lock: Existing codexmgr lock data.
        cwd: Current project root used to rebind portable targets.
        codexmgr_home: Current manager home used to rebind portable sources.
    """
    previous = previous_guide_copies(previous_lock, cwd, codexmgr_home)
    for copy in copies:
        if copy.target.exists() and not copy.target.is_file():
            raise CommandError(f"Guide target is not a regular file: {copy.target}")
        if copy.relative_path not in previous and copy.target.exists():
            raise CommandError(f"Refusing to overwrite unmanaged guide file: {copy.target}")


def previous_guide_copies(
    previous_lock: Mapping[str, Any],
    cwd: Path,
    codexmgr_home: Path,
) -> dict[str, GuideCopy]:
    """Read managed guide-copy metadata from lock data.

    Args:
        previous_lock: Parsed .codex/codexmgr.lock data.
        cwd: Current project root used to rebind portable targets.
        codexmgr_home: Current manager home used to rebind portable sources.

    Returns:
        Previous guide copies keyed by relative path.
    """
    table = previous_lock.get("guides", {})
    if not isinstance(table, Mapping):
        raise CommandError("codexmgr.lock [guides] must be a table")
    raw_copies = plain_toml_value(table.get("copies", []))
    if not isinstance(raw_copies, list):
        raise CommandError("codexmgr.lock guides.copies must be a list")
    copies: dict[str, GuideCopy] = {}
    for raw_copy in raw_copies:
        copy = _copy_from_lock_entry(raw_copy, cwd, codexmgr_home)
        copies[copy.relative_path] = copy
    return copies


def obsolete_guide_copy_targets(
    previous_lock: Mapping[str, Any],
    current_copies: list[GuideCopy],
    cwd: Path,
    codexmgr_home: Path,
) -> list[Path]:
    """Return previous managed targets absent from current state.

    Args:
        previous_lock: Existing codexmgr lock data.
        current_copies: Current managed guide copies.
        cwd: Current project root used to rebind portable targets.
        codexmgr_home: Current manager home used to rebind portable sources.

    Returns:
        Sorted obsolete file targets.
    """
    current = {copy.relative_path for copy in current_copies}
    return sorted(
        copy.target
        for relative_path, copy in previous_guide_copies(
            previous_lock,
            cwd,
            codexmgr_home,
        ).items()
        if relative_path not in current
    )


def guide_copy_lock_entries(copies: list[GuideCopy]) -> list[dict[str, str]]:
    """Build lockfile entries for managed guide copies.

    Args:
        copies: Current managed guide copies.

    Returns:
        TOML-serializable lock entries.
    """
    return [
        {
            "relative_path": copy.relative_path,
            "source": CODEXMGR_HOME_SOURCE,
            "target": f".guides/{copy.relative_path}",
        }
        for copy in copies
    ]


def expected_guide_copy_files(copies: list[GuideCopy]) -> list[GuideCopyFile]:
    """Build expected bytes for managed guide copies.

    Args:
        copies: Current managed guide copies.

    Returns:
        Expected target file contents.
    """
    return [
        GuideCopyFile(copy.source, copy.target, copy.source.read_bytes())
        for copy in copies
    ]


def apply_guide_copy(copy: GuideCopy, skip_targets: set[Path] | None = None) -> None:
    """Copy one source guide file to the project-local target.

    Args:
        copy: Managed guide copy to refresh.
        skip_targets: Exact target files to preserve for this apply.
    """
    if skip_targets is not None and copy.target.absolute() in skip_targets:
        return
    copy.target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(copy.source, copy.target)


def remove_guide_copy_target(target: Path, root: Path) -> None:
    """Remove one previously managed guide file and empty parent directories.

    Args:
        target: Managed guide file target to remove.
        root: Actual project guide root bounding empty-directory cleanup.
    """
    if target.is_file():
        target.unlink()
    _prune_empty_dirs(target.parent, root)


def _copy_from_lock_entry(
    raw_copy: Any,
    cwd: Path,
    codexmgr_home: Path,
) -> GuideCopy:
    """Parse one guide copy lock entry.

    Args:
        raw_copy: Plain lock entry value.
        cwd: Current project root used to rebind the target.
        codexmgr_home: Current manager home used to rebind the source.

    Returns:
        Parsed guide copy.
    """
    if not isinstance(raw_copy, Mapping):
        raise CommandError("codexmgr.lock guides.copies entries must be tables")
    relative_path = raw_copy.get("relative_path")
    source = raw_copy.get("source")
    target = raw_copy.get("target")
    if (
        not isinstance(relative_path, str)
        or not isinstance(source, str)
        or not isinstance(target, str)
    ):
        raise CommandError(
            "codexmgr.lock guides.copies entries must include relative_path, source, and target"
        )
    portable_path = PurePosixPath(relative_path)
    if (
        relative_path in {"", ".", ".."}
        or "\\" in relative_path
        or portable_path.is_absolute()
        or portable_path.as_posix() != relative_path
        or any(part == ".." for part in portable_path.parts)
    ):
        raise CommandError(
            "codexmgr.lock guides.copies entries must use a safe relative_path"
        )
    return GuideCopy(
        relative_path,
        safe_guide_path(guides_source_root(codexmgr_home), relative_path),
        safe_guide_path(project_guides_dir(cwd), relative_path),
    )


def _prune_empty_dirs(path: Path, root: Path) -> None:
    """Remove empty `.guides` directories without touching unmanaged content.

    Args:
        path: Directory where pruning should begin.
        root: Project guide root; never prune above this directory.
    """
    current = path
    while current != root:
        if not _remove_empty_dir(current):
            return
        current = current.parent
    _remove_empty_dir(current)


def _remove_empty_dir(path: Path) -> bool:
    """Try to remove an empty directory.

    Args:
        path: Directory to remove when empty.

    Returns:
        True when the directory was removed.
    """
    try:
        path.rmdir()
        return True
    except OSError:
        return False
