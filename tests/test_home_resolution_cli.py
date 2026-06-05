"""CLI tests for resolving Codex and codexmgr home directories separately."""


def test_named_agentsmd_uses_codexmgr_home_environment(
    workspace,
    monkeypatch,
    write_home_template,
    run_cli,
    run_cli_with_environment,
    read_lock,
    assert_agents_md,
):
    """Named AGENTS.md templates resolve from CODEXMGR_HOME, not CODEX_HOME."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    write_home_template(
        codexmgr_home,
        "coding",
        '''
[rules]
text = "from codexmgr home"
''',
    )

    run_cli(["setup"], project, codex_home)
    monkeypatch.setenv("CODEX_HOME", str(codex_home))
    monkeypatch.setenv("CODEXMGR_HOME", str(codexmgr_home))
    exit_code, _, stderr = run_cli_with_environment(["agentsmd", "add", "coding"], project)

    assert exit_code == 0
    assert stderr == ""
    assert read_lock(project)["agents_md"]["coding"]["rules"]["text"] == (
        "from codexmgr home"
    )
    assert_agents_md(project, "# rules\nfrom codexmgr home\n")


def test_apply_uses_codexmgr_home_for_agentsmd_and_codex_home_for_skills(
    workspace,
    write_home_template,
    run_cli_with_homes,
    read_lock,
    read_codex_config,
):
    """apply resolves named templates and named skills from their separate homes."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    skill_file = _write_skill(codex_home, "review")
    write_home_template(
        codexmgr_home,
        "coding",
        '''
[rules]
text = "from codexmgr home"
''',
    )

    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(
        ["agentsmd", "add", "--no-sync", "coding"],
        project,
        codex_home,
        codexmgr_home,
    )
    run_cli_with_homes(
        ["skill", "enable", "--no-sync", "review"],
        project,
        codex_home,
        codexmgr_home,
    )
    exit_code, _, stderr = run_cli_with_homes(
        ["apply"], project, codex_home, codexmgr_home
    )

    assert exit_code == 0
    assert stderr == ""
    assert read_lock(project)["agents_md"]["coding"]["rules"]["text"] == (
        "from codexmgr home"
    )
    assert read_codex_config(project)["skills"]["config"] == [
        {"path": str(skill_file.resolve()), "enabled": True},
    ]


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
