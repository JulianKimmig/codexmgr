"""Behavioral tests for portable generated skill selectors and copy locks."""

from pathlib import Path


def test_project_skill_uses_declared_name_selector(
    workspace,
    run_cli,
    read_codex_config,
    read_lock,
):
    """A named project skill produces a repository-portable name selector."""
    project, codex_home = workspace
    _write_skill(project / ".agents" / "skills", "review", "code-review")
    run_cli(["setup"], project, codex_home)

    exit_code, _, stderr = run_cli(
        ["skill", "enable", "review"],
        project,
        codex_home,
    )

    expected = [{"name": "code-review", "enabled": True}]
    assert exit_code == 0
    assert stderr == ""
    assert read_codex_config(project)["skills"]["config"] == expected
    assert read_lock(project)["skills"]["config"] == expected


def test_named_skill_fails_when_project_and_codex_home_both_match(
    workspace,
    run_cli,
    read_codex_config,
):
    """A bare name cannot silently choose between project and home sources."""
    project, codex_home = workspace
    project_file = _write_skill(project / ".agents" / "skills", "review", "review")
    home_file = _write_skill(codex_home / "skills", "review", "review")
    run_cli(["setup"], project, codex_home)
    run_cli(["skill", "enable", "--no-sync", "review"], project, codex_home)

    exit_code, stdout, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert "Ambiguous skill reference: review" in stderr
    assert f"project: {project_file.resolve()}" in stderr
    assert f"codex_home: {home_file.resolve()}" in stderr
    assert "Configure an explicit path to select one." in stderr
    assert read_codex_config(project) == {}
    assert not (project / ".codex" / "codexmgr.lock").exists()


def test_name_selector_fails_for_duplicate_declared_skill_names(
    workspace,
    run_cli,
    read_codex_config,
):
    """Different folders cannot make a generated name selector ambiguous."""
    project, codex_home = workspace
    project_file = _write_skill(
        project / ".agents" / "skills",
        "project-review",
        "shared-review",
    )
    home_file = _write_skill(
        codex_home / "skills",
        "home-review",
        "shared-review",
    )
    run_cli(["setup"], project, codex_home)
    run_cli(
        ["skill", "enable", "--no-sync", "project-review"],
        project,
        codex_home,
    )

    exit_code, stdout, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert "Ambiguous declared skill name: shared-review" in stderr
    assert str(project_file.resolve()) in stderr
    assert str(home_file.resolve()) in stderr
    assert "Configure an explicit path to select one." in stderr
    assert read_codex_config(project) == {}


def test_named_project_skill_requires_valid_frontmatter(
    workspace,
    run_cli,
    read_codex_config,
):
    """Invalid selected metadata fails before generated files are changed."""
    project, codex_home = workspace
    skill_file = project / ".agents" / "skills" / "review" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text("# Missing frontmatter\n", encoding="utf-8")
    run_cli(["setup"], project, codex_home)
    run_cli(["skill", "enable", "--no-sync", "review"], project, codex_home)

    exit_code, stdout, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert f"Invalid skill metadata in {skill_file.resolve()}" in stderr
    assert "missing YAML frontmatter" in stderr
    assert read_codex_config(project) == {}
    assert not (project / ".codex" / "codexmgr.lock").exists()


def test_missing_explicit_skill_path_fails_instead_of_becoming_a_name(
    workspace,
    run_cli,
    read_codex_config,
):
    """An explicit missing path is an error rather than a name fallback."""
    project, codex_home = workspace
    missing = project / "skills" / "missing"
    run_cli(["setup"], project, codex_home)
    run_cli(
        ["skill", "enable", "--no-sync", str(missing)],
        project,
        codex_home,
    )

    exit_code, stdout, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 1
    assert stdout == ""
    assert stderr == f"Skill path not found: {missing}\n"
    assert read_codex_config(project) == {}
    assert not (project / ".codex" / "codexmgr.lock").exists()


def test_codexmgr_home_copy_uses_portable_selector_and_lock(
    workspace,
    run_cli_with_homes,
    read_codex_config,
    read_lock,
):
    """Managed home copies avoid machine-specific generated paths."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_skill(codexmgr_home / "skills", "review", "code-review")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, _, stderr = run_cli_with_homes(
        ["skill", "enable", "review"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert read_codex_config(project)["skills"]["config"] == [
        {"name": "code-review", "enabled": True},
    ]
    assert read_lock(project)["skills"]["copies"] == [
        {
            "name": "review",
            "source": "codexmgr_home",
            "target": ".agents/skills/review",
        },
    ]


def test_apply_migrates_legacy_absolute_copy_lock(
    workspace,
    run_cli_with_homes,
    read_lock,
):
    """Apply reads legacy absolute copy paths and writes the portable shape."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    source_file = _write_skill(codexmgr_home / "skills", "review", "review")
    target_file = _write_skill(project / ".agents" / "skills", "review", "review")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    (project / ".codex" / "codexmgr.toml").write_text(
        '[skills]\nenabled = ["review"]\n',
        encoding="utf-8",
    )
    (project / ".codex" / "codexmgr.lock").write_text(
        "[skills]\n"
        "[[skills.copies]]\n"
        'name = "review"\n'
        f'source = "{source_file.parent.resolve()}"\n'
        f'target = "{target_file.parent.resolve()}"\n',
        encoding="utf-8",
    )

    exit_code, _, stderr = run_cli_with_homes(
        ["apply"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert read_lock(project)["skills"]["copies"] == [
        {
            "name": "review",
            "source": "codexmgr_home",
            "target": ".agents/skills/review",
        },
    ]


def test_portable_skill_outputs_match_after_project_root_changes(
    workspace,
    run_cli_with_homes,
):
    """Clones at different roots generate identical config and lock files."""
    first_project, codex_home = workspace
    second_project = first_project.parent / "moved-project"
    second_project.mkdir()
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_skill(codexmgr_home / "skills", "review", "review")

    for project in [first_project, second_project]:
        run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
        exit_code, _, stderr = run_cli_with_homes(
            ["skill", "enable", "review"],
            project,
            codex_home,
            codexmgr_home,
        )
        assert exit_code == 0
        assert stderr == ""

    assert _read_generated(first_project, "config.toml") == _read_generated(
        second_project,
        "config.toml",
    )
    assert _read_generated(first_project, "codexmgr.lock") == _read_generated(
        second_project,
        "codexmgr.lock",
    )


def _write_skill(root: Path, folder: str, declared_name: str) -> Path:
    """Create one valid skill and return its instruction-file path.

    Args:
        root: Skill-store root directory.
        folder: Skill folder name below the root.
        declared_name: Skill name declared in YAML frontmatter.

    Returns:
        Path to the created ``SKILL.md`` file.
    """
    skill_file = root / folder / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(
        f"---\nname: {declared_name}\ndescription: Test skill.\n---\n\n# Skill\n",
        encoding="utf-8",
    )
    return skill_file


def _read_generated(project: Path, name: str) -> str:
    """Read one generated project Codex file.

    Args:
        project: Project root directory.
        name: File name below the project ``.codex`` directory.

    Returns:
        UTF-8 file content.
    """
    return (project / ".codex" / name).read_text(encoding="utf-8")
