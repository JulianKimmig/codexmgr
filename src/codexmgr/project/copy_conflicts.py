"""Discover and resolve edits to source-backed managed copy files."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from ..core.errors import CommandError


class ManagedCopyFile(Protocol):
    """Structural contract for one expected source-backed copy file."""

    source: Path
    path: Path
    content: bytes
    resource_kind: str


class CopyResolution(StrEnum):
    """Supported actions for a differing managed copy target."""

    KEEP_LOCAL = "keep-local"
    OVERWRITE_LOCAL = "overwrite-local"
    UPDATE_SOURCE = "update-source"
    ABORT = "abort"


@dataclass(frozen=True)
class CopyConflict:
    """One differing target and its discovery-time source and target bytes.

    Attributes:
        source: Canonical reusable source file.
        target: Project-local managed copy file.
        source_content: Source bytes observed during project-state construction.
        target_content: Target bytes observed during conflict discovery.
        resource_kind: Resource family used for validation and display.
    """

    source: Path
    target: Path
    source_content: bytes
    target_content: bytes
    resource_kind: str


ConflictResolver = Callable[[CopyConflict], CopyResolution]
SourceUpdateReporter = Callable[[CopyConflict], None]


def find_copy_conflicts(copy_files: Iterable[ManagedCopyFile]) -> list[CopyConflict]:
    """Return existing copied targets whose bytes differ from their sources.

    Args:
        copy_files: Expected one-to-one source-backed copy files.

    Returns:
        Conflicts sorted by target path.
    """
    conflicts = []
    for copy_file in copy_files:
        if not copy_file.path.is_file():
            continue
        target_content = copy_file.path.read_bytes()
        if target_content == copy_file.content:
            continue
        conflicts.append(
            CopyConflict(
                copy_file.source,
                copy_file.path,
                copy_file.content,
                target_content,
                copy_file.resource_kind,
            ),
        )
    return sorted(conflicts, key=lambda conflict: str(conflict.target))


def parse_copy_resolutions(
    cwd: Path,
    values: Sequence[Sequence[str]],
) -> dict[Path, CopyResolution]:
    """Parse repeatable CLI target/action pairs into normalized resolutions.

    Args:
        cwd: Project root used to resolve relative target paths.
        values: Two-item target and action sequences from argument parsing.

    Returns:
        Resolutions keyed by absolute target path without resolving symlinks.
    """
    resolutions: dict[Path, CopyResolution] = {}
    for target_text, action_text in values:
        target = _absolute_target(cwd, Path(target_text))
        if target in resolutions:
            raise CommandError(f"Duplicate copy resolution target: {target_text}")
        try:
            action = CopyResolution(action_text)
        except ValueError as exc:
            choices = ", ".join(action.value for action in writable_resolutions())
            raise CommandError(
                f"Unsupported copy resolution '{action_text}'; choose {choices}",
            ) from exc
        if action not in writable_resolutions():
            choices = ", ".join(item.value for item in writable_resolutions())
            raise CommandError(
                f"Unsupported copy resolution '{action_text}'; choose {choices}",
            )
        resolutions[target] = action
    return resolutions


def choose_copy_resolutions(
    cwd: Path,
    conflicts: Sequence[CopyConflict],
    provided: Mapping[Path, CopyResolution],
    resolver: ConflictResolver | None,
) -> dict[Path, CopyResolution]:
    """Resolve every conflict before any apply write occurs.

    Args:
        cwd: Project root used in user-facing target paths.
        conflicts: Discovered managed-copy conflicts.
        provided: Explicit per-target resolutions for this invocation.
        resolver: Optional interactive callback for unresolved targets.

    Returns:
        Complete actions keyed by conflict target.
    """
    normalized = {_absolute_target(cwd, path): action for path, action in provided.items()}
    conflict_targets = {_absolute_target(cwd, item.target) for item in conflicts}
    unexpected = sorted(set(normalized) - conflict_targets, key=str)
    if unexpected:
        paths = ", ".join(display_target(cwd, path) for path in unexpected)
        raise CommandError(f"Resolution target is not a current copy conflict: {paths}")
    selected = dict(normalized)
    unresolved = [
        conflict
        for conflict in conflicts
        if _absolute_target(cwd, conflict.target) not in selected
    ]
    if unresolved and resolver is None:
        raise CommandError(_unresolved_message(cwd, unresolved))
    for conflict in unresolved:
        action = resolver(conflict) if resolver is not None else CopyResolution.ABORT
        if action == CopyResolution.ABORT:
            raise CommandError("Apply aborted; no files changed")
        selected[_absolute_target(cwd, conflict.target)] = action
    return selected


def writable_resolutions() -> tuple[CopyResolution, ...]:
    """Return actions accepted by the noninteractive CLI.

    Returns:
        The three non-abort resolution actions.
    """
    return (
        CopyResolution.KEEP_LOCAL,
        CopyResolution.OVERWRITE_LOCAL,
        CopyResolution.UPDATE_SOURCE,
    )


def display_target(cwd: Path, target: Path) -> str:
    """Format a target relative to the project when possible.

    Args:
        cwd: Project root used as the display base.
        target: Managed target path.

    Returns:
        Project-relative POSIX path or an absolute path outside the project.
    """
    absolute = _absolute_target(cwd, target)
    try:
        return absolute.relative_to(cwd.absolute()).as_posix()
    except ValueError:
        return str(absolute)


def _unresolved_message(cwd: Path, conflicts: Sequence[CopyConflict]) -> str:
    """Build the actionable error for noninteractive unresolved conflicts.

    Args:
        cwd: Project root used for display paths.
        conflicts: Conflicts missing a resolution.

    Returns:
        Multi-line command error text.
    """
    lines = ["Managed copy conflicts require a resolution before apply:"]
    for conflict in conflicts:
        target = display_target(cwd, conflict.target)
        lines.extend(
            (
                f"- Managed copy conflict: {target}",
                f"  Source: {conflict.source}",
                f"  Resolve with: codexmgr apply --resolve {target} "
                "<keep-local|overwrite-local|update-source>",
            ),
        )
    return "\n".join(lines)


def _absolute_target(cwd: Path, target: Path) -> Path:
    """Normalize a target path without following filesystem symlinks.

    Args:
        cwd: Project root used for relative paths.
        target: Relative or absolute target path.

    Returns:
        Absolute normalized path.
    """
    return target.absolute() if target.is_absolute() else (cwd / target).absolute()
