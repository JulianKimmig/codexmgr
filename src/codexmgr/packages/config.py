"""Load and validate codexmgr packaged configuration files."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..core.errors import CommandError
from ..core.toml_io import load_toml_file, plain_toml_value
from .sources import require_package_config

SUPPORTED_KEYS = ("agentsmd", "hooks", "skills")


@dataclass(frozen=True)
class PackageConfig:
    """A reusable package of codexmgr configuration entries.

    Attributes:
        name: Bare package name.
        agentsmd: AGENTS.md template references to add or remove.
        hooks: Hook bundle names to enable or disable.
        skills: Skill references to enable or disable.
    """

    name: str
    agentsmd: list[str]
    hooks: list[str]
    skills: list[str]


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
    unsupported = sorted(key for key in data if key not in SUPPORTED_KEYS)
    if unsupported:
        raise CommandError(f"Unsupported package config key: {unsupported[0]}")
    if not any(key in data for key in SUPPORTED_KEYS):
        raise CommandError(f"Package config must include agentsmd, hooks, or skills: {path}")
    return PackageConfig(
        name=name,
        agentsmd=_string_list(data, "agentsmd", path),
        hooks=_string_list(data, "hooks", path),
        skills=_string_list(data, "skills", path),
    )


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
