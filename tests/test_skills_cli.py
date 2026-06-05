"""CLI behavior tests for skill enable and disable configuration."""


def write_skill(codex_home, name):
    """Create a global skill directory with a SKILL.md file."""
    skill_dir = codex_home / "skills" / name
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# Skill\n", encoding="utf-8")
    return skill_file


def test_skill_enable_creates_enabled_entry_and_applies(
    workspace, run_cli, read_project_config, read_lock, read_codex_config
):
    """skill enable records the skill and refreshes generated outputs."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)

    exit_code, stdout, stderr = run_cli(["skill", "enable", "coding"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert "Enabled coding" in stdout
    assert read_project_config(project)["skills"] == {
        "enabled": ["coding"],
        "disabled": [],
    }
    expected_entries = [{"name": "coding", "enabled": True}]
    assert read_codex_config(project)["skills"]["config"] == expected_entries
    assert read_lock(project)["skills"]["config"] == expected_entries


def test_skill_disable_creates_disabled_entry_and_applies(
    workspace, run_cli, read_project_config, read_lock, read_codex_config
):
    """skill disable records the skill and refreshes generated outputs."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)

    exit_code, stdout, stderr = run_cli(["skill", "disable", "coding"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert "Disabled coding" in stdout
    assert read_project_config(project)["skills"] == {
        "enabled": [],
        "disabled": ["coding"],
    }
    expected_entries = [{"name": "coding", "enabled": False}]
    assert read_codex_config(project)["skills"]["config"] == expected_entries
    assert read_lock(project)["skills"]["config"] == expected_entries


def test_skill_enable_removes_skill_from_disabled(workspace, run_cli, read_project_config):
    """skill enable keeps the enabled and disabled lists mutually exclusive."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    run_cli(["skill", "disable", "coding"], project, codex_home)

    exit_code, _, stderr = run_cli(["skill", "enable", "coding"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert read_project_config(project)["skills"] == {
        "enabled": ["coding"],
        "disabled": [],
    }


def test_skill_disable_removes_skill_from_enabled(workspace, run_cli, read_project_config):
    """skill disable keeps the enabled and disabled lists mutually exclusive."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    run_cli(["skill", "enable", "coding"], project, codex_home)

    exit_code, _, stderr = run_cli(["skill", "disable", "coding"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert read_project_config(project)["skills"] == {
        "enabled": [],
        "disabled": ["coding"],
    }


def test_skill_enable_does_not_duplicate_entries(workspace, run_cli, read_project_config):
    """Repeated skill enable commands keep one entry."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)

    run_cli(["skill", "enable", "coding"], project, codex_home)
    exit_code, _, stderr = run_cli(["skill", "enable", "coding"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert read_project_config(project)["skills"]["enabled"] == ["coding"]


def test_skill_path_is_stored_as_given(workspace, run_cli, read_project_config):
    """skill commands accept path-like values and store them unchanged."""
    project, codex_home = workspace
    skill_path = str(project / "skills" / "review")
    run_cli(["setup"], project, codex_home)

    exit_code, _, stderr = run_cli(["skill", "enable", skill_path], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert read_project_config(project)["skills"]["enabled"] == [skill_path]


def test_skill_command_preserves_agents_md_config(
    workspace,
    write_home_template,
    run_cli,
    read_project_config,
):
    """skill commands update only [skills] and preserve existing config tables."""
    project, codex_home = workspace
    write_home_template(
        codex_home,
        "coding",
        '''
[rules]
text = "keep"
''',
    )
    run_cli(["setup"], project, codex_home)
    run_cli(["agentsmd", "add", "coding"], project, codex_home)

    exit_code, _, stderr = run_cli(["skill", "enable", "review"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    config = read_project_config(project)
    assert config["agents_md"]["src"] == ["coding"]
    assert config["skills"]["enabled"] == ["review"]


def test_apply_writes_enabled_and_disabled_skill_config(
    workspace,
    run_cli,
    read_lock,
    read_codex_config,
):
    """apply writes [[skills.config]] entries for enabled and disabled skills."""
    project, codex_home = workspace
    enabled_skill = write_skill(codex_home, "coding")
    disabled_skill = write_skill(codex_home, "review")
    run_cli(["setup"], project, codex_home)
    run_cli(["skill", "enable", "coding"], project, codex_home)
    run_cli(["skill", "disable", "review"], project, codex_home)

    exit_code, _, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    expected_entries = [
        {"path": str(enabled_skill.resolve()), "enabled": True},
        {"path": str(disabled_skill.resolve()), "enabled": False},
    ]
    assert read_codex_config(project)["skills"]["config"] == expected_entries
    assert read_lock(project)["skills"]["config"] == expected_entries


def test_apply_resolves_skill_directory_and_skill_file_paths(
    workspace,
    run_cli,
    read_lock,
    read_codex_config,
):
    """apply accepts configured skill paths to either directories or SKILL.md files."""
    project, codex_home = workspace
    enabled_dir = project / "skills" / "local-enabled"
    disabled_dir = project / "skills" / "local-disabled"
    enabled_dir.mkdir(parents=True)
    disabled_dir.mkdir(parents=True)
    enabled_file = enabled_dir / "SKILL.md"
    disabled_file = disabled_dir / "SKILL.md"
    enabled_file.write_text("# Enabled\n", encoding="utf-8")
    disabled_file.write_text("# Disabled\n", encoding="utf-8")
    run_cli(["setup"], project, codex_home)
    run_cli(["skill", "enable", str(enabled_dir)], project, codex_home)
    run_cli(["skill", "disable", str(disabled_file)], project, codex_home)

    exit_code, _, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    expected_entries = [
        {"path": str(enabled_file.resolve()), "enabled": True},
        {"path": str(disabled_file.resolve()), "enabled": False},
    ]
    assert read_codex_config(project)["skills"]["config"] == expected_entries
    assert read_lock(project)["skills"]["config"] == expected_entries


def test_apply_preserves_existing_codex_config_values(
    workspace,
    run_cli,
    read_codex_config,
):
    """apply replaces skill config entries without removing unrelated config."""
    project, codex_home = workspace
    skill_file = write_skill(codex_home, "coding")
    run_cli(["setup"], project, codex_home)
    (project / ".codex" / "config.toml").write_text(
        '''
model_instructions_file = "codexmgr-AGENTS.md"

[[skills.config]]
path = "/old/SKILL.md"
enabled = false
''',
        encoding="utf-8",
    )
    run_cli(["skill", "enable", "coding"], project, codex_home)

    exit_code, _, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    config = read_codex_config(project)
    assert config["model_instructions_file"] == "codexmgr-AGENTS.md"
    assert config["skills"]["config"] == [
        {"path": str(skill_file.resolve()), "enabled": True},
    ]


def test_apply_missing_named_skill_writes_name_entry(
    workspace,
    run_cli,
    read_lock,
    read_codex_config,
):
    """apply writes a name entry when a named skill cannot be resolved to a path."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    run_cli(["skill", "enable", "missing"], project, codex_home)

    exit_code, _, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    expected_entries = [{"name": "missing", "enabled": True}]
    assert read_codex_config(project)["skills"]["config"] == expected_entries
    assert read_lock(project)["skills"]["config"] == expected_entries


def test_apply_missing_path_skill_writes_name_entry(
    workspace,
    run_cli,
    read_lock,
    read_codex_config,
):
    """apply writes a name entry when a path-like skill cannot be resolved."""
    project, codex_home = workspace
    missing_path = str(project / "skills" / "missing")
    run_cli(["setup"], project, codex_home)
    run_cli(["skill", "disable", missing_path], project, codex_home)

    exit_code, _, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    expected_entries = [{"name": missing_path, "enabled": False}]
    assert read_codex_config(project)["skills"]["config"] == expected_entries
    assert read_lock(project)["skills"]["config"] == expected_entries
