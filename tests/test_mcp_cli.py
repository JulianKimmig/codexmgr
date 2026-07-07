"""CLI tests for project-local MCP source and override management."""


def test_mcp_enable_writes_source_ref_and_applies_without_touching_user_config(
    workspace,
    run_cli_with_homes,
    read_project_config,
    read_codex_config,
    read_lock,
):
    """mcp enable records a reusable source and writes local Codex config."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_mcp_source(
        codexmgr_home,
        "browsermcp",
        '''
[mcp_servers.browsermcp]
command = "browsermcp"
args = ["--port", "3000"]
env_vars = ["BROWSERMCP_TOKEN"]
''',
    )
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
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["mcp", "enable", "browsermcp"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == (
        "Enabled MCP source browsermcp\n"
        "Applied project Codex configuration\n"
    )
    assert read_project_config(project)["mcp"]["enabled"] == ["browsermcp"]
    assert read_codex_config(project)["mcp_servers"]["browsermcp"] == {
        "command": "browsermcp",
        "args": ["--port", "3000"],
        "env_vars": ["BROWSERMCP_TOKEN"],
    }
    assert read_lock(project)["mcp"]["enabled"] == ["browsermcp"]
    assert read_lock(project)["mcp"]["servers"]["browsermcp"]["command"] == "browsermcp"
    assert user_config.read_text(encoding="utf-8") == original_user_config


def test_mcp_enable_no_sync_updates_only_codexmgr_toml(
    workspace,
    run_cli_with_homes,
    read_project_config,
    read_codex_config,
):
    """--no-sync keeps generated local Codex config untouched for sources."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_mcp_source(codexmgr_home, "browsermcp")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["mcp", "enable", "--no-sync", "browsermcp"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "Enabled MCP source browsermcp\n"
    assert read_project_config(project)["mcp"]["enabled"] == ["browsermcp"]
    assert read_codex_config(project) == {}
    assert not (codex_home / "config.toml").exists()


