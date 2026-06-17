"""CLI tests for project status and doctor checks."""

import json


def test_status_reports_configured_state_and_sync_status(
    workspace,
    write_home_template,
    run_cli_with_homes,
):
    """status prints configured snippets, skills, hooks, agents, and sync state."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    write_home_template(
        codexmgr_home,
        "coding",
        '''
[rules]
text = "current"
''',
    )
    _write_skill(codex_home, "review")
    _write_hook_bundle(codexmgr_home, "rules-hook")
    _write_agent(codexmgr_home, "rule-retriever")

    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(["agentsmd", "add", "coding"], project, codex_home, codexmgr_home)
    run_cli_with_homes(["skill", "enable", "review"], project, codex_home, codexmgr_home)
    run_cli_with_homes(
        ["hooks", "enable", "rules-hook"],
        project,
        codex_home,
        codexmgr_home,
    )
    run_cli_with_homes(
        ["agents", "enable", "rule-retriever"],
        project,
        codex_home,
        codexmgr_home,
    )
    exit_code, stdout, stderr = run_cli_with_homes(
        ["status"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert f"Project: {project}" in stdout
    assert f"CODEX_HOME: {codex_home}" in stdout
    assert f"CODEXMGR_HOME: {codexmgr_home}" in stdout
    assert "AGENTS.md snippets: coding" in stdout
    assert "Enabled skills: review" in stdout
    assert "Disabled skills: none" in stdout
    assert "Enabled hooks: rules-hook" in stdout
    assert "Disabled hooks: none" in stdout
    assert "Enabled agents: rule-retriever" in stdout
    assert "Disabled agents: none" in stdout
    assert "Generated files: in sync" in stdout


def test_status_reports_configured_rules(workspace, run_cli_with_homes):
    """status prints configured enabled and disabled rules."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_rule(codexmgr_home, "react/components.md")
    _write_rule(codexmgr_home, "react/materials/colors.md")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(["rules", "enable", "react/"], project, codex_home, codexmgr_home)
    run_cli_with_homes(
        ["rules", "disable", "react/materials/"],
        project,
        codex_home,
        codexmgr_home,
    )

    exit_code, stdout, stderr = run_cli_with_homes(
        ["status"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert "Enabled rules: react/" in stdout
    assert "Disabled rules: react/materials/" in stdout
    assert "Generated files: in sync" in stdout


def test_status_reports_out_of_sync_generated_files(
    workspace,
    write_home_template,
    run_cli,
):
    """status reports when generated files do not match codexmgr.toml."""
    project, codex_home = workspace
    write_home_template(
        codex_home,
        "coding",
        '''
[rules]
text = "pending"
''',
    )

    run_cli(["setup"], project, codex_home)
    run_cli(["agentsmd", "add", "--no-sync", "coding"], project, codex_home)
    exit_code, stdout, stderr = run_cli(["status"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert "Generated files: out of sync" in stdout
    assert ".codex/codexmgr.lock" in stdout
    assert "AGENTS.md" in stdout


def test_doctor_fails_when_project_codex_directory_is_missing(workspace, run_cli):
    """doctor reports a missing project .codex directory."""
    project, codex_home = workspace

    exit_code, stdout, stderr = run_cli(["doctor"], project, codex_home)

    assert exit_code == 1
    assert stderr == ""
    assert "ERROR Project .codex directory not found" in stdout


def test_doctor_reports_invalid_project_config(workspace, run_cli):
    """doctor reports invalid codexmgr.toml syntax."""
    project, codex_home = workspace
    (project / ".codex").mkdir()
    (project / ".codex" / "codexmgr.toml").write_text(
        "not valid toml",
        encoding="utf-8",
    )

    exit_code, stdout, stderr = run_cli(["doctor"], project, codex_home)

    assert exit_code == 1
    assert stderr == ""
    assert "ERROR Invalid TOML" in stdout


def test_doctor_reports_missing_agentsmd_source(workspace, run_cli):
    """doctor reports configured AGENTS.md snippets that cannot be resolved."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    (project / ".codex" / "codexmgr.toml").write_text(
        '''
[agents_md]
src = ["missing-snippet"]
''',
        encoding="utf-8",
    )

    exit_code, stdout, stderr = run_cli(["doctor"], project, codex_home)

    assert exit_code == 1
    assert stderr == ""
    assert "ERROR Template not found:" in stdout
    assert "missing-snippet.toml" in stdout


def test_doctor_reports_missing_enabled_skill_and_stale_outputs(workspace, run_cli):
    """doctor reports missing enabled skills and stale generated files."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    (project / ".codex" / "codexmgr.toml").write_text(
        '''
[skills]
enabled = ["missing-skill"]
disabled = []
''',
        encoding="utf-8",
    )

    exit_code, stdout, stderr = run_cli(["doctor"], project, codex_home)

    assert exit_code == 1
    assert stderr == ""
    assert "ERROR Missing enabled skill: missing-skill" in stdout
    assert "ERROR Out of sync: .codex/codexmgr.lock" in stdout
    assert "ERROR Out of sync: .codex/config.toml" in stdout


def test_doctor_reports_missing_enabled_hook_and_stale_outputs(
    workspace,
    run_cli_with_homes,
):
    """doctor reports missing enabled hook bundles and stale generated files."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    (project / ".codex" / "codexmgr.toml").write_text(
        '''
[hooks]
enabled = ["missing-hook"]
disabled = []
''',
        encoding="utf-8",
    )

    exit_code, stdout, stderr = run_cli_with_homes(
        ["doctor"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stderr == ""
    assert "ERROR Missing enabled hook: missing-hook" in stdout
    assert "ERROR Out of sync: .codex/codexmgr.lock" in stdout
    assert "ERROR Out of sync: .codex/hooks.json" in stdout


def test_doctor_reports_missing_enabled_agent_and_stale_outputs(
    workspace,
    run_cli_with_homes,
):
    """doctor reports missing enabled custom-agent files and stale outputs."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    (project / ".codex" / "codexmgr.toml").write_text(
        '''
[agents]
enabled = ["missing-agent"]
disabled = []
''',
        encoding="utf-8",
    )

    exit_code, stdout, stderr = run_cli_with_homes(
        ["doctor"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stderr == ""
    assert "ERROR Missing enabled agent: missing-agent" in stdout
    assert "ERROR Out of sync: .codex/codexmgr.lock" in stdout


def test_doctor_reports_missing_enabled_rule_but_not_disabled_rule(
    workspace,
    run_cli_with_homes,
):
    """doctor reports missing enabled rules and ignores disabled missing refs."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    (project / ".codex" / "codexmgr.toml").write_text(
        '''
[rules]
enabled = ["missing/"]
disabled = ["also-missing/"]
''',
        encoding="utf-8",
    )

    exit_code, stdout, stderr = run_cli_with_homes(
        ["doctor"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stderr == ""
    assert "ERROR Missing enabled rule: missing/" in stdout
    assert "also-missing" not in stdout


def test_doctor_reports_stale_managed_rule_copy(workspace, run_cli_with_homes):
    """doctor reports stale managed rule files."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_rule(codexmgr_home, "react/components.md")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(["rules", "enable", "react/"], project, codex_home, codexmgr_home)
    target_file = project / ".rules" / "react" / "components.md"
    target_file.write_text("# Local edit\n", encoding="utf-8")

    exit_code, stdout, stderr = run_cli_with_homes(
        ["doctor"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stderr == ""
    assert "ERROR Out of sync: .rules/react/components.md" in stdout


def test_doctor_reports_stale_managed_skill_copy(workspace, run_cli_with_homes):
    """doctor reports stale managed skill copies."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_skill(codexmgr_home, "review")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(["skill", "enable", "review"], project, codex_home, codexmgr_home)
    target_file = project / ".agents" / "skills" / "review" / "SKILL.md"
    target_file.write_text("# Local edit\n", encoding="utf-8")

    exit_code, stdout, stderr = run_cli_with_homes(
        ["doctor"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stderr == ""
    assert "ERROR Out of sync: .agents/skills/review/SKILL.md" in stdout


def test_doctor_warns_when_home_environment_variables_are_unset(
    workspace,
    run_cli,
):
    """doctor warns about unset home variables while using resolved defaults."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    (project / ".codex" / "codexmgr.toml").write_text("", encoding="utf-8")

    exit_code, stdout, stderr = run_cli(["doctor"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert "WARN CODEX_HOME not set" in stdout
    assert "WARN CODEXMGR_HOME not set" in stdout
    assert "OK Project checks passed" in stdout


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


def _write_agent(home, name):
    """Create a named custom agent under CODEXMGR_HOME.

    Args:
        home: Codexmgr home directory where the agent should be created.
        name: Agent file stem.

    Returns:
        Path to the created custom-agent TOML file.
    """
    agents_dir = home / "agents"
    agents_dir.mkdir(parents=True)
    path = agents_dir / f"{name}.toml"
    path.write_text('name = "agent"\n', encoding="utf-8")
    return path


def _write_hook_bundle(home, name):
    """Create a named hook bundle under CODEXMGR_HOME.

    Args:
        home: codexmgr home directory where the hook should be created.
        name: Hook bundle directory name.

    Returns:
        Path to the created hooks.json file.
    """
    hook_dir = home / "hooks" / name
    hook_dir.mkdir(parents=True)
    hook_file = hook_dir / "hooks.json"
    hook_file.write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "python3 .codex/hooks/rules.py",
                                },
                            ],
                        },
                    ],
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return hook_file


def _write_rule(codexmgr_home, relative_path):
    """Create a reusable rule file under CODEXMGR_HOME."""
    path = codexmgr_home / "rules" / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Rule\n", encoding="utf-8")
    return path
