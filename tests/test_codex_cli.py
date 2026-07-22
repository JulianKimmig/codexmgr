"""CLI tests for the codex pass-through wrapper."""

import io
import tomllib
from types import SimpleNamespace

from codexmgr.commands.codex import build_codex_command
from codexmgr.interface.cli import main


def test_build_codex_command_proxies_args_without_flattening_project_config(workspace):
    """The command relies on project config instead of injected overrides."""
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

    assert command == ["codex", "exec", "hello"]


def test_build_codex_command_proxies_args_when_project_config_is_missing(workspace):
    """Missing .codex/config.toml does not affect argument proxying."""
    project, _ = workspace

    assert build_codex_command(project, ["--help"]) == ["codex", "--help"]


def test_build_codex_command_proxies_user_config_overrides(workspace):
    """User -c values retain their original order and representation."""
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
        'skills.config=[{name="imagegen", enabled=false}]',
        "--config",
        'sandbox_permissions=["network"]',
        '--config=model="o3"',
        "exec",
        "hello",
    ]


def test_build_codex_command_keeps_repeated_user_lists(workspace):
    """Repeated user list overrides remain separate pass-through arguments."""
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
        'skills.config=[{name="first", enabled=true}]',
        "-c",
        'skills.config=[{name="second", enabled=false}]',
    ]


def test_codex_subcommand_uses_project_runtime_home_auth_and_return_code(
    workspace,
    monkeypatch,
):
    """Default launch isolates runtime state and links the global auth file."""
    project, codex_home = workspace
    (project / ".codex").mkdir()
    (project / ".codex" / "codexmgr.toml").write_text(
        '[mcp.servers.example]\ncommand = "example"\n',
        encoding="utf-8",
    )
    user_home = project.parent / "user-home"
    global_auth = user_home / ".codex" / "auth.json"
    global_auth.parent.mkdir(parents=True)
    global_auth.write_text('{"token": "test"}\n', encoding="utf-8")
    stale_auth = project.parent / "stale-auth.json"
    stale_auth.write_text('{"token": "stale"}\n', encoding="utf-8")
    runtime_home = project / ".codex" / ".runtime"
    runtime_home.mkdir()
    (runtime_home / "auth.json").symlink_to(stale_auth)
    monkeypatch.delenv("CODEX_GLOBAL_AUTH", raising=False)
    monkeypatch.setenv("HOME", str(user_home))
    monkeypatch.setenv("CODEXMGR_LAUNCH_TEST", "forwarded")
    captured = {}

    def fake_run(command, cwd, env):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["codex_home"] = env["CODEX_HOME"]
        captured["environment_marker"] = env["CODEXMGR_LAUNCH_TEST"]
        captured["runtime_config_exists"] = (
            project / ".codex" / ".runtime" / "config.toml"
        ).exists()
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
        "codex_home": str(runtime_home),
        "environment_marker": "forwarded",
        "runtime_config_exists": False,
    }
    assert runtime_home.is_dir()
    assert tomllib.loads(
        (project / ".codex" / "config.toml").read_text(encoding="utf-8")
    )["mcp_servers"]["example"] == {"command": "example"}
    auth_link = runtime_home / "auth.json"
    assert auth_link.is_symlink()
    assert auth_link.samefile(global_auth)


def test_codex_subcommand_warns_when_global_auth_is_missing(workspace, monkeypatch):
    """Default launch warns and continues when no global auth file exists."""
    project, codex_home = workspace
    (project / ".codex").mkdir()
    (project / ".codex" / "codexmgr.toml").write_text("", encoding="utf-8")
    missing_auth = codex_home / "missing-auth.json"
    monkeypatch.setenv("CODEX_GLOBAL_AUTH", str(missing_auth))
    captured = {}

    def fake_run(command, cwd, env):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["codex_home"] = env["CODEX_HOME"]
        return SimpleNamespace(returncode=0)

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

    assert exit_code == 0
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == (
        "codexmgr codex: warning: no global auth found at "
        f"{missing_auth}; you may need to auth once.\n"
    )
    assert captured == {
        "command": ["codex", "exec", "hello"],
        "cwd": project,
        "codex_home": str(project / ".codex" / ".runtime"),
    }
    assert (project / ".codex" / ".runtime").is_dir()
    assert not (project / ".codex" / ".runtime" / "auth.json").exists()


