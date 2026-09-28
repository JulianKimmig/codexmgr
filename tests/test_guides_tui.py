"""Guide tree navigation, staged selections, preview, and persistence."""

import pytest
from textual.widgets import Tree, Static

from codexmgr.tui.app import CodexMgrTui
from test_guides_cli import guides
from test_package_skill_groups import write_package


@pytest.mark.asyncio
async def test_guide_tree_folder_and_file_selection_save(guides, read_project_config):
    """Nested folders remain navigable while parent selections and exclusions persist."""
    project, codex, manager, _ = guides
    app = CodexMgrTui(cwd=project, codex_home=codex, codexmgr_home=manager, no_sync=False, show_diff=True)
    async with app.run_test() as pilot:
        await pilot.press("9")
        tree = app.query_one("#guide-tree", Tree)
        assert not tree.root.children[0].is_expanded
        await pilot.press("space", "enter", "down", "enter", "down")
        assert tree.cursor_node.data.selection_value() == "games/general/frameworks/"
        await pilot.press("space", "space")
        assert tree.cursor_node.data.state == "disabled"
        assert tree.cursor_node.data.selection_value() == "games/general/frameworks/"
        await pilot.press("1", "9")
        assert tree.root.children[0].is_expanded
        assert tree.cursor_node.data.selection_value() == "games/general/frameworks/"
        assert app.staged.config["guides"] == {"enabled": ["games/"], "disabled": ["games/general/frameworks/"]}
        await pilot.press("s")
    assert read_project_config(project)["guides"]["enabled"] == ["games/"]
    assert (project / ".guides/games/general/monetization/intro.md").exists()
    assert not (project / ".guides/games/general/frameworks").exists()


@pytest.mark.asyncio
async def test_guide_leaf_cycle_and_no_sync(guides, read_project_config):
    """Leaf selections cycle independently and no-sync does not copy documents."""
    project, codex, manager, _ = guides
    app = CodexMgrTui(cwd=project, codex_home=codex, codexmgr_home=manager, no_sync=True, show_diff=False)
    async with app.run_test() as pilot:
        await pilot.press("9", "down", "enter", "down", "space")
        tree = app.query_one("#guide-tree", Tree)
        assert tree.cursor_node.data.selection_value() == "other/readme.txt"
        assert tree.cursor_node.data.state == "enabled"
        await pilot.press("space", "space")
        assert tree.cursor_node.data.state == "available"
        await pilot.press("space", "s")
    assert read_project_config(project)["guides"]["enabled"] == ["other/readme.txt"]
    assert not (project / ".guides").exists()


@pytest.mark.asyncio
async def test_empty_and_missing_guides_tree(workspace, run_cli_with_homes):
    """Empty trees and nested missing exclusions stay navigable and clearable."""
    project, codex = workspace
    manager = project.parent / "manager"
    assert run_cli_with_homes(["setup"], project, codex, manager)[0] == 0
    app = CodexMgrTui(cwd=project, codex_home=codex, codexmgr_home=manager, no_sync=True, show_diff=False)
    async with app.run_test() as pilot:
        await pilot.press("9", "space", "enter")
        assert not app.staged.dirty()
        app.staged.set_guide_enabled("missing/deep/file.md", False)
        app.action_section("guides")
        tree = app.query_one("#guide-tree", Tree)
        leaf = tree.root.children[0].children[0].children[0]
        assert leaf.data.missing
        tree.select_node(leaf)
        await pilot.press("space")
        assert app.staged.config["guides"] == {"enabled": [], "disabled": []}


@pytest.mark.asyncio
async def test_package_guides_save_from_tui(guides):
    """Real package selection applies guide copies through the normal save flow."""
    project, codex, manager, _ = guides
    write_package(manager, 'guides = ["games/"]\n')
    app = CodexMgrTui(cwd=project, codex_home=codex, codexmgr_home=manager, no_sync=False, show_diff=False)
    async with app.run_test() as pilot:
        await pilot.press("7", "space")
        assert app.staged.package_state("phaser") == "enabled"
        await pilot.press("s")
    assert (project / ".guides/games/general/frameworks/intro.md").exists()


@pytest.mark.asyncio
async def test_unsafe_guide_discovery_reports_error_without_crashing(guides):
    """Invalid source discovery leaves the TUI usable for other resource sections."""
    project, codex, manager, _ = guides
    (manager / "guides/games/loop").symlink_to(manager / "guides/games", target_is_directory=True)
    app = CodexMgrTui(cwd=project, codex_home=codex, codexmgr_home=manager, no_sync=True, show_diff=False)
    async with app.run_test() as pilot:
        await pilot.press("9")
        assert "symlink" in str(app.query_one("#detail", Static).render())
        await pilot.press("1")
        assert app.section == "dashboard"
