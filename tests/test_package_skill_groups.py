"""Package group expansion across CLI, profiles, stores, and launch overlays."""

from copy import deepcopy
from pathlib import Path

import pytest

from codexmgr.commands.codex_jit import CodexJitRequest, build_jit_project_state
from codexmgr.core.toml_io import write_toml_file
from test_nested_skills_cli import write_skill


def write_package(manager: Path, content: str, name: str = "phaser") -> Path:
    """Write package TOML under manager/packages/name and return its path."""
    file = manager / "packages" / name / "config.toml"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(content, encoding="utf-8")
    return file


def prepare_group(workspace, run_cli_with_homes):
    """Create an isolated Phaser-style package; return project and both stores."""
    project, codex = workspace
    manager = project.parent / "manager"
    write_skill(manager, "phaserjs/audio", "audio")
    write_skill(manager, "phaserjs/physics/arcade", "arcade")
    write_package(manager, 'skills = ["phaserjs/"]\n')
    assert run_cli_with_homes(["setup"], project, codex, manager)[0] == 0
    return project, codex, manager


def test_package_group_enable_disable_and_repeated_enable(
    workspace, run_cli_with_homes, read_project_config, read_lock,
):
    """Packages store leaf references, copy them flat, and remove only owned copies."""
    project, codex, manager = prepare_group(workspace, run_cli_with_homes)
    result = run_cli_with_homes(["package", "enable", "phaser"], project, codex, manager)
    assert result[0] == 0, result[2]
    refs = ["phaserjs/audio", "phaserjs/physics/arcade"]
    assert read_project_config(project)["skills"] == {"enabled": refs, "disabled": []}
    assert {copy["source_path"] for copy in read_lock(project)["skills"]["copies"]} == set(refs)
    before = (project / ".codex" / "codexmgr.toml").read_bytes()
    assert run_cli_with_homes(["package", "enable", "phaser"], project, codex, manager)[0] == 0
    assert (project / ".codex" / "codexmgr.toml").read_bytes() == before
    assert run_cli_with_homes(["package", "disable", "phaser"], project, codex, manager)[0] == 0
    assert read_project_config(project)["skills"] == {"enabled": [], "disabled": refs}
    for name in ("audio", "arcade"):
        assert not (project / ".agents" / "skills" / name).exists()
    assert (manager / "skills" / "phaserjs" / "audio" / "SKILL.md").exists()


def test_profiles_expand_groups_and_deduplicate_overlaps(workspace, run_cli_with_homes, read_project_config):
    """Root references, group descendants, aliases, and repeated profiles merge once."""
    project, codex, manager = prepare_group(workspace, run_cli_with_homes)
    write_package(manager, 'skills = ["phaserjs/audio"]\n[profiles.full]\nskills = ["phaserjs/", "audio"]\n')
    for command in ("enable", "disable"):
        result = run_cli_with_homes(
            ["package", command, "phaser", "--profile", "full"], project, codex, manager,
        )
        assert result[0] == 0, result[2]
        assert read_project_config(project)["skills"][f"{command}d"] == [
            "phaserjs/audio", "phaserjs/physics/arcade",
        ]


def test_package_group_no_sync_and_new_descendants(workspace, run_cli_with_homes, read_project_config):
    """No-sync writes expanded state only; later activation discovers added skills."""
    project, codex, manager = prepare_group(workspace, run_cli_with_homes)
    result = run_cli_with_homes(["package", "enable", "--no-sync", "phaser"], project, codex, manager)
    assert result[0] == 0, result[2]
    assert not (project / ".agents" / "skills").exists()
    write_skill(manager, "phaserjs/scenes", "scenes")
    assert "phaserjs/scenes" not in read_project_config(project)["skills"]["enabled"]
    assert run_cli_with_homes(["package", "enable", "--no-sync", "phaser"], project, codex, manager)[0] == 0
    assert "phaserjs/scenes" in read_project_config(project)["skills"]["enabled"]


@pytest.mark.parametrize("command", ["enable", "disable"])
def test_invalid_package_group_preserves_config(command, workspace, run_cli_with_homes):
    """An invalid second package cannot partially persist the first package's changes."""
    project, codex, manager = prepare_group(workspace, run_cli_with_homes)
    write_package(manager, 'skills = ["unknown/"]\n', "invalid")
    config = project / ".codex" / "codexmgr.toml"
    before = config.read_bytes()
    result = run_cli_with_homes(
        ["package", command, "--no-sync", "phaser", "invalid"], project, codex, manager,
    )
    assert result[0] == 1
    assert "Skill group not found: unknown/" in result[2]
    assert config.read_bytes() == before


def test_package_group_uses_actual_project_and_codex_stores(workspace, run_cli_with_homes, read_project_config):
    """Group expansion includes the caller's Codex store and project-local sources."""
    project, codex, manager = prepare_group(workspace, run_cli_with_homes)
    write_skill(codex, "phaserjs/from-codex", "from-codex")
    write_skill(project / ".agents", "phaserjs/from-project", "from-project")
    result = run_cli_with_homes(["package", "enable", "phaser"], project, codex, manager)
    assert result[0] == 0, result[2]
    assert len(read_project_config(project)["skills"]["enabled"]) == 4


def test_package_enable_repairs_group_token_left_by_old_failure(workspace, run_cli_with_homes, read_project_config):
    """Re-enabling replaces the literal group token previously saved by broken activation."""
    project, codex, manager = prepare_group(workspace, run_cli_with_homes)
    write_toml_file(project / ".codex" / "codexmgr.toml", {"skills": {"enabled": ["phaserjs/"]}})
    result = run_cli_with_homes(["package", "enable", "phaser"], project, codex, manager)
    assert result[0] == 0, result[2]
    assert read_project_config(project)["skills"]["enabled"] == ["phaserjs/audio", "phaserjs/physics/arcade"]


def test_jit_package_groups_expand_without_mutating_base(workspace, run_cli_with_homes):
    """The temporary launch overlay resolves group copies without persisting package state."""
    project, codex, manager = prepare_group(workspace, run_cli_with_homes)
    base = {"skills": {"enabled": [], "disabled": []}}
    before = deepcopy(base)
    state = build_jit_project_state(base, CodexJitRequest(True, ["phaser"], [], []), project, codex, manager)
    assert base == before
    assert {copy.source_path for copy in state.skill_copies} == {"phaserjs/audio", "phaserjs/physics/arcade"}
    assert not (project / ".agents" / "skills").exists()
