"""CLI tests for project-local MCP override management."""

from types import SimpleNamespace


def test_mcp_enable_writes_project_config_and_applies_without_touching_user_config(
    workspace,
    run_cli,
    read_project_config,
    read_codex_config,
    read_lock,
):
    """mcp enable records a project override and writes local Codex config."""
    project, codex_home = workspace
    user_config = codex_home / "config.toml"
    user_config.write_text(
        '''
[mcp_servers.browsermcp]
command = "browsermcp"
enabled = false
''',
        encoding="utf-8",
    )
    original_user_config = user_config.read_text(encoding="utf-8")
    run_cli(["setup"], project, codex_home)

    exit_code, stdout, stderr = run_cli(["mcp", "enable", "browsermcp"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert stdout == (
        "Enabled MCP server override browsermcp\n"
        "Applied project Codex configuration\n"
    )
    assert read_project_config(project)["mcp"]["servers"]["browsermcp"] == {
        "enabled": True,
    }
    assert read_codex_config(project)["mcp_servers"]["browsermcp"] == {
        "enabled": True,
    }
    assert read_lock(project)["mcp"]["servers"]["browsermcp"] == {
        "enabled": True,
    }
    assert user_config.read_text(encoding="utf-8") == original_user_config


def test_mcp_disable_no_sync_updates_only_codexmgr_toml(
    workspace,
    run_cli,
    read_project_config,
    read_codex_config,
):
    """--no-sync keeps generated local Codex config untouched."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)

    exit_code, stdout, stderr = run_cli(
        ["mcp", "disable", "--no-sync", "browsermcp"],
        project,
        codex_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "Disabled MCP server override browsermcp\n"
    assert read_project_config(project)["mcp"]["servers"]["browsermcp"] == {
        "enabled": False,
    }
    assert read_codex_config(project) == {}
    assert not (codex_home / "config.toml").exists()


def test_mcp_mutation_preserves_codexmgr_toml_comments(workspace, run_cli):
    """MCP mutations preserve existing comments in project codexmgr.toml."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    config_path = project / ".codex" / "codexmgr.toml"
    config_path.write_text(
        '''
# project source config
[skills]
# keep this skills comment
enabled = []
disabled = []
''',
        encoding="utf-8",
    )

    exit_code, _, stderr = run_cli(
        ["mcp", "enable", "--no-sync", "browsermcp"],
        project,
        codex_home,
    )

    assert exit_code == 0
    assert stderr == ""
    content = config_path.read_text(encoding="utf-8")
    assert "# project source config" in content
    assert "# keep this skills comment" in content
    assert "[mcp.servers.browsermcp]" in content


def test_mcp_apply_preserves_existing_local_server_fields(workspace, run_cli, read_codex_config):
    """Generated MCP overrides update fields without replacing manual local fields."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    (project / ".codex" / "config.toml").write_text(
        '''
model = "gpt-5"

[mcp_servers.browsermcp]
command = "browsermcp"
args = ["--port", "3000"]
enabled = false
''',
        encoding="utf-8",
    )

    exit_code, _, stderr = run_cli(["mcp", "enable", "browsermcp"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    config = read_codex_config(project)
    assert config["model"] == "gpt-5"
    assert config["mcp_servers"]["browsermcp"] == {
        "command": "browsermcp",
        "args": ["--port", "3000"],
        "enabled": True,
    }


def test_mcp_commands_require_project_setup(workspace, run_cli):
    """mcp mutations are project config changes and require .codex/."""
    project, codex_home = workspace

    exit_code, stdout, stderr = run_cli(["mcp", "enable", "browsermcp"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert "Project .codex directory not found" in stderr
    assert not (codex_home / "config.toml").exists()


def test_mcp_list_merges_codex_servers_with_project_overrides(workspace, run_cli, monkeypatch):
    """mcp list shows available Codex servers plus local override state."""
    project, codex_home = workspace
    captured = {}

    def fake_run(command, cwd, capture_output, text):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["capture_output"] = capture_output
        captured["text"] = text
        return SimpleNamespace(
            returncode=0,
            stdout='''
[
  {"name": "browsermcp", "enabled": true},
  {"name": "context7", "enabled": false}
]
''',
            stderr="",
        )

    monkeypatch.setattr("codexmgr.mcp.discovery.subprocess.run", fake_run)
    run_cli(["setup"], project, codex_home)
    run_cli(["mcp", "disable", "--no-sync", "browsermcp"], project, codex_home)
    run_cli(["mcp", "set-token-env", "--no-sync", "browsermcp", "BROWSERMCP_TOKEN"], project, codex_home)

    list_exit, list_stdout, list_stderr = run_cli(["mcp", "list"], project, codex_home)

    assert captured == {
        "command": ["codex", "mcp", "list", "--json"],
        "cwd": project,
        "capture_output": True,
        "text": True,
    }
    assert list_exit == 0
    assert list_stderr == ""
    assert "browsermcp available=enabled override=disabled" in list_stdout
    assert "fields=bearer_token_env_var, enabled" in list_stdout
    assert "context7 available=disabled override=none" in list_stdout


def test_mcp_list_reports_codex_discovery_failures(workspace, run_cli, monkeypatch):
    """mcp list fails loudly when Codex server discovery fails."""
    project, codex_home = workspace

    def fake_run(command, cwd, capture_output, text):
        return SimpleNamespace(returncode=2, stdout="", stderr="bad config")

    monkeypatch.setattr("codexmgr.mcp.discovery.subprocess.run", fake_run)

    exit_code, stdout, stderr = run_cli(["mcp", "list"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert "codex mcp list --json failed: bad config" in stderr


def test_mcp_show_reads_project_overrides(workspace, run_cli):
    """mcp show inspects configured project override entries."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    run_cli(["mcp", "disable", "--no-sync", "browsermcp"], project, codex_home)
    run_cli(["mcp", "set-token-env", "--no-sync", "browsermcp", "BROWSERMCP_TOKEN"], project, codex_home)

    show_exit, show_stdout, show_stderr = run_cli(["mcp", "show", "browsermcp"], project, codex_home)

    assert show_exit == 0
    assert show_stderr == ""
    assert "Server override: browsermcp" in show_stdout
    assert "State: disabled" in show_stdout
    assert "Bearer token env var: BROWSERMCP_TOKEN" in show_stdout


def test_mcp_parameter_commands_write_project_overrides(workspace, run_cli, read_project_config):
    """Parameter commands mutate the [mcp.servers] project override table."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)

    commands = [
        ["mcp", "set-token-env", "--no-sync", "browsermcp", "BROWSERMCP_TOKEN"],
        ["mcp", "add-env-var", "--no-sync", "browsermcp", "BROWSER_ENV"],
        ["mcp", "add-env-var", "--no-sync", "browsermcp", "BROWSER_ENV"],
        ["mcp", "set-env-header", "--no-sync", "browsermcp", "Authorization", "AUTH_ENV"],
        ["mcp", "set-field", "--no-sync", "browsermcp", "enabled_tools", '["open"]'],
        ["mcp", "set-field", "--no-sync", "browsermcp", "required", "true"],
    ]
    for command in commands:
        exit_code, _, stderr = run_cli(command, project, codex_home)
        assert exit_code == 0
        assert stderr == ""

    server = read_project_config(project)["mcp"]["servers"]["browsermcp"]
    assert server == {
        "bearer_token_env_var": "BROWSERMCP_TOKEN",
        "env_vars": ["BROWSER_ENV"],
        "env_http_headers": {"Authorization": "AUTH_ENV"},
        "enabled_tools": ["open"],
        "required": True,
    }
    assert not (codex_home / "config.toml").exists()


def test_mcp_remove_env_var_and_unset_env_header_update_project_overrides(
    workspace,
    run_cli,
    read_project_config,
):
    """Removal commands remove only the requested override values."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    run_cli(["mcp", "add-env-var", "--no-sync", "browsermcp", "BROWSER_ENV"], project, codex_home)
    run_cli(["mcp", "set-env-header", "--no-sync", "browsermcp", "Authorization", "AUTH_ENV"], project, codex_home)

    env_exit, _, env_stderr = run_cli(
        ["mcp", "remove-env-var", "--no-sync", "browsermcp", "BROWSER_ENV"],
        project,
        codex_home,
    )
    header_exit, _, header_stderr = run_cli(
        ["mcp", "unset-env-header", "--no-sync", "browsermcp", "Authorization"],
        project,
        codex_home,
    )

    assert env_exit == 0
    assert env_stderr == ""
    assert header_exit == 0
    assert header_stderr == ""
    server = read_project_config(project)["mcp"]["servers"]["browsermcp"]
    assert server["env_vars"] == []
    assert server["env_http_headers"] == {}


def test_mcp_set_field_rejects_unsafe_fields_without_touching_user_config(workspace, run_cli):
    """set-field cannot write raw env or other unsafe server definition fields."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)

    exit_code, stdout, stderr = run_cli(
        ["mcp", "set-field", "--no-sync", "browsermcp", "command", '"browsermcp"'],
        project,
        codex_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "Unsupported MCP field for set-field: command" in stderr
    assert not (codex_home / "config.toml").exists()


def test_mcp_validate_reports_project_override_warnings(workspace, run_cli):
    """validate checks project override shape and does not read user config."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    (project / ".codex" / "codexmgr.toml").write_text(
        '''
[mcp.servers.browsermcp]
enabled = true
env = { TOKEN = "raw" }
''',
        encoding="utf-8",
    )

    exit_code, stdout, stderr = run_cli(["mcp", "validate"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert "Valid MCP config: 1 server override" in stdout
    assert "WARN Unsupported MCP override field preserved nowhere: browsermcp.env" in stdout
    assert not (codex_home / "config.toml").exists()
