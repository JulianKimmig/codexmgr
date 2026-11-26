"""Apply flattened package resources through the project resource handlers."""

from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

from ..core.paths import resolve_template
from ..core.toml_io import ensure_toml_table
from ..custom_agents.config import agent_lists, set_agent_state_in_config
from ..custom_agents.sources import require_agent_source
from ..guides.config import guide_lists, remove_guide, set_guide_state_in_config
from ..guides.sources import canonical_guide_ref
from ..hooks.config import hook_lists, set_hook_state_in_config
from ..hooks.sources import require_hook_source
from ..project.config import agents_md_sources, set_agents_md_sources
from ..rules.config import rule_lists, set_rule_state_in_config
from ..rules.sources import canonical_rule_ref
from ..skills.groups import set_skill_references_state
from .config import PackageEntries

_STATE_LISTS = {
    "agents": agent_lists, "hooks": hook_lists, "rules": rule_lists, "guides": guide_lists,
}


def validate_package_enable(entries: PackageEntries, cwd: Path, codexmgr_home: Path) -> None:
    """Validate entries whose source must be present when enabling a package.

    Args:
        entries: Flattened package resources.
        cwd: Project directory for path-based templates.
        codexmgr_home: Manager home for reusable sources.
    """
    for reference in entries.agentsmd:
        resolve_template(reference, cwd, codexmgr_home)
    for agent in entries.agents:
        require_agent_source(agent, codexmgr_home)
    for hook in entries.hooks:
        require_hook_source(hook, codexmgr_home)
    for rule in entries.rules:
        canonical_rule_ref(rule, codexmgr_home)
    for guide in entries.guides:
        canonical_guide_ref(guide, codexmgr_home)


def apply_package_entries(
    config: MutableMapping[str, Any],
    entries: PackageEntries,
    codexmgr_home: Path,
    *,
    state: str,
    cwd: Path,
    codex_home: Path,
) -> None:
    """Apply one resource state to a caller-owned working configuration.

    Args:
        config: Working project configuration.
        entries: Flattened package resources.
        codexmgr_home: Manager home for reusable sources.
        state: Enabled, disabled, or available.
        cwd: Project directory for resource resolution.
        codex_home: Codex home for skill discovery.
    """
    enabled = state == "enabled"
    for guide in entries.guides:
        if state == "available":
            remove_guide(config, guide, codexmgr_home)
        else:
            set_guide_state_in_config(config, guide, codexmgr_home, enabled=enabled)
    if entries.skills:
        set_skill_references_state(config, entries.skills, state, cwd, codex_home, codexmgr_home)
    if entries.agentsmd:
        sources = agents_md_sources(config)
        if enabled:
            sources.extend(ref for ref in entries.agentsmd if ref not in sources)
        else:
            removed = set(entries.agentsmd)
            sources = [source for source in sources if source not in removed]
        set_agents_md_sources(config, sources)
    if state == "available":
        remove_package_refs(config, "rules", entries.rules)
        remove_package_refs(config, "agents", entries.agents)
        remove_package_refs(config, "hooks", entries.hooks)
        return
    for rule in entries.rules:
        set_rule_state_in_config(config, rule, codexmgr_home, enabled=enabled)
    for agent in entries.agents:
        set_agent_state_in_config(config, agent, enabled=enabled)
    for hook in entries.hooks:
        set_hook_state_in_config(config, hook, enabled=enabled)


def remove_package_refs(
    config: MutableMapping[str, Any], family: str, refs: list[str], *, enabled_only: bool = False,
) -> None:
    """Remove exact references from configured state, optionally preserving exclusions.

    Args:
        config: Working project configuration, with validated resource tables.
        family: Project config resource table.
        refs: Project config reference spellings to remove.
        enabled_only: Whether to leave the disabled list untouched.
    """
    if not refs or family not in config:
        return
    enabled, disabled = _STATE_LISTS[family](config)
    table = ensure_toml_table(config, family, f"codexmgr.toml [{family}] must be a table")
    remove = set(refs)
    table["enabled"] = [ref for ref in enabled if ref not in remove]
    if not enabled_only:
        table["disabled"] = [ref for ref in disabled if ref not in remove]
