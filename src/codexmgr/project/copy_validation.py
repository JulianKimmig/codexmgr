"""Validate and apply local-to-source managed-copy updates."""

import shutil
from collections.abc import Mapping, Sequence
from pathlib import Path

from ..core.errors import CommandError
from ..core.toml_io import load_toml_file
from ..skills.metadata import read_skill_name
from .copy_conflicts import CopyConflict, CopyResolution, SourceUpdateReporter


def prepare_source_updates(
    cwd: Path,
    conflicts: Sequence[CopyConflict],
    resolutions: Mapping[Path, CopyResolution],
) -> list[CopyConflict]:
    """Validate decisions and ensure conflict snapshots are still current.

    Args:
        cwd: Project root used to normalize resolution paths.
        conflicts: Conflicts captured before decisions were collected.
        resolutions: Complete per-target resolution mapping.

    Returns:
        Conflicts whose local targets should update their canonical sources.
    """
    updates = [
        conflict
        for conflict in conflicts
        if resolutions[_absolute_target(cwd, conflict.target)]
        == CopyResolution.UPDATE_SOURCE
    ]
    for conflict in updates:
        _validate_source_update(conflict)
    for conflict in conflicts:
        _require_unchanged(conflict)
    return updates


def apply_source_updates(
    conflicts: Sequence[CopyConflict],
    reporter: SourceUpdateReporter | None,
) -> None:
    """Copy validated local target bytes back to canonical sources.

    Args:
        conflicts: Validated update-source conflicts.
        reporter: Optional callback invoked immediately before each write.
    """
    for conflict in conflicts:
        if reporter is not None:
            reporter(conflict)
        shutil.copy2(conflict.target, conflict.source)


def skipped_copy_targets(
    cwd: Path,
    resolutions: Mapping[Path, CopyResolution],
) -> set[Path]:
    """Return targets that normal source-to-local copying must skip.

    Args:
        cwd: Project root used to normalize resolution paths.
        resolutions: Complete conflict resolutions.

    Returns:
        Target paths selected for keep-local or update-source.
    """
    return {
        _absolute_target(cwd, target)
        for target, action in resolutions.items()
        if action in {CopyResolution.KEEP_LOCAL, CopyResolution.UPDATE_SOURCE}
    }


def _validate_source_update(conflict: CopyConflict) -> None:
    """Run the validator owned by a conflict's resource type.

    Args:
        conflict: Proposed local-to-source update.
    """
    if conflict.resource_kind == "skill" and conflict.source.name == "SKILL.md":
        source_name = read_skill_name(conflict.source)
        target_name = read_skill_name(conflict.target)
        if source_name != target_name:
            raise CommandError(
                "Updated skill metadata must preserve the canonical name "
                f"'{source_name}': {conflict.target}",
            )
    if conflict.resource_kind == "custom-agent":
        load_toml_file(conflict.target)


def _require_unchanged(conflict: CopyConflict) -> None:
    """Reject source or target changes made after conflict discovery.

    Args:
        conflict: Discovery-time copy conflict snapshot.
    """
    if (
        not conflict.source.is_file()
        or conflict.source.read_bytes() != conflict.source_content
    ):
        raise CommandError(f"Managed copy source changed during apply: {conflict.source}")
    if (
        not conflict.target.is_file()
        or conflict.target.read_bytes() != conflict.target_content
    ):
        raise CommandError(f"Managed copy target changed during apply: {conflict.target}")


def _absolute_target(cwd: Path, target: Path) -> Path:
    """Normalize a target path without following filesystem symlinks.

    Args:
        cwd: Project root used for relative paths.
        target: Relative or absolute target path.

    Returns:
        Absolute normalized path.
    """
    return target.absolute() if target.is_absolute() else (cwd / target).absolute()
