"""Argument parser helpers for MCP subcommands."""

import argparse
from collections.abc import Callable

NoSyncAdder = Callable[[argparse.ArgumentParser], None]


def add_mcp_parser(
    subparsers: argparse._SubParsersAction,
    add_no_sync_argument: NoSyncAdder,
) -> None:
    """Add MCP user config management parsers.

    Args:
        subparsers: Top-level subparser action.
        add_no_sync_argument: Helper that registers the shared no-sync flag.

    Returns:
        None. The parser is mutated in place.
    """
    mcp = subparsers.add_parser("mcp", help="Manage project MCP server overrides")
    mcp_subparsers = mcp.add_subparsers(dest="mcp_command", required=True)

    mcp_subparsers.add_parser("list", help="List project MCP server overrides")

    show = mcp_subparsers.add_parser("show", help="Show one project MCP override")
    show.add_argument("server_id", help="MCP server id")

    enable = mcp_subparsers.add_parser("enable", help="Enable an MCP server locally")
    add_no_sync_argument(enable)
    enable.add_argument("server_ids", nargs="+", help="MCP server ids")

    disable = mcp_subparsers.add_parser("disable", help="Disable an MCP server locally")
    add_no_sync_argument(disable)
    disable.add_argument("server_ids", nargs="+", help="MCP server ids")

    token = mcp_subparsers.add_parser(
        "set-token-env",
        help="Set bearer_token_env_var in a project MCP override",
    )
    add_no_sync_argument(token)
    token.add_argument("server_id", help="MCP server id")
    token.add_argument("env_var", help="Environment variable name")

    add_env = mcp_subparsers.add_parser(
        "add-env-var",
        help="Forward an environment variable in a project MCP override",
    )
    add_no_sync_argument(add_env)
    add_env.add_argument("server_id", help="MCP server id")
    add_env.add_argument("env_var", help="Environment variable name")

    remove_env = mcp_subparsers.add_parser(
        "remove-env-var",
        help="Stop forwarding an environment variable by string entry",
    )
    add_no_sync_argument(remove_env)
    remove_env.add_argument("server_id", help="MCP server id")
    remove_env.add_argument("env_var", help="Environment variable name")

    set_header = mcp_subparsers.add_parser(
        "set-env-header",
        help="Map an HTTP header to an environment variable",
    )
    add_no_sync_argument(set_header)
    set_header.add_argument("server_id", help="MCP server id")
    set_header.add_argument("header", help="HTTP header name")
    set_header.add_argument("env_var", help="Environment variable name")

    unset_header = mcp_subparsers.add_parser(
        "unset-env-header",
        help="Remove an env_http_headers mapping",
    )
    add_no_sync_argument(unset_header)
    unset_header.add_argument("server_id", help="MCP server id")
    unset_header.add_argument("header", help="HTTP header name")

    set_field = mcp_subparsers.add_parser(
        "set-field",
        help="Set an allowlisted non-secret MCP field from a TOML value",
    )
    add_no_sync_argument(set_field)
    set_field.add_argument("server_id", help="MCP server id")
    set_field.add_argument("field", help="Allowlisted field name")
    set_field.add_argument("value", help="TOML value literal")

    mcp_subparsers.add_parser("validate", help="Validate MCP config")
