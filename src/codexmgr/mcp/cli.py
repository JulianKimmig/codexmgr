"""CLI helpers for project-local MCP source and server configuration."""

import argparse
from pathlib import Path
from typing import TextIO

from . import config as mcp
from .project import disable_mcp_sources, enable_mcp_sources, mcp_source_names
from .resolution import validate_mcp_config
from .sources import (
    available_mcp_source_names,
    mcp_source_file,
    resolve_mcp_source,
)
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
        _write_lines(stdout, _list_lines(cwd, codexmgr_home))
        return 0
    if command == "show":
        _write_lines(stdout, _show_lines(cwd, codexmgr_home, args.server_id))
        return 0
    if command == "validate":
        _write_lines(stdout, validate_mcp_config(cwd, codexmgr_home))
        return 0
    messages = _mutate(args, cwd, codexmgr_home)
    return _finish_mcp_change(
        messages,
        args.no_sync,
        cwd,
        codex_home,
        codexmgr_home,
        stdout,
    )


def _mutate(args: argparse.Namespace, cwd: Path, codexmgr_home: Path) -> list[str]:
    """Run one mutating MCP command.

    Args:
        args: Parsed argparse namespace.
        cwd: Project directory.
        codexmgr_home: Codexmgr home directory containing MCP source files.

    Returns:
        User-facing success messages.
    """
    command = args.mcp_command
    if command == "enable":
        names = enable_mcp_sources(args.server_ids, cwd, codexmgr_home)
        return [f"Enabled MCP source {name}" for name in names]
    if command == "disable":
        names = disable_mcp_sources(args.server_ids, cwd, codexmgr_home)
        return [f"Disabled MCP source {name}" for name in names]
    if command == "set-token-env":
        server_id = mcp.set_token_env(cwd, args.server_id, args.env_var)
        return [f"Updated MCP server override {server_id} bearer_token_env_var"]
    if command == "add-env-var":
        server_id = mcp.add_env_var(cwd, args.server_id, args.env_var)
        return [f"Updated MCP server override {server_id} env_vars"]
    if command == "remove-env-var":
        server_id = mcp.remove_env_var(cwd, args.server_id, args.env_var)
        return [f"Updated MCP server override {server_id} env_vars"]
    if command == "set-env-header":
        server_id = mcp.set_env_header(cwd, args.server_id, args.header, args.env_var)
        return [f"Updated MCP server override {server_id} env_http_headers"]
    if command == "unset-env-header":
        server_id = mcp.unset_env_header(cwd, args.server_id, args.header)
        return [f"Updated MCP server override {server_id} env_http_headers"]
    if command == "set-field":
        server_id = mcp.set_field(cwd, args.server_id, args.field, args.value)
        return [f"Updated MCP server override {server_id} {args.field}"]
    raise AssertionError(f"Unhandled mcp command: {command}")


def _list_lines(cwd: Path, codexmgr_home: Path) -> list[str]:
    """Build display lines for reusable MCP sources and project overlays.

    Args:
        cwd: Project directory.
        codexmgr_home: Codexmgr home directory containing MCP source files.

    Returns:
        Display lines.
    """
    overrides = mcp.configured_overrides(cwd)
    enabled_sources = mcp_source_names(_project_config(cwd))
    available_sources = set(available_mcp_source_names(codexmgr_home))
    names = sorted(available_sources | set(enabled_sources) | set(overrides))
    if not names:
        return ["MCP sources: none"]
    lines: list[str] = []
    for name in names:
        fields = overrides.get(name, {})
        field_names = ", ".join(sorted(fields))
        line = f"{name} source={_source_state(name, enabled_sources, available_sources)}"
        source = resolve_mcp_source(name, codexmgr_home)
        if source is not None:
            line = f"{line} servers={', '.join(sorted(source.servers))}"
        if field_names:
            line = f"{line} override_fields={field_names}"
        lines.append(line)
    return lines


def _show_lines(cwd: Path, codexmgr_home: Path, name: str) -> list[str]:
    """Build display lines for one reusable MCP source.

    Args:
        cwd: Project directory.
        codexmgr_home: Codexmgr home directory containing MCP source files.
        name: MCP source name.

    Returns:
        Display lines.
    """
    enabled_sources = mcp_source_names(_project_config(cwd))
    overrides = mcp.configured_overrides(cwd)
    source = resolve_mcp_source(name, codexmgr_home)
    if source is None and name not in enabled_sources and name not in overrides:
        return [f"MCP source not configured: {name}"]
    lines = [f"MCP source: {name}", f"State: {_source_state(name, enabled_sources, set(available_mcp_source_names(codexmgr_home)))}"]
    lines.append(f"Path: {mcp_source_file(codexmgr_home, name)}")
    if source is None:
        lines.append("Source file: missing")
    else:
        lines.append(f"Servers: {', '.join(sorted(source.servers))}")
    server_ids = set(source.servers) if source is not None else {name}
    override_lines = _override_lines(overrides, server_ids)
    if override_lines:
        lines.extend(override_lines)
    return lines


def _source_state(name: str, enabled_sources: list[str], available_sources: set[str]) -> str:
    """Return display state for an MCP source.

    Args:
        name: MCP source name.
        enabled_sources: Project-enabled source names.
        available_sources: Source names available in CODEXMGR_HOME.

    Returns:
        Display state.
    """
    if name in enabled_sources:
        return "enabled" if name in available_sources else "missing"
    return "available" if name in available_sources else "none"


def _override_lines(overrides: dict[str, dict], server_ids: set[str]) -> list[str]:
    """Build display lines for project server overlay fields.

    Args:
        overrides: Project overlays keyed by server id.
        server_ids: Server ids relevant to the displayed source.

    Returns:
        Display lines describing configured overlay fields.
    """
    fields = [
        f"{server_id}.{field}"
        for server_id, table in sorted(overrides.items())
        if server_id in server_ids
        for field in sorted(table)
    ]
    return [f"Project override fields: {', '.join(fields)}"] if fields else []


def _project_config(cwd: Path) -> dict:
    """Load project MCP config source for read-only display commands.

    Args:
        cwd: Project directory.

    Returns:
        Parsed project config.
    """
    from ..core.paths import config_path
    from ..core.toml_io import load_optional_toml_file

    return load_optional_toml_file(config_path(cwd))


def _finish_mcp_change(
    messages: list[str],
    no_sync: bool,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
    stdout: TextIO,
) -> int:
    """Apply project config after an MCP mutation unless opted out.

    Args:
        messages: User-facing mutation messages.
        no_sync: Whether to skip apply.
        cwd: Project directory.
        codex_home: Codex home used by apply.
        codexmgr_home: codexmgr home used by apply.
        stdout: Output stream.

    Returns:
        Zero when successful.
    """
    output = list(messages)
    if not no_sync:
        apply_project_config(cwd, codex_home, codexmgr_home)
        output.append("Applied project Codex configuration")
    stdout.write("\n".join(output) + "\n")
    return 0


def _write_lines(stdout: TextIO, lines: list[str]) -> None:
    """Write display lines with a trailing newline.

    Args:
        stdout: Output stream.
        lines: Lines to write.
    """
    stdout.write("\n".join(lines) + "\n")
