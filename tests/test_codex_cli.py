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


def test_codex_subcommand_passes_args_and_return_code(workspace, monkeypatch):
    """codexmgr codex forwards all args to the external codex command."""
    project, codex_home = workspace
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
