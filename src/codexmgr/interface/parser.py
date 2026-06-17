"""Argument parser construction for the codexmgr CLI."""

import argparse

from ..commands.navigation import add_cd_arguments


def build_parser() -> argparse.ArgumentParser:
    """Build the codexmgr argument parser.

    Returns:
        Configured top-level argparse parser.
    """
    parser = argparse.ArgumentParser(prog="codexmgr")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("setup", help="Create a project .codex directory")
    _add_apply_parser(subparsers)
    _add_cd_parser(subparsers)
    _add_codex_parser(subparsers)
    _add_agentsmd_parser(subparsers)
    _add_skill_parser(subparsers)
    _add_hooks_parser(subparsers)
    _add_mcp_parser(subparsers)
    _add_init_template_parser(subparsers)
    subparsers.add_parser("doctor", help="Check project configuration health")
    subparsers.add_parser("status", help="Summarize project codexmgr state")
    return parser


def _add_apply_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the apply parser.

    Args:
        subparsers: Top-level subparser action.

    Returns:
        None. The parser is mutated in place.
    """
    apply = subparsers.add_parser("apply", help="Apply the project configuration")
    apply.add_argument(
        "--check",
        action="store_true",
        help="Fail when generated files are out of sync without writing them",
    )
    apply.add_argument(
        "--diff",
        action="store_true",
        help="Print generated file diffs without writing them",
    )


def _add_cd_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the cd parser.

    Args:
        subparsers: Top-level subparser action.

    Returns:
        None. The parser is mutated in place.
    """
    cd = subparsers.add_parser("cd", help="Launch shell in CODEXMGR_HOME")
    add_cd_arguments(cd)


def _add_codex_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the codex pass-through parser.

    Args:
        subparsers: Top-level subparser action.

    Returns:
        None. The parser is mutated in place.
    """
    codex = subparsers.add_parser("codex", add_help=False, help="Run codex")
    codex.add_argument("codex_args", nargs=argparse.REMAINDER)


def _add_agentsmd_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add AGENTS.md snippet management parsers.

    Args:
        subparsers: Top-level subparser action.

    Returns:
        None. The parser is mutated in place.
    """
    agentsmd = subparsers.add_parser("agentsmd", help="Manage AGENTS.md fragments")
    agentsmd_subparsers = agentsmd.add_subparsers(
        dest="agentsmd_command",
        required=True,
    )

    add = agentsmd_subparsers.add_parser("add", help="Add an AGENTS.md template")
    _add_no_sync_argument(add)
    add.add_argument("reference", help="Template name or TOML file path")

    remove = agentsmd_subparsers.add_parser("remove", help="Remove a template")
    _add_no_sync_argument(remove)
    remove.add_argument("source_id", help="Template source identifier")

    agentsmd_subparsers.add_parser("list", help="List available templates")

    show = agentsmd_subparsers.add_parser("show", help="Render a template")
    show.add_argument("reference", help="Template name or TOML file path")

    validate = agentsmd_subparsers.add_parser("validate", help="Validate a template")
    validate.add_argument("reference", help="Template name or TOML file path")


def _add_skill_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add skill management parsers.

    Args:
        subparsers: Top-level subparser action.

    Returns:
        None. The parser is mutated in place.
    """
    skill = subparsers.add_parser("skill", help="Manage project skill configuration")
    skill_subparsers = skill.add_subparsers(dest="skill_command", required=True)

    enable = skill_subparsers.add_parser("enable", help="Enable a skill")
    _add_no_sync_argument(enable)
    enable.add_argument("skill", help="Skill name or path")

    disable = skill_subparsers.add_parser("disable", help="Disable a skill")
    _add_no_sync_argument(disable)
    disable.add_argument("skill", help="Skill name or path")

    skill_subparsers.add_parser("list", help="List available and configured skills")


def _add_hooks_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add hook bundle management parsers.

    Args:
        subparsers: Top-level subparser action.

    Returns:
        None. The parser is mutated in place.
    """
    hooks = subparsers.add_parser("hooks", help="Manage project hook configuration")
    hooks_subparsers = hooks.add_subparsers(dest="hooks_command", required=True)

    enable = hooks_subparsers.add_parser("enable", help="Enable a hook bundle")
    _add_no_sync_argument(enable)
    enable.add_argument("hook", help="Hook bundle name")

    disable = hooks_subparsers.add_parser("disable", help="Disable a hook bundle")
    _add_no_sync_argument(disable)
    disable.add_argument("hook", help="Hook bundle name")

    hooks_subparsers.add_parser("list", help="List available and configured hooks")


