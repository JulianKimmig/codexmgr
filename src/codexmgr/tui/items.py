"""Build selectable display items for staged TUI screens."""

from pathlib import Path

from ..agents.manager import list_agentsmd_options
from ..custom_agents.config import agent_lists
from ..custom_agents.sources import available_agent_names, resolve_agent_source
from ..core.paths import resolve_template
from ..core.errors import CommandError
from ..hooks.config import hook_lists
from ..hooks.sources import available_hook_names, resolve_hook_source
from ..mcp.config import resolve_overrides
from ..mcp.discovery import available_state, discover_codex_servers
from ..packages.config import load_package_config
from ..packages.sources import available_package_names
from ..project.config import agents_md_sources
from ..skills.config import _skill_lists
from ..skills.sources import available_skill_names, resolve_skill_file
from .models import DashboardSummary, ManagedItem
from .package_refs import package_profile_value, package_value
from .state import StagedConfig


def dashboard_summary(staged: StagedConfig, diff_count: int) -> DashboardSummary:
    """Build dashboard summary data for the staged project.

    Args:
        staged: Staged project configuration.
        diff_count: Number of staged generated diffs.

    Returns:
        Dashboard display data.
    """
    return DashboardSummary(
        str(staged.cwd),
        str(staged.codex_home),
        str(staged.codexmgr_home),
        staged.dirty(),
        diff_count,
    )


def agentsmd_items(staged: StagedConfig) -> list[ManagedItem]:
    """Return staged AGENTS.md source items.

    Args:
        staged: Staged project configuration.

    Returns:
        Sorted display items.
    """
    sources = agents_md_sources(staged.config)
    names = sorted(set(list_agentsmd_options(staged.codexmgr_home)) | set(sources))
    return [
        ManagedItem(name, "enabled" if name in sources else "available", _missing_template(name, staged))
        for name in names
    ]


def skill_items(staged: StagedConfig) -> list[ManagedItem]:
    """Return staged skill items.

    Args:
        staged: Staged project configuration.

    Returns:
        Sorted display items.
    """
    enabled, disabled = _skill_lists(staged.config)
    available = set(available_skill_names(staged.cwd, staged.codex_home, staged.codexmgr_home))
    names = sorted(available | set(enabled) | set(disabled))
    return [
        ManagedItem(
            name,
            _state(name, enabled, disabled),
            _missing_skill(name, staged),
        )
        for name in names
    ]


def hook_items(staged: StagedConfig) -> list[ManagedItem]:
    """Return staged hook bundle items.

    Args:
        staged: Staged project configuration.

    Returns:
        Sorted display items.
    """
    enabled, disabled = hook_lists(staged.config)
    available = set(available_hook_names(staged.codexmgr_home))
    names = sorted(available | set(enabled) | set(disabled))
    return [
        ManagedItem(name, _state(name, enabled, disabled), _missing_hook(name, staged))
        for name in names
    ]


def agent_items(staged: StagedConfig) -> list[ManagedItem]:
    """Return staged custom-agent items.

    Args:
        staged: Staged project configuration.

    Returns:
        Sorted display items.
    """
    enabled, disabled = agent_lists(staged.config)
    available = set(available_agent_names(staged.codexmgr_home))
    names = sorted(available | set(enabled) | set(disabled))
    return [
        ManagedItem(name, _state(name, enabled, disabled), _missing_agent(name, staged))
        for name in names
    ]


def package_items(staged: StagedConfig) -> list[ManagedItem]:
    """Return package items with computed staged state.

    Args:
        staged: Staged project configuration.

    Returns:
        Sorted display items.
    """
    items: list[ManagedItem] = []
    for name in available_package_names(staged.codexmgr_home):
        try:
            package = load_package_config(name, staged.codexmgr_home)
            items.append(
                ManagedItem(
                    name,
                    staged.package_state(name),
                    detail="package",
                    value=package_value(name),
                ),
            )
            for profile in sorted(package.profiles):
                items.append(
                    ManagedItem(
                        f"{name} / {profile}",
                        staged.package_profile_state(name, profile),
                        detail="profile",
                        value=package_profile_value(name, profile),
                    ),
                )
        except CommandError as exc:
            items.append(ManagedItem(name, "error", True, str(exc), package_value(name)))
    return items


