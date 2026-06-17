"""Section-specific TUI item and selection dispatch."""

from ..core.errors import CommandError
from .items import agent_items, agentsmd_items, hook_items, mcp_items, package_items, rule_items, skill_items
from .models import ManagedItem
from .mutations import remove_agent, remove_hook, remove_rule, remove_skill
from .package_refs import parse_package_value
from .package_selection import set_package_selection
from .state import StagedConfig

TRI_STATE_SECTIONS = {"skills", "hooks", "agents", "rules", "packages"}


def items_for_section(staged: StagedConfig, section: str) -> tuple[list[ManagedItem], str]:
    """Return display items for one TUI section.

    Args:
        staged: Staged project configuration.
        section: Active section identifier.

    Returns:
        Display items and optional warning text.
    """
    if section == "agentsmd":
        return agentsmd_items(staged), ""
    if section == "skills":
        return skill_items(staged), ""
    if section == "hooks":
        return hook_items(staged), ""
    if section == "agents":
        return agent_items(staged), ""
    if section == "rules":
        return rule_items(staged), ""
    if section == "packages":
        return package_items(staged), ""
    if section == "mcp":
        return mcp_items(staged, discover=True)
    return [], ""


def set_section_selected(staged: StagedConfig, section: str, value: str, selected: bool) -> None:
    """Apply one selected state to the active section.

    Args:
        staged: Staged project configuration.
        section: Active section identifier.
        value: Item value from the selection list.
        selected: Whether the item is selected.

    Raises:
        CommandError: If the selected item cannot be resolved or updated.
    """
    if section == "agentsmd":
        staged.set_agentsmd_enabled(value, selected)
    elif section == "skills":
        staged.set_skill_selected(value, selected)
    elif section == "hooks":
        staged.set_hook_selected(value, selected)
    elif section == "agents":
        staged.set_agent_selected(value, selected)
    elif section == "rules":
        staged.set_rule_selected(value, selected)
    elif section == "packages":
        set_package_selection(staged, value, selected)
    elif section == "mcp":
        staged.set_mcp_selected(value, selected)
    else:
        raise CommandError(f"Unsupported TUI section: {section}")


def cycle_section_state(
    staged: StagedConfig,
    section: str,
    item: ManagedItem,
) -> None:
    """Cycle one selectable row through its section states.

    Args:
        staged: Staged project configuration.
        section: Active section identifier.
        item: Display item for the highlighted row.

    Raises:
        CommandError: If the selected item cannot be resolved or updated.
    """
    value = item.selection_value()
    next_state = _next_state(section, item.state)
    set_section_state(staged, section, value, next_state)


def set_section_state(
    staged: StagedConfig,
    section: str,
    value: str,
    state: str,
) -> None:
    """Set one row to an explicit state.

    Args:
        staged: Staged project configuration.
        section: Active section identifier.
        value: Item value from the selection list.
        state: Target state, such as ``enabled``, ``disabled``, or ``available``.
    """
    if section == "agentsmd":
        staged.set_agentsmd_enabled(value, state == "enabled")
    elif section == "skills":
        _set_skill_state(staged, value, state)
    elif section == "hooks":
        _set_hook_state(staged, value, state)
    elif section == "agents":
        _set_agent_state(staged, value, state)
    elif section == "rules":
        _set_rule_state(staged, value, state)
    elif section == "packages":
        _set_package_state(staged, value, state)
    elif section == "mcp":
        staged.set_mcp_enabled(value, state == "enabled")
    else:
        raise CommandError(f"Unsupported TUI section: {section}")


def _next_state(section: str, state: str) -> str:
    """Return the next state for a section cycle.

    Args:
        section: Active section identifier.
        state: Current item state.

    Returns:
        Next item state.
    """
    if section not in TRI_STATE_SECTIONS:
        return "available" if state == "enabled" else "enabled"
    if state == "available":
        return "enabled"
    if state == "enabled":
        return "disabled"
    return "available"


def _set_skill_state(staged: StagedConfig, value: str, state: str) -> None:
    """Set one skill row state."""
    if state == "enabled":
        staged.set_skill_enabled(value, True)
    elif state == "disabled":
        staged.set_skill_enabled(value, False)
    else:
        remove_skill(staged.config, value)


def _set_hook_state(staged: StagedConfig, value: str, state: str) -> None:
    """Set one hook row state."""
    if state == "enabled":
        staged.set_hook_enabled(value, True)
    elif state == "disabled":
        staged.set_hook_enabled(value, False)
    else:
        remove_hook(staged.config, value)


def _set_agent_state(staged: StagedConfig, value: str, state: str) -> None:
    """Set one agent row state."""
    if state == "enabled":
        staged.set_agent_enabled(value, True)
    elif state == "disabled":
        staged.set_agent_enabled(value, False)
    else:
        remove_agent(staged.config, value)


def _set_rule_state(staged: StagedConfig, value: str, state: str) -> None:
    """Set one rule row state."""
    if state == "enabled":
        staged.set_rule_enabled(value, True)
    elif state == "disabled":
        staged.set_rule_enabled(value, False)
    else:
        remove_rule(staged.config, value)


def _set_package_state(staged: StagedConfig, value: str, state: str) -> None:
    """Set one package or profile row state."""
    package = parse_package_value(value)
    if package.kind == "profile":
        _set_package_profile_state(staged, package.package, package.profile, state)
    elif state == "available":
        staged.set_package_available(package.package)
    else:
        staged.set_package_enabled(package.package, state == "enabled")


def _set_package_profile_state(
    staged: StagedConfig,
    package: str,
    profile: str,
    state: str,
) -> None:
    """Set one package profile row state."""
    if state == "available":
        staged.set_package_profile_available(package, profile)
    else:
        staged.set_package_profile_enabled(package, profile, state == "enabled")
