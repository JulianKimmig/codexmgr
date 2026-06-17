"""Manage project-local copies of codexmgr-home hook bundle files."""

import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.errors import CommandError
from ..core.toml_io import plain_toml_value


@dataclass(frozen=True)
class HookCopy:
    """A managed hook bundle directory copy.

    Attributes:
        name: Bare hook bundle name.
        source: Source hook directory under CODEXMGR_HOME.
        target: Project-local .codex hook directory.
    """

    name: str
    source: Path
    target: Path


@dataclass(frozen=True)
class HookCopyFile:
    """Expected file inside a managed hook copy.

    Attributes:
        path: Project-local copied file path.
        content: Expected byte content from the source file.
    """

    path: Path
    content: bytes


def validate_hook_copy_targets(
    copies: list[HookCopy],
    previous_lock: Mapping[str, Any],
) -> None:
    """Reject first-time copies over unmanaged target folders.

    Args:
        copies: Current managed hook copies to create or refresh.
        previous_lock: Previous codexmgr lock data.
    """
    previous = previous_hook_copies(previous_lock)
    for copy in copies:
        if copy.name not in previous and copy.target.exists():
            raise CommandError(f"Refusing to overwrite unmanaged hook copy: {copy.target}")


def previous_hook_copies(previous_lock: Mapping[str, Any]) -> dict[str, HookCopy]:
    """Read managed hook-copy metadata from previous lock data.

    Args:
        previous_lock: Parsed .codex/codexmgr.lock data.

    Returns:
        Previous managed hook copies keyed by hook bundle name.
    """
    raw_copies = plain_toml_value(previous_lock.get("hooks", {}).get("copies", []))
    if not isinstance(raw_copies, list):
        raise CommandError("codexmgr.lock hooks.copies must be a list")
    copies: dict[str, HookCopy] = {}
    for raw_copy in raw_copies:
        copy = _copy_from_lock_entry(raw_copy)
        copies[copy.name] = copy
    return copies


def obsolete_hook_copy_targets(
    previous_lock: Mapping[str, Any],
    current_copies: list[HookCopy],
) -> list[Path]:
    """Return previous managed hook copy targets absent from current state.

    Args:
        previous_lock: Previous codexmgr lock data.
        current_copies: Current managed hook copies.

    Returns:
        Sorted target directories to remove.
    """
    current_names = {copy.name for copy in current_copies}
    return sorted(
        copy.target
        for name, copy in previous_hook_copies(previous_lock).items()
        if name not in current_names
    )


def hook_copy_lock_entries(copies: list[HookCopy]) -> list[dict[str, str]]:
    """Build lockfile entries for managed hook copies.

    Args:
        copies: Current managed hook copies.

    Returns:
        Lockfile table entries.
    """
    return [
        {
            "name": copy.name,
            "source": str(copy.source.resolve()),
            "target": str(copy.target.resolve()),
        }
        for copy in copies
    ]


def expected_hook_copy_files(copies: list[HookCopy]) -> list[HookCopyFile]:
    """Build expected file contents for managed hook copies.

    Args:
        copies: Current managed hook copies.

    Returns:
        Expected copied files in stable order.
    """
    files: list[HookCopyFile] = []
    for copy in copies:
        for source_file in source_hook_files(copy.source):
            target_file = copy.target / source_file.relative_to(copy.source)
            files.append(HookCopyFile(target_file, source_file.read_bytes()))
    return files


def apply_hook_copy(copy: HookCopy) -> None:
    """Overlay-copy one managed hook directory.

    Args:
        copy: Managed hook copy to refresh.
    """
    for source_dir in _source_dirs(copy.source):
        target_dir = copy.target / source_dir.relative_to(copy.source)
        target_dir.mkdir(parents=True, exist_ok=True)
    for source_file in source_hook_files(copy.source):
        target_file = copy.target / source_file.relative_to(copy.source)
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target_file)


def remove_hook_copy_target(target: Path) -> None:
    """Remove a previously managed hook copy target.

    Args:
        target: Project-local copied hook path to remove.
    """
    if not target.exists():
        return
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()


def has_hook_copy_files(source: Path) -> bool:
    """Return whether a source hook bundle has support files to copy.

    Args:
        source: Source hook bundle directory.

    Returns:
        True when the source has files other than its root hooks.json.
    """
    return bool(source_hook_files(source))


def source_hook_files(source: Path) -> list[Path]:
    """Return source files that should be copied into the project.

    Args:
        source: Source hook bundle directory.

    Returns:
        Sorted source file paths excluding the root hooks.json.
    """
    config_file = source / "hooks.json"
    return sorted(
        path
        for path in source.rglob("*")
        if path.is_file() and path.resolve() != config_file.resolve()
    )


def _copy_from_lock_entry(raw_copy: Any) -> HookCopy:
    """Parse one hook-copy lock entry.

    Args:
        raw_copy: Plain lock entry value.

    Returns:
        Parsed managed hook copy.
    """
    if not isinstance(raw_copy, Mapping):
        raise CommandError("codexmgr.lock hooks.copies entries must be tables")
    name = raw_copy.get("name")
    source = raw_copy.get("source")
    target = raw_copy.get("target")
    if not isinstance(name, str) or not isinstance(source, str) or not isinstance(target, str):
        raise CommandError("codexmgr.lock hooks.copies entries must include name, source, and target")
    return HookCopy(name, Path(source), Path(target))


def _source_dirs(source: Path) -> list[Path]:
    """Return source directories in stable order.

    Args:
        source: Source hook directory.

    Returns:
        Source directory paths including the root directory.
    """
    return [source, *sorted(path for path in source.rglob("*") if path.is_dir())]
