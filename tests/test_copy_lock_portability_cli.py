"""Behavioral tests for portable managed-copy lock entries."""

import json
from pathlib import Path

import pytest

from codexmgr.core.toml_io import write_toml_file


def test_managed_copy_locks_use_logical_sources_and_relative_targets(
    workspace,
    run_cli_with_homes,
    read_lock,
):
    """All manager-home copy families write repository-portable lock entries."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_managed_sources(codexmgr_home)
    _setup_managed_project(project, codex_home, codexmgr_home, run_cli_with_homes)

    lock = read_lock(project)

    assert lock["agents"]["copies"] == [
        {
            "name": "reviewer",
            "source": "codexmgr_home",
            "target": ".codex/agents/reviewer.toml",
        },
    ]
    assert lock["hooks"]["copies"] == [
        {
            "name": "audit",
            "source": "codexmgr_home",
            "target": ".codex/hooks/audit",
        },
    ]
    assert lock["rules"]["copies"] == [
        {
            "relative_path": "python/testing.md",
            "source": "codexmgr_home",
            "target": ".rules/python/testing.md",
        },
    ]


def test_apply_migrates_all_legacy_absolute_copy_locks(
    workspace,
    run_cli_with_homes,
    read_lock,
):
    """Apply accepts absolute legacy metadata and rewrites every copy family."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_managed_sources(codexmgr_home)
    _setup_project_config(project, codex_home, codexmgr_home, run_cli_with_homes)
    write_toml_file(
        project / ".codex" / "codexmgr.lock",
        _legacy_lock(project.parent / "old-project", project.parent / "old-home"),
    )

    exit_code, _, stderr = run_cli_with_homes(
        ["apply"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    lock = read_lock(project)
    assert lock["agents"]["copies"][0]["source"] == "codexmgr_home"
    assert lock["agents"]["copies"][0]["target"] == ".codex/agents/reviewer.toml"
    assert lock["hooks"]["copies"][0]["source"] == "codexmgr_home"
    assert lock["hooks"]["copies"][0]["target"] == ".codex/hooks/audit"
    assert lock["rules"]["copies"][0]["source"] == "codexmgr_home"
    assert lock["rules"]["copies"][0]["target"] == ".rules/python/testing.md"


def test_portable_copy_locks_match_across_project_and_home_roots(
    tmp_path,
    run_cli_with_homes,
):
    """Different clone and manager-home paths produce identical lock content."""
    lock_contents: list[str] = []
    for suffix in ("first", "second"):
        project = tmp_path / suffix / "project"
        codex_home = tmp_path / suffix / "codex-home"
        codexmgr_home = tmp_path / suffix / "codexmgr-home"
        project.mkdir(parents=True)
        codex_home.mkdir(parents=True)
        _write_managed_sources(codexmgr_home)
        _setup_managed_project(
            project,
            codex_home,
            codexmgr_home,
            run_cli_with_homes,
        )
        lock_contents.append(
            (project / ".codex" / "codexmgr.lock").read_text(encoding="utf-8"),
        )

    assert lock_contents[0] == lock_contents[1]


def test_legacy_obsolete_copy_cleanup_rebinds_to_current_project(
    workspace,
    run_cli_with_homes,
):
    """Legacy ownership removes current-clone targets without touching old paths."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    old_project = project.parent / "old-project"
    old_home = project.parent / "old-home"
    _setup_empty_copy_config(project, codex_home, codexmgr_home, run_cli_with_homes)
    write_toml_file(
        project / ".codex" / "codexmgr.lock",
        _legacy_lock(old_project, old_home),
    )
    current_targets = _write_copy_targets(project)
    old_targets = _write_copy_targets(old_project)

    exit_code, _, stderr = run_cli_with_homes(
        ["apply"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 0
    assert stderr == ""
    assert all(not target.exists() for target in current_targets)
    assert all(target.exists() for target in old_targets)


@pytest.mark.parametrize(
    ("section", "identity_key", "identity_value"),
    [
        ("agents", "name", "../outside"),
        ("agents", "name", ".."),
        ("hooks", "name", "../outside"),
        ("hooks", "name", "."),
        ("hooks", "name", ".."),
        ("rules", "relative_path", "../outside.md"),
        ("rules", "relative_path", "."),
    ],
)
def test_apply_rejects_unsafe_copy_lock_identities(
    workspace,
    run_cli_with_homes,
    section,
    identity_key,
    identity_value,
):
    """Lock identities cannot escape their current source or target roots."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _setup_empty_copy_config(project, codex_home, codexmgr_home, run_cli_with_homes)
    write_toml_file(
        project / ".codex" / "codexmgr.lock",
        {
            section: {
                "copies": [
                    {
                        identity_key: identity_value,
                        "source": "/legacy/source",
                        "target": "/legacy/target",
                    },
                ],
            },
        },
    )

    exit_code, stdout, stderr = run_cli_with_homes(
        ["apply"],
        project,
        codex_home,
        codexmgr_home,
    )

    assert exit_code == 1
    assert stdout == ""
    assert f"codexmgr.lock {section}.copies entries must use a safe" in stderr


def _setup_managed_project(
    project: Path,
    codex_home: Path,
    codexmgr_home: Path,
    run_cli_with_homes,
) -> None:
    """Configure and apply all managed-copy resource families.

    Args:
        project: Project root receiving managed copies.
        codex_home: Codex home passed to the CLI.
        codexmgr_home: Manager home containing reusable sources.
        run_cli_with_homes: Test CLI helper fixture.
    """
    _setup_project_config(project, codex_home, codexmgr_home, run_cli_with_homes)
    exit_code, _, stderr = run_cli_with_homes(
        ["apply"],
        project,
        codex_home,
        codexmgr_home,
    )
    assert exit_code == 0, stderr


def _setup_project_config(
    project: Path,
    codex_home: Path,
    codexmgr_home: Path,
    run_cli_with_homes,
) -> None:
    """Initialize a project with every managed-copy family enabled.

    Args:
        project: Project root to initialize.
        codex_home: Codex home passed to the CLI.
        codexmgr_home: Manager home passed to the CLI.
        run_cli_with_homes: Test CLI helper fixture.
    """
    exit_code, _, stderr = run_cli_with_homes(
        ["setup"],
        project,
        codex_home,
        codexmgr_home,
    )
    assert exit_code == 0, stderr
    write_toml_file(
        project / ".codex" / "codexmgr.toml",
        {
            "agents": {"enabled": ["reviewer"], "disabled": []},
            "hooks": {"enabled": ["audit"], "disabled": []},
            "rules": {"enabled": ["python/testing.md"], "disabled": []},
        },
    )


def _setup_empty_copy_config(
    project: Path,
    codex_home: Path,
    codexmgr_home: Path,
    run_cli_with_homes,
) -> None:
    """Initialize a project with empty managed-copy sections.

    Args:
        project: Project root to initialize.
        codex_home: Codex home passed to the CLI.
        codexmgr_home: Manager home passed to the CLI.
        run_cli_with_homes: Test CLI helper fixture.
    """
    exit_code, _, stderr = run_cli_with_homes(
        ["setup"],
        project,
        codex_home,
        codexmgr_home,
    )
    assert exit_code == 0, stderr
    write_toml_file(
        project / ".codex" / "codexmgr.toml",
        {
            "agents": {"enabled": [], "disabled": []},
            "hooks": {"enabled": [], "disabled": []},
            "rules": {"enabled": [], "disabled": []},
        },
    )


def _write_managed_sources(codexmgr_home: Path) -> None:
    """Create representative agent, hook, and rule sources.

    Args:
        codexmgr_home: Manager home where reusable sources are written.
    """
    agent = codexmgr_home / "agents" / "reviewer.toml"
    agent.parent.mkdir(parents=True)
    agent.write_text('name = "reviewer"\n', encoding="utf-8")

    hook_dir = codexmgr_home / "hooks" / "audit"
    hook_dir.mkdir(parents=True)
    (hook_dir / "hooks.json").write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {"type": "command", "command": "python audit.py"},
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
    (hook_dir / "audit.py").write_text('print("audit")\n', encoding="utf-8")

    rule = codexmgr_home / "rules" / "python" / "testing.md"
    rule.parent.mkdir(parents=True)
    rule.write_text("# Testing\n", encoding="utf-8")


def _legacy_lock(old_project: Path, old_home: Path) -> dict:
    """Build legacy absolute lock metadata for all copy families.

    Args:
        old_project: Historical project root embedded in target paths.
        old_home: Historical manager-home root embedded in source paths.

    Returns:
        Parsed TOML data using the legacy absolute-path shape.
    """
    return {
        "agents": {
            "copies": [
                {
                    "name": "reviewer",
                    "source": str(old_home / "agents" / "reviewer.toml"),
                    "target": str(old_project / ".codex" / "agents" / "reviewer.toml"),
                },
            ],
        },
        "hooks": {
            "copies": [
                {
                    "name": "audit",
                    "source": str(old_home / "hooks" / "audit"),
                    "target": str(old_project / ".codex" / "hooks" / "audit"),
                },
            ],
        },
        "rules": {
            "copies": [
                {
                    "relative_path": "python/testing.md",
                    "source": str(old_home / "rules" / "python" / "testing.md"),
                    "target": str(old_project / ".rules" / "python" / "testing.md"),
                },
            ],
        },
    }


def _write_copy_targets(project: Path) -> list[Path]:
    """Write representative managed targets below one project root.

    Args:
        project: Project root receiving target files.

    Returns:
        Target paths whose existence can be asserted after cleanup.
    """
    agent = project / ".codex" / "agents" / "reviewer.toml"
    hook_file = project / ".codex" / "hooks" / "audit" / "audit.py"
    rule = project / ".rules" / "python" / "testing.md"
    for path in (agent, hook_file, rule):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("managed\n", encoding="utf-8")
    return [agent, hook_file.parent, rule]
