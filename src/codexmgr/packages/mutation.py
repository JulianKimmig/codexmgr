"""Apply package enable and disable mutations to project config."""

from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

from ..core.paths import config_path, resolve_template
from ..core.toml_io import load_optional_toml_file, write_toml_file
from ..hooks.config import set_hook_state_in_config
from ..hooks.sources import require_hook_source
from ..project.config import agents_md_sources, require_codex_dir, set_agents_md_sources
from ..skills.config import set_skill_state_in_config
from .config import PackageConfig, load_package_config


def enable_package(name: str, cwd: Path, codexmgr_home: Path) -> str:
    """Enable all entries declared by one packaged configuration.

    Args:
        name: Bare package name.
        cwd: Project directory whose codexmgr.toml should be updated.
        codexmgr_home: codexmgr home directory containing package sources.

    Returns:
        The package name that was enabled.
    """
    package = load_package_config(name, codexmgr_home)
    _validate_enable_sources(package, cwd, codexmgr_home)
    require_codex_dir(cwd)
    config = load_optional_toml_file(config_path(cwd))
    _add_agentsmd(config, package.agentsmd)
    for skill in package.skills:
        set_skill_state_in_config(config, skill, enabled=True)
    for hook in package.hooks:
        set_hook_state_in_config(config, hook, enabled=True)
    write_toml_file(config_path(cwd), config)
    return package.name


def disable_package(name: str, cwd: Path, codexmgr_home: Path) -> str:
    """Disable all entries declared by one packaged configuration.

    Args:
        name: Bare package name.
        cwd: Project directory whose codexmgr.toml should be updated.
        codexmgr_home: codexmgr home directory containing package sources.

    Returns:
        The package name that was disabled.
    """
    package = load_package_config(name, codexmgr_home)
    require_codex_dir(cwd)
    config = load_optional_toml_file(config_path(cwd))
    _remove_agentsmd(config, package.agentsmd)
    for skill in package.skills:
        set_skill_state_in_config(config, skill, enabled=False)
    for hook in package.hooks:
        set_hook_state_in_config(config, hook, enabled=False)
    write_toml_file(config_path(cwd), config)
    return package.name


def _validate_enable_sources(
    package: PackageConfig,
    cwd: Path,
    codexmgr_home: Path,
) -> None:
    """Validate package references that direct enable commands validate.

    Args:
        package: Parsed package configuration.
        cwd: Project directory used to resolve path-backed AGENTS.md templates.
        codexmgr_home: codexmgr home directory used to resolve named sources.
    """
    for reference in package.agentsmd:
        resolve_template(reference, cwd, codexmgr_home)
    for hook in package.hooks:
        require_hook_source(hook, codexmgr_home)


def _add_agentsmd(config: MutableMapping[str, Any], references: list[str]) -> None:
    """Add AGENTS.md references to a parsed project config.

    Args:
        config: Parsed codexmgr.toml data to mutate.
        references: AGENTS.md template references to add.
    """
    if not references:
        return
    sources = agents_md_sources(config)
    for reference in references:
        if reference not in sources:
            sources.append(reference)
    set_agents_md_sources(config, sources)


def _remove_agentsmd(config: MutableMapping[str, Any], references: list[str]) -> None:
    """Remove AGENTS.md references from a parsed project config.

    Args:
        config: Parsed codexmgr.toml data to mutate.
        references: AGENTS.md template references to remove when present.
    """
    if not references:
        return
    removed = set(references)
    set_agents_md_sources(
        config,
        [source for source in agents_md_sources(config) if source not in removed],
    )
