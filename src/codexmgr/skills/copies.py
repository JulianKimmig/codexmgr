"""Manage project-local copies of codexmgr-home skills."""

import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.errors import CommandError
from ..core.toml_io import plain_toml_value
from .sources import CODEXMGR_HOME_SOURCE, project_skill_dir


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
        source: Canonical source file path.
        path: Project-local copied file path.
        content: Expected byte content from the source file.
        resource_kind: Resource family used for conflict validation.
    """

    source: Path
    path: Path
    content: bytes
    resource_kind: str = "skill"


def validate_copy_targets(
    copies: list[SkillCopy],
    previous_lock: Mapping[str, Any],
    cwd: Path,
    codexmgr_home: Path,
) -> None:
    """Reject first-time copies over unmanaged target folders.

    Args:
        copies: Current managed copies to create or refresh.
        previous_lock: Previous codexmgr lock data.
        cwd: Current project root used to rebind portable targets.
        codexmgr_home: Current codexmgr home used to rebind portable sources.
    """
    previous = previous_skill_copies(previous_lock, cwd, codexmgr_home)
    for copy in copies:
        if copy.name not in previous and copy.target.exists():
            raise CommandError(
                f"Refusing to overwrite unmanaged skill copy: {copy.target}"
            )


def previous_skill_copies(
    previous_lock: Mapping[str, Any],
    cwd: Path,
    codexmgr_home: Path,
) -> dict[str, SkillCopy]:
    """Read managed skill-copy metadata from previous lock data.

    Args:
        previous_lock: Parsed .codex/codexmgr.lock data.
        cwd: Current project root used to rebind portable targets.
        codexmgr_home: Current codexmgr home used to rebind portable sources.

    Returns:
        Previous managed copies keyed by skill name.
    """
    raw_copies = plain_toml_value(previous_lock.get("skills", {}).get("copies", []))
    if not isinstance(raw_copies, list):
        raise CommandError("codexmgr.lock skills.copies must be a list")
    copies: dict[str, SkillCopy] = {}
    for raw_copy in raw_copies:
        copy = _copy_from_lock_entry(raw_copy, cwd, codexmgr_home)
        copies[copy.name] = copy
    return copies


def obsolete_copy_targets(
    previous_lock: Mapping[str, Any],
    current_copies: list[SkillCopy],
    cwd: Path,
    codexmgr_home: Path,
) -> list[Path]:
    """Return previous managed copy targets absent from current state.

    Args:
        previous_lock: Previous codexmgr lock data.
        current_copies: Current managed copies.
        cwd: Current project root used to rebind portable targets.
        codexmgr_home: Current codexmgr home used to rebind portable sources.

    Returns:
        Sorted target directories to remove.
    """
    current_names = {copy.name for copy in current_copies}
    return sorted(
        copy.target
        for name, copy in previous_skill_copies(
            previous_lock,
            cwd,
            codexmgr_home,
        ).items()
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
            "source": CODEXMGR_HOME_SOURCE,
            "target": f".agents/skills/{copy.name}",
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
            files.append(
                SkillCopyFile(source_file, target_file, source_file.read_bytes()),
            )
    return files


def apply_skill_copy(copy: SkillCopy, skip_targets: set[Path] | None = None) -> None:
    """Overlay-copy one managed skill directory.

    Args:
        copy: Managed copy to refresh.
        skip_targets: Exact target files to preserve for this apply.
    """
    for source_dir in _source_dirs(copy.source):
        target_dir = copy.target / source_dir.relative_to(copy.source)
        target_dir.mkdir(parents=True, exist_ok=True)
    for source_file in _source_files(copy.source):
        target_file = copy.target / source_file.relative_to(copy.source)
        if skip_targets is not None and target_file.absolute() in skip_targets:
            continue
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


def _copy_from_lock_entry(
    raw_copy: Any,
    cwd: Path,
    codexmgr_home: Path,
) -> SkillCopy:
    """Parse one skill-copy lock entry.

    Args:
        raw_copy: Plain lock entry value.
        cwd: Current project root used to rebind the target.
        codexmgr_home: Current codexmgr home used to rebind the source.

    Returns:
        Parsed managed skill copy.
    """
    if not isinstance(raw_copy, Mapping):
        raise CommandError("codexmgr.lock skills.copies entries must be tables")
    name = raw_copy.get("name")
    source = raw_copy.get("source")
    target = raw_copy.get("target")
    if not all(isinstance(value, str) for value in (name, source, target)):
        raise CommandError(
            "codexmgr.lock skills.copies entries must include name, source, "
            "and target"
        )
    if name in {"", ".", ".."} or Path(name).name != name:
        raise CommandError(
            "codexmgr.lock skills.copies entries must use a safe skill name"
        )
    return SkillCopy(
        name,
        codexmgr_home / "skills" / name,
        project_skill_dir(cwd, name),
    )


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
