"""Manage project-local copies of codexmgr-home skills."""

import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.errors import CommandError
from ..core.toml_io import plain_toml_value


@dataclass(frozen=True)
class SkillCopy:
    """A managed skill directory copy.

    Attributes:
        name: Bare skill name.
        source: Source skill directory under CODEXMGR_HOME.
        target: Project-local .agents skill directory.
    """

    name: str
    source: Path
    target: Path


@dataclass(frozen=True)
class SkillCopyFile:
    """Expected file inside a managed skill copy.

    Attributes:
        path: Project-local copied file path.
        content: Expected byte content from the source file.
    """

    path: Path
    content: bytes


def validate_copy_targets(copies: list[SkillCopy], previous_lock: Mapping[str, Any]) -> None:
    """Reject first-time copies over unmanaged target folders.

    Args:
        copies: Current managed copies to create or refresh.
        previous_lock: Previous codexmgr lock data.
    """
    previous = previous_skill_copies(previous_lock)
    for copy in copies:
        if copy.name not in previous and copy.target.exists():
            raise CommandError(f"Refusing to overwrite unmanaged skill copy: {copy.target}")


def previous_skill_copies(previous_lock: Mapping[str, Any]) -> dict[str, SkillCopy]:
    """Read managed skill-copy metadata from previous lock data.

    Args:
        previous_lock: Parsed .codex/codexmgr.lock data.

    Returns:
        Previous managed copies keyed by skill name.
    """
    raw_copies = plain_toml_value(previous_lock.get("skills", {}).get("copies", []))
    if not isinstance(raw_copies, list):
        raise CommandError("codexmgr.lock skills.copies must be a list")
    copies: dict[str, SkillCopy] = {}
    for raw_copy in raw_copies:
        copy = _copy_from_lock_entry(raw_copy)
        copies[copy.name] = copy
    return copies


def obsolete_copy_targets(
    previous_lock: Mapping[str, Any],
    current_copies: list[SkillCopy],
) -> list[Path]:
    """Return previous managed copy targets absent from current state.

    Args:
        previous_lock: Previous codexmgr lock data.
        current_copies: Current managed copies.

    Returns:
        Sorted target directories to remove.
    """
    current_names = {copy.name for copy in current_copies}
    return sorted(
        copy.target
        for name, copy in previous_skill_copies(previous_lock).items()
        if name not in current_names
    )


def copy_lock_entries(copies: list[SkillCopy]) -> list[dict[str, str]]:
    """Build lockfile entries for managed skill copies.

    Args:
        copies: Current managed copies.

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


def expected_copy_files(copies: list[SkillCopy]) -> list[SkillCopyFile]:
    """Build expected file contents for managed skill copies.

    Args:
        copies: Current managed copies.

    Returns:
        Expected copied files in stable order.
    """
    files: list[SkillCopyFile] = []
    for copy in copies:
        for source_file in _source_files(copy.source):
            target_file = copy.target / source_file.relative_to(copy.source)
            files.append(SkillCopyFile(target_file, source_file.read_bytes()))
    return files


def apply_skill_copy(copy: SkillCopy) -> None:
    """Overlay-copy one managed skill directory.

    Args:
        copy: Managed copy to refresh.
    """
    for source_dir in _source_dirs(copy.source):
        target_dir = copy.target / source_dir.relative_to(copy.source)
        target_dir.mkdir(parents=True, exist_ok=True)
    for source_file in _source_files(copy.source):
        target_file = copy.target / source_file.relative_to(copy.source)
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target_file)


def remove_skill_copy_target(target: Path) -> None:
    """Remove a previously managed skill copy target.

    Args:
        target: Project-local copy path to remove.
    """
    if not target.exists():
        return
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()


def _copy_from_lock_entry(raw_copy: Any) -> SkillCopy:
    """Parse one skill-copy lock entry.

    Args:
        raw_copy: Plain lock entry value.

    Returns:
        Parsed managed skill copy.
    """
    if not isinstance(raw_copy, Mapping):
        raise CommandError("codexmgr.lock skills.copies entries must be tables")
    name = raw_copy.get("name")
    source = raw_copy.get("source")
    target = raw_copy.get("target")
    if not isinstance(name, str) or not isinstance(source, str) or not isinstance(target, str):
        raise CommandError("codexmgr.lock skills.copies entries must include name, source, and target")
    return SkillCopy(name, Path(source), Path(target))


def _source_dirs(source: Path) -> list[Path]:
    """Return source directories in stable order.

    Args:
        source: Source skill directory.

    Returns:
        Source directory paths including the root directory.
    """
    return [source, *sorted(path for path in source.rglob("*") if path.is_dir())]


def _source_files(source: Path) -> list[Path]:
    """Return source files in stable order.

    Args:
        source: Source skill directory.

    Returns:
        Source file paths.
    """
    return sorted(path for path in source.rglob("*") if path.is_file())
