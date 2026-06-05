"""Round-trip helpers for user-owned Codex config.toml files."""

from pathlib import Path
from typing import Any

import tomlkit
from tomlkit.exceptions import TOMLKitError

from .errors import CommandError
from .paths import global_codex_config_path


def load_user_config(codex_home: Path, *, required: bool) -> Any:
    """Load CODEX_HOME/config.toml as a round-trip TOML document.

    Args:
        codex_home: Codex home directory containing config.toml.
        required: Whether a missing config.toml should be an error.

    Returns:
        A tomlkit TOML document.
    """
    path = global_codex_config_path(codex_home)
    if not path.exists():
        if required:
            raise CommandError(f"Codex config not found: {path}")
        return tomlkit.document()
    try:
        return tomlkit.parse(path.read_text(encoding="utf-8"))
    except TOMLKitError as exc:
        raise CommandError(f"Invalid TOML in {path}: {exc}") from exc


def write_user_config(codex_home: Path, document: Any) -> None:
    """Write a round-trip TOML document to CODEX_HOME/config.toml.

    Args:
        codex_home: Codex home directory containing config.toml.
        document: tomlkit TOML document to serialize.

    Returns:
        None. The existing config.toml file is replaced.
    """
    path = global_codex_config_path(codex_home)
    path.write_text(tomlkit.dumps(document), encoding="utf-8")


def parse_toml_value(raw_value: str) -> Any:
    """Parse one TOML value literal.

    Args:
        raw_value: Raw TOML literal text.

    Returns:
        Parsed tomlkit value.
    """
    try:
        return tomlkit.parse(f"value = {raw_value}")["value"]
    except TOMLKitError as exc:
        raise CommandError(f"Invalid TOML value: {raw_value}") from exc
