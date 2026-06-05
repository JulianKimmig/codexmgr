"""CLI tests for listing available AGENTS.md snippets."""


def test_agentsmd_list_outputs_sorted_named_templates(
    workspace,
    write_home_template,
    run_cli,
):
    """agentsmd list prints available codexmgr home snippets in sorted order."""
    project, codex_home = workspace
    write_home_template(
        codex_home,
        "review",
        '''
[rules]
text = "review"
''',
    )
    write_home_template(
        codex_home,
        "coding",
        '''
[rules]
text = "coding"
''',
    )
    agentsmd_dir = codex_home / "agentsmd"
    (agentsmd_dir / "README.md").write_text("# ignored\n", encoding="utf-8")
    (agentsmd_dir / "nested").mkdir()
    (agentsmd_dir / "nested" / "other.toml").write_text(
        "[rules]\ntext = 'ignored'\n",
        encoding="utf-8",
    )

    exit_code, stdout, stderr = run_cli(["agentsmd", "list"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "coding\nreview\n"


def test_agentsmd_list_uses_codexmgr_home(
    workspace,
    write_home_template,
    run_cli_with_homes,
):
    """agentsmd list resolves snippets from CODEXMGR_HOME, not CODEX_HOME."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    write_home_template(
        codex_home,
        "wrong-home",
        '''
[rules]
text = "wrong"
''',
    )
    write_home_template(
        codexmgr_home,
        "right-home",
        '''
[rules]
text = "right"
''',
    )

    exit_code, stdout, stderr = run_cli_with_homes(
        ["agentsmd", "list"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "right-home\n"


def test_agentsmd_list_outputs_nothing_when_no_snippets_exist(workspace, run_cli):
    """agentsmd list succeeds with empty output when no snippets are installed."""
    project, codex_home = workspace

    exit_code, stdout, stderr = run_cli(["agentsmd", "list"], project, codex_home)

    assert exit_code == 0
    assert stdout == ""
    assert stderr == ""
