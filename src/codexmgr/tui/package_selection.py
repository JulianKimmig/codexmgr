"""Apply package selection-list values to staged TUI config."""

from typing import TYPE_CHECKING

from .package_refs import parse_package_value

if TYPE_CHECKING:
    from .state import StagedConfig


def set_package_selection(staged: "StagedConfig", value: str, selected: bool) -> None:
    """Apply one package or package-profile selection value.

    Args:
        staged: Staged project configuration to mutate.
        value: Encoded TUI selection value.
        selected: Whether the row is selected.
    """
    package = parse_package_value(value)
    if package.kind == "profile":
        staged.set_package_profile_enabled(package.package, package.profile, selected)
    else:
        staged.set_package_enabled(package.package, selected)
