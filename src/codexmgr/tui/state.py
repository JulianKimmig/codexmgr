"""Staged project configuration for the interactive TUI."""

from __future__ import annotations

from collections.abc import MutableMapping
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.paths import config_path, resolve_template
from ..core.toml_io import dump_toml, load_optional_toml_file, write_toml_file
from ..hooks.config import hook_lists, set_hook_state_in_config
from ..hooks.sources import require_hook_source
from ..mcp.config import resolve_overrides, set_enabled_in_config
from ..packages.config import PackageConfig, PackageEntries, load_package_config
from ..packages.mutation import apply_package_entries_to_config
from ..project.apply import apply_project_config
from ..project.config import agents_md_sources, require_codex_dir, set_agents_md_sources
from ..skills.config import _skill_lists, set_skill_state_in_config
from .mutations import (
    package_checks,
    remove_hook,
    remove_mcp_server,
    remove_skill,
    validate_package_enable,
)


@dataclass
class StagedConfig:
    """Mutable in-memory project configuration.

    Attributes:
        cwd: Project directory being managed.
        codex_home: Codex home used for skill resolution during apply.
        codexmgr_home: Codexmgr home used for reusable resources.
        config: Parsed TOML document staged for later saving.
        original_text: Serialized config text as it existed when loaded.
        original_skills: Skill refs configured when the stage was loaded.
        original_hooks: Hook names configured when the stage was loaded.
        original_mcp_servers: MCP server ids configured when the stage was loaded.
    """

    cwd: Path
    codex_home: Path
    codexmgr_home: Path
    config: MutableMapping[str, Any]
    original_text: str
    original_skills: frozenset[str]
    original_hooks: frozenset[str]
    original_mcp_servers: frozenset[str]

    def dirty(self) -> bool:
        """Return whether staged config differs from the loaded file.

        Returns:
            True when the staged TOML serializes differently from the original.
        """
        return dump_toml(self.config) != self.original_text

    def set_agentsmd_enabled(self, reference: str, enabled: bool) -> None:
        """Add or remove an AGENTS.md source reference.

        Args:
            reference: Template name or path-like reference.
            enabled: Whether the reference should be present.
        """
        if enabled:
            resolve_template(reference, self.cwd, self.codexmgr_home)
        sources = agents_md_sources(self.config)
        if enabled and reference not in sources:
            sources.append(reference)
        if not enabled:
            sources = [source for source in sources if source != reference]
        set_agents_md_sources(self.config, sources)

    def set_skill_enabled(self, skill: str, enabled: bool) -> None:
        """Set a skill reference to enabled or disabled.

        Args:
            skill: Skill name or path reference.
            enabled: Desired enabled state.
        """
        set_skill_state_in_config(self.config, skill, enabled=enabled)

    def set_skill_selected(self, skill: str, selected: bool) -> None:
        """Apply checkbox semantics for a skill selection.

        Args:
            skill: Skill name or path reference.
            selected: Whether the skill is currently checked.
        """
        if selected:
            self.set_skill_enabled(skill, True)
        elif skill in self.original_skills:
            self.set_skill_enabled(skill, False)
        else:
            remove_skill(self.config, skill)

    def set_hook_enabled(self, hook: str, enabled: bool) -> None:
        """Set a hook bundle to enabled or disabled.

        Args:
            hook: Hook bundle name.
            enabled: Desired enabled state.
        """
        if enabled:
            require_hook_source(hook, self.codexmgr_home)
        set_hook_state_in_config(self.config, hook, enabled=enabled)

    def set_hook_selected(self, hook: str, selected: bool) -> None:
        """Apply checkbox semantics for a hook selection.

        Args:
            hook: Hook bundle name.
            selected: Whether the hook is currently checked.
        """
        if selected:
            self.set_hook_enabled(hook, True)
        elif hook in self.original_hooks:
            self.set_hook_enabled(hook, False)
        else:
            remove_hook(self.config, hook)

    def set_package_enabled(self, name: str, enabled: bool) -> None:
        """Enable or disable all entries from a packaged configuration.

        Args:
            name: Package name under CODEXMGR_HOME/packages.
            enabled: Whether package entries should be active.
        """
        package = load_package_config(name, self.codexmgr_home)
        self._set_package_entries(_root_entries(package), enabled)

    def set_package_profile_enabled(
        self,
        name: str,
        profile: str,
        enabled: bool,
    ) -> None:
        """Enable or disable one package profile entry set.

        Args:
            name: Package name under CODEXMGR_HOME/packages.
            profile: Profile name within the package config.
            enabled: Whether profile entries should be active.
        """
        package = load_package_config(name, self.codexmgr_home)
        self._set_package_entries(_profile_entries(package, profile), enabled)

    def package_state(self, name: str) -> str:
        """Return enabled, partial, or disabled for a package.

        Args:
            name: Package name under CODEXMGR_HOME/packages.

        Returns:
            Package state computed from staged entries.
        """
        package = load_package_config(name, self.codexmgr_home)
        return _state_from_checks(package_checks(self.config, _root_entries(package)))

    def package_profile_state(self, name: str, profile: str) -> str:
        """Return enabled, partial, or disabled for a package profile.

        Args:
            name: Package name under CODEXMGR_HOME/packages.
            profile: Profile name within the package config.

        Returns:
            Package profile state computed from staged entries.
        """
        package = load_package_config(name, self.codexmgr_home)
        return _state_from_checks(
            package_checks(self.config, _profile_entries(package, profile)),
        )

    def _set_package_entries(self, entries: PackageEntries, enabled: bool) -> None:
        """Enable or disable package entries in staged config.

        Args:
            entries: Package root or profile entries.
            enabled: Whether entries should be active.
        """
        if enabled:
            validate_package_enable(entries, self.cwd, self.codexmgr_home)
        apply_package_entries_to_config(self.config, entries, enabled=enabled)

    def set_mcp_enabled(self, server_id: str, enabled: bool) -> None:
        """Set an MCP server enabled override.

        Args:
            server_id: MCP server id.
            enabled: Desired enabled state.
        """
        set_enabled_in_config(self.config, server_id, enabled)

    def set_mcp_selected(self, server_id: str, selected: bool) -> None:
        """Apply checkbox semantics for an MCP server.

        Args:
            server_id: MCP server id.
            selected: Whether the server is currently checked.
        """
        if selected or server_id in self.original_mcp_servers:
            self.set_mcp_enabled(server_id, selected)
        else:
            remove_mcp_server(self.config, server_id)


