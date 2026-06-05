"""CLI tests for MCP user config validation."""

from pathlib import Path


def write_user_config(codex_home: Path, content: str) -> None:
    """Write a temporary CODEX_HOME config.toml fixture.

    Args:
        codex_home: Temporary Codex home directory.
        content: TOML content to write.
    """
    (codex_home / "config.toml").write_text(content, encoding="utf-8")


def test_mcp_validate_reports_valid_config_and_warnings(workspace, run_cli):
    """validate succeeds for valid config and reports deterministic warnings."""
    project, codex_home = workspace
    write_user_config(
        codex_home,
        '''
[mcp_servers.context7]
command = "npx"
env_vars = ["CONTEXT7_TOKEN"]

[mcp_servers.context7.env]
RAW_TOKEN = "raw-secret"

[mcp_servers.figma]
url = "https://mcp.figma.com/mcp"
http_headers = { Authorization = "Bearer raw-secret" }
''',
    )

    exit_code, stdout, stderr = run_cli(["mcp", "validate"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert "Valid MCP config: 2 servers" in stdout
    assert "WARN Raw env values configured for context7: RAW_TOKEN" in stdout
    assert "WARN Static HTTP headers configured for figma: Authorization" in stdout
    assert "raw-secret" not in stdout


def test_mcp_validate_one_server(workspace, run_cli):
    """validate can check one existing server id."""
    project, codex_home = workspace
    write_user_config(
        codex_home,
        '''
[mcp_servers.context7]
command = "npx"

[mcp_servers.figma]
url = "https://mcp.figma.com/mcp"
''',
    )

    exit_code, stdout, stderr = run_cli(["mcp", "validate", "figma"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert "Valid MCP server figma" in stdout
    assert "context7" not in stdout


def test_mcp_validate_fails_for_invalid_mcp_servers_shape(workspace, run_cli):
    """validate reports a non-table mcp_servers value."""
    project, codex_home = workspace
    write_user_config(codex_home, 'mcp_servers = "invalid"\n')

    exit_code, stdout, stderr = run_cli(["mcp", "validate"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert "config.toml [mcp_servers] must be a table" in stderr


def test_mcp_validate_fails_for_transport_conflicts(workspace, run_cli):
    """validate catches missing or conflicting server transports."""
    project, codex_home = workspace
    write_user_config(
        codex_home,
        '''
[mcp_servers.conflict]
command = "npx"
url = "https://example.test/mcp"
''',
    )

    exit_code, stdout, stderr = run_cli(["mcp", "validate"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert "mcp_servers.conflict must set exactly one of command or url" in stderr


def test_mcp_validate_fails_for_invalid_mutated_field_shapes(workspace, run_cli):
    """validate catches invalid fields this feature reads or mutates."""
    project, codex_home = workspace
    write_user_config(
        codex_home,
        '''
[mcp_servers.context7]
command = "npx"
enabled = "sometimes"
enabled_tools = "search"
''',
    )

    exit_code, stdout, stderr = run_cli(["mcp", "validate"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert "mcp_servers.context7.enabled must be a boolean" in stderr
