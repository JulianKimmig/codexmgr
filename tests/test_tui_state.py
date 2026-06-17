"""Tests for the interactive codexmgr staged configuration model."""

import json

from codexmgr.interface.parser import build_parser
from codexmgr.project.sync import generated_file_diffs
from codexmgr.tui.diff import staged_diff_lines
from codexmgr.tui.items import package_items
from codexmgr.tui.state import load_staged_config, save_staged_config


def test_tui_parser_accepts_interactive_flags():
    """The interactive CLI has explicit no-sync and diff-preview flags."""
    args = build_parser().parse_args(["tui", "--no-sync", "--show-diff"])

    assert args.command == "tui"
    assert args.no_sync is True
    assert args.show_diff is True


def test_tui_cli_dispatches_to_runner(workspace, monkeypatch, run_cli_with_homes):
    """The tui command dispatches parsed flags to the interactive runner."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    captured = {}

    def fake_run_tui_command(args, cwd, injected_codex_home, injected_codexmgr_home):
        captured["args"] = args
        captured["cwd"] = cwd
        captured["codex_home"] = injected_codex_home
        captured["codexmgr_home"] = injected_codexmgr_home
        return 7

    monkeypatch.setattr("codexmgr.interface.cli.run_tui_command", fake_run_tui_command)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["tui", "--no-sync", "--show-diff"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 7
    assert stdout == ""
    assert stderr == ""
    assert captured["args"].no_sync is True
    assert captured["args"].show_diff is True
    assert captured["cwd"] == project
    assert captured["codex_home"] == codex_home
    assert captured["codexmgr_home"] == codexmgr_home


def test_staged_skill_toggle_writes_only_on_save(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """Skill toggles stay in memory until the staged config is saved."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_skill(codexmgr_home, "review")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    staged = load_staged_config(project, codex_home, codexmgr_home)
    staged.set_skill_enabled("review", True)

    assert "skills" not in read_project_config(project)

    save_staged_config(staged, no_sync=True)

    assert read_project_config(project)["skills"] == {
        "enabled": ["review"],
        "disabled": [],
    }
    assert not (project / ".agents" / "skills" / "review").exists()


def test_staged_package_toggle_enables_and_disables_referenced_entries(
    workspace,
    write_home_template,
    run_cli_with_homes,
    read_project_config,
):
    """Package toggles proxy their AGENTS.md, skill, and hook entries."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    write_home_template(codexmgr_home, "coding", "[rules]\ntext = \"rendered\"\n")
    _write_skill(codexmgr_home, "repo-rule-manager")
    _write_hook_bundle(codexmgr_home, "repo-rules")
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

    staged = load_staged_config(project, codex_home, codexmgr_home)
    staged.set_package_enabled("repo-rules", True)
    assert staged.package_state("repo-rules") == "enabled"
    save_staged_config(staged, no_sync=True)

    assert read_project_config(project) == {
        "agents_md": {"src": ["coding"]},
        "skills": {"enabled": ["repo-rule-manager"], "disabled": []},
        "hooks": {"enabled": ["repo-rules"], "disabled": []},
    }

    staged = load_staged_config(project, codex_home, codexmgr_home)
    staged.set_package_enabled("repo-rules", False)
    assert staged.package_state("repo-rules") == "disabled"
    save_staged_config(staged, no_sync=True)

    assert read_project_config(project) == {
        "agents_md": {"src": []},
        "skills": {"enabled": [], "disabled": ["repo-rule-manager"]},
        "hooks": {"enabled": [], "disabled": ["repo-rules"]},
    }


def test_staged_package_reports_partial_state(
    workspace,
    write_home_template,
    run_cli_with_homes,
):
    """Packages display partial state when only some entries are active."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    write_home_template(codexmgr_home, "coding", "[rules]\ntext = \"rendered\"\n")
    _write_skill(codexmgr_home, "repo-rule-manager")
    _write_hook_bundle(codexmgr_home, "repo-rules")
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
    run_cli_with_homes(
        ["skill", "enable", "--no-sync", "repo-rule-manager"],
        project,
        codex_home,
        codexmgr_home,
    )

    staged = load_staged_config(project, codex_home, codexmgr_home)

    assert staged.package_state("repo-rules") == "partial"