def test_mcp_enable_and_disable_accept_multiple_sources(
    workspace,
    run_cli_with_homes,
    read_project_config,
    read_codex_config,
):
    """mcp enable and disable accept multiple source names per call."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_mcp_source(codexmgr_home, "browsermcp")
    _write_mcp_source(
        codexmgr_home,
        "context7",
        '''
[mcp_servers.context7]
command = "context7"
''',
    )
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    enable_exit, enable_stdout, enable_stderr = run_cli_with_homes(
        ["mcp", "enable", "browsermcp", "context7"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert enable_exit == 0
    assert enable_stderr == ""
    assert enable_stdout == (
        "Enabled MCP source browsermcp\n"
        "Enabled MCP source context7\n"
        "Applied project Codex configuration\n"
    )
    assert read_project_config(project)["mcp"]["enabled"] == ["browsermcp", "context7"]
    assert read_codex_config(project)["mcp_servers"] == {
        "browsermcp": {"command": "browsermcp"},
        "context7": {"command": "context7"},
    }

    disable_exit, disable_stdout, disable_stderr = run_cli_with_homes(
        ["mcp", "disable", "browsermcp", "context7"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert disable_exit == 0
    assert disable_stderr == ""
    assert disable_stdout == (
        "Disabled MCP source browsermcp\n"
        "Disabled MCP source context7\n"
        "Applied project Codex configuration\n"
    )
    assert read_project_config(project)["mcp"]["enabled"] == []
    assert "browsermcp" not in read_codex_config(project).get("mcp_servers", {})
    assert "context7" not in read_codex_config(project).get("mcp_servers", {})


def test_mcp_mutation_preserves_codexmgr_toml_comments(workspace, run_cli):
    """MCP server override mutations preserve existing comments."""
    project, codex_home = workspace
    _write_mcp_source(codex_home, "browsermcp")
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
    assert "[mcp]" in content
    assert 'enabled = ["browsermcp"]' in content


def test_mcp_apply_preserves_existing_local_server_fields(workspace, run_cli, read_codex_config):
    """Generated MCP source fields update without replacing unrelated manual fields."""
    project, codex_home = workspace
    _write_mcp_source(
        codex_home,
        "browsermcp",
        '''
[mcp_servers.browsermcp]
enabled = true
''',
    )
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
    """mcp source mutations are project config changes and require .codex/."""
    project, codex_home = workspace
    _write_mcp_source(codex_home, "browsermcp")

    exit_code, stdout, stderr = run_cli(["mcp", "enable", "browsermcp"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert "Project .codex directory not found" in stderr
    assert not (codex_home / "config.toml").exists()


def test_mcp_enable_rejects_missing_source_without_touching_project_config(
    workspace,
    run_cli,
    read_project_config,
):
    """mcp enable validates reusable sources before writing project config."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    original_config = read_project_config(project)

    exit_code, stdout, stderr = run_cli(["mcp", "enable", "missing"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert "MCP source not found" in stderr
    assert read_project_config(project) == original_config
    assert not (codex_home / "config.toml").exists()


def test_mcp_enable_rejects_duplicate_server_ids_without_writing(
    workspace,
    run_cli,
    read_project_config,
):
    """Enabled reusable MCP sources cannot declare the same server id."""
    project, codex_home = workspace
    _write_mcp_source(
        codex_home,
        "one",
        '''
[mcp_servers.shared]
command = "one"
''',
    )
    _write_mcp_source(
        codex_home,
        "two",
        '''
[mcp_servers.shared]
command = "two"
''',
    )
    run_cli(["setup"], project, codex_home)
    original_config = read_project_config(project)

    exit_code, stdout, stderr = run_cli(["mcp", "enable", "one", "two"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert "Duplicate MCP server id shared" in stderr
    assert read_project_config(project) == original_config


def test_mcp_list_shows_available_enabled_and_missing_sources(workspace, run_cli):
    """mcp list shows reusable sources without reading user Codex config."""
    project, codex_home = workspace
    _write_mcp_source(codex_home, "browsermcp")
    _write_mcp_source(
        codex_home,
        "context7",
        '''
[mcp_servers.context7]
command = "context7"
''',
    )
    run_cli(["setup"], project, codex_home)
    run_cli(["mcp", "enable", "--no-sync", "browsermcp"], project, codex_home)
    config_path = project / ".codex" / "codexmgr.toml"
    config_path.write_text(config_path.read_text(encoding="utf-8").replace(
        'enabled = ["browsermcp"]',
        'enabled = ["browsermcp", "missing"]',
    ), encoding="utf-8")

    list_exit, list_stdout, list_stderr = run_cli(["mcp", "list"], project, codex_home)

    assert list_exit == 0
    assert list_stderr == ""
    assert "browsermcp source=enabled servers=browsermcp" in list_stdout
    assert "context7 source=available servers=context7" in list_stdout
    assert "missing source=missing" in list_stdout


def test_mcp_list_reports_invalid_source_files(workspace, run_cli):
    """mcp list fails loudly when an available source file is invalid."""
    project, codex_home = workspace
    _write_mcp_source(codex_home, "bad", 'model = "gpt-5"\n')

    exit_code, stdout, stderr = run_cli(["mcp", "list"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert "must contain an [mcp_servers] table" in stderr


def test_mcp_show_reads_project_overrides(workspace, run_cli):
    """mcp show inspects reusable sources and project enabled state."""
    project, codex_home = workspace
    _write_mcp_source(codex_home, "browsermcp")
    run_cli(["setup"], project, codex_home)
    run_cli(["mcp", "enable", "--no-sync", "browsermcp"], project, codex_home)
    run_cli(["mcp", "set-token-env", "--no-sync", "browsermcp", "BROWSERMCP_TOKEN"], project, codex_home)

    show_exit, show_stdout, show_stderr = run_cli(["mcp", "show", "browsermcp"], project, codex_home)

    assert show_exit == 0
    assert show_stderr == ""
    assert "MCP source: browsermcp" in show_stdout
    assert "State: enabled" in show_stdout
    assert "Servers: browsermcp" in show_stdout
    assert "Project override fields: browsermcp.bearer_token_env_var" in show_stdout


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
    """validate accepts Codex-shaped server fields and does not read user config."""
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
    assert "Valid MCP config: 0 sources, 1 server" in stdout
    assert not (codex_home / "config.toml").exists()


def _write_mcp_source(codexmgr_home, name, content=None):
    """Create a reusable MCP source file for CLI tests.

    Args:
        codexmgr_home: Codexmgr home directory.
        name: Source file stem.
        content: Optional TOML content for the source.

    Returns:
        Path to the created source file.
    """
    source_dir = codexmgr_home / "mcp"
    source_dir.mkdir(parents=True, exist_ok=True)
    path = source_dir / f"{name}.toml"
    path.write_text(
        content
        if content is not None
        else f'[mcp_servers.{name}]\ncommand = "{name}"\n',
        encoding="utf-8",
    )
    return path
