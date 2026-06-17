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


def package_checks(config: MutableMapping[str, Any], entries: PackageEntries) -> list[bool]:
    """Return per-entry active checks for package entries.

    Args:
        config: Staged codexmgr.toml document.
        entries: Package entries to inspect.

    Returns:
        Boolean active states for all package entries.
    """
    enabled_skills, _ = _skill_lists(config)
    enabled_agents, _ = agent_lists(config)
    enabled_hooks, _ = hook_lists(config)
    sources = agents_md_sources(config)
    return [
        *(reference in sources for reference in entries.agentsmd),
        *(agent in enabled_agents for agent in entries.agents),
        *(skill in enabled_skills for skill in entries.skills),
        *(hook in enabled_hooks for hook in entries.hooks),
    ]


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
