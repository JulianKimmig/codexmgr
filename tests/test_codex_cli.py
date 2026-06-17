"""CLI tests for the codex pass-through wrapper."""

import io
from types import SimpleNamespace

from codexmgr.cli import main
from codexmgr.codex import build_codex_command


def test_build_codex_command_includes_configured_skills(workspace):
    """The wrapper prepends config overrides from .codex/config.toml."""
    project, _ = workspace
    (project / ".codex").mkdir()
    (project / ".codex" / "config.toml").write_text(
        '''
model_instructions_file = "codexmgr-AGENTS.md"
sandbox_permissions = ["disk-full-read-access"]

[shell_environment_policy]
inherit = "all"

[[skills.config]]
path = "/abs/enabled/SKILL.md"
enabled = true

[[skills.config]]
path = "/abs/disabled/SKILL.md"
enabled = false

[[skills.config]]
name = "missing"
enabled = false
''',
        encoding="utf-8",
    )

    command = build_codex_command(project, ["exec", "hello"])

    assert command == [
        "codex",
        "-c",
        'model_instructions_file="codexmgr-AGENTS.md"',
        "-c",
        'sandbox_permissions=["disk-full-read-access"]',
        "-c",
        'shell_environment_policy.inherit="all"',
        "-c",
        'skills.config=[{path="/abs/enabled/SKILL.md", enabled=true}, '
        '{path="/abs/disabled/SKILL.md", enabled=false}, '
        '{name="missing", enabled=false}]',
        "exec",
        "hello",
    ]


def test_build_codex_command_uses_no_config_overrides_when_missing(workspace):
    """Missing .codex/config.toml forwards only the original codex args."""
    project, _ = workspace

    assert build_codex_command(project, ["--help"]) == ["codex", "--help"]


def test_build_codex_command_merges_user_config_overrides(workspace):
    """User -c values merge after project config before invoking codex."""
    project, _ = workspace
    (project / ".codex").mkdir()
    (project / ".codex" / "config.toml").write_text(
        '''
model = "gpt-5"
sandbox_permissions = ["disk-read"]

[[skills.config]]
path = "/abs/enabled/SKILL.md"
enabled = true
''',
        encoding="utf-8",
    )

    command = build_codex_command(
        project,
        [
            "-c",
            'skills.config=[{name="imagegen", enabled=false}]',
            "--config",
            'sandbox_permissions=["network"]',
            "--config=model=\"o3\"",
            "exec",
            "hello",
        ],
    )

    assert command == [
        "codex",
        "-c",
        'model="o3"',
        "-c",
        'sandbox_permissions=["disk-read", "network"]',
        "-c",
        'skills.config=[{path="/abs/enabled/SKILL.md", enabled=true}, '
        '{name="imagegen", enabled=false}]',
        "exec",
        "hello",
    ]


def test_build_codex_command_merges_repeated_user_lists(workspace):
    """Repeated user list overrides append into one final config value."""
    project, _ = workspace

    command = build_codex_command(
        project,
        [
            "-c",
            'skills.config=[{name="first", enabled=true}]',
            "-c",
            'skills.config=[{name="second", enabled=false}]',
        ],
    )

    assert command == [
        "codex",
        "-c",
        'skills.config=[{name="first", enabled=true}, {name="second", enabled=false}]',
    ]


def test_codex_subcommand_passes_args_and_return_code(workspace, monkeypatch):
    """codexmgr codex forwards all args to the external codex command."""
    project, codex_home = workspace
    (project / ".codex").mkdir()
    (project / ".codex" / "codexmgr.toml").write_text("", encoding="utf-8")
    captured = {}

    def fake_run(command, cwd):
        captured["command"] = command
        captured["cwd"] = cwd
        return SimpleNamespace(returncode=42)

    monkeypatch.setattr("codexmgr.codex.subprocess.run", fake_run)

    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = main(
        ["codex", "--help"],
        cwd=project,
        codex_home=codex_home,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 42
    assert stderr.getvalue() == ""
    assert captured == {
        "command": ["codex", "--help"],
        "cwd": project,
    }


def test_codex_subcommand_applies_project_config_before_running_codex(
    workspace,
    monkeypatch,
):
    """codexmgr codex refreshes generated config before starting codex."""
    project, codex_home = workspace
    skill_file = codex_home / "skills" / "example" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text("# Example\n", encoding="utf-8")
    (project / ".codex").mkdir()
    (project / ".codex" / "codexmgr.toml").write_text(
        '''
[skills]
enabled = ["example"]
''',
        encoding="utf-8",
    )

    captured = {}

    def fake_run(command, cwd):
        captured["command"] = command
        captured["cwd"] = cwd
        assert (project / ".codex" / "config.toml").is_file()
        return SimpleNamespace(returncode=7)

    monkeypatch.setattr("codexmgr.codex.subprocess.run", fake_run)

    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = main(
        ["codex", "exec", "hello"],
        cwd=project,
        codex_home=codex_home,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 7
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == ""
    assert captured == {
        "command": [
            "codex",
            "-c",
            f'skills.config=[{{path="{skill_file.resolve()}", enabled=true}}]',
            "exec",
            "hello",
        ],
        "cwd": project,
    }


def test_codex_subcommand_does_not_run_codex_when_apply_fails(
    workspace,
    monkeypatch,
):
    """codexmgr codex stops before subprocess execution when apply fails."""
    project, codex_home = workspace

    def fake_run(command, cwd):
        raise AssertionError("codex subprocess should not run")

    monkeypatch.setattr("codexmgr.codex.subprocess.run", fake_run)

    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = main(
        ["codex", "--help"],
        cwd=project,
        codex_home=codex_home,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "Project .codex directory not found" in stderr.getvalue()
