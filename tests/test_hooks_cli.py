"""CLI behavior tests for managed Codex hook bundles."""

import json


def test_hooks_list_marks_available_enabled_disabled_and_missing(
    workspace,
    run_cli_with_homes,
):
    """hooks list reports available hook bundle names with project state markers."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_hook_bundle(codexmgr_home, "rules")
    _write_hook_bundle(codexmgr_home, "audit")

    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(
        ["hooks", "enable", "--no-sync", "rules"],
        project,
        codex_home,
        codexmgr_home,
    )
    run_cli_with_homes(
        ["hooks", "disable", "--no-sync", "legacy"],
        project,
        codex_home,
        codexmgr_home,
    )
    exit_code, stdout, stderr = run_cli_with_homes(
        ["hooks", "list"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert stdout == (
        "available audit\n"
        "disabled legacy (missing)\n"
        "enabled rules\n"
    )


def test_hooks_enable_applies_and_copies_bundle(
    workspace,
    run_cli_with_homes,
    read_project_config,
    read_lock,
):
    """hooks enable stores config, merges hooks.json, copies files, and locks state."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    source_file = _write_hook_bundle(
        codexmgr_home,
        "rules",
        files={"rules_context.py": "print('rules')\n"},
    )
    target_dir = project / ".codex" / "hooks" / "rules"
    target_file = target_dir / "rules_context.py"

    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    exit_code, stdout, stderr = run_cli_with_homes(
        ["hooks", "enable", "rules"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert "Enabled rules" in stdout
    assert read_project_config(project)["hooks"] == {
        "enabled": ["rules"],
        "disabled": [],
    }
    assert _read_project_hooks(project) == _expected_rules_hooks("rules")
    assert target_file.read_text(encoding="utf-8") == "print('rules')\n"
    assert read_lock(project)["hooks"] == {
        "enabled": ["rules"],
        "disabled": [],
        "created_hooks_json": True,
        "copies": [
            {
                "name": "rules",
                "source": str(source_file.parent.resolve()),
                "target": str(target_dir.resolve()),
            },
        ],
    }


def test_hooks_enable_preserves_unmanaged_local_hooks(
    workspace,
    run_cli_with_homes,
):
    """Generated hook handlers are merged without deleting unmanaged hooks."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_hook_bundle(codexmgr_home, "rules")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    unmanaged = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 local.py",
                        },
                    ],
                },
            ],
        },
    }
    _write_project_hooks(project, unmanaged)

    exit_code, _, stderr = run_cli_with_homes(
        ["hooks", "enable", "rules"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    hooks = _read_project_hooks(project)["hooks"]
    assert hooks["PostToolUse"] == unmanaged["hooks"]["PostToolUse"]
    assert hooks["SessionStart"] == _expected_rules_hooks("rules")["hooks"][
        "SessionStart"
    ]


def test_hooks_enable_does_not_duplicate_entries(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """Repeated enable keeps one config entry and one managed hook handler."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_hook_bundle(codexmgr_home, "rules")

    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(["hooks", "enable", "rules"], project, codex_home, codexmgr_home)
    exit_code, _, stderr = run_cli_with_homes(
        ["hooks", "enable", "rules"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert read_project_config(project)["hooks"]["enabled"] == ["rules"]
    handlers = _read_project_hooks(project)["hooks"]["SessionStart"][0]["hooks"]
    assert handlers == _expected_rules_hooks("rules")["hooks"]["SessionStart"][0][
        "hooks"
    ]


def test_hooks_enable_and_disable_accept_multiple_bundles(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """hooks enable and disable accept multiple hook bundle names per call."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_hook_bundle(codexmgr_home, "rules")
    _write_hook_bundle(codexmgr_home, "audit")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    enable_exit, enable_stdout, enable_stderr = run_cli_with_homes(
        ["hooks", "enable", "rules", "audit"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert enable_exit == 0
    assert enable_stderr == ""
    assert enable_stdout == (
        "Enabled rules\n"
        "Enabled audit\n"
        "Applied project Codex configuration\n"
    )
    assert read_project_config(project)["hooks"] == {
        "enabled": ["rules", "audit"],
        "disabled": [],
    }

    disable_exit, disable_stdout, disable_stderr = run_cli_with_homes(
        ["hooks", "disable", "rules", "audit"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert disable_exit == 0
    assert disable_stderr == ""
    assert disable_stdout == (
        "Disabled rules\n"
        "Disabled audit\n"
        "Applied project Codex configuration\n"
    )
    assert read_project_config(project)["hooks"] == {
        "enabled": [],
        "disabled": ["rules", "audit"],
    }


def test_hooks_disable_removes_managed_handlers_and_copy(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """hooks disable removes generated handlers and managed copied files."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_hook_bundle(
        codexmgr_home,
        "rules",
        files={"rules_context.py": "print('rules')\n"},
    )
    unmanaged = {
        "hooks": {
            "PostToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "python3 local.py",
                        },
                    ],
                },
            ],
        },
    }
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    _write_project_hooks(project, unmanaged)
    run_cli_with_homes(["hooks", "enable", "rules"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["hooks", "disable", "rules"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert "Disabled rules" in stdout
    assert read_project_config(project)["hooks"] == {
        "enabled": [],
        "disabled": ["rules"],
    }
    assert _read_project_hooks(project) == unmanaged
    assert not (project / ".codex" / "hooks" / "rules").exists()


def test_hooks_disable_removes_created_hooks_json_when_empty(
    workspace,
    run_cli_with_homes,
):
    """A hooks.json file created only for managed hooks is removed on disable."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_hook_bundle(codexmgr_home, "rules")
    hooks_json = project / ".codex" / "hooks.json"

    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    run_cli_with_homes(["hooks", "enable", "rules"], project, codex_home, codexmgr_home)
    exit_code, _, stderr = run_cli_with_homes(
        ["hooks", "disable", "rules"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert not hooks_json.exists()


def test_hooks_enable_refuses_unmanaged_copy_target(
    workspace,
    run_cli_with_homes,
):
    """Existing untracked .codex hook folders are not overwritten."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_hook_bundle(
        codexmgr_home,
        "rules",
        files={"rules_context.py": "print('rules')\n"},
    )
    local_file = project / ".codex" / "hooks" / "rules" / "rules_context.py"
    local_file.parent.mkdir(parents=True)
    local_file.write_text("local\n", encoding="utf-8")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["hooks", "enable", "rules"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "Refusing to overwrite unmanaged hook copy:" in stderr
    assert local_file.read_text(encoding="utf-8") == "local\n"


def test_hooks_enable_fails_for_missing_bundle(workspace, run_cli_with_homes):
    """hooks enable validates named hook bundles before writing config."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["hooks", "enable", "missing"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert "Hook bundle not found:" in stderr


def test_hooks_enable_no_sync_updates_config_without_applying(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """hooks enable --no-sync updates config without refreshing generated outputs."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_hook_bundle(codexmgr_home, "rules")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)

    exit_code, stdout, stderr = run_cli_with_homes(
        ["hooks", "enable", "--no-sync", "rules"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert "Enabled rules" in stdout
    assert read_project_config(project)["hooks"] == {
        "enabled": ["rules"],
        "disabled": [],
    }
    assert not (project / ".codex" / "hooks.json").exists()


def _write_hook_bundle(home, name, hooks_json=None, files=None):
    """Create a named hook bundle under CODEXMGR_HOME.

    Args:
        home: codexmgr home directory where the hook should be created.
        name: Hook bundle directory name.
        hooks_json: Optional hooks.json data. A SessionStart command is used
            when omitted.
        files: Optional mapping of relative file paths to text content.

    Returns:
        Path to the created hooks.json file.
    """
    hook_dir = home / "hooks" / name
    hook_dir.mkdir(parents=True)
    hook_file = hook_dir / "hooks.json"
    hook_file.write_text(
        json.dumps(hooks_json or _source_rules_hooks(), indent=2) + "\n",
        encoding="utf-8",
    )
    for relative_path, content in (files or {}).items():
        path = hook_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return hook_file


def _source_rules_hooks():
    """Build a source hooks.json document for the rules hook bundle."""
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
                                '.codex/hooks/rules/rules_context.py"'
                            ),
                            "timeout": 10,
                            "statusMessage": "Loading rule headers",
                        },
                    ],
                },
            ],
        },
    }


def _expected_rules_hooks(name):
    """Build expected project hooks.json data with managed metadata."""
    data = _source_rules_hooks()
    handler = data["hooks"]["SessionStart"][0]["hooks"][0]
    handler["codexmanager_meta"] = {
        "managed": True,
        "hook": name,
        "version": 1,
    }
    return data


def _read_project_hooks(project):
    """Read project-local hooks.json as JSON."""
    return json.loads((project / ".codex" / "hooks.json").read_text(encoding="utf-8"))


def _write_project_hooks(project, data):
    """Write project-local hooks.json as JSON."""
    path = project / ".codex" / "hooks.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
