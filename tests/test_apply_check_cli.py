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
