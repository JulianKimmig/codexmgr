"""Resolve project rule configuration into managed copies."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import rule_lists
from .copies import (
    RuleCopy,
    expected_rule_copy_files,
    obsolete_rule_copy_targets,
    rule_copy_lock_entries,
    validate_rule_copy_targets,
)
from .sources import canonical_rule_ref, project_rules_dir, rules_source_root


@dataclass(frozen=True)
class RuleResolution:
    """Resolved reusable rule state.

    Attributes:
        copies: Managed project-local rule file copies.
        copy_files: Expected files inside managed rule copies.
        obsolete_copy_targets: Previous managed rule files to remove.
        enabled: Configured enabled rule refs.
        disabled: Configured disabled rule refs.
    """

    copies: list[RuleCopy]
    copy_files: list[Any]
    obsolete_copy_targets: list[Path]
    enabled: list[str]
    disabled: list[str]


def empty_rule_resolution() -> RuleResolution:
    """Return empty rule resolution for projects without rules config.

    Returns:
        Empty reusable rule state.
    """
    return RuleResolution([], [], [], [], [])


def resolve_project_rules(
    project_config: Mapping[str, Any],
    cwd: Path,
    codexmgr_home: Path,
    previous_lock: Mapping[str, Any],
) -> RuleResolution:
    """Resolve configured rule refs into managed copies.

    Args:
        project_config: Parsed project codexmgr config.
        cwd: Project directory.
        codexmgr_home: Codexmgr home containing source rules.
        previous_lock: Existing codexmgr lock data.

    Returns:
        Resolved rule state.
    """
    enabled, disabled = rule_lists(project_config)
    copies = _selected_copies(enabled, disabled, cwd, codexmgr_home)
    validate_rule_copy_targets(copies, previous_lock)
    return RuleResolution(
        copies,
        expected_rule_copy_files(copies),
        obsolete_rule_copy_targets(previous_lock, copies),
        enabled,
        disabled,
    )


def rule_lock_data(resolution: RuleResolution) -> dict[str, Any]:
    """Build lockfile data for reusable rules.

    Args:
        resolution: Resolved rule state.

    Returns:
        TOML-serializable lock data.
    """
    data: dict[str, Any] = {
        "enabled": resolution.enabled,
        "disabled": resolution.disabled,
    }
    copy_entries = rule_copy_lock_entries(resolution.copies)
    if copy_entries:
        data["copies"] = copy_entries
    return data


def _selected_copies(
    enabled: list[str],
    disabled: list[str],
    cwd: Path,
    codexmgr_home: Path,
) -> list[RuleCopy]:
    """Expand enabled refs and apply disabled exclusions.

    Args:
        enabled: Enabled rule refs.
        disabled: Disabled rule refs.
        cwd: Project directory.
        codexmgr_home: Codexmgr home containing source rules.

    Returns:
        Managed rule copy plan.
    """
    candidates = _enabled_files(enabled, codexmgr_home)
    selected = [
        relative_path
        for relative_path in sorted(candidates)
        if not _is_disabled(relative_path, disabled)
    ]
    return [_rule_copy(relative_path, cwd, codexmgr_home) for relative_path in selected]


def _enabled_files(enabled: list[str], codexmgr_home: Path) -> set[str]:
    """Expand enabled refs into source file paths.

    Args:
        enabled: Enabled rule refs.
        codexmgr_home: Codexmgr home containing source rules.

    Returns:
        POSIX relative source file paths.
    """
    files: set[str] = set()
    root = rules_source_root(codexmgr_home)
    for ref in enabled:
        canonical = canonical_rule_ref(ref, codexmgr_home)
        if canonical.is_dir:
            source_dir = root / canonical.value.rstrip("/")
            files.update(
                path.relative_to(root).as_posix()
                for path in source_dir.rglob("*")
                if path.is_file()
            )
        else:
            files.add(canonical.value)
    return files


def _is_disabled(relative_path: str, disabled: list[str]) -> bool:
    """Return whether a file is removed by disabled refs.

    Args:
        relative_path: Candidate rule file path.
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


def _rule_copy(relative_path: str, cwd: Path, codexmgr_home: Path) -> RuleCopy:
    """Build one managed rule copy.

    Args:
        relative_path: POSIX path under the rules source root.
        cwd: Project directory.
        codexmgr_home: Codexmgr home containing source rules.

    Returns:
        Rule copy plan.
    """
    return RuleCopy(
        relative_path,
        rules_source_root(codexmgr_home) / relative_path,
        project_rules_dir(cwd) / relative_path,
    )
