"""CLI and generated-state tests for reusable rule files."""

from pathlib import Path


def test_rules_list_marks_nested_available_enabled_disabled_and_missing(
    workspace,
    run_cli_with_homes,
):
    """rules list reports nested source files and configured state."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_rule(codexmgr_home, "react/components.md", "# Components\n")
    _write_rule(codexmgr_home, "react/materials/colors.md", "# Colors\n")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    (project / ".codex" / "codexmgr.toml").write_text(
        '[rules]\nenabled = ["react/", "missing.md"]\ndisabled = ["react/materials/", "legacy.md"]\n',
        encoding="utf-8",
    )

    exit_code, stdout, stderr = run_cli_with_homes(
        ["rules", "list"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == (
        "disabled legacy.md (missing)\n"
        "enabled missing.md (missing)\n"
        "enabled react/\n"
        "available react/components.md\n"
        "disabled react/materials/\n"
        "available react/materials/colors.md\n"
    )


def test_rules_enable_folder_recursively_copies_and_locks_files(
    workspace,
    run_cli_with_homes,
    read_project_config,
    read_lock,
):
    """rules enable copies every regular file from a source folder."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_rule(codexmgr_home, "react/components.md", "# Components\n")
    _write_rule(codexmgr_home, "react/materials/colors.md", "# Colors\n")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["rules", "enable", "react/"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "Enabled react/\nApplied project Codex configuration\n"
    assert read_project_config(project)["rules"] == {
        "enabled": ["react/"],
        "disabled": [],
    }
    assert (project / ".rules" / "react" / "components.md").read_text() == "# Components\n"
    assert (project / ".rules" / "react" / "materials" / "colors.md").read_text() == "# Colors\n"
    assert read_lock(project)["rules"]["copies"] == [
        {
            "relative_path": "react/components.md",
            "source": str((codexmgr_home / "rules" / "react" / "components.md").resolve()),
            "target": str((project / ".rules" / "react" / "components.md").resolve()),
        },
        {
            "relative_path": "react/materials/colors.md",
            "source": str((codexmgr_home / "rules" / "react" / "materials" / "colors.md").resolve()),
            "target": str((project / ".rules" / "react" / "materials" / "colors.md").resolve()),
        },
    ]


def test_rules_enable_extensionless_file_prefers_markdown(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """Extensionless file refs canonicalize to an existing .md source."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_rule(codexmgr_home, "python/testing.md", "# Testing\n")
    _write_rule(codexmgr_home, "python/testing", "exact\n")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["rules", "enable", "python/testing"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout.startswith("Enabled python/testing.md\n")
    assert read_project_config(project)["rules"]["enabled"] == ["python/testing.md"]
    assert (project / ".rules" / "python" / "testing.md").read_text() == "# Testing\n"


def test_rules_disable_nested_subfolder_and_single_file_win_after_parent_enable(
    workspace,
    run_cli_with_homes,
):
    """Disabled file and folder refs remove candidates after enabled expansion."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_rule(codexmgr_home, "react/components.md", "# Components\n")
    _write_rule(codexmgr_home, "react/materials/colors.md", "# Colors\n")
    _write_rule(codexmgr_home, "react/materials/spacing.md", "# Spacing\n")
    _write_rule(codexmgr_home, "react/legacy.md", "# Legacy\n")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(["rules", "enable", "react/"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["rules", "disable", "react/materials/", "react/legacy.md"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert "Disabled react/materials/" in stdout
    assert "Disabled react/legacy.md" in stdout
    assert (project / ".rules" / "react" / "components.md").is_file()
    assert not (project / ".rules" / "react" / "materials").exists()
    assert not (project / ".rules" / "react" / "legacy.md").exists()


def test_rules_enable_rejects_invalid_refs(workspace, run_cli_with_homes):
    """Invalid rule refs fail before config mutation."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    for ref in ["", "/abs.md", "../up.md", "react\\bad.md"]:
        exit_code, stdout, stderr = run_cli_with_homes(
            ["rules", "enable", ref],
            project,
            codex_home,
            codexmgr_home,
        )

        assert exit_code == 1
        assert stdout == ""
        assert "Invalid rule ref" in stderr


def test_rules_enable_rejects_unmanaged_target_overwrite(
    workspace,
    run_cli_with_homes,
):
    """First-time managed rule copies do not overwrite unmanaged .rules files."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_rule(codexmgr_home, "react/components.md", "# Components\n")
    target = project / ".rules" / "react" / "components.md"
    target.parent.mkdir(parents=True)
    target.write_text("# Local\n", encoding="utf-8")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["rules", "enable", "react/"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "Refusing to overwrite unmanaged rule file:" in stderr
    assert target.read_text(encoding="utf-8") == "# Local\n"


def test_rules_enable_accepts_multiple_refs_and_no_sync(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """rules enable supports multiple refs and skipping automatic apply."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_rule(codexmgr_home, "react/components.md", "# Components\n")
    _write_rule(codexmgr_home, "python/testing.md", "# Testing\n")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["rules", "enable", "--no-sync", "react/", "python/testing"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "Enabled react/\nEnabled python/testing.md\n"
    assert read_project_config(project)["rules"] == {
        "enabled": ["react/", "python/testing.md"],
        "disabled": [],
    }
    assert not (project / ".rules").exists()


def test_apply_check_and_diff_report_stale_rule_copies(
    workspace,
    run_cli_with_homes,
):
    """apply --check and --diff include managed .rules copy drift."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_rule(codexmgr_home, "react/components.md", "# Components\n")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(["rules", "enable", "react/"], project, codex_home, codexmgr_home)
    target = project / ".rules" / "react" / "components.md"
    target.write_text("# Local\n", encoding="utf-8")

    check_code, check_stdout, check_stderr = run_cli_with_homes(
        ["apply", "--check"],
        project,
        codex_home,
        codexmgr_home,
    )
    diff_code, diff_stdout, diff_stderr = run_cli_with_homes(
        ["apply", "--diff"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert check_code == 1
    assert check_stderr == ""
    assert "Out of sync: .rules/react/components.md" in check_stdout
    assert diff_code == 1
    assert diff_stderr == ""
    assert "--- .rules/react/components.md (current)" in diff_stdout
    assert "+++ .rules/react/components.md (expected)" in diff_stdout
    assert "-# Local" in diff_stdout
    assert "+# Components" in diff_stdout


def _write_rule(codexmgr_home: Path, relative_path: str, content: str) -> Path:
    """Create one reusable rule source file.

    Args:
        codexmgr_home: Codexmgr home directory.
        relative_path: POSIX path below the rules source root.
        content: File content to write.

    Returns:
        Path to the created rule file.
    """
    path = codexmgr_home / "rules" / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
