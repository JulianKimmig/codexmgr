"""CLI tests for project-local managed skill copies."""


def test_apply_copies_enabled_codexmgr_home_skill(
    workspace,
    run_cli_with_homes,
    read_codex_config,
    read_lock,
):
    """Enabled CODEXMGR_HOME skills are copied into .agents/skills."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    source_file = _write_skill(codexmgr_home, "review", "# Review\n")
    source_dir = source_file.parent
    target_dir = project / ".agents" / "skills" / "review"
    target_file = target_dir / "SKILL.md"

    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    exit_code, stdout, stderr = run_cli_with_homes(
        ["skill", "enable", "review"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert "Enabled review" in stdout
    assert target_file.read_text(encoding="utf-8") == "# Review\n"
    expected_entries = [{"path": str(target_file.resolve()), "enabled": True}]
    assert read_codex_config(project)["skills"]["config"] == expected_entries
    assert read_lock(project)["skills"]["config"] == expected_entries
    assert read_lock(project)["skills"]["copies"] == [
        {
            "name": "review",
            "source": str(source_dir.resolve()),
            "target": str(target_dir.resolve()),
        },
    ]


def test_apply_overlay_copy_overwrites_source_files_and_keeps_extra_files(
    workspace,
    run_cli_with_homes,
):
    """Repeated apply refreshes source files without deleting extra local files."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    source_file = _write_skill(codexmgr_home, "review", "# Review v1\n")
    source_nested = source_file.parent / "notes" / "guide.md"
    source_nested.parent.mkdir()
    source_nested.write_text("source v1\n", encoding="utf-8")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(["skill", "enable", "review"], project, codex_home, codexmgr_home)

    target_dir = project / ".agents" / "skills" / "review"
    target_file = target_dir / "SKILL.md"
    target_file.write_text("local edit\n", encoding="utf-8")
    extra_file = target_dir / "local-only.md"
    extra_file.write_text("keep me\n", encoding="utf-8")
    source_file.write_text("# Review v2\n", encoding="utf-8")
    source_nested.write_text("source v2\n", encoding="utf-8")
    exit_code, _, stderr = run_cli_with_homes(
        ["apply"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert target_file.read_text(encoding="utf-8") == "# Review v2\n"
    assert (target_dir / "notes" / "guide.md").read_text(encoding="utf-8") == (
        "source v2\n"
    )
    assert extra_file.read_text(encoding="utf-8") == "keep me\n"


def test_disabling_codexmgr_home_skill_removes_managed_copy(
    workspace,
    run_cli_with_homes,
    read_codex_config,
    read_lock,
):
    """Disabled CODEXMGR_HOME skills remove previously managed local copies."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_skill(codexmgr_home, "review", "# Review\n")
    target_dir = project / ".agents" / "skills" / "review"
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(["skill", "enable", "review"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["skill", "disable", "review"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert "Disabled review" in stdout
    assert not target_dir.exists()
    expected_entries = [{"name": "review", "enabled": False}]
    assert read_codex_config(project)["skills"]["config"] == expected_entries
    assert read_lock(project)["skills"] == {"config": expected_entries}


def test_disabling_local_only_agents_skill_keeps_folder_and_disables_path(
    workspace,
    run_cli_with_homes,
    read_codex_config,
):
    """A local-only .agents skill is disabled via config without removal."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    local_file = project / ".agents" / "skills" / "review" / "SKILL.md"
    local_file.parent.mkdir(parents=True)
    local_file.write_text("# Local review\n", encoding="utf-8")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["skill", "disable", "review"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert "Disabled review" in stdout
    assert local_file.is_file()
    assert read_codex_config(project)["skills"]["config"] == [
        {"path": str(local_file.resolve()), "enabled": False},
    ]


def test_enabling_codexmgr_home_skill_fails_when_target_is_unmanaged(
    workspace,
    run_cli_with_homes,
):
    """Existing untracked .agents skill folders are not overwritten."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_skill(codexmgr_home, "review", "# Review\n")
    local_file = project / ".agents" / "skills" / "review" / "SKILL.md"
    local_file.parent.mkdir(parents=True)
    local_file.write_text("# Local review\n", encoding="utf-8")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["skill", "enable", "review"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "Refusing to overwrite unmanaged skill copy:" in stderr
    assert local_file.read_text(encoding="utf-8") == "# Local review\n"


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
