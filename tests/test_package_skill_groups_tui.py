"""Staged and headless package-group selection, state, and save behavior."""

from copy import deepcopy

import pytest

from codexmgr.core.errors import CommandError
from codexmgr.tui.app import CodexMgrTui
from codexmgr.tui.state import load_staged_config
from test_package_skill_groups import prepare_group, write_package


def test_staged_package_states_follow_group_leaves(workspace, run_cli_with_homes):
    """Group-based packages reflect individual overrides and clear all descendants."""
    project, codex, manager = prepare_group(workspace, run_cli_with_homes)
    staged = load_staged_config(project, codex, manager)
    assert staged.package_state("phaser") == "available"
    staged.set_package_enabled("phaser", True)
    assert staged.package_state("phaser") == "enabled"
    staged.set_skill_enabled("phaserjs/audio", False)
    assert staged.package_state("phaser") == "partial"
    staged.set_package_enabled("phaser", False)
    assert staged.package_state("phaser") == "disabled"
    staged.set_package_available("phaser")
    assert staged.config["skills"] == {"enabled": [], "disabled": []}
    assert staged.package_state("phaser") == "available"


def test_profile_group_lifecycle_preserves_root_and_recognizes_bare_alias(workspace, run_cli_with_homes):
    """Profiles enable, disable and clear grouped skills independently of root entries."""
    project, codex, manager = prepare_group(workspace, run_cli_with_homes)
    write_package(manager, 'skills = ["base"]\n[profiles.full]\nskills = ["phaserjs/"]\n')
    staged = load_staged_config(project, codex, manager)
    staged.set_package_enabled("phaser", True)
    staged.set_skill_enabled("audio", True)
    assert staged.package_profile_state("phaser", "full") == "partial"
    staged.set_package_profile_enabled("phaser", "full", True)
    assert staged.package_profile_state("phaser", "full") == "enabled"
    staged.set_package_profile_enabled("phaser", "full", False)
    assert staged.package_profile_state("phaser", "full") == "disabled"
    staged.set_package_profile_available("phaser", "full")
    assert staged.config["skills"] == {"enabled": ["base"], "disabled": []}
    assert staged.package_profile_state("phaser", "full") == "available"


@pytest.mark.parametrize("operation", ["enable", "disable", "clear"])
def test_invalid_group_does_not_partially_mutate_staged_package(operation, workspace, run_cli_with_homes):
    """Group validation precedes unrelated staged package mutations."""
    project, codex, manager = prepare_group(workspace, run_cli_with_homes)
    template = manager / "agentsmd" / "base.toml"
    template.parent.mkdir()
    template.write_text('[coding]\ntext = "hello"\n')
    write_package(manager, 'agentsmd = ["base"]\nskills = ["missing/"]\n')
    staged = load_staged_config(project, codex, manager)
    before = deepcopy(staged.config)
    with pytest.raises(CommandError, match="Skill group not found"):
        if operation == "clear":
            staged.set_package_available("phaser")
        else:
            staged.set_package_enabled("phaser", operation == "enable")
    assert staged.config == before


@pytest.mark.asyncio
async def test_tui_package_group_saves_and_applies(workspace, run_cli_with_homes, read_project_config):
    """Selecting the package in the real TUI saves leaf refs and copies their skills."""
    project, codex, manager = prepare_group(workspace, run_cli_with_homes)
    app = CodexMgrTui(cwd=project, codex_home=codex, codexmgr_home=manager, no_sync=False, show_diff=False)
    async with app.run_test() as pilot:
        await pilot.press("7", "space")
        assert app.staged.package_state("phaser") == "enabled"
        await pilot.press("s")
    assert read_project_config(project)["skills"]["enabled"] == ["phaserjs/audio", "phaserjs/physics/arcade"]
    assert (project / ".agents" / "skills" / "audio" / "SKILL.md").is_file()
    assert (project / ".agents" / "skills" / "arcade" / "SKILL.md").is_file()