def mcp_items(staged: StagedConfig, *, discover: bool) -> tuple[list[ManagedItem], str]:
    """Return MCP server items and an optional discovery warning.

    Args:
        staged: Staged project configuration.
        discover: Whether to call the Codex CLI for available servers.

    Returns:
        Display items and a warning message when discovery failed.
    """
    overrides = resolve_overrides(staged.config, strict=False)
    available = {}
    warning = ""
    if discover:
        try:
            available = discover_codex_servers(staged.cwd)
        except CommandError as exc:
            warning = str(exc)
    names = sorted(set(available) | set(overrides))
    return [_mcp_item(name, overrides, available) for name in names], warning


def _state(name: str, enabled: list[str], disabled: list[str]) -> str:
    """Return enabled, disabled, or available for a staged item.

    Args:
        name: Item name.
        enabled: Enabled staged entries.
        disabled: Disabled staged entries.

    Returns:
        Display state.
    """
    if name in enabled:
        return "enabled"
    if name in disabled:
        return "disabled"
    return "available"


def _missing_template(name: str, staged: StagedConfig) -> bool:
    """Return whether an AGENTS.md template is missing.

    Args:
        name: Template name or reference.
        staged: Staged project configuration.

    Returns:
        True when the template cannot be resolved.
    """
    try:
        resolve_template(name, staged.cwd, staged.codexmgr_home)
        return False
    except CommandError:
        return True


def _missing_skill(name: str, staged: StagedConfig) -> bool:
    """Return whether a configured skill cannot be resolved.

    Args:
        name: Skill name or reference.
        staged: Staged project configuration.

    Returns:
        True when the skill is configured and missing.
    """
    enabled, disabled = _skill_lists(staged.config)
    if name not in enabled and name not in disabled:
        return False
    return resolve_skill_file(name, staged.cwd, staged.codex_home, staged.codexmgr_home) is None


def _missing_hook(name: str, staged: StagedConfig) -> bool:
    """Return whether a configured hook cannot be resolved.

    Args:
        name: Hook bundle name.
        staged: Staged project configuration.

    Returns:
        True when the hook is configured and missing.
    """
    enabled, disabled = hook_lists(staged.config)
    if name not in enabled and name not in disabled:
        return False
    return resolve_hook_source(name, staged.codexmgr_home) is None


def _missing_agent(name: str, staged: StagedConfig) -> bool:
    """Return whether a configured custom agent cannot be resolved.

    Args:
        name: Custom-agent name.
        staged: Staged project configuration.

    Returns:
        True when the custom agent is configured and missing.
    """
    enabled, disabled = agent_lists(staged.config)
    if name not in enabled and name not in disabled:
        return False
    return resolve_agent_source(name, staged.codexmgr_home) is None


def _mcp_item(name: str, overrides: dict, available: dict) -> ManagedItem:
    """Build one MCP display item.

    Args:
        name: MCP server id.
        overrides: Project-local overrides keyed by server id.
        available: Codex-discovered servers keyed by server id.

    Returns:
        MCP display item.
    """
    fields = overrides.get(name, {})
    state = _mcp_override_state(fields)
    detail = f"available={available_state(available.get(name))}"
    return ManagedItem(name, state, False, detail)


def _mcp_override_state(fields: dict) -> str:
    """Return MCP override state from configured fields.

    Args:
        fields: Project-local MCP override fields.

    Returns:
        Display state.
    """
    if fields.get("enabled") is True:
        return "enabled"
    if fields.get("enabled") is False:
        return "disabled"
    return "configured" if fields else "available"
