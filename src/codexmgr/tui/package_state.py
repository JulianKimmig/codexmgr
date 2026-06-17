"""Package-related staged configuration helpers for the TUI."""

from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

from ..packages.config import PackageConfig, PackageEntries, load_package_config
from ..packages.mutation import apply_package_entries_to_config
from .mutations import package_checks, validate_package_enable


def set_package_enabled(
    config: MutableMapping[str, Any],
    name: str,
    enabled: bool,
    cwd: Path,
    codexmgr_home: Path,
) -> None:
    """Enable or disable all root entries from one package.

    Args:
        config: Staged project configuration.
        name: Package name under CODEXMGR_HOME/packages.
        enabled: Whether package entries should be active.
        cwd: Project directory used for validation.
        codexmgr_home: Codexmgr home containing reusable resources.
    """
    package = load_package_config(name, codexmgr_home)
    _set_package_entries(config, _root_entries(package), enabled, cwd, codexmgr_home)


def set_package_profile_enabled(
    config: MutableMapping[str, Any],
    name: str,
    profile: str,
    enabled: bool,
    cwd: Path,
    codexmgr_home: Path,
) -> None:
    """Enable or disable one package profile entry set.

    Args:
        config: Staged project configuration.
        name: Package name under CODEXMGR_HOME/packages.
        profile: Profile name within the package config.
        enabled: Whether profile entries should be active.
        cwd: Project directory used for validation.
        codexmgr_home: Codexmgr home containing reusable resources.
    """
    package = load_package_config(name, codexmgr_home)
    _set_package_entries(config, package.profiles[profile], enabled, cwd, codexmgr_home)


def package_state(config: MutableMapping[str, Any], name: str, codexmgr_home: Path) -> str:
    """Return enabled, partial, or disabled for a package.

    Args:
        config: Staged project configuration.
        name: Package name under CODEXMGR_HOME/packages.
        codexmgr_home: Codexmgr home containing reusable resources.

    Returns:
        Package state computed from staged entries.
    """
    package = load_package_config(name, codexmgr_home)
    return _state_from_checks(package_checks(config, _root_entries(package)))


def package_profile_state(
    config: MutableMapping[str, Any],
    name: str,
    profile: str,
    codexmgr_home: Path,
) -> str:
    """Return enabled, partial, or disabled for a package profile.

    Args:
        config: Staged project configuration.
        name: Package name under CODEXMGR_HOME/packages.
        profile: Profile name within the package config.
        codexmgr_home: Codexmgr home containing reusable resources.

    Returns:
        Package profile state computed from staged entries.
    """
    package = load_package_config(name, codexmgr_home)
    return _state_from_checks(package_checks(config, package.profiles[profile]))


def _set_package_entries(
    config: MutableMapping[str, Any],
    entries: PackageEntries,
    enabled: bool,
    cwd: Path,
    codexmgr_home: Path,
) -> None:
    """Enable or disable package entries in staged config.

    Args:
        config: Staged project configuration.
        entries: Package root or profile entries.
        enabled: Whether entries should be active.
        cwd: Project directory used for validation.
        codexmgr_home: Codexmgr home containing reusable resources.
    """
    if enabled:
        validate_package_enable(entries, cwd, codexmgr_home)
    apply_package_entries_to_config(config, entries, enabled=enabled)


def _root_entries(package: PackageConfig) -> PackageEntries:
    """Return root entries for a package.

    Args:
        package: Package configuration.

    Returns:
        Package root entries.
    """
    return PackageEntries(package.agentsmd, package.agents, package.hooks, package.skills)


def _state_from_checks(checks: list[bool]) -> str:
    """Return TUI state from per-entry checks.

    Args:
        checks: Active state for each entry in a package or profile.

    Returns:
        ``enabled``, ``partial``, or ``disabled``.
    """
    if checks and all(checks):
        return "enabled"
    if any(checks):
        return "partial"
    return "disabled"
