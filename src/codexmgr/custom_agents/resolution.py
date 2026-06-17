"""Resolve project custom-agent configuration into generated state."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import agent_lists
from .copies import (
    AgentCopy,
    expected_agent_copy_files,
    obsolete_agent_copy_targets,
    validate_agent_copy_targets,
)
from .sources import project_agent_path, resolve_agent_source


@dataclass(frozen=True)
class AgentResolution:
    """Resolved custom-agent configuration state.

    Attributes:
        copies: Managed project-local custom-agent copies.
        copy_files: Expected files inside managed custom-agent copies.
        obsolete_copy_targets: Previous managed custom-agent targets to remove.
        enabled: Configured enabled custom-agent names.
        disabled: Configured disabled custom-agent names.
    """

    copies: list[AgentCopy]
    copy_files: list[Any]
    obsolete_copy_targets: list[Path]
    enabled: list[str]
    disabled: list[str]


def empty_agent_resolution() -> AgentResolution:
    """Return an empty custom-agent resolution for projects without config.

    Returns:
        A resolved custom-agent state with no generated outputs.
    """
    return AgentResolution([], [], [], [], [])


def resolve_project_agents(
    project_config: Mapping[str, Any],
    cwd: Path,
    codexmgr_home: Path,
    previous_lock: Mapping[str, Any],
) -> AgentResolution:
    """Resolve configured custom agents into managed copy state.

    Args:
        project_config: Parsed project codexmgr config.
        cwd: Project directory.
        codexmgr_home: codexmgr home directory.
        previous_lock: Previous codexmgr lock data.

    Returns:
        Resolved custom-agent state.
    """
    enabled, disabled = agent_lists(project_config)
    copies = _managed_agent_copies(enabled, cwd, codexmgr_home)
    validate_agent_copy_targets(copies, previous_lock)
    return AgentResolution(
        copies,
        expected_agent_copy_files(copies),
        obsolete_agent_copy_targets(previous_lock, copies),
        enabled,
        disabled,
    )


def _managed_agent_copies(
    enabled: list[str],
    cwd: Path,
    codexmgr_home: Path,
) -> list[AgentCopy]:
    """Build managed copy plans for enabled custom agents.

    Args:
        enabled: Configured enabled custom-agent names.
        cwd: Project directory.
        codexmgr_home: codexmgr home directory.

    Returns:
        Managed custom-agent copy plans.
    """
    copies: list[AgentCopy] = []
    for name in enabled:
        source = resolve_agent_source(name, codexmgr_home)
        if source is not None:
            copies.append(AgentCopy(name, source.source_file, project_agent_path(cwd, name)))
    return copies
