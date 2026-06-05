"""Tests for MCP commands that edit user Codex config safely."""

import tomllib
from pathlib import Path


def write_user_config(codex_home: Path, content: str) -> Path:
    """Write a temporary CODEX_HOME config.toml fixture.

    Args:
        codex_home: Temporary Codex home directory.
        content: TOML content to write.

    Returns:
        The written config path.
    """
    path = codex_home / "config.toml"
    path.write_text(content, encoding="utf-8")
    return path


def read_user_config(codex_home: Path):
    """Read a temporary CODEX_HOME config.toml fixture.

    Args:
        codex_home: Temporary Codex home directory.

    Returns:
        Parsed TOML data.
    """
    return tomllib.loads((codex_home / "config.toml").read_text(encoding="utf-8"))


def test_mcp_list_reads_injected_codex_home_without_project_setup(workspace, run_cli):
    """mcp list reads CODEX_HOME/config.toml and does not require .codex/."""
    project, codex_home = workspace
    write_user_config(
        codex_home,
        '''
[mcp_servers.context7]
command = "npx"
args = ["-y", "@upstash/context7-mcp"]
''',
    )

    exit_code, stdout, stderr = run_cli(["mcp", "list"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert "context7" in stdout
    assert "enabled" in stdout
    assert "implicit" in stdout
    assert "stdio" in stdout
    assert "npx -y @upstash/context7-mcp" in stdout
    assert not (project / ".codex").exists()


def test_mcp_list_reports_none_when_user_config_is_missing(workspace, run_cli):
    """mcp list handles a missing user config as an empty MCP config."""
    project, codex_home = workspace

    exit_code, stdout, stderr = run_cli(["mcp", "list"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "MCP servers: none\n"


def test_mcp_disable_preserves_comments_and_unrelated_config(workspace, run_cli):
    """disable mutates only enabled on an existing server and preserves comments."""
    project, codex_home = workspace
    path = write_user_config(
        codex_home,
        '''
# user-owned model comment
model = "gpt-5"

[mcp_servers.context7]
# server command comment
command = "npx"
args = ["-y", "@upstash/context7-mcp"]
env_vars = ["CONTEXT7_TOKEN"]
''',
    )

    exit_code, stdout, stderr = run_cli(["mcp", "disable", "context7"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "Disabled MCP server context7\n"
    raw = path.read_text(encoding="utf-8")
    assert "# user-owned model comment" in raw
    assert "# server command comment" in raw
    config = read_user_config(codex_home)
    assert config["model"] == "gpt-5"
    assert config["mcp_servers"]["context7"]["enabled"] is False
    assert config["mcp_servers"]["context7"]["args"] == [
        "-y",
        "@upstash/context7-mcp",
    ]


def test_mcp_enable_updates_existing_disabled_server(workspace, run_cli):
    """enable sets enabled true on an existing disabled MCP server."""
    project, codex_home = workspace
    write_user_config(
        codex_home,
        '''
[mcp_servers.figma]
url = "https://mcp.figma.com/mcp"
enabled = false
''',
    )

    exit_code, stdout, stderr = run_cli(["mcp", "enable", "figma"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "Enabled MCP server figma\n"
    assert read_user_config(codex_home)["mcp_servers"]["figma"]["enabled"] is True


def test_mcp_disable_missing_server_fails_without_creating_entry(workspace, run_cli):
    """disable fails for absent server ids and does not create new servers."""
    project, codex_home = workspace
    write_user_config(
        codex_home,
        '''
[mcp_servers.context7]
command = "npx"
''',
    )

    exit_code, stdout, stderr = run_cli(["mcp", "disable", "missing"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert "MCP server not found: missing" in stderr
    config = read_user_config(codex_home)
    assert sorted(config["mcp_servers"]) == ["context7"]


def test_mcp_disable_missing_user_config_fails(workspace, run_cli):
    """Mutating MCP commands fail clearly when user config.toml is missing."""
    project, codex_home = workspace

    exit_code, stdout, stderr = run_cli(["mcp", "disable", "context7"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert f"Codex config not found: {codex_home / 'config.toml'}" in stderr


def test_mcp_disable_invalid_enabled_value_fails_without_overwriting(workspace, run_cli):
    """enabled must be boolean when present and is not silently replaced."""
    project, codex_home = workspace
    write_user_config(
        codex_home,
        '''
[mcp_servers.context7]
command = "npx"
enabled = "sometimes"
''',
    )

    exit_code, stdout, stderr = run_cli(["mcp", "disable", "context7"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert "mcp_servers.context7.enabled must be a boolean" in stderr
    assert read_user_config(codex_home)["mcp_servers"]["context7"]["enabled"] == "sometimes"
