"""Resolve project guide configuration into managed copies."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import guide_lists
from .copies import (
    GuideCopy,
    expected_guide_copy_files,
    obsolete_guide_copy_targets,
    guide_copy_lock_entries,
    validate_guide_copy_targets,
)
from .sources import (
    canonical_guide_ref, canonical_guide_ref_if_exists, normalize_missing_guide_ref,
    project_guides_dir, guides_source_root, guide_descendants, safe_guide_path,
)


@dataclass(frozen=True)
class GuideResolution:
    """Resolved reusable guide state.

    Attributes:
        copies: Managed project-local guide file copies.
        copy_files: Expected files inside managed guide copies.
        obsolete_copy_targets: Previous managed guide files to remove.
        enabled: Configured enabled guide refs.
        disabled: Configured disabled guide refs.
    """

    copies: list[GuideCopy]
    copy_files: list[Any]
    obsolete_copy_targets: list[Path]
    enabled: list[str]
    disabled: list[str]


def resolve_project_guides(
    project_config: Mapping[str, Any],
    cwd: Path,
    codexmgr_home: Path,
    previous_lock: Mapping[str, Any],
) -> GuideResolution:
    """Resolve configured guide refs into managed copies.

    Args:
        project_config: Parsed project codexmgr config.
        cwd: Project directory.
        codexmgr_home: Codexmgr home containing source guides.
        previous_lock: Existing codexmgr lock data.

    Returns:
        Resolved guide state.
    """
    enabled, disabled = guide_lists(project_config)
    enabled = list(dict.fromkeys(canonical_guide_ref(ref, codexmgr_home).value for ref in enabled))
    disabled = list(dict.fromkeys(
        (canonical_guide_ref_if_exists(ref, codexmgr_home) or normalize_missing_guide_ref(ref)).value
        for ref in disabled
    ))
    copies = _selected_copies(enabled, disabled, cwd, codexmgr_home)
    validate_guide_copy_targets(copies, previous_lock, cwd, codexmgr_home)
    return GuideResolution(
        copies,
        expected_guide_copy_files(copies),
        obsolete_guide_copy_targets(previous_lock, copies, cwd, codexmgr_home),
        enabled,
        disabled,
    )


def guide_lock_data(resolution: GuideResolution) -> dict[str, Any]:
    """Build lockfile data for reusable guides.

    Args:
        resolution: Resolved guide state.

    Returns:
        TOML-serializable lock data.
    """
    data: dict[str, Any] = {
        "enabled": resolution.enabled,
        "disabled": resolution.disabled,
    }
    copy_entries = guide_copy_lock_entries(resolution.copies)
    if copy_entries:
        data["copies"] = copy_entries
    return data


def _selected_copies(
    enabled: list[str],
    disabled: list[str],
    cwd: Path,
    codexmgr_home: Path,
) -> list[GuideCopy]:
    """Expand enabled refs and apply disabled exclusions.

    Args:
        enabled: Enabled guide refs.
        disabled: Disabled guide refs.
        cwd: Project directory.
        codexmgr_home: Codexmgr home containing source guides.

    Returns:
        Managed guide copy plan.
    """
    candidates = _enabled_files(enabled, codexmgr_home)
    selected = [
        relative_path
        for relative_path in sorted(candidates)
        if not _is_disabled(relative_path, disabled)
    ]
    return [_guide_copy(relative_path, cwd, codexmgr_home) for relative_path in selected]


def _enabled_files(enabled: list[str], codexmgr_home: Path) -> set[str]:
    """Expand enabled refs into source file paths.

    Args:
        enabled: Enabled guide refs.
        codexmgr_home: Codexmgr home containing source guides.

    Returns:
        POSIX relative source file paths.
    """
    files: set[str] = set()
    root = guides_source_root(codexmgr_home)
    for ref in enabled:
        canonical = canonical_guide_ref(ref, codexmgr_home)
        if canonical.is_dir:
            files.update(
                path.relative_to(root).as_posix()
                for path in guide_descendants(root, canonical.value)
                if path.is_file()
            )
        else:
            files.add(canonical.value)
    return files


def _is_disabled(relative_path: str, disabled: list[str]) -> bool:
    """Return whether a file is removed by disabled refs.

    Args:
        relative_path: Candidate guide file path.
        disabled: Disabled file or folder refs.

    Returns:
        True when the file should not be copied.
    """
    for ref in disabled:
        if ref.endswith("/") and relative_path.startswith(ref):
            return True
        if ref == relative_path:
            return True
    return False


def _guide_copy(relative_path: str, cwd: Path, codexmgr_home: Path) -> GuideCopy:
    """Build one managed guide copy.

    Args:
        relative_path: POSIX path under the guides source root.
        cwd: Project directory.
        codexmgr_home: Codexmgr home containing source guides.

    Returns:
        Guide copy plan.
    """
    return GuideCopy(
        relative_path,
        safe_guide_path(guides_source_root(codexmgr_home), relative_path),
        safe_guide_path(project_guides_dir(cwd), relative_path),
    )
