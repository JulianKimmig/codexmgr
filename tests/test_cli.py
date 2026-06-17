"""CLI behavior tests for project Codex configuration management."""

BEGIN = "<!-- BEGIN CODEXMGR GENERATED -->"
END = "<!-- END CODEXMGR GENERATED -->"


def test_setup_creates_project_config_and_applies_empty_codex_config(
    workspace,
    run_cli,
    read_project_config,
    read_codex_config,
):
    """setup creates source and generated config files for an empty project."""
    project, codex_home = workspace

    exit_code, stdout, stderr = run_cli(["setup"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert "Created" in stdout
    assert "Applied project Codex configuration" in stdout
    assert (project / ".codex").is_dir()
    assert (project / ".codex" / "codexmgr.toml").is_file()
    assert (project / ".codex" / "config.toml").is_file()
    assert read_project_config(project) == {}
    assert read_codex_config(project) == {}


def test_setup_preserves_existing_project_config_and_applies(
    workspace,
    write_home_template,
    run_cli,
    read_project_config,
    read_lock,
    assert_agents_md,
):
    """setup keeps an existing codexmgr.toml and refreshes generated outputs."""
    project, codex_home = workspace
    write_home_template(
        codex_home,
        "coding",
        '''
[rules]
text = "from existing config"
''',
    )
    (project / ".codex").mkdir()
    (project / ".codex" / "codexmgr.toml").write_text(
        '''
[agents_md]
src = ["coding"]
''',
        encoding="utf-8",
    )

    exit_code, _, stderr = run_cli(["setup"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert read_project_config(project)["agents_md"]["src"] == ["coding"]
    assert read_lock(project)["agents_md"]["coding"]["rules"]["text"] == (
        "from existing config"
    )
    assert_agents_md(project, "# rules\nfrom existing config\n")


def test_add_named_template_updates_config_and_applies(
    workspace, write_home_template, run_cli, read_project_config, read_lock, assert_agents_md
):
    """agentsmd add stores a named source and refreshes generated outputs."""
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
    assert read_lock(project)["agents_md"]["coding"]["basics"]["text"] == "foo"
    assert not (project / ".codex" / "agents-predef.toml").exists()
    assert_agents_md(project, "# basics\nfoo\n")


def test_add_full_path_updates_config_with_path_source(
    workspace, run_cli, read_project_config, read_lock, assert_agents_md
):
    """agentsmd add stores explicit path sources and applies them."""
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
    assert read_lock(project)["agents_md"]["custom"]["rules"]["text"] == "from path"
    assert_agents_md(project, "# rules\nfrom path\n")


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


def test_add_named_template_uses_codexmgr_home_environment(
    workspace,
    monkeypatch,
    write_home_template,
    run_cli,
    run_cli_with_environment,
    read_project_config,
):
    """Named add uses CODEXMGR_HOME when codexmgr home is not injected."""
    project, codex_home = workspace
    env_codexmgr_home = codex_home / "custom-codexmgr"
    write_home_template(
        env_codexmgr_home,
        "coding",
        '''
[rules]
text = "from env"
''',
    )

    run_cli(["setup"], project, codex_home)
    monkeypatch.setenv("CODEXMGR_HOME", str(env_codexmgr_home))
    exit_code, _, stderr = run_cli_with_environment(["agentsmd", "add", "coding"], project)

    assert exit_code == 0
    assert stderr == ""
    assert read_project_config(project)["agents_md"]["src"] == ["coding"]


def test_remove_deletes_source_from_config_and_applies(
    workspace,
    write_home_template,
    run_cli,
    read_project_config,
    read_lock,
    assert_agents_md,
):
    """agentsmd remove updates source config and refreshes generated outputs."""
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
    assert read_lock(project)["agents_md"].keys() == {"review"}
    assert_agents_md(project, "# review\nreview\n")


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


def test_apply_empty_project_config_writes_empty_codex_config(
    workspace,
    run_cli,
    read_codex_config,
):
    """apply writes an empty local Codex config for empty codexmgr.toml."""
    project, codex_home = workspace
    (project / ".codex").mkdir()
    (project / ".codex" / "codexmgr.toml").write_text("", encoding="utf-8")

    exit_code, stdout, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert "Applied" in stdout
    assert read_codex_config(project) == {}
    assert not (project / ".codex" / "codexmgr.lock").exists()
    assert not (project / "AGENTS.md").exists()


def test_apply_missing_config_fails_without_creating_outputs(workspace, run_cli):
    """apply requires .codex/codexmgr.toml."""
    project, codex_home = workspace
    (project / ".codex").mkdir()

    exit_code, _, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 1
    assert "Project codexmgr.toml not found" in stderr
    assert not (project / ".codex" / "codexmgr.lock").exists()
    assert not (project / "AGENTS.md").exists()


def test_add_missing_template_fails_without_mutating_config(
    workspace,
    run_cli,
    read_project_config,
    read_codex_config,
):
    """agentsmd add validates source existence before mutating config."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)

    exit_code, _, stderr = run_cli(["agentsmd", "add", "missing"], project, codex_home)

    assert exit_code == 1
    assert "Template not found" in stderr
    assert read_project_config(project) == {}
    assert read_codex_config(project) == {}
