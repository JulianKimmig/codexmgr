"""Resolve project configuration inputs before generated-file building."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..agents.manager import resolve_locked_agents_md
from ..custom_agents.resolution import (
    AgentResolution,
    empty_agent_resolution,
    resolve_project_agents,
)
from ..hooks.resolution import (
    HookResolution,
    empty_hook_resolution,
    resolve_project_hooks,
)
from ..mcp.resolution import McpResolution, empty_mcp_resolution, resolve_project_mcp
from ..rules.resolution import (
    RuleResolution,
    empty_rule_resolution,
    resolve_project_rules,
)
from ..skills.resolution import SkillResolution, resolve_project_skills


@dataclass(frozen=True)
class ProjectResolution:
    """Resolved project inputs used to build generated files.

    Attributes:
        locked_agents_md: Resolved AGENTS.md source data.
        agents: Resolved custom-agent state.
        skills: Resolved skill state.
        hooks: Resolved hook state.
        rules: Resolved reusable-rule state.
        mcp: Resolved MCP state.
    """

    locked_agents_md: dict[str, Any]
    agents: AgentResolution
    skills: SkillResolution
    hooks: HookResolution
    rules: RuleResolution
    mcp: McpResolution


def resolve_project_components(
    config: Mapping[str, Any],
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    previous_lock: Mapping[str, Any],
) -> ProjectResolution:
    """Resolve all configured project component state.

    Args:
        config: Parsed project codexmgr configuration.
        cwd: Project directory.
        codex_home: Codex home used to resolve named skills.
        codexmgr_home: Codexmgr home used to resolve reusable resources.
        previous_lock: Existing codexmgr lock data.

    Returns:
        Resolved project component state.
    """
    return ProjectResolution(
        resolve_locked_agents_md(config, cwd, codexmgr_home),
        _resolve_agents(config, cwd, codexmgr_home, previous_lock),
        _resolve_skills(config, cwd, codex_home, codexmgr_home, previous_lock),
        _resolve_hooks(config, cwd, codexmgr_home, previous_lock),
        _resolve_rules(config, cwd, codexmgr_home, previous_lock),
        _resolve_mcp(config, codexmgr_home),
    )


def _resolve_skills(
    config: Mapping[str, Any],
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    previous_lock: Mapping[str, Any],
) -> SkillResolution:
    """Resolve skills only when the project config owns the skills table.

    Args:
        config: Parsed project codexmgr configuration.
        cwd: Project directory.
        codex_home: Codex home directory.
        codexmgr_home: Codexmgr home directory.
        previous_lock: Existing codexmgr lock data.

    Returns:
        Resolved skill state.
    """
    if "skills" not in config:
        return SkillResolution([], [], [])
    return resolve_project_skills(config, cwd, codex_home, codexmgr_home, previous_lock)


def _resolve_agents(
    config: Mapping[str, Any],
    cwd: Path,
    codexmgr_home: Path,
    previous_lock: Mapping[str, Any],
) -> AgentResolution:
    """Resolve custom agents only when the project config owns the agents table.

    Args:
        config: Parsed project codexmgr configuration.
        cwd: Project directory.
        codexmgr_home: Codexmgr home directory.
        previous_lock: Existing codexmgr lock data.

    Returns:
        Resolved custom-agent state.
    """
    if "agents" not in config:
        return empty_agent_resolution()
    return resolve_project_agents(config, cwd, codexmgr_home, previous_lock)


def _resolve_hooks(
    config: Mapping[str, Any],
    cwd: Path,
    codexmgr_home: Path,
    previous_lock: Mapping[str, Any],
) -> HookResolution:
    """Resolve hooks only when the project config owns the hooks table.

    Args:
        config: Parsed project codexmgr configuration.
        cwd: Project directory.
        codexmgr_home: Codexmgr home directory.
        previous_lock: Existing codexmgr lock data.

    Returns:
        Resolved hook state.
    """
    if "hooks" not in config:
        return empty_hook_resolution()
    return resolve_project_hooks(config, cwd, codexmgr_home, previous_lock)


def _resolve_rules(
    config: Mapping[str, Any],
    cwd: Path,
    codexmgr_home: Path,
    previous_lock: Mapping[str, Any],
) -> RuleResolution:
    """Resolve rules only when the project config owns the rules table.

    Args:
        config: Parsed project codexmgr configuration.
        cwd: Project directory.
        codexmgr_home: Codexmgr home directory.
        previous_lock: Existing codexmgr lock data.

    Returns:
        Resolved reusable-rule state.
    """
    if "rules" not in config:
        return empty_rule_resolution()
    return resolve_project_rules(config, cwd, codexmgr_home, previous_lock)


def _resolve_mcp(config: Mapping[str, Any], codexmgr_home: Path) -> McpResolution:
    """Resolve MCP only when the project config owns the MCP table.

    Args:
        config: Parsed project codexmgr configuration.
        codexmgr_home: Codexmgr home directory containing MCP source files.

    Returns:
        Resolved MCP state.
    """
    if "mcp" not in config:
        return empty_mcp_resolution()
    return resolve_project_mcp(config, codexmgr_home)