def test_staged_package_profile_toggle_updates_profile_entries(
    workspace,
    write_home_template,
    run_cli_with_homes,
    read_project_config,
):
    """Package profiles can be toggled independently from package root entries."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    write_home_template(codexmgr_home, "coding", "[rules]\ntext = \"rendered\"\n")
    write_home_template(codexmgr_home, "strict-coding", "[rules]\ntext = \"strict\"\n")
    _write_skill(codexmgr_home, "repo-rule-manager")
    _write_skill(codexmgr_home, "strict-review")
    _write_package(
        codexmgr_home,
        "repo-rules",
        '''
agentsmd = ["coding"]
skills = ["repo-rule-manager"]

[profiles.strict]
agentsmd = ["strict-coding"]
skills = ["strict-review"]
''',
    )
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    staged = load_staged_config(project, codex_home, codexmgr_home)
    staged.set_package_enabled("repo-rules", True)
    staged.set_package_profile_enabled("repo-rules", "strict", True)

    assert staged.package_state("repo-rules") == "enabled"
    assert staged.package_profile_state("repo-rules", "strict") == "enabled"
    save_staged_config(staged, no_sync=True)

    assert read_project_config(project) == {
        "agents_md": {"src": ["coding", "strict-coding"]},
        "skills": {
            "enabled": ["repo-rule-manager", "strict-review"],
            "disabled": [],
        },
    }

    staged = load_staged_config(project, codex_home, codexmgr_home)
    staged.set_package_profile_enabled("repo-rules", "strict", False)
    save_staged_config(staged, no_sync=True)

    assert read_project_config(project) == {
        "agents_md": {"src": ["coding"]},
        "skills": {
            "enabled": ["repo-rule-manager"],
            "disabled": ["strict-review"],
        },
    }


def test_package_items_include_profile_rows(
    workspace,
    write_home_template,
    run_cli_with_homes,
):
    """The TUI package list exposes package profiles as selectable rows."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    write_home_template(codexmgr_home, "strict-coding", "[rules]\ntext = \"strict\"\n")
    _write_skill(codexmgr_home, "strict-review")
    _write_package(
        codexmgr_home,
        "repo-rules",
        '''
[profiles.strict]
agentsmd = ["strict-coding"]
skills = ["strict-review"]
''',
    )
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    staged = load_staged_config(project, codex_home, codexmgr_home)

    items = package_items(staged)

    assert [(item.name, item.value, item.detail) for item in items] == [
        ("repo-rules", "package:repo-rules", "package"),
        ("repo-rules / strict", "package-profile:repo-rules:strict", "profile"),
    ]


def test_staged_mcp_toggle_updates_enabled_field_only(
    workspace,
    run_cli,
    read_project_config,
):
    """MCP editing in the TUI is limited to the enabled override field."""
    project, codex_home = workspace
    run_cli(["setup"], project, codex_home)
    config_path = project / ".codex" / "codexmgr.toml"
    config_path.write_text(
        '''
[mcp.servers.browsermcp]
bearer_token_env_var = "BROWSERMCP_TOKEN"
''',
        encoding="utf-8",
    )

    staged = load_staged_config(project, codex_home, codex_home)
    staged.set_mcp_enabled("browsermcp", True)
    save_staged_config(staged, no_sync=True)

    assert read_project_config(project)["mcp"]["servers"]["browsermcp"] == {
        "bearer_token_env_var": "BROWSERMCP_TOKEN",
        "enabled": True,
    }


def test_staged_diff_summary_and_unified_diff_do_not_write_files(
    workspace,
    write_home_template,
    run_cli,
):
    """Diff preview reports staged generated changes without applying them."""
    project, codex_home = workspace
    write_home_template(codex_home, "coding", "[rules]\ntext = \"preview\"\n")
    run_cli(["setup"], project, codex_home)

    staged = load_staged_config(project, codex_home, codex_home)
    staged.set_agentsmd_enabled("coding", True)

    summary = staged_diff_lines(staged, show_diff=False)
    detailed = staged_diff_lines(staged, show_diff=True)

    assert "Out of sync: .codex/codexmgr.lock" in summary
    assert "Out of sync: AGENTS.md" in summary
    assert "--- AGENTS.md (current)" in detailed
    assert "+++ AGENTS.md (expected)" in detailed
    assert "+# rules" in detailed
    assert not (project / "AGENTS.md").exists()
    assert generated_file_diffs(project, codex_home, codex_home) == []


def _write_skill(home, name):
    """Create a codexmgr-home skill for tests."""
    skill_dir = home / "skills" / name
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# Skill\n", encoding="utf-8")
    return skill_file


def _write_hook_bundle(home, name):
    """Create a codexmgr-home hook bundle for tests."""
    hook_dir = home / "hooks" / name
    hook_dir.mkdir(parents=True)
    hook_file = hook_dir / "hooks.json"
    hook_file.write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "matcher": "startup",
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
        ),
        encoding="utf-8",
    )
    return hook_file


def _write_package(home, name, content):
    """Create a codexmgr-home package for tests."""
    package_dir = home / "packages" / name
    package_dir.mkdir(parents=True)
    path = package_dir / "config.toml"
    path.write_text(content, encoding="utf-8")
    return path
