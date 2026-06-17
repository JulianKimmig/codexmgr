"""Pass-through wrapper for the external codex command."""

import subprocess
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ..core.errors import CommandError
from ..core.paths import codex_config_path
from ..core.toml_io import format_toml_value, load_optional_toml_file
from .codex_jit import parse_codex_jit_request, run_with_jit_overlay


def run_codex_command(
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    codex_args: list[str],
) -> int:
    """Apply project config and run Codex, optionally with a JIT overlay.

    Args:
        cwd: Project working directory for the external Codex process.
        codex_home: Codex home used to resolve project skills.
        codexmgr_home: codexmgr home containing package sources.
        codex_args: Raw arguments after ``codexmgr codex``.

    Returns:
        The external Codex process return code.
    """
    request = parse_codex_jit_request(codex_args)
    if request.enabled:
        return run_with_jit_overlay(request, cwd, codex_home, codexmgr_home, run_codex)
    from ..project.apply import apply_project_config

    apply_project_config(cwd, codex_home, codexmgr_home)
    return run_codex(cwd, codex_args)


def run_codex(cwd: Path, codex_args: list[str]) -> int:
    """Run the external codex command with project config prepended.

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
    user_config, passthrough_args = _extract_config_args(codex_args)
    return ["codex", *_config_overrides(cwd, user_config), *passthrough_args]


def _config_overrides(cwd: Path, user_config: list[str]) -> list[str]:
    """Build Codex ``-c`` arguments from project and user config.

    Args:
        cwd: Project directory whose .codex/config.toml should be read.
        user_config: Raw key=value config overrides from the user command.

    Returns:
        A flat argv fragment containing repeated ``-c`` overrides.
    """
    config = _merged_config(cwd, user_config)
    overrides: list[str] = []
    for key, value in config.items():
        overrides.extend(["-c", f"{key}={format_toml_value(value)}"])
    return overrides


def _merged_config(cwd: Path, user_config: list[str]) -> dict[str, Any]:
    """Merge project Codex config with user-provided overrides.

    Args:
        cwd: Project directory whose .codex/config.toml should be read.
        user_config: Raw key=value config overrides from the user command.

    Returns:
        Flattened Codex config override values keyed by dotted config path.
    """
    merged = dict(_iter_overrides(load_optional_toml_file(codex_config_path(cwd))))
    for raw_config in user_config:
        key, value = _parse_config_override(raw_config)
        _merge_config_value(merged, key, value)
    return merged


def _extract_config_args(codex_args: list[str]) -> tuple[list[str], list[str]]:
    """Split Codex config overrides from pass-through arguments.

    Args:
        codex_args: Raw arguments intended for the external codex command.

    Returns:
        The raw config override values and the remaining pass-through args.
    """
    config_args: list[str] = []
    passthrough_args: list[str] = []
    index = 0
    while index < len(codex_args):
        arg = codex_args[index]
        if arg in {"-c", "--config"}:
            if index + 1 >= len(codex_args):
                raise CommandError(f"{arg} requires a key=value argument")
            config_args.append(codex_args[index + 1])
            index += 2
        elif arg.startswith("--config="):
            config_args.append(arg.removeprefix("--config="))
            index += 1
        else:
            passthrough_args.append(arg)
            index += 1
    return config_args, passthrough_args


def _parse_config_override(raw_config: str) -> tuple[str, Any]:
    """Parse a Codex ``key=value`` config override.

    Args:
        raw_config: Raw override text after ``-c`` or ``--config``.

    Returns:
        The config key and parsed TOML value.
    """
    key, separator, raw_value = raw_config.partition("=")
    if not separator or not key:
        raise CommandError(f"Invalid codex config override: {raw_config}")
    return key, _parse_config_value(raw_value)


def _parse_config_value(raw_value: str) -> Any:
    """Parse a config override value as TOML when possible.

    Args:
        raw_value: Raw value string from a key=value override.

    Returns:
        Parsed TOML value, or the raw string when it is not valid TOML.
    """
    try:
        return tomllib.loads(f"value = {raw_value}")["value"]
    except tomllib.TOMLDecodeError:
        return raw_value


def _merge_config_value(config: dict[str, Any], key: str, value: Any) -> None:
    """Merge one parsed user override into accumulated config.

    Args:
        config: Mutable flattened config dictionary.
        key: Dotted config key to merge.
        value: Parsed override value.
    """
    if isinstance(value, list):
        existing = config.get(key)
        config[key] = [*(existing if isinstance(existing, list) else []), *value]
    else:
        config[key] = value


def _iter_overrides(
    config: Mapping[str, Any],
    prefix: tuple[str, ...] = (),
) -> list[tuple[str, Any]]:
    """Flatten nested project Codex config into dotted override keys.

    Args:
        config: Parsed Codex config table to flatten.
        prefix: Dotted key path accumulated during recursion.

    Returns:
        Flattened key/value pairs suitable for ``codex -c``.
    """
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
    """Return whether a config value should recurse as a TOML table.

    Args:
        value: Parsed TOML value.

    Returns:
        True when the value is a mapping.
    """
    return isinstance(value, Mapping)


def _validate_override_value(path: tuple[str, ...], value: Any) -> None:
    """Validate a flattened project config value before formatting.

    Args:
        path: Dotted config path represented as path segments.
        value: Parsed TOML value at that path.
    """
    if isinstance(value, list) and any(isinstance(item, Mapping) for item in value):
        if not all(isinstance(item, Mapping) for item in value):
            raise CommandError(f".codex/config.toml {'.'.join(path)} must not mix tables and values")
