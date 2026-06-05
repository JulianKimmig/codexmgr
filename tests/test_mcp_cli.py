"""CLI behavior tests for MCP user config management."""

import tomllib
from pathlib import Path


def write_user_config(codex_home: Path, content: str) -> None:
    """Write a temporary CODEX_HOME config.toml fixture.

    Args:
        codex_home: Temporary Codex home directory.
        content: TOML content to write.
    """
    (codex_home / "config.toml").write_text(content, encoding="utf-8")


def read_user_config(codex_home: Path):
    """Read a temporary CODEX_HOME config.toml fixture.

    Args:
        codex_home: Temporary Codex home directory.

    Returns:
        Parsed TOML data.
    """
    return tomllib.loads((codex_home / "config.toml").read_text(encoding="utf-8"))


def test_mcp_show_redacts_raw_env_and_static_headers(workspace, run_cli):
    """show displays safe metadata without printing raw secret values."""
    project, codex_home = workspace
    write_user_config(
        codex_home,
        '''
[mcp_servers.secure]
url = "https://mcp.example.test/mcp"
bearer_token_env_var = "MCP_TOKEN"
env_vars = ["VISIBLE_ENV"]
http_headers = { Authorization = "Bearer raw-secret" }

[mcp_servers.secure.env]
API_TOKEN = "raw-env-secret"
''',
    )

    exit_code, stdout, stderr = run_cli(["mcp", "show", "secure"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert "Server: secure" in stdout
    assert "Transport: http" in stdout
    assert "Bearer token env var: MCP_TOKEN" in stdout
    assert "Forwarded env vars: VISIBLE_ENV" in stdout
    assert "Raw env values: API_TOKEN=<redacted>" in stdout
    assert "Static HTTP headers: Authorization=<redacted>" in stdout
    assert "raw-secret" not in stdout
    assert "raw-env-secret" not in stdout


def test_mcp_show_missing_server_fails(workspace, run_cli):
    """show fails for server ids that do not exist."""
    project, codex_home = workspace
    write_user_config(
        codex_home,
        '''
[mcp_servers.context7]
command = "npx"
''',
    )

    exit_code, stdout, stderr = run_cli(["mcp", "show", "missing"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert "MCP server not found: missing" in stderr


def test_mcp_set_token_env_updates_existing_server(workspace, run_cli):
    """set-token-env stores a bearer token environment variable name."""
    project, codex_home = workspace
    write_user_config(
        codex_home,
        '''
[mcp_servers.figma]
url = "https://mcp.figma.com/mcp"
''',
    )

    exit_code, stdout, stderr = run_cli(
        ["mcp", "set-token-env", "figma", "FIGMA_TOKEN"],
        project,
        codex_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "Updated MCP server figma bearer_token_env_var\n"
    assert (
        read_user_config(codex_home)["mcp_servers"]["figma"]["bearer_token_env_var"]
        == "FIGMA_TOKEN"
    )


def test_mcp_add_env_var_preserves_inline_entries_and_avoids_duplicates(workspace, run_cli):
    """add-env-var appends string env vars while preserving object entries."""
    project, codex_home = workspace
    write_user_config(
        codex_home,
        '''
[mcp_servers.context7]
command = "npx"
env_vars = ["LOCAL_TOKEN", { name = "REMOTE_TOKEN", source = "remote" }]
''',
    )

    first_exit, _, first_err = run_cli(
        ["mcp", "add-env-var", "context7", "LOCAL_TOKEN"],
        project,
        codex_home,
    )
    second_exit, stdout, second_err = run_cli(
        ["mcp", "add-env-var", "context7", "EXTRA_TOKEN"],
        project,
        codex_home,
    )

    assert first_exit == 0
    assert first_err == ""
    assert second_exit == 0
    assert second_err == ""
    assert stdout == "Updated MCP server context7 env_vars\n"
    env_vars = read_user_config(codex_home)["mcp_servers"]["context7"]["env_vars"]
    assert env_vars == [
        "LOCAL_TOKEN",
        {"name": "REMOTE_TOKEN", "source": "remote"},
        "EXTRA_TOKEN",
    ]


def test_mcp_remove_env_var_removes_only_string_entries(workspace, run_cli):
    """remove-env-var keeps object entries and removes matching string entries."""
    project, codex_home = workspace
    write_user_config(
        codex_home,
        '''
[mcp_servers.context7]
command = "npx"
env_vars = ["LOCAL_TOKEN", { name = "LOCAL_TOKEN", source = "remote" }]
''',
    )

    exit_code, stdout, stderr = run_cli(
        ["mcp", "remove-env-var", "context7", "LOCAL_TOKEN"],
        project,
        codex_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "Updated MCP server context7 env_vars\n"
    assert read_user_config(codex_home)["mcp_servers"]["context7"]["env_vars"] == [
        {"name": "LOCAL_TOKEN", "source": "remote"}
    ]


def test_mcp_set_and_unset_env_header(workspace, run_cli):
    """env header commands mutate env_http_headers on an existing server."""
    project, codex_home = workspace
    write_user_config(
        codex_home,
        '''
[mcp_servers.figma]
url = "https://mcp.figma.com/mcp"
''',
    )

    set_exit, set_stdout, set_stderr = run_cli(
        ["mcp", "set-env-header", "figma", "X-Figma-Token", "FIGMA_TOKEN"],
        project,
        codex_home,
    )
    unset_exit, unset_stdout, unset_stderr = run_cli(
        ["mcp", "unset-env-header", "figma", "X-Figma-Token"],
        project,
        codex_home,
    )

    assert set_exit == 0
    assert set_stderr == ""
    assert set_stdout == "Updated MCP server figma env_http_headers\n"
    assert unset_exit == 0
    assert unset_stderr == ""
    assert unset_stdout == "Updated MCP server figma env_http_headers\n"
    assert read_user_config(codex_home)["mcp_servers"]["figma"]["env_http_headers"] == {}


def test_mcp_set_field_updates_allowlisted_toml_values(workspace, run_cli):
    """set-field parses TOML values for non-secret allowlisted fields."""
    project, codex_home = workspace
    write_user_config(
        codex_home,
        '''
[mcp_servers.context7]
command = "npx"
''',
    )

    exit_code, stdout, stderr = run_cli(
        ["mcp", "set-field", "context7", "enabled_tools", '["search", "open"]'],
        project,
        codex_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "Updated MCP server context7 enabled_tools\n"
    assert read_user_config(codex_home)["mcp_servers"]["context7"]["enabled_tools"] == [
        "search",
        "open",
    ]


def test_mcp_set_field_rejects_unknown_or_invalid_fields(workspace, run_cli):
    """set-field accepts only the documented safe field allowlist."""
    project, codex_home = workspace
    write_user_config(
        codex_home,
        '''
[mcp_servers.context7]
command = "npx"
''',
    )

    unknown_exit, _, unknown_err = run_cli(
        ["mcp", "set-field", "context7", "env", '{TOKEN="raw"}'],
        project,
        codex_home,
    )
    invalid_exit, _, invalid_err = run_cli(
        ["mcp", "set-field", "context7", "default_tools_approval_mode", '"always"'],
        project,
        codex_home,
    )

    assert unknown_exit == 1
    assert "Unsupported MCP field for set-field: env" in unknown_err
    assert invalid_exit == 1
    assert "default_tools_approval_mode must be one of auto, prompt, approve" in invalid_err
    assert "env" not in read_user_config(codex_home)["mcp_servers"]["context7"]


def test_mcp_parameter_mutation_missing_server_does_not_create_entry(workspace, run_cli):
    """Parameter commands fail for absent server ids and do not create entries."""
    project, codex_home = workspace
    write_user_config(
        codex_home,
        '''
[mcp_servers.context7]
command = "npx"
''',
    )

    exit_code, stdout, stderr = run_cli(
        ["mcp", "set-token-env", "missing", "TOKEN"],
        project,
        codex_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "MCP server not found: missing" in stderr
    assert sorted(read_user_config(codex_home)["mcp_servers"]) == ["context7"]
