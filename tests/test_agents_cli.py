"""CLI tests for project custom-agent management."""


def test_agents_list_marks_available_enabled_disabled_and_missing(
    workspace,
    run_cli_with_homes,
):
    """agents list reports available custom agents with project state markers."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_agent(codexmgr_home, "reviewer")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(
        ["agents", "enable", "--no-sync", "reviewer"],
        project,
        codex_home,
        codexmgr_home,
    )
    run_cli_with_homes(
        ["agents", "disable", "--no-sync", "legacy"],
        project,
        codex_home,
        codexmgr_home,
    )

    exit_code, stdout, stderr = run_cli_with_homes(
        ["agents", "list"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "disabled legacy (missing)\nenabled reviewer\n"


def test_agents_enable_applies_and_copies_agent(
    workspace,
    run_cli_with_homes,
    read_project_config,
    read_lock,
):
    """agents enable stores config, copies the TOML file, and locks ownership."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    source = _write_agent(codexmgr_home, "reviewer", 'name = "reviewer"\n')
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["agents", "enable", "reviewer"],
        project,
        codex_home,
        codexmgr_home,
    )

    target = project / ".codex" / "agents" / "reviewer.toml"
    assert exit_code == 0
    assert stderr == ""
    assert stdout == "Enabled reviewer\nApplied project Codex configuration\n"
    assert read_project_config(project)["agents"] == {
        "enabled": ["reviewer"],
        "disabled": [],
    }
    assert target.read_text(encoding="utf-8") == 'name = "reviewer"\n'
    assert read_lock(project)["agents"] == {
        "enabled": ["reviewer"],
        "disabled": [],
        "copies": [
            {
                "name": "reviewer",
                "source": str(source.resolve()),
                "target": str(target.resolve()),
            },
        ],
    }


def test_agents_enable_and_disable_accept_multiple_names(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """agents enable and disable accept multiple agent names per call."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_agent(codexmgr_home, "reviewer")
    _write_agent(codexmgr_home, "rules")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    enable_exit, enable_stdout, enable_stderr = run_cli_with_homes(
        ["agents", "enable", "reviewer", "rules"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert enable_exit == 0
    assert enable_stderr == ""
    assert enable_stdout == (
        "Enabled reviewer\n"
        "Enabled rules\n"
        "Applied project Codex configuration\n"
    )
    assert read_project_config(project)["agents"] == {
        "enabled": ["reviewer", "rules"],
        "disabled": [],
    }

    disable_exit, disable_stdout, disable_stderr = run_cli_with_homes(
        ["agents", "disable", "reviewer", "rules"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert disable_exit == 0
    assert disable_stderr == ""
    assert disable_stdout == (
        "Disabled reviewer\n"
        "Disabled rules\n"
        "Applied project Codex configuration\n"
    )
    assert read_project_config(project)["agents"] == {
        "enabled": [],
        "disabled": ["reviewer", "rules"],
    }
    assert not (project / ".codex" / "agents" / "reviewer.toml").exists()
    assert not (project / ".codex" / "agents" / "rules.toml").exists()


def test_agents_enable_no_sync_updates_config_without_copying(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """agents enable --no-sync updates config without refreshing copied agents."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_agent(codexmgr_home, "reviewer")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["agents", "enable", "--no-sync", "reviewer"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "Enabled reviewer\n"
    assert read_project_config(project)["agents"] == {
        "enabled": ["reviewer"],
        "disabled": [],
    }
    assert not (project / ".codex" / "agents" / "reviewer.toml").exists()


def test_agents_enable_fails_for_missing_agent(
    workspace,
    run_cli_with_homes,
):
    """agents enable validates named source files before writing config."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["agents", "enable", "missing"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "Agent not found:" in stderr
    assert "missing.toml" in stderr


def test_agents_enable_rejects_invalid_agent_toml(
    workspace,
    run_cli_with_homes,
):
    """agents enable validates source TOML before writing config."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_agent(codexmgr_home, "bad", "not valid toml")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["agents", "enable", "bad"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "Invalid TOML" in stderr


def test_agents_enable_refuses_unmanaged_copy_target(
    workspace,
    run_cli_with_homes,
):
    """agents enable refuses to overwrite an untracked project-local agent."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_agent(codexmgr_home, "reviewer")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    target = project / ".codex" / "agents" / "reviewer.toml"
    target.parent.mkdir(parents=True)
    target.write_text('name = "local"\n', encoding="utf-8")

    exit_code, stdout, stderr = run_cli_with_homes(
        ["agents", "enable", "reviewer"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "Refusing to overwrite unmanaged agent copy:" in stderr
    assert target.read_text(encoding="utf-8") == 'name = "local"\n'


def _write_agent(home, name, content='name = "agent"\n'):
    """Create a named custom agent under CODEXMGR_HOME.

    Args:
        home: Codexmgr home directory where the agent should be created.
        name: Agent file stem.
        content: TOML content to write.

    Returns:
        Path to the created custom-agent TOML file.
    """
    agents_dir = home / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    path = agents_dir / f"{name}.toml"
    path.write_text(content, encoding="utf-8")
    return path
