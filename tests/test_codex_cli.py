"""CLI tests for the codex pass-through wrapper."""

import io
import tomllib
from types import SimpleNamespace

from codexmgr.commands.codex import build_codex_command
from codexmgr.interface.cli import main


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

    monkeypatch.setattr("codexmgr.commands.codex.subprocess.run", fake_run)

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

    monkeypatch.setattr("codexmgr.commands.codex.subprocess.run", fake_run)

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

    monkeypatch.setattr("codexmgr.commands.codex.subprocess.run", fake_run)

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


def test_codex_subcommand_supports_jit_package_profiles(
    workspace,
    monkeypatch,
    run_cli_with_homes,
):
    """codex can run with an ephemeral package/profile overlay."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_home_template(codexmgr_home, "strict-agents", "[rules]\ntext = \"strict\"\n")
    _write_home_skill(codexmgr_home, "base-skill")
    _write_home_skill(codexmgr_home, "strict-skill")
    _write_package(
        codexmgr_home,
        "repo-rules",
        '''
agentsmd = ["strict-agents"]
skills = ["base-skill"]

[profiles.strict]
skills = ["strict-skill"]
''',
    )
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    captured = {}

    def fake_run(command, cwd):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["codexmgr_toml"] = (
            project / ".codex" / "codexmgr.toml"
        ).read_text(encoding="utf-8")
        captured["config"] = tomllib.loads(
            (project / ".codex" / "config.toml").read_text(encoding="utf-8")
        )
        captured["agents_md"] = (project / "AGENTS.md").read_text(encoding="utf-8")
        return SimpleNamespace(returncode=5)

    monkeypatch.setattr("codexmgr.commands.codex.subprocess.run", fake_run)

    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = main(
        [
            "codex",
            "repo-rules",
            "--profile",
            "strict",
            "--",
            "exec",
            "hello",
        ],
        cwd=project,
        codex_home=codex_home,
        codexmgr_home=codexmgr_home,
        stdout=stdout,
        stderr=stderr,
    )

    base_skill = project / ".agents" / "skills" / "base-skill" / "SKILL.md"
    strict_skill = project / ".agents" / "skills" / "strict-skill" / "SKILL.md"
    assert exit_code == 5
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == ""
    assert captured["cwd"] == project
    assert captured["codexmgr_toml"] == ""
    assert captured["config"]["skills"]["config"] == [
        {"path": str(base_skill.resolve()), "enabled": True},
        {"path": str(strict_skill.resolve()), "enabled": True},
    ]
    assert "# rules\nstrict\n" in captured["agents_md"]
    assert captured["command"] == [
        "codex",
        "-c",
        f'skills.config=[{{path="{base_skill.resolve()}", enabled=true}}, '
        f'{{path="{strict_skill.resolve()}", enabled=true}}]',
        "exec",
        "hello",
    ]
    assert (project / ".codex" / "codexmgr.toml").read_text(encoding="utf-8") == ""
    assert tomllib.loads((project / ".codex" / "config.toml").read_text()) == {}
    assert not (project / ".codex" / "codexmgr.lock").exists()
    assert not (project / "AGENTS.md").exists()
    assert not base_skill.exists()
    assert not strict_skill.exists()


def _write_package(codexmgr_home, name, content):
    """Create a package config for codex command tests.

    Args:
        codexmgr_home: codexmgr home directory.
        name: Bare package name.
        content: TOML content to write.

    Returns:
        Path to the created package config.
    """
    package_dir = codexmgr_home / "packages" / name
    package_dir.mkdir(parents=True)
    path = package_dir / "config.toml"
    path.write_text(content, encoding="utf-8")
    return path


def _write_home_skill(codexmgr_home, name):
    """Create a codexmgr-home skill for codex command tests.

    Args:
        codexmgr_home: codexmgr home directory.
        name: Bare skill name.

    Returns:
        Path to the created SKILL.md file.
    """
    skill_dir = codexmgr_home / "skills" / name
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# Skill\n", encoding="utf-8")
    return skill_file


def _write_home_template(codexmgr_home, name, content):
    """Create a named AGENTS.md template for codex command tests.

    Args:
        codexmgr_home: codexmgr home directory.
        name: Bare template name.
        content: TOML content to write.

    Returns:
        Path to the created template.
    """
    template_dir = codexmgr_home / "agentsmd"
    template_dir.mkdir(parents=True)
    path = template_dir / f"{name}.toml"
    path.write_text(content, encoding="utf-8")
    return path
