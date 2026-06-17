"""CLI helpers for project-local MCP server override configuration."""

import argparse
from pathlib import Path
from typing import TextIO

from . import config as mcp
from .discovery import available_state, discover_codex_servers
from ..project.apply import apply_project_config


def run_mcp_command(
    args: argparse.Namespace,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Run a parsed mcp subcommand.

    Args:
        args: Parsed argparse namespace.
        cwd: Project directory.
        codex_home: Codex home directory for apply.
        codexmgr_home: codexmgr home directory for apply.
        stdout: Stream for command output.

    Returns:
        A process-style exit code.
    """
    command = args.mcp_command
    if command == "list":
        _write_lines(stdout, _list_lines(cwd))
        return 0
    if command == "show":
        _write_lines(stdout, _show_lines(cwd, args.server_id))
        return 0
    if command == "validate":
        _write_lines(stdout, mcp.validate_overrides(cwd))
        return 0
    message = _mutate(args, cwd)
    return _finish_mcp_change(message, args.no_sync, cwd, codex_home, codexmgr_home, stdout)


def _mutate(args: argparse.Namespace, cwd: Path) -> str:
    """Run one mutating MCP command.

    Args:
        args: Parsed argparse namespace.
        cwd: Project directory.

    Returns:
        User-facing success message.
    """
    command = args.mcp_command
    if command == "enable":
        server_id = mcp.set_enabled(cwd, args.server_id, True)
        return f"Enabled MCP server override {server_id}"
    if command == "disable":
        server_id = mcp.set_enabled(cwd, args.server_id, False)
        return f"Disabled MCP server override {server_id}"
    if command == "set-token-env":
        server_id = mcp.set_token_env(cwd, args.server_id, args.env_var)
        return f"Updated MCP server override {server_id} bearer_token_env_var"
    if command == "add-env-var":
        server_id = mcp.add_env_var(cwd, args.server_id, args.env_var)
        return f"Updated MCP server override {server_id} env_vars"
    if command == "remove-env-var":
        server_id = mcp.remove_env_var(cwd, args.server_id, args.env_var)
        return f"Updated MCP server override {server_id} env_vars"
    if command == "set-env-header":
        server_id = mcp.set_env_header(cwd, args.server_id, args.header, args.env_var)
        return f"Updated MCP server override {server_id} env_http_headers"
    if command == "unset-env-header":
        server_id = mcp.unset_env_header(cwd, args.server_id, args.header)
        return f"Updated MCP server override {server_id} env_http_headers"
    if command == "set-field":
        server_id = mcp.set_field(cwd, args.server_id, args.field, args.value)
        return f"Updated MCP server override {server_id} {args.field}"
    raise AssertionError(f"Unhandled mcp command: {command}")


def _list_lines(cwd: Path) -> list[str]:
    """Build display lines for available MCP servers and project overrides.

    Args:
        cwd: Project directory.

    Returns:
        Display lines.
    """
    overrides = mcp.configured_overrides(cwd)
    available = discover_codex_servers(cwd)
    server_ids = sorted(set(available) | set(overrides))
    if not server_ids:
        return ["MCP servers: none"]
    lines: list[str] = []
    for server_id in server_ids:
        fields = overrides.get(server_id, {})
        field_names = ", ".join(sorted(fields))
        line = (
            f"{server_id} available={available_state(available.get(server_id))} "
            f"override={_override_state(fields)}"
        )
        if field_names:
            line = f"{line} fields={field_names}"
        lines.append(line)
    return lines


def _show_lines(cwd: Path, server_id: str) -> list[str]:
    """Build display lines for one MCP override.

    Args:
        cwd: Project directory.
        server_id: MCP server id.

    Returns:
        Display lines.
    """
    overrides = mcp.configured_overrides(cwd)
    if server_id not in overrides:
        return [f"MCP server override not configured: {server_id}"]
    fields = overrides[server_id]
    lines = [f"Server override: {server_id}", f"State: {_override_state(fields)}"]
    if "bearer_token_env_var" in fields:
        lines.append(f"Bearer token env var: {fields['bearer_token_env_var']}")
    if "env_vars" in fields:
        lines.append(f"Forwarded env vars: {', '.join(fields['env_vars'])}")
    if "env_http_headers" in fields:
        headers = ", ".join(f"{key}={value}" for key, value in fields["env_http_headers"].items())
        lines.append(f"Env HTTP headers: {headers}")
    return lines


def _override_state(fields: dict) -> str:
    """Return display state for an override table.

    Args:
        fields: MCP override fields.

    Returns:
        Display state.
    """
    if not fields:
        return "none"
    if fields.get("enabled") is True:
        return "enabled"
    if fields.get("enabled") is False:
        return "disabled"
    return "configured"


def _finish_mcp_change(
    message: str,
    no_sync: bool,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Apply project config after an MCP mutation unless opted out.

    Args:
        message: User-facing mutation message.
        no_sync: Whether to skip apply.
        cwd: Project directory.
        codex_home: Codex home used by apply.
        codexmgr_home: codexmgr home used by apply.
        stdout: Output stream.

    Returns:
        Zero when successful.
    """
    messages = [message]
    if not no_sync:
        apply_project_config(cwd, codex_home, codexmgr_home)
        messages.append("Applied project Codex configuration")
    stdout.write("\n".join(messages) + "\n")
    return 0


def _write_lines(stdout: TextIO, lines: list[str]) -> None:
    """Write display lines with a trailing newline.

    Args:
        stdout: Output stream.
        lines: Lines to write.
    """
    stdout.write("\n".join(lines) + "\n")
