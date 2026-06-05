"""CLI tests for AGENTS.md snippet utility commands."""


def test_agentsmd_show_renders_named_template_without_project_changes(
    workspace,
    write_home_template,
    run_cli,
):
    """agentsmd show prints rendered markdown for a named snippet."""
    project, codex_home = workspace
    write_home_template(
        codex_home,
        "coding",
        '''
[rules]
text = "rendered"
''',
    )

    exit_code, stdout, stderr = run_cli(["agentsmd", "show", "coding"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "# rules\nrendered\n"
    assert not (project / ".codex" / "codexmgr.toml").exists()


def test_agentsmd_validate_accepts_renderable_path_template(workspace, run_cli):
    """agentsmd validate accepts a valid path-backed snippet."""
    project, codex_home = workspace
    source = project / "custom.toml"
    source.write_text(
        '''
[rules]
text = "valid"
''',
        encoding="utf-8",
    )

    exit_code, stdout, stderr = run_cli(
        ["agentsmd", "validate", str(source)],
        project,
        codex_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "Valid custom\n"


def test_agentsmd_validate_rejects_unrenderable_template(workspace, run_cli):
    """agentsmd validate fails when a snippet cannot render."""
    project, codex_home = workspace
    source = project / "broken.toml"
    source.write_text('rules = "not a table"\n', encoding="utf-8")

    exit_code, stdout, stderr = run_cli(
        ["agentsmd", "validate", str(source)],
        project,
        codex_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "Template section must be a table: rules" in stderr


def test_init_template_agentsmd_creates_starter_template(workspace, run_cli):
    """init-template agentsmd creates a starter snippet in CODEXMGR_HOME."""
    project, codex_home = workspace

    exit_code, stdout, stderr = run_cli(
        ["init-template", "agentsmd", "coding"],
        project,
        codex_home,
    )

    template = codex_home / "agentsmd" / "coding.toml"
    assert exit_code == 0
    assert stderr == ""
    assert stdout == f"Created {template}\n"
    assert "[instructions]" in template.read_text(encoding="utf-8")
    assert "text =" in template.read_text(encoding="utf-8")


def test_init_template_agentsmd_refuses_to_overwrite_existing_template(
    workspace,
    write_home_template,
    run_cli,
):
    """init-template agentsmd fails loudly when the snippet already exists."""
    project, codex_home = workspace
    existing = write_home_template(
        codex_home,
        "coding",
        '''
[rules]
text = "existing"
''',
    )

    exit_code, stdout, stderr = run_cli(
        ["init-template", "agentsmd", "coding"],
        project,
        codex_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert f"Template already exists: {existing}" in stderr
    assert "existing" in existing.read_text(encoding="utf-8")
