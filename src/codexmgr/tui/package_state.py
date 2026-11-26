"""Package-related staged configuration helpers for the TUI."""

from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

from ..guides.config import guide_reference_states
from ..packages.config import PackageEntries
from ..packages.operations import (
    PackageWorkspace, package_selection_display_entries, update_package_selections,
)
from ..skills.groups import skill_reference_states
from .mutations import package_checks


def set_package_enabled(
    config: MutableMapping[str, Any],
    name: str,
    enabled: bool,
    cwd: Path,
    codexmgr_home: Path,
    *, codex_home: Path,
) -> None:
    """Enable or disable all root entries from one package.

    Args:
        config: Staged project configuration.
        name: Package name under CODEXMGR_HOME/packages.
        enabled: Whether package entries should be active.
        cwd: Project directory used for validation.
        codexmgr_home: Codexmgr home containing reusable resources.
        codex_home: Codex skill store used for group expansion.
    """
    update_package_selections(
        config, [(name, None)], PackageWorkspace(cwd, codex_home, codexmgr_home),
        state="enabled" if enabled else "disabled",
    )


def set_package_profile_enabled(
    config: MutableMapping[str, Any],
    name: str,
    profile: str,
    enabled: bool,
    cwd: Path,
    codexmgr_home: Path,
    *, codex_home: Path,
) -> None:
    """Enable or disable one package profile entry set.

    Args:
        config: Staged project configuration.
        name: Package name under CODEXMGR_HOME/packages.
        profile: Profile name within the package config.
        enabled: Whether profile entries should be active.
        cwd: Project directory used for validation.
        codexmgr_home: Codexmgr home containing reusable resources.
        codex_home: Codex skill store used for group expansion.
    """
    update_package_selections(
        config, [(name, profile)], PackageWorkspace(cwd, codex_home, codexmgr_home),
        state="enabled" if enabled else "disabled",
    )


def set_package_available(
    config: MutableMapping[str, Any],
    name: str,
    cwd: Path,
    codexmgr_home: Path,
    *, codex_home: Path,
) -> None:
    """Clear root package entries from staged config.

    Args:
        config: Staged project configuration.
        name: Package name under CODEXMGR_HOME/packages.
        cwd: Project directory used for validation.
        codexmgr_home: Codexmgr home containing reusable resources.
        codex_home: Codex skill store used for group expansion.
    """
    update_package_selections(
        config, [(name, None)], PackageWorkspace(cwd, codex_home, codexmgr_home),
        state="available",
    )


def set_package_profile_available(
    config: MutableMapping[str, Any],
    name: str,
    profile: str,
    codexmgr_home: Path,
    *, cwd: Path, codex_home: Path,
) -> None:
    """Clear profile package entries from staged config.

    Args:
        config: Staged project configuration.
        name: Package name under CODEXMGR_HOME/packages.
        profile: Profile name within the package config.
        codexmgr_home: Codexmgr home containing reusable resources.
        cwd: Project root used to discover group descendants.
        codex_home: Codex skill store used for group expansion.
    """
    update_package_selections(
        config, [(name, profile)], PackageWorkspace(cwd, codex_home, codexmgr_home),
        state="available",
    )


def package_state(
    config: MutableMapping[str, Any], name: str, codexmgr_home: Path,
    *, cwd: Path, codex_home: Path,
) -> str:
    """Return enabled, partial, or disabled for a package.

    Args:
        config: Staged project configuration.
        name: Package name under CODEXMGR_HOME/packages.
        codexmgr_home: Codexmgr home containing reusable resources.
        cwd: Project root used to discover group descendants.
        codex_home: Codex skill store used for group expansion.

    Returns:
        Package state computed from staged entries.
    """
    entries = package_selection_display_entries(config, (name, None), PackageWorkspace(cwd, codex_home, codexmgr_home))
    return _entries_state(config, entries, cwd, codex_home, codexmgr_home)


def package_profile_state(
    config: MutableMapping[str, Any],
    name: str,
    profile: str,
    codexmgr_home: Path,
    *, cwd: Path, codex_home: Path,
) -> str:
    """Return enabled, partial, or disabled for a package profile.

    Args:
        config: Staged project configuration.
        name: Package name under CODEXMGR_HOME/packages.
        profile: Profile name within the package config.
        codexmgr_home: Codexmgr home containing reusable resources.
        cwd: Project root used to discover group descendants.
        codex_home: Codex skill store used for group expansion.

    Returns:
        Package profile state computed from staged entries.
    """
    entries = package_selection_display_entries(config, (name, profile), PackageWorkspace(cwd, codex_home, codexmgr_home))
    return _entries_state(config, entries, cwd, codex_home, codexmgr_home)


def _entries_state(
    config: MutableMapping[str, Any], entries: PackageEntries,
    cwd: Path, codex_home: Path, codexmgr_home: Path,
) -> str:
    """Summarize package state after resolving individual skill descendants.

    Args:
        config: Staged project configuration.
        entries: Package root or profile references.
        cwd: Project root used to discover grouped skills.
        codex_home: Codex skill store.
        codexmgr_home: Manager skill store.

    Returns:
        Aggregate package state based on expanded skill identities and resources.
    """
    states = skill_reference_states(config, entries.skills, cwd, codex_home, codexmgr_home)
    return _state_from_checks([
        *package_checks(config, entries, skill_states=states),
        *guide_reference_states(config, entries.guides, codexmgr_home),
    ])


def _state_from_checks(checks: list[str]) -> str:
    """Return TUI state from per-entry checks.

    Args:
        checks: State for each entry in a package or profile.

    Returns:
        ``enabled``, ``partial``, or ``disabled``.
    """
    if checks and all(check == "enabled" for check in checks):
        return "enabled"
    if any(check == "enabled" for check in checks):
        return "partial"
    if any(check == "disabled" for check in checks):
        return "disabled"
    return "available"
