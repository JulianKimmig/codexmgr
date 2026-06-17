"""Low-level staged mutation helpers for the TUI."""

from collections.abc import MutableMapping
from pathlib import Path
from typing import Any

from ..custom_agents.config import agent_lists
from ..custom_agents.sources import require_agent_source
from ..core.paths import resolve_template
from ..core.toml_io import ensure_toml_table
from ..hooks.config import hook_lists
from ..hooks.sources import require_hook_source
from ..packages.config import PackageEntries
from ..project.config import agents_md_sources
from ..rules.config import rule_lists
from ..rules.sources import canonical_rule_ref
from ..skills.config import _skill_lists


def validate_package_enable(
    entries: PackageEntries,
    cwd: Path,
    codexmgr_home: Path,
) -> None:
    """Validate package references that require enable-time validation.

    Args:
        entries: Package entries to validate.
        cwd: Project directory used for path-backed AGENTS.md templates.
        codexmgr_home: Codexmgr home containing reusable resources.
    """
    for reference in entries.agentsmd:
        resolve_template(reference, cwd, codexmgr_home)
    for agent in entries.agents:
        require_agent_source(agent, codexmgr_home)
    for hook in entries.hooks:
        require_hook_source(hook, codexmgr_home)
    for rule in entries.rules:
        canonical_rule_ref(rule, codexmgr_home)


def package_checks(config: MutableMapping[str, Any], entries: PackageEntries) -> list[str]:
    """Return per-entry states for package entries.

    Args:
        config: Staged codexmgr.toml document.
        entries: Package entries to inspect.

    Returns:
        State labels for all package entries.
    """
    enabled_skills, disabled_skills = _skill_lists(config)
    enabled_agents, disabled_agents = agent_lists(config)
    enabled_hooks, disabled_hooks = hook_lists(config)
    enabled_rules, disabled_rules = rule_lists(config)
    sources = agents_md_sources(config)
    return [
        *(_agentsmd_state(reference, sources) for reference in entries.agentsmd),
        *(_state(agent, enabled_agents, disabled_agents) for agent in entries.agents),
        *(_state(skill, enabled_skills, disabled_skills) for skill in entries.skills),
        *(_state(hook, enabled_hooks, disabled_hooks) for hook in entries.hooks),
        *(_state(rule, enabled_rules, disabled_rules) for rule in entries.rules),
    ]


def _agentsmd_state(reference: str, sources: list[str]) -> str:
    """Return the staged state for one AGENTS.md package entry.

    Args:
        reference: Template reference.
        sources: Configured AGENTS.md sources.

    Returns:
        ``enabled`` when present, otherwise ``available``.
    """
    return "enabled" if reference in sources else "available"


def _state(name: str, enabled: list[str], disabled: list[str]) -> str:
    """Return the staged state for one enable/disable package entry.

    Args:
        name: Entry reference.
        enabled: Enabled refs.
        disabled: Disabled refs.

    Returns:
        ``enabled``, ``disabled``, or ``available``.
    """
    if name in enabled:
        return "enabled"
    if name in disabled:
        return "disabled"
    return "available"


def remove_skill(config: MutableMapping[str, Any], skill: str) -> None:
    """Remove a skill from both staged skill state lists.

    Args:
        config: Staged codexmgr.toml document.
        skill: Skill reference to remove.
    """
    if "skills" not in config:
        return
    enabled, disabled = _skill_lists(config)
    skills = ensure_toml_table(config, "skills", "codexmgr.toml [skills] must be a table")
    skills["enabled"] = [item for item in enabled if item != skill]
    skills["disabled"] = [item for item in disabled if item != skill]


def remove_hook(config: MutableMapping[str, Any], hook: str) -> None:
    """Remove a hook from both staged hook state lists.

    Args:
        config: Staged codexmgr.toml document.
        hook: Hook bundle name to remove.
    """
    if "hooks" not in config:
        return
    enabled, disabled = hook_lists(config)
    hooks = ensure_toml_table(config, "hooks", "codexmgr.toml [hooks] must be a table")
    hooks["enabled"] = [item for item in enabled if item != hook]
    hooks["disabled"] = [item for item in disabled if item != hook]


def remove_rule(config: MutableMapping[str, Any], rule: str) -> None:
    """Remove a rule from both staged rule state lists.

    Args:
        config: Staged codexmgr.toml document.
        rule: Rule reference to remove.
    """
    if "rules" not in config:
        return
    enabled, disabled = rule_lists(config)
    rules = ensure_toml_table(config, "rules", "codexmgr.toml [rules] must be a table")
    rules["enabled"] = [item for item in enabled if item != rule]
    rules["disabled"] = [item for item in disabled if item != rule]


def remove_agent(config: MutableMapping[str, Any], agent: str) -> None:
    """Remove a custom agent from both staged agent state lists.

    Args:
        config: Staged codexmgr.toml document.
        agent: Custom-agent name to remove.
    """
    if "agents" not in config:
        return
    enabled, disabled = agent_lists(config)
    agents = ensure_toml_table(config, "agents", "codexmgr.toml [agents] must be a table")
    agents["enabled"] = [item for item in enabled if item != agent]
    agents["disabled"] = [item for item in disabled if item != agent]


def remove_mcp_server(config: MutableMapping[str, Any], server_id: str) -> None:
    """Remove a staged MCP server created only by TUI selection.

    Args:
        config: Staged codexmgr.toml document.
        server_id: MCP server id to remove.
    """
    mcp = config.get("mcp")
    if not isinstance(mcp, MutableMapping):
        return
    servers = mcp.get("servers")
    if not isinstance(servers, MutableMapping):
        return
    servers.pop(server_id, None)
