"""CLI behavior tests for packaged codexmgr configurations."""

import json
from pathlib import Path


def test_package_list_prints_available_packages(workspace, run_cli_with_homes):
    """package list prints sorted package names with config.toml files."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_package(codexmgr_home, "repo-rules", 'hooks = ["repo-rules"]\n')
    _write_package(codexmgr_home, "coding", 'skills = ["review"]\n')
    (codexmgr_home / "packages" / "empty").mkdir(parents=True)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["package", "list"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "coding\nrepo-rules\n"


def test_package_enable_applies_agentsmd_skills_and_hooks(
    workspace,
    write_home_template,
    run_cli_with_homes,
    read_project_config,
    read_codex_config,
    assert_agents_md,
):
    """package enable mutates all referenced domains and applies once."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    write_home_template(
        codexmgr_home,
        "coding",
        '''
[rules]
text = "rendered"
''',
    )
    _write_skill(codexmgr_home, "repo-rule-manager")
    _write_hook_bundle(
        codexmgr_home,
        "repo-rules",
        files={"rules_context.py": "print('rules')\n"},
    )
    _write_package(
        codexmgr_home,
        "repo-rules",
        '''
agentsmd = ["coding"]
hooks = ["repo-rules"]
skills = ["repo-rule-manager"]
''',
    )
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["package", "enable", "repo-rules"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert "Enabled package repo-rules" in stdout
    assert "Applied project Codex configuration" in stdout
    assert read_project_config(project) == {
        "agents_md": {"src": ["coding"]},
        "skills": {"enabled": ["repo-rule-manager"], "disabled": []},
        "hooks": {"enabled": ["repo-rules"], "disabled": []},
    }
    assert_agents_md(project, "# rules\nrendered\n")
    skill_file = project / ".agents" / "skills" / "repo-rule-manager" / "SKILL.md"
    assert read_codex_config(project)["skills"]["config"] == [
        {"path": str(skill_file.resolve()), "enabled": True},
    ]
    assert skill_file.read_text(encoding="utf-8") == "# Skill\n"
    assert _read_project_hooks(project) == _expected_hooks("repo-rules")
    assert (
        project / ".codex" / "hooks" / "repo-rules" / "rules_context.py"
    ).read_text(encoding="utf-8") == "print('rules')\n"


def test_package_disable_disables_entries_and_removes_managed_copies(
    workspace,
    write_home_template,
    run_cli_with_homes,
    read_project_config,
    read_codex_config,
    assert_agents_md,
):
    """package disable applies the corresponding remove and disable actions."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    write_home_template(codexmgr_home, "coding", "[rules]\ntext = \"rendered\"\n")
    _write_skill(codexmgr_home, "repo-rule-manager")
    _write_hook_bundle(
        codexmgr_home,
        "repo-rules",
        files={"rules_context.py": "print('rules')\n"},
    )
    _write_package(
        codexmgr_home,
        "repo-rules",
        '''
agentsmd = ["coding"]
hooks = ["repo-rules"]
skills = ["repo-rule-manager"]
''',
    )
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(["package", "enable", "repo-rules"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["package", "disable", "repo-rules"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert "Disabled package repo-rules" in stdout
    assert read_project_config(project) == {
        "agents_md": {"src": []},
        "skills": {"enabled": [], "disabled": ["repo-rule-manager"]},
        "hooks": {"enabled": [], "disabled": ["repo-rules"]},
    }
    assert_agents_md(project, "")
    assert read_codex_config(project)["skills"]["config"] == [
        {"name": "repo-rule-manager", "enabled": False},
    ]
    assert not (project / ".agents" / "skills" / "repo-rule-manager").exists()
    assert not (project / ".codex" / "hooks" / "repo-rules").exists()
    assert not (project / ".codex" / "hooks.json").exists()


def test_package_enable_no_sync_updates_config_without_applying(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """package enable --no-sync writes config without refreshing outputs."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_hook_bundle(codexmgr_home, "repo-rules")
    _write_package(codexmgr_home, "repo-rules", 'hooks = ["repo-rules"]\n')
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["package", "enable", "--no-sync", "repo-rules"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == "Enabled package repo-rules\n"
    assert read_project_config(project)["hooks"] == {
        "enabled": ["repo-rules"],
        "disabled": [],
    }
    assert not (project / ".codex" / "hooks.json").exists()


def test_package_enable_does_not_duplicate_existing_entries(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """Repeated package enable commands keep one entry per referenced item."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_hook_bundle(codexmgr_home, "repo-rules")
    _write_package(
        codexmgr_home,
        "repo-rules",
        'hooks = ["repo-rules"]\nskills = ["repo-rule-manager"]\n',
    )
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    run_cli_with_homes(["package", "enable", "repo-rules"], project, codex_home, codexmgr_home)
    exit_code, _, stderr = run_cli_with_homes(
        ["package", "enable", "repo-rules"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    config = read_project_config(project)
    assert config["hooks"]["enabled"] == ["repo-rules"]
    assert config["skills"]["enabled"] == ["repo-rule-manager"]


def test_package_enable_accepts_multiple_packages(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """package enable accepts multiple package names and applies once."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_hook_bundle(codexmgr_home, "repo-rules")
    _write_hook_bundle(codexmgr_home, "audit")
    _write_package(codexmgr_home, "repo-rules", 'hooks = ["repo-rules"]\n')
    _write_package(codexmgr_home, "audit", 'hooks = ["audit"]\nskills = ["review"]\n')
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["package", "enable", "repo-rules", "audit"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == (
        "Enabled package repo-rules\n"
        "Enabled package audit\n"
        "Applied project Codex configuration\n"
    )
    assert read_project_config(project)["hooks"]["enabled"] == ["repo-rules", "audit"]
    assert read_project_config(project)["skills"]["enabled"] == ["review"]


def test_package_enable_accepts_multiple_profiles(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """package enable applies root entries plus repeated multi-value profiles."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_hook_bundle(codexmgr_home, "repo-rules")
    _write_hook_bundle(codexmgr_home, "coding-hook")
    _write_package(
        codexmgr_home,
        "repo-rules",
        '''
hooks = ["repo-rules"]
skills = ["base-skill"]

[profiles.strict]
skills = ["strict-skill"]

[profiles.coding]
hooks = ["coding-hook"]

[profiles.python]
skills = ["python-skill"]
''',
    )
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        [
            "package",
            "enable",
            "repo-rules",
            "--profile",
            "strict",
            "coding",
            "--profile",
            "python",
        ],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == (
        "Enabled package repo-rules (profiles: strict, coding, python)\n"
        "Applied project Codex configuration\n"
    )
    assert read_project_config(project)["hooks"] == {
        "enabled": ["repo-rules", "coding-hook"],
        "disabled": [],
    }
    assert read_project_config(project)["skills"] == {
        "enabled": ["base-skill", "strict-skill", "python-skill"],
        "disabled": [],
    }


def test_package_disable_accepts_profiles(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """package disable applies disable semantics to selected profile entries."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_hook_bundle(codexmgr_home, "repo-rules")
    _write_package(
        codexmgr_home,
        "repo-rules",
        '''
hooks = ["repo-rules"]
skills = ["base-skill"]

[profiles.strict]
skills = ["strict-skill"]
''',
    )
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(
        ["package", "enable", "repo-rules", "--profile", "strict"],
        project,
        codex_home,
        codexmgr_home,
    )

    exit_code, stdout, stderr = run_cli_with_homes(
        ["package", "disable", "repo-rules", "--profile", "strict"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == (
        "Disabled package repo-rules (profiles: strict)\n"
        "Applied project Codex configuration\n"
    )
    assert read_project_config(project)["hooks"] == {
        "enabled": [],
        "disabled": ["repo-rules"],
    }
    assert read_project_config(project)["skills"] == {
        "enabled": [],
        "disabled": ["base-skill", "strict-skill"],
    }


def test_package_enable_rejects_missing_profile_before_writing(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """Missing package profiles fail before project config mutation."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_hook_bundle(codexmgr_home, "repo-rules")
    _write_package(codexmgr_home, "repo-rules", 'hooks = ["repo-rules"]\n')
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["package", "enable", "repo-rules", "--profile", "missing"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "Package profile not found: repo-rules.missing" in stderr
    assert read_project_config(project) == {}


def test_package_enable_fails_for_missing_package(workspace, run_cli_with_homes):
    """package enable fails when the named package config does not exist."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["package", "enable", "missing"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "Package not found:" in stderr


def test_package_enable_rejects_invalid_package_schema(
    workspace,
    run_cli_with_homes,
):
    """package enable rejects supported keys that are not string lists."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    package_config = _write_package(codexmgr_home, "bad", 'hooks = "repo-rules"\n')
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["package", "enable", "bad"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert f"{package_config} hooks must be a list of strings" in stderr


def test_package_enable_rejects_unknown_package_keys(
    workspace,
    run_cli_with_homes,
):
    """package enable rejects unsupported package config keys."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_package(codexmgr_home, "bad", 'mcp = ["browsermcp"]\n')
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["package", "enable", "bad"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "Unsupported package config key: mcp" in stderr


def test_package_enable_rejects_missing_agentsmd_before_writing(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """Missing AGENTS.md templates fail before package config mutation."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_package(codexmgr_home, "bad", 'agentsmd = ["missing"]\n')
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["package", "enable", "bad"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "Template not found:" in stderr
    assert read_project_config(project) == {}


def test_package_enable_rejects_missing_hook_before_writing(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """Missing hook bundles fail before package config mutation."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_package(codexmgr_home, "bad", 'hooks = ["missing"]\n')
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["package", "enable", "bad"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "Hook bundle not found:" in stderr
    assert read_project_config(project) == {}


def _write_package(codexmgr_home: Path, name: str, content: str) -> Path:
    """Create a package config under CODEXMGR_HOME.

    Args:
        codexmgr_home: codexmgr home directory.
        name: Bare package name.
        content: TOML content for config.toml.

    Returns:
        Path to the created package config.
    """
    package_dir = codexmgr_home / "packages" / name
    package_dir.mkdir(parents=True)
    path = package_dir / "config.toml"
    path.write_text(content, encoding="utf-8")
    return path


def _write_skill(codexmgr_home: Path, name: str) -> Path:
    """Create a codexmgr-home skill with a SKILL.md file.

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


def _write_hook_bundle(
    codexmgr_home: Path,
    name: str,
    files: dict[str, str] | None = None,
) -> Path:
    """Create a named hook bundle under CODEXMGR_HOME.

    Args:
        codexmgr_home: codexmgr home directory.
        name: Bare hook bundle name.
        files: Optional support files to write under the bundle directory.

    Returns:
        Path to the created hooks.json file.
    """
    hook_dir = codexmgr_home / "hooks" / name
    hook_dir.mkdir(parents=True)
    hook_file = hook_dir / "hooks.json"
    hook_file.write_text(json.dumps(_source_hooks(), indent=2) + "\n", encoding="utf-8")
    for relative_path, content in (files or {}).items():
        path = hook_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return hook_file


def _source_hooks() -> dict:
    """Build a source hooks.json document for tests.

    Returns:
        JSON-compatible hook bundle data.
    """
    return {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "startup|resume",
                    "hooks": [
                        {
                            "type": "command",
                            "command": (
                                "/usr/bin/python3 "
                                '"$(git rev-parse --show-toplevel)/'
                                '.codex/hooks/repo-rules/rules_context.py"'
                            ),
                            "timeout": 10,
                            "statusMessage": "Loading rule headers",
                        },
                    ],
                },
            ],
        },
    }


def _expected_hooks(name: str) -> dict:
    """Build expected generated project hooks with managed metadata.

    Args:
        name: Managed hook bundle name.

    Returns:
        JSON-compatible hook config data.
    """
    data = _source_hooks()
    data["hooks"]["SessionStart"][0]["hooks"][0]["codexmanager_meta"] = {
        "managed": True,
        "hook": name,
        "version": 1,
    }
    return data


def _read_project_hooks(project: Path) -> dict:
    """Read project-local hooks.json as JSON.

    Args:
        project: Project root directory.

    Returns:
        Parsed hooks.json data.
    """
    return json.loads((project / ".codex" / "hooks.json").read_text(encoding="utf-8"))
