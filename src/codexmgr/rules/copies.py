"""Manage project-local copies of reusable rule files."""

import shutil
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.errors import CommandError
from ..core.toml_io import plain_toml_value


@dataclass(frozen=True)
class RuleCopy:
    """One managed reusable rule file copy.

    Attributes:
        relative_path: POSIX path under the source and target rules roots.
        source: Source file under CODEXMGR_HOME/rules.
        target: Project-local target file under `.rules`.
    """

    relative_path: str
    source: Path
    target: Path


@dataclass(frozen=True)
class RuleCopyFile:
    """Expected content for one managed rule copy.

    Attributes:
        path: Project-local target file.
        content: Expected bytes read from the source file.
    """

    path: Path
    content: bytes


def validate_rule_copy_targets(copies: list[RuleCopy], previous_lock: Mapping[str, Any]) -> None:
    """Reject first-time copies over unmanaged target files.

    Args:
        copies: Current managed rule copies.
        previous_lock: Existing codexmgr lock data.
    """
    previous = previous_rule_copies(previous_lock)
    for copy in copies:
        if copy.relative_path not in previous and copy.target.exists():
            raise CommandError(f"Refusing to overwrite unmanaged rule file: {copy.target}")


def previous_rule_copies(previous_lock: Mapping[str, Any]) -> dict[str, RuleCopy]:
    """Read managed rule-copy metadata from lock data.

    Args:
        previous_lock: Parsed .codex/codexmgr.lock data.

    Returns:
        Previous rule copies keyed by relative path.
    """
    raw_copies = plain_toml_value(previous_lock.get("rules", {}).get("copies", []))
    if not isinstance(raw_copies, list):
        raise CommandError("codexmgr.lock rules.copies must be a list")
    copies: dict[str, RuleCopy] = {}
    for raw_copy in raw_copies:
        copy = _copy_from_lock_entry(raw_copy)
        copies[copy.relative_path] = copy
    return copies


def obsolete_rule_copy_targets(
    previous_lock: Mapping[str, Any],
    current_copies: list[RuleCopy],
) -> list[Path]:
    """Return previous managed targets absent from current state.

    Args:
        previous_lock: Existing codexmgr lock data.
        current_copies: Current managed rule copies.

    Returns:
        Sorted obsolete file targets.
    """
    current = {copy.relative_path for copy in current_copies}
    return sorted(
        copy.target
        for relative_path, copy in previous_rule_copies(previous_lock).items()
        if relative_path not in current
    )


def rule_copy_lock_entries(copies: list[RuleCopy]) -> list[dict[str, str]]:
    """Build lockfile entries for managed rule copies.

    Args:
        copies: Current managed rule copies.

    Returns:
        TOML-serializable lock entries.
    """
    return [
        {
            "relative_path": copy.relative_path,
            "source": str(copy.source.resolve()),
            "target": str(copy.target.resolve()),
        }
        for copy in copies
    ]


def expected_rule_copy_files(copies: list[RuleCopy]) -> list[RuleCopyFile]:
    """Build expected bytes for managed rule copies.

    Args:
        copies: Current managed rule copies.

    Returns:
        Expected target file contents.
    """
    return [RuleCopyFile(copy.target, copy.source.read_bytes()) for copy in copies]


def apply_rule_copy(copy: RuleCopy) -> None:
    """Copy one source rule file to the project-local target.

    Args:
        copy: Managed rule copy to refresh.
    """
    copy.target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(copy.source, copy.target)


def remove_rule_copy_target(target: Path) -> None:
    """Remove one previously managed rule file and empty parent directories.

    Args:
        target: Managed rule file target to remove.
    """
    if target.is_file():
        target.unlink()
    _prune_empty_dirs(target.parent)


def _copy_from_lock_entry(raw_copy: Any) -> RuleCopy:
    """Parse one rule copy lock entry.

    Args:
        raw_copy: Plain lock entry value.

    Returns:
        Parsed rule copy.
    """
    if not isinstance(raw_copy, Mapping):
        raise CommandError("codexmgr.lock rules.copies entries must be tables")
    relative_path = raw_copy.get("relative_path")
    source = raw_copy.get("source")
    target = raw_copy.get("target")
    if (
        not isinstance(relative_path, str)
        or not isinstance(source, str)
        or not isinstance(target, str)
    ):
        raise CommandError(
            "codexmgr.lock rules.copies entries must include relative_path, source, and target"
        )
    return RuleCopy(relative_path, Path(source), Path(target))


def _prune_empty_dirs(path: Path) -> None:
    """Remove empty `.rules` directories without touching unmanaged content.

    Args:
        path: Directory where pruning should begin.
    """
    current = path
    while current.name != ".rules":
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
