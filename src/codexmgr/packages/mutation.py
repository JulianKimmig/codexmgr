"""Apply package enable and disable mutations to project config."""

from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

from ..core.paths import config_path, resolve_template
from ..core.toml_io import load_optional_toml_file, write_toml_file
from ..custom_agents.config import set_agent_state_in_config
from ..custom_agents.sources import require_agent_source
from ..hooks.config import set_hook_state_in_config
from ..hooks.sources import require_hook_source
from ..project.config import agents_md_sources, require_codex_dir, set_agents_md_sources
from ..skills.config import set_skill_state_in_config
from .config import PackageEntries, load_package_config, selected_package_entries


def enable_packages(
    names: list[str],
    cwd: Path,
    codexmgr_home: Path,
    profiles: list[str],
) -> list[str]:
    """Enable selected entries from multiple packaged configurations.

    Args:
        names: Bare package names.
        cwd: Project directory whose codexmgr.toml should be updated.
        codexmgr_home: codexmgr home directory containing package sources.
        profiles: Profile names to merge into every selected package.

    Returns:
        Package names that were enabled.
    """
    return _mutate_packages(names, cwd, codexmgr_home, profiles, enabled=True)


def disable_packages(
    names: list[str],
    cwd: Path,
    codexmgr_home: Path,
    profiles: list[str],
) -> list[str]:
    """Disable selected entries from multiple packaged configurations.

    Args:
        names: Bare package names.
        cwd: Project directory whose codexmgr.toml should be updated.
        codexmgr_home: codexmgr home directory containing package sources.
        profiles: Profile names to merge into every selected package.

    Returns:
        Package names that were disabled.
    """
    return _mutate_packages(names, cwd, codexmgr_home, profiles, enabled=False)


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


def apply_package_entries_to_config(
    config: MutableMapping[str, Any],
    entries: PackageEntries,
    *,
    enabled: bool,
) -> None:
    """Apply package entry state to an in-memory project config.

    Args:
        config: Parsed project config to mutate.
        entries: Package entries selected from root and profiles.
        enabled: Whether entries should be enabled or disabled.
    """
    if enabled:
        _add_agentsmd(config, entries.agentsmd)
    else:
        _remove_agentsmd(config, entries.agentsmd)
    for skill in entries.skills:
        set_skill_state_in_config(config, skill, enabled=enabled)
    for agent in entries.agents:
        set_agent_state_in_config(config, agent, enabled=enabled)
    for hook in entries.hooks:
        set_hook_state_in_config(config, hook, enabled=enabled)


def selected_entries_for_package(
    name: str,
    codexmgr_home: Path,
    profiles: list[str],
) -> PackageEntries:
    """Load a package and return entries for selected profiles.

    Args:
        name: Bare package name.
        codexmgr_home: codexmgr home directory containing package sources.
        profiles: Profile names to merge.

    Returns:
        Root package entries plus selected profile entries.
    """
    package = load_package_config(name, codexmgr_home)
    return selected_package_entries(package, profiles)


def _mutate_packages(
    names: list[str],
    cwd: Path,
    codexmgr_home: Path,
    profiles: list[str],
    *,
    enabled: bool,
) -> list[str]:
    """Apply package mutations to project config with a single write.

    Args:
        names: Bare package names.
        cwd: Project directory whose codexmgr.toml should be updated.
        codexmgr_home: codexmgr home directory containing package sources.
        profiles: Profile names to merge into every package.
        enabled: Whether entries should be enabled or disabled.

    Returns:
        Package names that were mutated.
    """
    selections = [
        selected_entries_for_package(name, codexmgr_home, profiles) for name in names
    ]
    if enabled:
        for entries in selections:
            _validate_enable_sources(entries, cwd, codexmgr_home)
    require_codex_dir(cwd)
    config = load_optional_toml_file(config_path(cwd))
    for entries in selections:
        apply_package_entries_to_config(config, entries, enabled=enabled)
    write_toml_file(config_path(cwd), config)
    return list(names)


def _validate_enable_sources(
    entries: PackageEntries,
    cwd: Path,
    codexmgr_home: Path,
) -> None:
    """Validate package references that direct enable commands validate.

    Args:
        entries: Selected package entries.
        cwd: Project directory used to resolve path-backed AGENTS.md templates.
        codexmgr_home: codexmgr home directory used to resolve named sources.
    """
    for reference in entries.agentsmd:
        resolve_template(reference, cwd, codexmgr_home)
    for agent in entries.agents:
        require_agent_source(agent, codexmgr_home)
    for hook in entries.hooks:
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
