"""Load and validate codexmgr packaged configuration files."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.errors import CommandError
from ..core.toml_io import load_toml_file, plain_toml_value
from .sources import require_package_config

SUPPORTED_KEYS = ("agentsmd", "agents", "hooks", "skills", "rules")
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
    """

    agentsmd: list[str]
    agents: list[str]
    hooks: list[str]
    skills: list[str]
    rules: list[str]


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
        profiles: Optional named profile entries keyed by profile name.
    """

    name: str
    agentsmd: list[str]
    agents: list[str]
    hooks: list[str]
    skills: list[str]
    rules: list[str]
    profiles: dict[str, PackageEntries]


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
            f"rules, or profiles: {path}"
        )
    return PackageConfig(
        name=name,
        agentsmd=_string_list(data, "agentsmd", path),
        agents=_string_list(data, "agents", path),
        hooks=_string_list(data, "hooks", path),
        skills=_string_list(data, "skills", path),
        rules=_string_list(data, "rules", path),
        profiles=_profiles(data, path),
    )


def selected_package_entries(
    package: PackageConfig,
    profile_names: list[str],
) -> PackageEntries:
    """Return root package entries plus the requested profile entries.

    Args:
        package: Loaded package configuration.
        profile_names: Profile names to merge into the selected entries.

    Returns:
        Dedupe-preserving combined package entries.
    """
    agentsmd = list(package.agentsmd)
    agents = list(package.agents)
    hooks = list(package.hooks)
    skills = list(package.skills)
    rules = list(package.rules)
    for profile_name in profile_names:
        profile = package.profiles.get(profile_name)
        if profile is None:
            raise CommandError(
                f"Package profile not found: {package.name}.{profile_name}"
            )
        agentsmd = _append_unique(agentsmd, profile.agentsmd)
        agents = _append_unique(agents, profile.agents)
        hooks = _append_unique(hooks, profile.hooks)
        skills = _append_unique(skills, profile.skills)
        rules = _append_unique(rules, profile.rules)
    return PackageEntries(
        agentsmd=agentsmd,
        agents=agents,
        hooks=hooks,
        skills=skills,
        rules=rules,
    )


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
        parsed[name] = PackageEntries(
            agentsmd=_string_list(table, "agentsmd", path),
            agents=_string_list(table, "agents", path),
            hooks=_string_list(table, "hooks", path),
            skills=_string_list(table, "skills", path),
            rules=_string_list(table, "rules", path),
        )
    return parsed


def _string_list(data: Mapping[str, Any], key: str, path: Path) -> list[str]:
    """Read one package string-list field.

    Args:
        data: Parsed package TOML mapping.
        key: Supported package key to read.
        path: Source config path used in error messages.

    Returns:
        A shallow copy of the configured string list, or an empty list.
    """
    value = plain_toml_value(data.get(key, []))
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise CommandError(f"{path} {key} must be a list of strings")
    return list(value)


def _append_unique(values: list[str], additions: list[str]) -> list[str]:
    """Append missing additions while preserving first-seen order.

    Args:
        values: Existing values.
        additions: Candidate values to append.

    Returns:
        Combined list without duplicate entries.
    """
    combined = list(values)
    for addition in additions:
        if addition not in combined:
            combined.append(addition)
    return combined
