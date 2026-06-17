"""CLI tests for checking generated codexmgr files without writing them."""


def test_apply_check_succeeds_when_generated_files_are_current(
    workspace,
    write_home_template,
    run_cli,
):
    """apply --check exits successfully when generated files match config."""
    project, codex_home = workspace
    write_home_template(
        codex_home,
        "coding",
        '''
[rules]
text = "current"
''',
    )

    run_cli(["setup"], project, codex_home)
    run_cli(["agentsmd", "add", "coding"], project, codex_home)
    exit_code, stdout, stderr = run_cli(["apply", "--check"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "Project Codex configuration is in sync\n"


def test_apply_check_fails_when_generated_files_are_stale(
    workspace,
    write_home_template,
    run_cli,
):
    """apply --check reports stale generated files without writing them."""
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
    exit_code, stdout, stderr = run_cli(["apply", "--check"], project, codex_home)

    assert exit_code == 1
    assert stderr == ""
    assert "Out of sync: .codex/codexmgr.lock" in stdout
    assert "Out of sync: AGENTS.md" in stdout
    assert not (project / ".codex" / "codexmgr.lock").exists()
    assert not (project / "AGENTS.md").exists()


def test_apply_check_reports_missing_empty_codex_config(workspace, run_cli):
    """apply --check treats a missing empty local config as out of sync."""
    project, codex_home = workspace
    (project / ".codex").mkdir()
    (project / ".codex" / "codexmgr.toml").write_text("", encoding="utf-8")

    exit_code, stdout, stderr = run_cli(["apply", "--check"], project, codex_home)

    assert exit_code == 1
    assert stderr == ""
    assert "Out of sync: .codex/config.toml" in stdout


def test_apply_diff_prints_expected_changes_without_writing(
    workspace,
    write_home_template,
    run_cli,
):
    """apply --diff prints a unified diff and leaves generated files unchanged."""
    project, codex_home = workspace
    write_home_template(
        codex_home,
        "coding",
        '''
[rules]
text = "diff me"
''',
    )

    run_cli(["setup"], project, codex_home)
    run_cli(["agentsmd", "add", "--no-sync", "coding"], project, codex_home)
    exit_code, stdout, stderr = run_cli(["apply", "--diff"], project, codex_home)

    assert exit_code == 1
    assert stderr == ""
    assert "--- AGENTS.md (current)" in stdout
    assert "+++ AGENTS.md (expected)" in stdout
    assert "+# rules" in stdout
    assert "+diff me" in stdout
    assert not (project / "AGENTS.md").exists()


def test_apply_check_reports_stale_managed_skill_copy(
    workspace,
    run_cli_with_homes,
):
    """apply --check reports managed CODEXMGR_HOME skill copies as stale."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_skill(codexmgr_home, "review", "# Review\n")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(["skill", "enable", "review"], project, codex_home, codexmgr_home)
    target_file = project / ".agents" / "skills" / "review" / "SKILL.md"
    target_file.write_text("# Local edit\n", encoding="utf-8")

    exit_code, stdout, stderr = run_cli_with_homes(
        ["apply", "--check"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stderr == ""
    assert "Out of sync: .agents/skills/review/SKILL.md" in stdout
    assert target_file.read_text(encoding="utf-8") == "# Local edit\n"


def test_apply_diff_reports_managed_skill_copy_changes_without_writing(
    workspace,
    run_cli_with_homes,
):
    """apply --diff prints managed skill copy diffs and leaves files unchanged."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_skill(codexmgr_home, "review", "# Review\n")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(["skill", "enable", "review"], project, codex_home, codexmgr_home)
    target_file = project / ".agents" / "skills" / "review" / "SKILL.md"
    target_file.write_text("# Local edit\n", encoding="utf-8")

    exit_code, stdout, stderr = run_cli_with_homes(
        ["apply", "--diff"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stderr == ""
    assert "--- .agents/skills/review/SKILL.md (current)" in stdout
    assert "+++ .agents/skills/review/SKILL.md (expected)" in stdout
    assert "-# Local edit" in stdout
    assert "+# Review" in stdout
    assert target_file.read_text(encoding="utf-8") == "# Local edit\n"


def _write_skill(home, name, content):
    """Create a named skill directory with a SKILL.md file.

    Args:
        home: Home directory whose skills folder should receive the skill.
        name: Skill directory name to create.
        content: SKILL.md text to write.

    Returns:
        Path to the created SKILL.md file.
    """
    skill_dir = home / "skills" / name
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content, encoding="utf-8")
    return skill_file
