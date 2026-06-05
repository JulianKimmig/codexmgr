"""Apply and sync tests for project-local MCP overrides."""


def test_apply_writes_mcp_overrides_and_composes_with_skills(
    workspace,
    run_cli,
    read_codex_config,
    read_lock,
):
    """apply writes MCP overrides into local .codex/config.toml with skills."""
    project, codex_home = workspace
    skill_dir = codex_home / "skills" / "review"
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# Skill\n", encoding="utf-8")
    run_cli(["setup"], project, codex_home)
    (project / ".codex" / "codexmgr.toml").write_text(
        '''
[skills]
enabled = ["review"]
disabled = []

[mcp.servers.browsermcp]
enabled = false
bearer_token_env_var = "BROWSERMCP_TOKEN"
''',
        encoding="utf-8",
    )
    user_config = codex_home / "config.toml"
    user_config.write_text(
        '''
[mcp_servers.browsermcp]
command = "browsermcp"
enabled = true
''',
        encoding="utf-8",
    )
    original_user_config = user_config.read_text(encoding="utf-8")

    exit_code, _, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    config = read_codex_config(project)
    assert config["skills"]["config"] == [
        {"path": str(skill_file.resolve()), "enabled": True},
    ]
    assert config["mcp_servers"]["browsermcp"] == {
        "enabled": False,
        "bearer_token_env_var": "BROWSERMCP_TOKEN",
    }
    assert read_lock(project)["mcp"]["servers"]["browsermcp"] == {
        "enabled": False,
        "bearer_token_env_var": "BROWSERMCP_TOKEN",
    }
    assert user_config.read_text(encoding="utf-8") == original_user_config


def test_apply_preserves_local_codex_config_comments(workspace, run_cli):
    """apply preserves comments in the project-local Codex config file."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    (project / ".codex" / "codexmgr.toml").write_text(
        '''
[mcp.servers.browsermcp]
enabled = true
''',
        encoding="utf-8",
    )
    config_path = project / ".codex" / "config.toml"
    config_path.write_text(
        '''
# local codex config
model = "gpt-5"

[mcp_servers.browsermcp]
# keep command comment
command = "browsermcp"
''',
        encoding="utf-8",
    )

    exit_code, _, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    content = config_path.read_text(encoding="utf-8")
    assert "# local codex config" in content
    assert "# keep command comment" in content
    assert "enabled = true" in content


def test_apply_check_reports_stale_local_mcp_config(workspace, run_cli):
    """apply --check includes MCP-generated local config in sync checks."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    run_cli(["mcp", "enable", "--no-sync", "browsermcp"], project, codex_home)

    exit_code, stdout, stderr = run_cli(["apply", "--check"], project, codex_home)

    assert exit_code == 1
    assert stderr == ""
    assert ".codex/config.toml" in stdout
    assert ".codex/codexmgr.lock" in stdout


def test_apply_diff_shows_local_mcp_config_without_touching_user_config(workspace, run_cli):
    """apply --diff previews MCP changes and never writes CODEX_HOME/config.toml."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    run_cli(["mcp", "disable", "--no-sync", "browsermcp"], project, codex_home)

    exit_code, stdout, stderr = run_cli(["apply", "--diff"], project, codex_home)

    assert exit_code == 1
    assert stderr == ""
    assert "[mcp_servers.browsermcp]" in stdout
    assert "enabled = false" in stdout
    assert not (codex_home / "config.toml").exists()
