"""Load and validate codexmgr packaged configuration files."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..core.errors import CommandError
from ..core.toml_io import load_toml_file, plain_toml_value
from .sources import require_package_config

RESOURCE_KEYS = ("agentsmd", "agents", "hooks", "skills", "rules", "guides")
SUPPORTED_KEYS = (*RESOURCE_KEYS, "packages")
TOP_LEVEL_KEYS = (*SUPPORTED_KEYS, "profiles")


@dataclass(frozen=True)
class PackageEntries:
    """Reusable package entries for one root or profile section.

    Attributes:
        agentsmd: AGENTS.md template references to add or remove.
        agents: Custom-agent names to enable or disable.
        hooks: Hook bundle names to enable or disable.
        skills: Skill references to enable or disable.
        rules: Reusable rule refs to enable or disable.
        guides: Persistent guide file or folder selections.
        packages: Names of included packages.
    """

    agentsmd: list[str]
    agents: list[str]
    hooks: list[str]
    skills: list[str]
    rules: list[str]
    guides: list[str]
    packages: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PackageConfig:
    """A reusable package of codexmgr configuration entries.

    Attributes:
        name: Bare package name.
        agentsmd: AGENTS.md template references to add or remove.
        agents: Custom-agent names to enable or disable.
        hooks: Hook bundle names to enable or disable.
        skills: Skill references to enable or disable.
        rules: Reusable rule refs to enable or disable.
        guides: Persistent guide file or folder selections.
        profiles: Optional named profile entries keyed by profile name.
        packages: Names of packages included by the root section.
    """

    name: str
    agentsmd: list[str]
    agents: list[str]
    hooks: list[str]
    skills: list[str]
    rules: list[str]
    guides: list[str]
    profiles: dict[str, PackageEntries]
    packages: list[str] = field(default_factory=list)


def load_package_config(name: str, codexmgr_home: Path) -> PackageConfig:
    """Load a named packaged configuration from CODEXMGR_HOME.

    Args:
        name: Bare package name.
        codexmgr_home: codexmgr home directory.

    Returns:
        Validated package configuration.
    """
    path = require_package_config(name, codexmgr_home)
    return parse_package_config(name, path, load_toml_file(path))


def parse_package_config(
    name: str,
    path: Path,
    data: Mapping[str, Any],
) -> PackageConfig:
    """Validate parsed package TOML data.

    Args:
        name: Bare package name.
        path: Source config path used in error messages.
        data: Parsed TOML mapping.

    Returns:
        Validated package configuration.
    """
    unsupported = sorted(key for key in data if key not in TOP_LEVEL_KEYS)
    if unsupported:
        raise CommandError(f"Unsupported package config key: {unsupported[0]}")
    if not any(key in data for key in TOP_LEVEL_KEYS):
        raise CommandError(
            "Package config must include agentsmd, agents, hooks, skills, "
            f"rules, guides, packages, or profiles: {path}"
        )
    return PackageConfig(
        name=name,
        agentsmd=_string_list(data, "agentsmd", path),
        agents=_string_list(data, "agents", path),
        hooks=_string_list(data, "hooks", path),
        skills=_string_list(data, "skills", path),
        rules=_string_list(data, "rules", path),
        guides=_string_list(data, "guides", path),
        profiles=_profiles(data, path),
        packages=_string_list(data, "packages", path),
    )


def root_package_entries(package: PackageConfig) -> PackageEntries:
    """Return the entries declared in a package's root section.

    Args:
        package: Loaded package configuration.

    Returns:
        Root resource and include references.
    """
    return PackageEntries(**{key: getattr(package, key) for key in SUPPORTED_KEYS})


def merge_package_resources(entries: Iterable[PackageEntries]) -> PackageEntries:
    """Merge resource lists in first-seen order.

    Args:
        entries: Sections in application order.

    Returns:
        Combined resources with duplicate references removed.
    """
    values = {key: {} for key in RESOURCE_KEYS}
    for section in entries:
        for key in RESOURCE_KEYS:
            values[key].update(dict.fromkeys(getattr(section, key)))
    return PackageEntries(**{key: list(refs) for key, refs in values.items()})


def _profiles(data: Mapping[str, Any], path: Path) -> dict[str, PackageEntries]:
    """Read optional profile tables from package config.

    Args:
        data: Parsed package TOML mapping.
        path: Source config path used in error messages.

    Returns:
        Profile entries keyed by profile name.
    """
    profiles = data.get("profiles", {})
    if not isinstance(profiles, Mapping):
        raise CommandError(f"{path} profiles must be a table")
    parsed: dict[str, PackageEntries] = {}
    for name, table in profiles.items():
        if not isinstance(table, Mapping):
            raise CommandError(f"{path} profiles.{name} must be a table")
        unsupported = sorted(key for key in table if key not in SUPPORTED_KEYS)
        if unsupported:
            raise CommandError(
                f"Unsupported package profile key: {name}.{unsupported[0]}"
            )
        parsed[name] = PackageEntries(**{
            key: _string_list(table, key, path, label=f"profiles.{name}.{key}")
            for key in SUPPORTED_KEYS
        })
    return parsed


def _string_list(
    data: Mapping[str, Any], key: str, path: Path, *, label: str | None = None,
) -> list[str]:
    """Read one package string-list field.

    Args:
        data: Parsed package TOML mapping.
        key: Supported package key to read.
        path: Source config path used in error messages.
        label: Optional section-qualified name for diagnostics.

    Returns:
        A shallow copy of the configured string list, or an empty list.
    """
    value = plain_toml_value(data.get(key, []))
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise CommandError(f"{path} {label or key} must be a list of strings")
    return list(value)
