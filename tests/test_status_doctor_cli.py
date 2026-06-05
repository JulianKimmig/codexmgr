"""CLI tests for project status and doctor checks."""


def test_status_reports_configured_state_and_sync_status(
    workspace,
    write_home_template,
    run_cli,
):
    """status prints a compact summary of configured snippets, skills, and sync."""
    project, codex_home = workspace
    write_home_template(
        codex_home,
        "coding",
        '''
[rules]
text = "current"
''',
    )
    _write_skill(codex_home, "review")

    run_cli(["setup"], project, codex_home)
    run_cli(["agentsmd", "add", "coding"], project, codex_home)
    run_cli(["skill", "enable", "review"], project, codex_home)
    exit_code, stdout, stderr = run_cli(["status"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert f"Project: {project}" in stdout
    assert f"CODEX_HOME: {codex_home}" in stdout
    assert "AGENTS.md snippets: coding" in stdout
    assert "Enabled skills: review" in stdout
    assert "Disabled skills: none" in stdout
    assert "Generated files: in sync" in stdout


def test_status_reports_out_of_sync_generated_files(
    workspace,
    write_home_template,
    run_cli,
):
    """status reports when generated files do not match codexmgr.toml."""
    project, codex_home = workspace
    write_home_template(
        codex_home,
        "coding",
        '''
[rules]
text = "pending"
''',
    )

    run_cli(["setup"], project, codex_home)
    run_cli(["agentsmd", "add", "--no-sync", "coding"], project, codex_home)
    exit_code, stdout, stderr = run_cli(["status"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert "Generated files: out of sync" in stdout
    assert ".codex/codexmgr.lock" in stdout
    assert "AGENTS.md" in stdout


def test_doctor_fails_when_project_codex_directory_is_missing(workspace, run_cli):
    """doctor reports a missing project .codex directory."""
    project, codex_home = workspace

    exit_code, stdout, stderr = run_cli(["doctor"], project, codex_home)

    assert exit_code == 1
    assert stderr == ""
    assert "ERROR Project .codex directory not found" in stdout


def test_doctor_reports_invalid_project_config(workspace, run_cli):
    """doctor reports invalid codexmgr.toml syntax."""
    project, codex_home = workspace
    (project / ".codex").mkdir()
    (project / ".codex" / "codexmgr.toml").write_text(
        "not valid toml",
        encoding="utf-8",
    )

    exit_code, stdout, stderr = run_cli(["doctor"], project, codex_home)

    assert exit_code == 1
    assert stderr == ""
    assert "ERROR Invalid TOML" in stdout


def test_doctor_reports_missing_agentsmd_source(workspace, run_cli):
    """doctor reports configured AGENTS.md snippets that cannot be resolved."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    (project / ".codex" / "codexmgr.toml").write_text(
        '''
[agents_md]
src = ["missing-snippet"]
''',
        encoding="utf-8",
    )

    exit_code, stdout, stderr = run_cli(["doctor"], project, codex_home)

    assert exit_code == 1
    assert stderr == ""
    assert "ERROR Template not found:" in stdout
    assert "missing-snippet.toml" in stdout


def test_doctor_reports_missing_enabled_skill_and_stale_outputs(workspace, run_cli):
    """doctor reports missing enabled skills and stale generated files."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    (project / ".codex" / "codexmgr.toml").write_text(
        '''
[skills]
enabled = ["missing-skill"]
disabled = []
''',
        encoding="utf-8",
    )

    exit_code, stdout, stderr = run_cli(["doctor"], project, codex_home)

    assert exit_code == 1
    assert stderr == ""
    assert "ERROR Missing enabled skill: missing-skill" in stdout
    assert "ERROR Out of sync: .codex/codexmgr.lock" in stdout
    assert "ERROR Out of sync: .codex/config.toml" in stdout


def test_doctor_warns_when_home_environment_variables_are_unset(
    workspace,
    run_cli,
):
    """doctor warns about unset home variables while using resolved defaults."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    (project / ".codex" / "codexmgr.toml").write_text("", encoding="utf-8")

    exit_code, stdout, stderr = run_cli(["doctor"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert "WARN CODEX_HOME not set" in stdout
    assert "WARN CODEXMGR_HOME not set" in stdout
    assert "OK Project checks passed" in stdout


def _write_skill(codex_home, name):
    """Create a named Codex skill under CODEX_HOME.

    Args:
        codex_home: Codex home directory where the skill should be created.
        name: Skill directory name to create.

    Returns:
        Path to the created SKILL.md file.
    """
    skill_dir = codex_home / "skills" / name
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# Skill\n", encoding="utf-8")
    return skill_file
