"""CLI tests for listing available and configured Codex skills."""


def test_skill_list_marks_available_enabled_disabled_and_missing(
    workspace,
    run_cli,
):
    """skill list reports available skill names with project state markers."""
    project, codex_home = workspace
    _write_skill(codex_home, "review")
    _write_skill(codex_home, "lint")

    run_cli(["setup"], project, codex_home)
    run_cli(["skill", "enable", "--no-sync", "review"], project, codex_home)
    run_cli(["skill", "disable", "--no-sync", "legacy"], project, codex_home)
    exit_code, stdout, stderr = run_cli(["skill", "list"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert stdout == (
        "disabled legacy (missing)\n"
        "available lint\n"
        "enabled review\n"
    )


def test_skill_list_outputs_nothing_when_no_skills_are_known(workspace, run_cli):
    """skill list succeeds with empty output when no skill names are known."""
    project, codex_home = workspace

    exit_code, stdout, stderr = run_cli(["skill", "list"], project, codex_home)

    assert exit_code == 0
    assert stdout == ""
    assert stderr == ""


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
