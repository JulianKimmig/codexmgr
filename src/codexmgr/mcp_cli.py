"""CLI helpers for user-level MCP server configuration."""

import argparse
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TextIO

from . import mcp_mutation, mcp_user_config
from .mcp_model import McpServer


def run_mcp_command(args: argparse.Namespace, codex_home: Path, stdout: TextIO) -> int:
    """Run a parsed mcp subcommand.

    Args:
        args: Parsed argparse namespace.
        codex_home: Codex home directory containing config.toml.
        stdout: Stream for command output.

    Returns:
        A process-style exit code.
    """
    command = args.mcp_command
    if command == "list":
        _write_lines(stdout, _list_lines(codex_home))
        return 0
    if command == "show":
        _write_lines(stdout, _show_lines(codex_home, args.server_id))
        return 0
    if command == "enable":
        server_id = mcp_mutation.set_enabled(codex_home, args.server_id, True)
        stdout.write(f"Enabled MCP server {server_id}\n")
        return 0
    if command == "disable":
        server_id = mcp_mutation.set_enabled(codex_home, args.server_id, False)
        stdout.write(f"Disabled MCP server {server_id}\n")
        return 0
    if command == "set-token-env":
        server_id = mcp_mutation.set_token_env(
            codex_home,
            args.server_id,
            args.env_var,
        )
        stdout.write(f"Updated MCP server {server_id} bearer_token_env_var\n")
        return 0
    if command == "add-env-var":
        server_id = mcp_mutation.add_env_var(
            codex_home,
            args.server_id,
            args.env_var,
        )
        stdout.write(f"Updated MCP server {server_id} env_vars\n")
        return 0
    if command == "remove-env-var":
        server_id = mcp_mutation.remove_env_var(
            codex_home,
            args.server_id,
            args.env_var,
        )
        stdout.write(f"Updated MCP server {server_id} env_vars\n")
        return 0
    if command == "set-env-header":
        server_id = mcp_mutation.set_env_header(
            codex_home,
            args.server_id,
            args.header,
            args.env_var,
        )
        stdout.write(f"Updated MCP server {server_id} env_http_headers\n")
        return 0
    if command == "unset-env-header":
        server_id = mcp_mutation.unset_env_header(
            codex_home,
            args.server_id,
            args.header,
        )
        stdout.write(f"Updated MCP server {server_id} env_http_headers\n")
        return 0
    if command == "set-field":
        server_id = mcp_mutation.set_field(
            codex_home,
            args.server_id,
            args.field,
            args.value,
        )
        stdout.write(f"Updated MCP server {server_id} {args.field}\n")
        return 0
    if command == "validate":
        _write_lines(stdout, mcp_user_config.validate(codex_home, args.server_id))
        return 0
    raise AssertionError(f"Unhandled mcp command: {command}")


def _list_lines(codex_home: Path) -> list[str]:
    """Build lines for mcp list.

    Args:
        codex_home: Codex home directory.

    Returns:
        Display lines.
    """
    servers = mcp_user_config.servers(codex_home)
    if not servers:
        return ["MCP servers: none"]
    lines: list[str] = []
    for item in servers:
        state = "enabled" if item.enabled else "disabled"
        if item.enabled and not item.enabled_is_explicit:
            state = "enabled implicit"
        lines.append(f"{item.server_id} {state} {item.transport} {_target(item)}".rstrip())
    return lines


def _show_lines(codex_home: Path, server_id: str) -> list[str]:
    """Build lines for mcp show.

    Args:
        codex_home: Codex home directory.
        server_id: MCP server identifier.

    Returns:
        Display lines.
    """
    item = mcp_user_config.server(codex_home, server_id)
    state = "enabled" if item.enabled else "disabled"
    if item.enabled and not item.enabled_is_explicit:
        state = "enabled implicit"
    lines = [
        f"Server: {item.server_id}",
        f"State: {state}",
        f"Transport: {item.transport}",
    ]
    if item.transport == "stdio":
        lines.append(f"Command: {_target(item)}")
    else:
        lines.append(f"URL: {item.table['url']}")
    if "bearer_token_env_var" in item.table:
        lines.append(f"Bearer token env var: {item.table['bearer_token_env_var']}")
    env_vars = _env_var_names(item.table.get("env_vars", []))
    if env_vars:
        lines.append(f"Forwarded env vars: {', '.join(env_vars)}")
    lines.extend(_redacted_map_line("Raw env values", item.table.get("env")))
    lines.extend(_redacted_map_line("Static HTTP headers", item.table.get("http_headers")))
    return lines


def _target(item: McpServer) -> str:
    """Return a one-line server target summary.

    Args:
        item: MCP server summary.

    Returns:
        Target command or URL.
    """
    if item.transport == "http":
        return str(item.table["url"])
    args = [str(value) for value in item.table.get("args", [])]
    return " ".join([str(item.table["command"]), *args])


def _env_var_names(values: Any) -> list[str]:
    """Return display names from env_vars entries.

    Args:
        values: env_vars value.

    Returns:
        Environment variable names.
    """
    names: list[str] = []
    if not isinstance(values, list):
        return names
    for item in values:
        if isinstance(item, str):
            names.append(item)
        elif isinstance(item, Mapping) and isinstance(item.get("name"), str):
            names.append(str(item["name"]))
    return names


def _redacted_map_line(label: str, value: Any) -> list[str]:
    """Build a redacted mapping display line.

    Args:
        label: Display label.
        value: Potential mapping value.

    Returns:
        One redacted display line or an empty list.
    """
    if not isinstance(value, Mapping) or not value:
        return []
    entries = ", ".join(f"{key}=<redacted>" for key in value)
    return [f"{label}: {entries}"]


def _write_lines(stdout: TextIO, lines: list[str]) -> None:
    """Write display lines with a trailing newline.

    Args:
        stdout: Output stream.
        lines: Lines to write.
    """
    stdout.write("\n".join(lines) + "\n")
