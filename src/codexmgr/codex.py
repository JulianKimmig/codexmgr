"""Pass-through wrapper for the external codex command."""

import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .errors import CommandError
from .paths import codex_config_path
from .toml_io import format_toml_value, load_optional_toml_file


def run_codex(cwd: Path, codex_args: list[str]) -> int:
    """Run the external codex command with project skill config prepended.

    Args:
        cwd: Project working directory for the external codex process.
        codex_args: Arguments to pass through to codex.

    Returns:
        The external codex process return code.
    """
    command = build_codex_command(cwd, codex_args)
    try:
        return subprocess.run(command, cwd=cwd).returncode
    except FileNotFoundError as exc:
        raise CommandError("codex command not found") from exc


def build_codex_command(cwd: Path, codex_args: list[str]) -> list[str]:
    """Build the external codex command invocation.

    Args:
        cwd: Project directory whose .codex/config.toml should be read.
        codex_args: Arguments to pass through to codex.

    Returns:
        The complete argv for the external codex process.
    """
    return ["codex", *_config_overrides(cwd), *codex_args]


def _config_overrides(cwd: Path) -> list[str]:
    config = load_optional_toml_file(codex_config_path(cwd))
    overrides: list[str] = []
    for key, value in _iter_overrides(config):
        overrides.extend(["-c", f"{key}={format_toml_value(value)}"])
    return overrides


def _iter_overrides(
    config: Mapping[str, Any],
    prefix: tuple[str, ...] = (),
) -> list[tuple[str, Any]]:
    overrides: list[tuple[str, Any]] = []
    for key, value in config.items():
        path = (*prefix, key)
        if _is_nested_table(value):
            overrides.extend(_iter_overrides(value, path))
        else:
            _validate_override_value(path, value)
            overrides.append((".".join(path), value))
    return overrides


def _is_nested_table(value: Any) -> bool:
    return isinstance(value, Mapping)


def _validate_override_value(path: tuple[str, ...], value: Any) -> None:
    if isinstance(value, list) and any(isinstance(item, Mapping) for item in value):
        if not all(isinstance(item, Mapping) for item in value):
            raise CommandError(f".codex/config.toml {'.'.join(path)} must not mix tables and values")
