"""Resolve packaged configuration sources from CODEXMGR_HOME."""

from pathlib import Path

from ..core.errors import CommandError


def available_package_names(codexmgr_home: Path) -> list[str]:
    """List packaged configuration names available under CODEXMGR_HOME.

    Args:
        codexmgr_home: codexmgr home directory.

    Returns:
        Sorted package names whose directory contains a config.toml file.
    """
    root = packages_dir(codexmgr_home)
    if not root.is_dir():
        return []
    return sorted(
        path.name
        for path in root.iterdir()
        if path.is_dir() and (path / "config.toml").is_file()
    )


def require_package_config(name: str, codexmgr_home: Path) -> Path:
    """Resolve one package config file or raise a user-facing error.

    Args:
        name: Bare package name from the CLI.
        codexmgr_home: codexmgr home directory.

    Returns:
        Path to CODEXMGR_HOME/packages/<name>/config.toml.
    """
    if not is_bare_package_name(name):
        raise CommandError(f"Package name must be a bare name: {name}")
    path = package_config_path(codexmgr_home, name)
    if not path.is_file():
        raise CommandError(f"Package not found: {path}")
    return path


def packages_dir(codexmgr_home: Path) -> Path:
    """Return the package source directory for a codexmgr home.

    Args:
        codexmgr_home: codexmgr home directory.

    Returns:
        Path to CODEXMGR_HOME/packages.
    """
    return codexmgr_home / "packages"


def package_config_path(codexmgr_home: Path, name: str) -> Path:
    """Return the expected config.toml path for one package name.

    Args:
        codexmgr_home: codexmgr home directory.
        name: Bare package name.

    Returns:
        Path to the package config.toml file.
    """
    return packages_dir(codexmgr_home) / name / "config.toml"


def is_bare_package_name(name: str) -> bool:
    """Return whether a package reference is a bare name.

    Args:
        name: Package reference from the CLI.

    Returns:
        True when the reference has no path separators and is not empty.
    """
    raw = name.strip()
    return bool(raw) and "/" not in raw and "\\" not in raw
