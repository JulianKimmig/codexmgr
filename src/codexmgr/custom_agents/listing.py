"""Read-only listing helpers for managed Codex custom agents."""

from dataclasses import dataclass
from pathlib import Path

from ..core.paths import config_path
from ..core.toml_io import load_optional_toml_file
from .config import agent_lists
from .sources import available_agent_names, resolve_agent_source


@dataclass(frozen=True)
class AgentListItem:
    """Display state for one known custom agent.

    Attributes:
        name: Custom-agent name or configured reference.
        state: One of ``available``, ``enabled``, or ``disabled``.
        missing: Whether a configured custom agent does not resolve.
    """

    name: str
    state: str
    missing: bool = False


def agent_list_lines(cwd: Path, codexmgr_home: Path) -> list[str]:
    """Build display lines for available and configured custom agents.

    Args:
        cwd: Project directory whose configured custom agents should be read.
        codexmgr_home: codexmgr home containing custom-agent sources.

    Returns:
        Sorted custom-agent list lines suitable for CLI output.
    """
    return [_format_item(item) for item in list_agent_items(cwd, codexmgr_home)]


def list_agent_items(cwd: Path, codexmgr_home: Path) -> list[AgentListItem]:
    """List available and configured custom agents with project state.

    Args:
        cwd: Project directory whose configured custom agents should be read.
        codexmgr_home: codexmgr home containing custom-agent sources.

    Returns:
        Custom-agent items sorted by displayed name.
    """
    enabled, disabled = configured_agent_lists(cwd)
    available = set(available_agent_names(codexmgr_home))
    names = sorted(available | set(enabled) | set(disabled))
    return [_agent_item(name, enabled, disabled, available, codexmgr_home) for name in names]


def configured_agent_lists(cwd: Path) -> tuple[list[str], list[str]]:
    """Read configured enabled and disabled custom-agent references.

    Args:
        cwd: Project directory whose codexmgr.toml should be read when present.

    Returns:
        Enabled and disabled custom-agent name lists.
    """
    return agent_lists(load_optional_toml_file(config_path(cwd)))


def missing_enabled_agents(cwd: Path, codexmgr_home: Path) -> list[str]:
    """Return enabled custom-agent references that do not resolve.

    Args:
        cwd: Project directory whose configured custom agents should be read.
        codexmgr_home: codexmgr home containing custom-agent sources.

    Returns:
        Enabled custom-agent names that are currently missing.
    """
    enabled, _ = configured_agent_lists(cwd)
    return [name for name in enabled if resolve_agent_source(name, codexmgr_home) is None]


def _agent_item(
    name: str,
    enabled: list[str],
    disabled: list[str],
    available: set[str],
    codexmgr_home: Path,
) -> AgentListItem:
    """Build one custom-agent list item.

    Args:
        name: Custom-agent name or configured reference.
        enabled: Enabled custom-agent names.
        disabled: Disabled custom-agent names.
        available: Available named custom agents.
        codexmgr_home: codexmgr home containing custom-agent sources.

    Returns:
        Display item for the custom agent.
    """
    if name in enabled:
        return AgentListItem(name, "enabled", _is_missing(name, codexmgr_home))
    if name in disabled:
        return AgentListItem(name, "disabled", _is_missing(name, codexmgr_home))
    return AgentListItem(name, "available", name not in available)


def _is_missing(name: str, codexmgr_home: Path) -> bool:
    """Return whether a configured custom agent is missing.

    Args:
        name: Configured custom-agent name.
        codexmgr_home: codexmgr home containing custom-agent sources.

    Returns:
        True when no custom-agent source file resolves for the reference.
    """
    return resolve_agent_source(name, codexmgr_home) is None


def _format_item(item: AgentListItem) -> str:
    """Format one custom-agent list item.

    Args:
        item: Custom-agent list item to format.

    Returns:
        Human-readable CLI line.
    """
    suffix = " (missing)" if item.missing else ""
    return f"{item.state} {item.name}{suffix}"