def test_codex_subcommand_simple_mode_runs_basic_codex(workspace, monkeypatch):
    """The --simple launch skips project apply, local home, and auth linking."""
    project, codex_home = workspace
    global_auth = codex_home / "auth.json"
    global_auth.write_text('{"token": "test"}\n', encoding="utf-8")
    monkeypatch.setenv("CODEX_GLOBAL_AUTH", str(global_auth))
    captured = {}

    def fake_run(command, cwd):
        captured["command"] = command
        captured["cwd"] = cwd
        return SimpleNamespace(returncode=12)

    monkeypatch.setattr("codexmgr.commands.codex.subprocess.run", fake_run)

    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = main(
        ["codex", "--simple", "exec", "hello"],
        cwd=project,
        codex_home=codex_home,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 12
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == ""
    assert captured == {"command": ["codex", "exec", "hello"], "cwd": project}
    assert not (project / ".codex").exists()


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
    _configure_global_auth(codex_home, monkeypatch)

    captured = {}

    def fake_run(command, cwd, env):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["codex_home"] = env["CODEX_HOME"]
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
        "command": ["codex", "exec", "hello"],
        "cwd": project,
        "codex_home": str(project / ".codex" / ".runtime"),
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
    _write_home_agent(codexmgr_home, "rule-retriever")
    _write_home_skill(codexmgr_home, "base-skill")
    _write_home_skill(codexmgr_home, "strict-skill")
    _write_package(
        codexmgr_home,
        "repo-rules",
        '''
agentsmd = ["strict-agents"]
agents = ["rule-retriever"]
skills = ["base-skill"]

[profiles.strict]
skills = ["strict-skill"]
''',
    )
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    _configure_global_auth(codex_home, monkeypatch)
    captured = {}

    def fake_run(command, cwd, env):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["codex_home"] = env["CODEX_HOME"]
        captured["codexmgr_toml"] = (
            project / ".codex" / "codexmgr.toml"
        ).read_text(encoding="utf-8")
        captured["config"] = tomllib.loads(
            (project / ".codex" / "config.toml").read_text(encoding="utf-8")
        )
        captured["agents_md"] = (project / "AGENTS.md").read_text(encoding="utf-8")
        captured["agent"] = (
            project / ".codex" / "agents" / "rule-retriever.toml"
        ).read_text(encoding="utf-8")
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
    agent_file = project / ".codex" / "agents" / "rule-retriever.toml"
    assert exit_code == 5
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == ""
    assert captured["cwd"] == project
    assert captured["codex_home"] == str(project / ".codex" / ".runtime")
    assert captured["codexmgr_toml"] == ""
    assert captured["config"]["skills"]["config"] == [
        {"path": str(base_skill.resolve()), "enabled": True},
        {"path": str(strict_skill.resolve()), "enabled": True},
    ]
    assert "# rules\nstrict\n" in captured["agents_md"]
    assert captured["agent"] == 'name = "agent"\n'
    assert captured["command"] == ["codex", "exec", "hello"]
    assert (project / ".codex" / "codexmgr.toml").read_text(encoding="utf-8") == ""
    assert tomllib.loads((project / ".codex" / "config.toml").read_text()) == {}
    assert not (project / ".codex" / "codexmgr.lock").exists()
    assert not (project / "AGENTS.md").exists()
    assert not agent_file.exists()
    assert not base_skill.exists()
    assert not strict_skill.exists()


def test_codex_jit_overlay_snapshots_and_restores_rules(
    workspace,
    monkeypatch,
    run_cli_with_homes,
):
    """codex JIT package overlays copy rules temporarily and restore them."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_home_rule(codexmgr_home, "react/components.md", "# Components\n")
    _write_package(codexmgr_home, "frontend", 'rules = ["react/"]\n')
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    _configure_global_auth(codex_home, monkeypatch)
    captured = {}

    def fake_run(command, cwd, env):
        captured["command"] = command
        captured["codex_home"] = env["CODEX_HOME"]
        captured["rule"] = (
            project / ".rules" / "react" / "components.md"
        ).read_text(encoding="utf-8")
        return SimpleNamespace(returncode=9)

    monkeypatch.setattr("codexmgr.commands.codex.subprocess.run", fake_run)

    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = main(
        ["codex", "--package", "frontend", "--", "exec", "hello"],
        cwd=project,
        codex_home=codex_home,
        codexmgr_home=codexmgr_home,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == 9
    assert stdout.getvalue() == ""
    assert stderr.getvalue() == ""
    assert captured["command"] == ["codex", "exec", "hello"]
    assert captured["codex_home"] == str(project / ".codex" / ".runtime")
    assert captured["rule"] == "# Components\n"
    assert not (project / ".rules").exists()


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


def _configure_global_auth(codex_home, monkeypatch):
    """Create and select an isolated global auth file for a launch test.

    Args:
        codex_home: Temporary Codex home in which to create auth.json.
        monkeypatch: Pytest environment mutation fixture.

    Returns:
        Path to the selected global auth file.
    """
    global_auth = codex_home / "auth.json"
    global_auth.write_text('{"token": "test"}\n', encoding="utf-8")
    monkeypatch.setenv("CODEX_GLOBAL_AUTH", str(global_auth))
    return global_auth


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


def _write_home_agent(codexmgr_home, name):
    """Create a codexmgr-home custom agent for codex command tests.

    Args:
        codexmgr_home: codexmgr home directory.
        name: Agent file stem.

    Returns:
        Path to the created custom-agent TOML file.
    """
    agents_dir = codexmgr_home / "agents"
    agents_dir.mkdir(parents=True)
    path = agents_dir / f"{name}.toml"
    path.write_text('name = "agent"\n', encoding="utf-8")
    return path


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


def _write_home_rule(codexmgr_home, relative_path, content):
    """Create a codexmgr-home rule file for codex command tests.

    Args:
        codexmgr_home: codexmgr home directory.
        relative_path: POSIX path below the rules source root.
        content: Rule file content.

    Returns:
        Path to the created rule file.
    """
    path = codexmgr_home / "rules" / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path
