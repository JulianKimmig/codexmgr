"""Discover user-configured MCP servers through the Codex CLI."""

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import CommandError


@dataclass(frozen=True)
class CodexMcpServer:
    """One MCP server reported by ``codex mcp list --json``.

    Attributes:
        name: Codex MCP server id.
        enabled: Whether Codex reports the server as enabled.
    """

    name: str
    enabled: bool | None


def discover_codex_servers(cwd: Path) -> dict[str, CodexMcpServer]:
    """List MCP servers configured in the user Codex configuration.

    Args:
        cwd: Working directory for the Codex CLI invocation.

    Returns:
        Discovered servers keyed by server id.
    """
    try:
        result = subprocess.run(
            ["codex", "mcp", "list", "--json"],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise CommandError("codex command not found") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise CommandError(f"codex mcp list --json failed: {detail}")

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CommandError("codex mcp list --json returned invalid JSON") from exc

    return {server.name: server for server in _servers_from_payload(payload)}


def available_state(server: CodexMcpServer | None) -> str:
    """Return display state for an available Codex MCP server.

    Args:
        server: Discovered server, or None when absent.

    Returns:
        Display state for list output.
    """
    if server is None:
        return "missing"
    if server.enabled is True:
        return "enabled"
    if server.enabled is False:
        return "disabled"
    return "configured"


def _servers_from_payload(payload: Any) -> list[CodexMcpServer]:
    """Parse supported Codex MCP JSON payload shapes.

    Args:
        payload: Decoded JSON payload.

    Returns:
        Parsed server entries.
    """
    if isinstance(payload, list):
        return [_server_from_item(item) for item in payload]
    if isinstance(payload, dict) and isinstance(payload.get("servers"), list):
        return [_server_from_item(item) for item in payload["servers"]]
    if isinstance(payload, dict):
        return [_server_from_mapping(name, item) for name, item in payload.items()]
    raise CommandError("codex mcp list --json returned unsupported JSON")


def _server_from_item(item: Any) -> CodexMcpServer:
    """Parse one list-style Codex MCP server item.

    Args:
        item: JSON item to parse.

    Returns:
        Parsed server entry.
    """
    if not isinstance(item, dict) or not isinstance(item.get("name"), str):
        raise CommandError("codex mcp list --json returned a server without a name")
    enabled = item.get("enabled")
    return CodexMcpServer(item["name"], enabled if isinstance(enabled, bool) else None)


def _server_from_mapping(name: str, item: Any) -> CodexMcpServer:
    """Parse one mapping-style Codex MCP server item.

    Args:
        name: Server id from the JSON object key.
        item: JSON object value to parse.

    Returns:
        Parsed server entry.
    """
    if not isinstance(name, str) or not isinstance(item, dict):
        raise CommandError("codex mcp list --json returned unsupported JSON")
    enabled = item.get("enabled")
    return CodexMcpServer(name, enabled if isinstance(enabled, bool) else None)
