"""Read-only listing helpers for packaged codexmgr configurations."""

from pathlib import Path

from .sources import available_package_names


def package_list_lines(codexmgr_home: Path) -> list[str]:
    """Build display lines for available packaged configurations.

    Args:
        codexmgr_home: codexmgr home directory containing package sources.

    Returns:
        Sorted package names suitable for CLI output.
    """
    return available_package_names(codexmgr_home)
