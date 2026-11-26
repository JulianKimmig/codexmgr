"""Persist explicit package selections and their applied resource references."""

from collections.abc import Mapping, MutableMapping
from os.path import normcase
from typing import Any

from ..core.errors import CommandError
from ..core.toml_io import plain_toml_value
from .config import RESOURCE_KEYS, PackageEntries

SELECTIONS_KEY = "package_selections"
Selection = tuple[str, str | None]


def selection_key(name: str, profile: str | None) -> Selection:
    """Return the platform-normalized package name and the TOML profile key."""
    return normcase(name), profile


def read_package_selections(config: Mapping[str, Any]) -> dict[Selection, PackageEntries]:
    """Read package root and profile snapshots from a project configuration.

    Args:
        config: Project configuration that may predate package selection records.

    Returns:
        Resources contributed by each recorded (package, optional profile) pair.
    """
    packages = _table(config.get(SELECTIONS_KEY, {}), SELECTIONS_KEY)
    selections: dict[Selection, PackageEntries] = {}
    for package, sections in packages.items():
        label = f"{SELECTIONS_KEY}.{package}"
        sections = _table(sections, label)
        if "root" in sections:
            selections[selection_key(package, None)] = _entries(sections["root"], f"{label}.root")
        profiles = _table(sections.get("profiles", {}), f"{label}.profiles")
        for profile, entries in profiles.items():
            selections[selection_key(package, profile)] = _entries(entries, f"{label}.profiles.{profile}")
    return selections


def write_package_selections(
    config: MutableMapping[str, Any], selections: Mapping[Selection, PackageEntries],
) -> None:
    """Save the selection records, removing the table when the last is released.

    Args:
        config: Working project configuration.
        selections: Resource snapshots keyed by package and optional profile.
    """
    if not selections:
        config.pop(SELECTIONS_KEY, None)
        return
    packages: dict[str, Any] = {}
    for (name, profile), entries in selections.items():
        package = packages.setdefault(name, {})
        values = {key: getattr(entries, key) for key in RESOURCE_KEYS if getattr(entries, key)}
        if profile is None:
            package["root"] = values
        else:
            package.setdefault("profiles", {})[profile] = values
    config[SELECTIONS_KEY] = packages


def _entries(value: Any, label: str) -> PackageEntries:
    """Validate a saved resource snapshot and return its package entries."""
    table = _table(value, label)
    values = {}
    for key in RESOURCE_KEYS:
        refs = plain_toml_value(table.get(key, []))
        if not isinstance(refs, list) or not all(isinstance(ref, str) for ref in refs):
            raise CommandError(f"codexmgr.toml {label}.{key} must be a list of strings")
        values[key] = refs
    return PackageEntries(**values)


def _table(value: Any, label: str) -> Mapping[str, Any]:
    """Return one validated TOML table for the given diagnostic label."""
    if not isinstance(value, Mapping):
        raise CommandError(f"codexmgr.toml {label} must be a table")
    return value
