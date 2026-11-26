"""Apply package enable and disable mutations to project config."""

from pathlib import Path

from ..core.paths import config_path, global_codex_dir
from ..core.toml_io import load_optional_toml_file, write_toml_file
from ..project.config import require_codex_dir
from .operations import PackageWorkspace, update_package_selections


def enable_packages(
    names: list[str],
    cwd: Path,
    codexmgr_home: Path,
    profiles: list[str],
    *,
    codex_home: Path | None = None,
) -> list[str]:
    """Enable selected entries from multiple packaged configurations.

    Args:
        names: Bare package names.
        cwd: Project directory whose codexmgr.toml should be updated.
        codexmgr_home: codexmgr home directory containing package sources.
        profiles: Profile names to merge into every selected package.
        codex_home: Codex skill store; defaults to the configured global home.

    Returns:
        Package names that were enabled.
    """
    return _mutate_packages(
        names, cwd, codexmgr_home, profiles,
        codex_home=codex_home if codex_home is not None else global_codex_dir(), enabled=True,
    )


def disable_packages(
    names: list[str],
    cwd: Path,
    codexmgr_home: Path,
    profiles: list[str],
    *,
    codex_home: Path | None = None,
) -> list[str]:
    """Disable selected entries from multiple packaged configurations.

    Args:
        names: Bare package names.
        cwd: Project directory whose codexmgr.toml should be updated.
        codexmgr_home: codexmgr home directory containing package sources.
        profiles: Profile names to merge into every selected package.
        codex_home: Codex skill store; defaults to the configured global home.

    Returns:
        Package names that were disabled.
    """
    return _mutate_packages(
        names, cwd, codexmgr_home, profiles,
        codex_home=codex_home if codex_home is not None else global_codex_dir(), enabled=False,
    )


def enable_package(name: str, cwd: Path, codexmgr_home: Path) -> str:
    """Enable all entries declared by one packaged configuration.

    Args:
        name: Bare package name.
        cwd: Project directory whose codexmgr.toml should be updated.
        codexmgr_home: codexmgr home directory containing package sources.

    Returns:
        The package name that was enabled.
    """
    return enable_packages([name], cwd, codexmgr_home, [])[0]


def disable_package(name: str, cwd: Path, codexmgr_home: Path) -> str:
    """Disable all entries declared by one packaged configuration.

    Args:
        name: Bare package name.
        cwd: Project directory whose codexmgr.toml should be updated.
        codexmgr_home: codexmgr home directory containing package sources.

    Returns:
        The package name that was disabled.
    """
    return disable_packages([name], cwd, codexmgr_home, [])[0]


def _mutate_packages(
    names: list[str],
    cwd: Path,
    codexmgr_home: Path,
    profiles: list[str],
    *,
    enabled: bool,
    codex_home: Path,
) -> list[str]:
    """Apply package mutations to project config with a single write.

    Args:
        names: Bare package names.
        cwd: Project directory whose codexmgr.toml should be updated.
        codexmgr_home: codexmgr home directory containing package sources.
        profiles: Profile names to merge into every package.
        enabled: Whether entries should be enabled or disabled.
        codex_home: Codex skill store used to expand package skill groups.

    Returns:
        Package names that were mutated.
    """
    require_codex_dir(cwd)
    config = load_optional_toml_file(config_path(cwd))
    requested = [(name, profile) for name in names for profile in (None, *profiles)]
    update_package_selections(
        config, requested, PackageWorkspace(cwd, codex_home, codexmgr_home),
        state="enabled" if enabled else "disabled",
    )
    write_toml_file(config_path(cwd), config)
    return list(names)
