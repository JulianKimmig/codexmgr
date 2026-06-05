"""CLI tests for applying explicitly empty skill configuration."""


def test_apply_empty_skills_clears_generated_skill_config(
    workspace,
    run_cli,
    read_lock,
    read_codex_config,
):
    """An explicit empty [skills] table replaces stale generated skill entries."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    (project / ".codex" / "codexmgr.toml").write_text(
        '''
[skills]
enabled = []
disabled = []
''',
        encoding="utf-8",
    )
    (project / ".codex" / "config.toml").write_text(
        '''
model = "gpt-5"

[[skills.config]]
name = "stale"
enabled = true
''',
        encoding="utf-8",
    )

    exit_code, _, stderr = run_cli(["apply"], project, codex_home)

    assert exit_code == 0
    assert stderr == ""
    assert read_codex_config(project) == {
        "model": "gpt-5",
        "skills": {"config": []},
    }
    assert read_lock(project) == {"skills": {"config": []}}
