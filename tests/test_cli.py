"""CLI behavior tests for project Codex configuration management."""

BEGIN = "<!-- BEGIN CODEXMGR GENERATED -->"
END = "<!-- END CODEXMGR GENERATED -->"


def test_setup_creates_project_codex_directory(workspace, run_cli):
    """setup creates a project .codex directory."""
    project, codex_home = workspace

    exit_code, stdout, stderr = run_cli(["setup"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert "Created" in stdout
    assert (project / ".codex").is_dir()


def test_add_named_template_updates_config_without_applying(
    workspace, write_home_template, run_cli, read_project_config
):
    """agentsmd add stores a named source without creating lock or AGENTS.md."""
    project, codex_home = workspace
    write_home_template(
        codex_home,
        "coding",
        '''
[basics]
text = "foo"
''',
    )

    run_cli(["setup"], project, codex_home)
    exit_code, _, stderr = run_cli(["agentsmd", "add", "coding"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert read_project_config(project)["agents_md"]["src"] == ["coding"]
    assert not (project / ".codex" / "agents-predef.toml").exists()
    assert not (project / ".codex" / "codexmgr.lock").exists()
    assert not (project / "AGENTS.md").exists()


def test_add_full_path_updates_config_with_path_source(workspace, run_cli, read_project_config):
    """agentsmd add stores explicit path sources in codexmgr.toml."""
    project, codex_home = workspace
    source = project / "custom.toml"
    source.write_text(
        '''
[rules]
text = "from path"
''',
        encoding="utf-8",
    )

    run_cli(["setup"], project, codex_home)
    exit_code, _, stderr = run_cli(["agentsmd", "add", str(source)], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert read_project_config(project)["agents_md"]["src"] == [str(source)]
    assert not (project / ".codex" / "codexmgr.lock").exists()
    assert not (project / "AGENTS.md").exists()


def test_add_does_not_duplicate_existing_source(
    workspace, write_home_template, run_cli, read_project_config
):
    """Adding the same source twice keeps one config entry."""
    project, codex_home = workspace
    write_home_template(
        codex_home,
        "coding",
        '''
[basics]
text = "foo"
''',
    )

    run_cli(["setup"], project, codex_home)
    run_cli(["agentsmd", "add", "coding"], project, codex_home)
    exit_code, _, stderr = run_cli(["agentsmd", "add", "coding"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert read_project_config(project)["agents_md"]["src"] == ["coding"]


def test_add_named_template_uses_codex_home_environment(
    workspace,
    monkeypatch,
    write_home_template,
    run_cli,
    run_cli_with_environment,
    read_project_config,
):
    """Named add uses CODEX_HOME when Codex home is not injected."""
    project, codex_home = workspace
    env_codex_home = codex_home / "custom-codex"
    write_home_template(
        env_codex_home,
        "coding",
        '''
[rules]
text = "from env"
''',
    )

    run_cli(["setup"], project, codex_home)
    monkeypatch.setenv("CODEX_HOME", str(env_codex_home))
    exit_code, _, stderr = run_cli_with_environment(["agentsmd", "add", "coding"], project)

    assert exit_code == 0
    assert stderr == ""
    assert read_project_config(project)["agents_md"]["src"] == ["coding"]


def test_remove_deletes_source_from_config_without_applying(
    workspace,
    write_home_template,
    run_cli,
    read_project_config,
):
    """agentsmd remove updates source config but does not refresh outputs."""
    project, codex_home = workspace
    write_home_template(
        codex_home,
        "coding",
        '''
[basics]
text = "coding"
''',
    )
    write_home_template(
        codex_home,
        "review",
        '''
[review]
text = "review"
''',
    )

    run_cli(["setup"], project, codex_home)
    run_cli(["agentsmd", "add", "coding"], project, codex_home)
    run_cli(["agentsmd", "add", "review"], project, codex_home)
    exit_code, _, stderr = run_cli(["agentsmd", "remove", "coding"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert read_project_config(project)["agents_md"]["src"] == ["review"]
    assert not (project / ".codex" / "codexmgr.lock").exists()
    assert not (project / "AGENTS.md").exists()


def test_apply_resolves_config_sources_writes_lock_and_agents_md(
    workspace,
    write_home_template,
    run_cli,
    read_lock,
    assert_agents_md,
):
    """apply expands configured sources into lock data and generated markdown."""
    project, codex_home = workspace
    write_home_template(
        codex_home,
        "coding",
        '''
[basics.debugging]
text = "abc"

[basics]
text = "foo"
''',
    )
    source = project / "custom.toml"
    source.write_text(
        '''
[rules]
text = """
- keep files small
- write tests first
"""
''',
        encoding="utf-8",
    )

    run_cli(["setup"], project, codex_home)
    run_cli(["agentsmd", "add", "coding"], project, codex_home)
    run_cli(["agentsmd", "add", str(source)], project, codex_home)
    exit_code, stdout, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert "Applied" in stdout
    lock = read_lock(project)
    assert lock["agents_md"]["coding"]["basics"]["text"] == "foo"
    assert lock["agents_md"]["coding"]["basics"]["debugging"]["text"] == "abc"
    assert lock["agents_md"]["custom"]["rules"]["text"].strip() == (
        "- keep files small\n- write tests first"
    )
    assert not (project / ".codex" / "agents-predef.toml").exists()
    assert_agents_md(
        project,
        "# basics\nfoo\n\n## debugging\nabc\n\n# rules\n"
        "- keep files small\n- write tests first\n",
    )


def test_apply_preserves_manual_agents_md_content(workspace, write_home_template, run_cli):
    """apply preserves manual project AGENTS.md content outside the managed block."""
    project, codex_home = workspace
    write_home_template(
        codex_home,
        "coding",
        '''
[generated]
text = "new"
''',
    )

    run_cli(["setup"], project, codex_home)
    (project / "AGENTS.md").write_text("# Manual\nkeep\n", encoding="utf-8")
    run_cli(["agentsmd", "add", "coding"], project, codex_home)
    exit_code, _, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert (project / "AGENTS.md").read_text(encoding="utf-8") == (
        f"# Manual\nkeep\n\n{BEGIN}\n# generated\nnew\n{END}\n"
    )


def test_apply_after_remove_uses_current_config_sources(
    workspace,
    write_home_template,
    run_cli,
    read_lock,
    assert_agents_md,
):
    """apply reflects the current agents_md.src list after source removal."""
    project, codex_home = workspace
    write_home_template(
        codex_home,
        "coding",
        '''
[basics]
text = "coding"
''',
    )
    write_home_template(
        codex_home,
        "review",
        '''
[review]
text = "review"
''',
    )

    run_cli(["setup"], project, codex_home)
    run_cli(["agentsmd", "add", "coding"], project, codex_home)
    run_cli(["agentsmd", "add", "review"], project, codex_home)
    run_cli(["agentsmd", "remove", "coding"], project, codex_home)
    exit_code, _, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert read_lock(project)["agents_md"].keys() == {"review"}
    assert_agents_md(project, "# review\nreview\n")


def test_apply_missing_config_fails_without_creating_outputs(workspace, run_cli):
    """apply requires .codex/codexmgr.toml."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)

    exit_code, _, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 1
    assert "Project codexmgr.toml not found" in stderr
    assert not (project / ".codex" / "codexmgr.lock").exists()
    assert not (project / "AGENTS.md").exists()


def test_add_missing_template_fails_without_creating_config(workspace, run_cli):
    """agentsmd add validates source existence before writing config."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)

    exit_code, _, stderr = run_cli(["agentsmd", "add", "missing"], project, codex_home)

    assert exit_code == 1
    assert "Template not found" in stderr
    assert not (project / ".codex" / "codexmgr.toml").exists()
