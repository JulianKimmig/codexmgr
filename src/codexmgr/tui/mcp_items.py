"""Build selectable MCP source items for the interactive TUI."""

from ..core.errors import CommandError
from ..mcp.project import mcp_source_names
from ..mcp.sources import available_mcp_source_names, resolve_mcp_source
from .models import ManagedItem
from .state import StagedConfig


def mcp_items(staged: StagedConfig) -> tuple[list[ManagedItem], str]:
    """Return reusable MCP source items and an optional warning.

    Args:
        staged: Staged project configuration.

    Returns:
        Display items and a warning message when source inspection failed.
    """
    try:
        enabled = mcp_source_names(staged.config)
        available = set(available_mcp_source_names(staged.codexmgr_home))
        names = sorted(available | set(enabled))
        return [_mcp_item(name, enabled, available, staged) for name in names], ""
    except CommandError as exc:
        return [], str(exc)


def _mcp_item(
    name: str,
    enabled: list[str],
    available: set[str],
    staged: StagedConfig,
) -> ManagedItem:
    """Build one reusable MCP source display item.

    Args:
        name: MCP source name.
        enabled: Project-enabled source names.
        available: Source names present in CODEXMGR_HOME.
        staged: Staged project configuration.

    Returns:
        Display item for the source.
    """
    if name in enabled and name not in available:
        return ManagedItem(name, "enabled", True, "source missing")
    source = resolve_mcp_source(name, staged.codexmgr_home)
    detail = f"servers={', '.join(sorted(source.servers))}" if source is not None else ""
    state = "enabled" if name in enabled else "available"
    return ManagedItem(name, state, False, detail)
