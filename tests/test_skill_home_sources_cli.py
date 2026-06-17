"""CLI tests for skill discovery across Codex and codexmgr homes."""


def test_skill_list_includes_codexmgr_home_skills(workspace, run_cli_with_homes):
    """skill list reports skills installed under CODEXMGR_HOME."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_skill(codexmgr_home, "review")

    exit_code, stdout, stderr = run_cli_with_homes(
        ["skill", "list"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "available review\n"


def test_skill_list_fails_for_duplicate_home_skill_names(
    workspace,
    run_cli_with_homes,
):
    """A named skill cannot exist in both home directories."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_skill(codex_home, "review")
    _write_skill(codexmgr_home, "review")

    exit_code, stdout, stderr = run_cli_with_homes(
        ["skill", "list"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "Skill exists in both CODEXMGR_HOME and CODEX_HOME: review" in stderr


def _write_skill(home, name):
    """Create a named skill directory with a SKILL.md file.

    Args:
        home: Home directory whose skills folder should receive the skill.
        name: Skill directory name to create.

    Returns:
        Path to the created SKILL.md file.
    """
    skill_dir = home / "skills" / name
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# Skill\n", encoding="utf-8")
    return skill_file