def _root_entries(package: PackageConfig) -> PackageEntries:
    """Return root entries for a package.

    Args:
        package: Package configuration.

    Returns:
        Package root entries.
    """
    return PackageEntries(package.agentsmd, package.hooks, package.skills)


def _profile_entries(package: PackageConfig, profile: str) -> PackageEntries:
    """Return entries for one package profile.

    Args:
        package: Package configuration.
        profile: Profile name.

    Returns:
        Package profile entries.
    """
    return package.profiles[profile]


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


def load_staged_config(cwd: Path, codex_home: Path, codexmgr_home: Path) -> StagedConfig:
    """Load project configuration into a staged config object.

    Args:
        cwd: Project directory.
        codex_home: Codex home used for apply.
        codexmgr_home: Codexmgr home containing reusable resources.

    Returns:
        Staged project configuration.
    """
    require_codex_dir(cwd)
    path = config_path(cwd)
    original_text = path.read_text(encoding="utf-8") if path.exists() else ""
    config = load_optional_toml_file(path)
    enabled_skills, disabled_skills = _skill_lists(config)
    enabled_hooks, disabled_hooks = hook_lists(config)
    mcp_servers = resolve_overrides(config, strict=False)
    return StagedConfig(
        cwd,
        codex_home,
        codexmgr_home,
        deepcopy(config),
        original_text,
        frozenset([*enabled_skills, *disabled_skills]),
        frozenset([*enabled_hooks, *disabled_hooks]),
        frozenset(mcp_servers),
    )


def save_staged_config(staged: StagedConfig, *, no_sync: bool) -> list[str]:
    """Write staged config and optionally apply generated files.

    Args:
        staged: Staged project configuration to persist.
        no_sync: Whether to skip apply after writing codexmgr.toml.

    Returns:
        User-facing status messages.
    """
    write_toml_file(config_path(staged.cwd), staged.config)
    messages = ["Saved project configuration"]
    if not no_sync:
        apply_project_config(staged.cwd, staged.codex_home, staged.codexmgr_home)
        messages.append("Applied project Codex configuration")
    staged.original_text = dump_toml(staged.config)
    return messages