def _add_mcp_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add MCP user config management parsers.

    Args:
        subparsers: Top-level subparser action.

    Returns:
        None. The parser is mutated in place.
    """
    mcp = subparsers.add_parser("mcp", help="Manage project MCP server overrides")
    mcp_subparsers = mcp.add_subparsers(dest="mcp_command", required=True)

    mcp_subparsers.add_parser("list", help="List project MCP server overrides")

    show = mcp_subparsers.add_parser("show", help="Show one project MCP override")
    show.add_argument("server_id", help="MCP server id")

    enable = mcp_subparsers.add_parser("enable", help="Enable an MCP server locally")
    _add_no_sync_argument(enable)
    enable.add_argument("server_id", help="MCP server id")

    disable = mcp_subparsers.add_parser("disable", help="Disable an MCP server locally")
    _add_no_sync_argument(disable)
    disable.add_argument("server_id", help="MCP server id")

    token = mcp_subparsers.add_parser(
        "set-token-env",
        help="Set bearer_token_env_var in a project MCP override",
    )
    _add_no_sync_argument(token)
    token.add_argument("server_id", help="MCP server id")
    token.add_argument("env_var", help="Environment variable name")

    add_env = mcp_subparsers.add_parser(
        "add-env-var",
        help="Forward an environment variable in a project MCP override",
    )
    _add_no_sync_argument(add_env)
    add_env.add_argument("server_id", help="MCP server id")
    add_env.add_argument("env_var", help="Environment variable name")

    remove_env = mcp_subparsers.add_parser(
        "remove-env-var",
        help="Stop forwarding an environment variable by string entry",
    )
    _add_no_sync_argument(remove_env)
    remove_env.add_argument("server_id", help="MCP server id")
    remove_env.add_argument("env_var", help="Environment variable name")

    set_header = mcp_subparsers.add_parser(
        "set-env-header",
        help="Map an HTTP header to an environment variable",
    )
    _add_no_sync_argument(set_header)
    set_header.add_argument("server_id", help="MCP server id")
    set_header.add_argument("header", help="HTTP header name")
    set_header.add_argument("env_var", help="Environment variable name")

    unset_header = mcp_subparsers.add_parser(
        "unset-env-header",
        help="Remove an env_http_headers mapping",
    )
    _add_no_sync_argument(unset_header)
    unset_header.add_argument("server_id", help="MCP server id")
    unset_header.add_argument("header", help="HTTP header name")

    set_field = mcp_subparsers.add_parser(
        "set-field",
        help="Set an allowlisted non-secret MCP field from a TOML value",
    )
    _add_no_sync_argument(set_field)
    set_field.add_argument("server_id", help="MCP server id")
    set_field.add_argument("field", help="Allowlisted field name")
    set_field.add_argument("value", help="TOML value literal")

    mcp_subparsers.add_parser("validate", help="Validate MCP config")


def _add_init_template_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add starter template creation parsers.

    Args:
        subparsers: Top-level subparser action.

    Returns:
        None. The parser is mutated in place.
    """
    init = subparsers.add_parser("init-template", help="Create starter templates")
    init_subparsers = init.add_subparsers(dest="init_template_command", required=True)
    agentsmd = init_subparsers.add_parser("agentsmd", help="Create AGENTS.md snippet")
    agentsmd.add_argument("name", help="Bare template name")


def _add_no_sync_argument(parser: argparse.ArgumentParser) -> None:
    """Add the shared sync opt-out flag to a mutating command.

    Args:
        parser: Subcommand parser that updates .codex/codexmgr.toml.

    Returns:
        None. The parser is mutated in place.
    """
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="Do not run apply after updating codexmgr.toml",
    )
