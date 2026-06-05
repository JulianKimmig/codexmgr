"""CLI tests for skipping automatic config synchronization."""


def test_agentsmd_add_no_sync_updates_config_without_applying(
    workspace, write_home_template, run_cli, read_project_config
):
    """agentsmd add --no-sync updates config without refreshing generated outputs."""
    project, codex_home = workspace
    write_home_template(
        codex_home,
        "coding",
        '''
[basics]
text = "foo"
''',
    )

    run_cli(["setup"], project, codex_home)
    exit_code, _, stderr = run_cli(
        ["agentsmd", "add", "--no-sync", "coding"], project, codex_home
    )

    assert exit_code == 0
    assert stderr == ""
    assert read_project_config(project)["agents_md"]["src"] == ["coding"]
    assert not (project / ".codex" / "codexmgr.lock").exists()
    assert not (project / "AGENTS.md").exists()


def test_agentsmd_remove_no_sync_updates_config_without_applying(
    workspace,
    write_home_template,
    run_cli,
    read_project_config,
):
    """agentsmd remove --no-sync updates config without refreshing generated outputs."""
    project, codex_home = workspace
    write_home_template(
        codex_home,
        "coding",
        '''
[basics]
text = "coding"
''',
    )
    write_home_template(
        codex_home,
        "review",
        '''
[review]
text = "review"
''',
    )

    run_cli(["setup"], project, codex_home)
    run_cli(["agentsmd", "add", "--no-sync", "coding"], project, codex_home)
    run_cli(["agentsmd", "add", "--no-sync", "review"], project, codex_home)
    exit_code, _, stderr = run_cli(
        ["agentsmd", "remove", "--no-sync", "coding"], project, codex_home
    )

    assert exit_code == 0
    assert stderr == ""
    assert read_project_config(project)["agents_md"]["src"] == ["review"]
    assert not (project / ".codex" / "codexmgr.lock").exists()
    assert not (project / "AGENTS.md").exists()


def test_skill_enable_no_sync_updates_config_without_applying(
    workspace, run_cli, read_project_config
):
    """skill enable --no-sync updates config without refreshing generated outputs."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)

    exit_code, stdout, stderr = run_cli(
        ["skill", "enable", "--no-sync", "coding"], project, codex_home
    )

    assert exit_code == 0
    assert stderr == ""
    assert "Enabled coding" in stdout
    assert read_project_config(project)["skills"] == {
        "enabled": ["coding"],
        "disabled": [],
    }
    assert not (project / ".codex" / "config.toml").exists()
    assert not (project / ".codex" / "codexmgr.lock").exists()


def test_skill_disable_no_sync_updates_config_without_applying(
    workspace, run_cli, read_project_config
):
    """skill disable --no-sync updates config without refreshing generated outputs."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)

    exit_code, stdout, stderr = run_cli(
        ["skill", "disable", "--no-sync", "coding"], project, codex_home
    )

    assert exit_code == 0
    assert stderr == ""
    assert "Disabled coding" in stdout
    assert read_project_config(project)["skills"] == {
        "enabled": [],
        "disabled": ["coding"],
    }
    assert not (project / ".codex" / "config.toml").exists()
    assert not (project / ".codex" / "codexmgr.lock").exists()
