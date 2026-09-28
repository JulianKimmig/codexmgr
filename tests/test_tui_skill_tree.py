"""Headless skill-tree navigation, group selection, and state persistence tests."""

import pytest
from textual.widgets import Tree

from codexmgr.tui.app import CodexMgrTui
from test_nested_skills_cli import write_skill


def make_app(workspace, run_cli_with_homes, *, references=None):
    """Create a real staged app with grouped sources; return the unsynced TUI."""
    project, codex = workspace
    manager = project.parent / "manager"
    for reference in references or ["set/one", "set/sub/two", "z-other/three"]:
        write_skill(manager, reference, reference.replace("/", "-"))
    run_cli_with_homes(["setup"], project, codex, manager)
    return CodexMgrTui(
        cwd=project, codex_home=codex, codexmgr_home=manager,
        no_sync=True, show_diff=False,
    )


@pytest.mark.asyncio
async def test_skill_groups_start_collapsed_and_expand_without_selection(workspace, run_cli_with_homes):
    """Folder entry reveals short child labels without changing staged config."""
    app = make_app(workspace, run_cli_with_homes)
    async with app.run_test() as pilot:
        await pilot.press("3")
        tree = app.query_one("#skill-tree", Tree)
        group = tree.root.children[0]
        assert group.data.selection_value() == "set/"
        assert not group.is_expanded
        await pilot.press("enter")
        assert group.is_expanded
        assert str(group.children[0].label).startswith("one ")
        assert group.children[1].data.selection_value() == "set/sub/"
        assert not app.staged.dirty()


@pytest.mark.asyncio
async def test_group_cycle_and_individual_override_preserve_focus_and_expansion(
    workspace, run_cli_with_homes, read_project_config,
):
    """A selected folder can be opened and a child disabled, yielding mixed state."""
    app = make_app(workspace, run_cli_with_homes)
    async with app.run_test() as pilot:
        await pilot.press("3", "space")
        tree = app.query_one("#skill-tree", Tree)
        assert app.staged.config["skills"]["enabled"] == ["set/one", "set/sub/two"]
        assert tree.cursor_node.data.selection_value() == "set/"
        assert not tree.root.children[0].is_expanded
        await pilot.press("enter", "down", "space")
        assert tree.cursor_node.data.selection_value() == "set/one"
        assert tree.root.children[0].data.state == "mixed"
        assert tree.root.children[0].is_expanded
        await pilot.press("1", "3")
        assert tree.root.children[0].is_expanded
        tree.select_node(tree.root.children[0])
        await pilot.press("space")
        assert tree.root.children[0].data.state == "enabled"
        await pilot.press("space")
        assert tree.root.children[0].data.state == "disabled"
        await pilot.press("space", "s")

    assert read_project_config(app.cwd)["skills"] == {"enabled": [], "disabled": []}


@pytest.mark.asyncio
async def test_subgroup_selection_saves_only_its_descendants(workspace, run_cli_with_homes, read_project_config):
    """Selecting an inner folder leaves siblings unchanged and persists its leaves."""
    app = make_app(workspace, run_cli_with_homes)
    async with app.run_test() as pilot:
        await pilot.press("3", "enter", "down", "down", "space", "s")
        tree = app.query_one("#skill-tree", Tree)
        assert tree.cursor_node.data.selection_value() == "set/sub/"
        assert tree.root.children[0].data.state == "mixed"
    assert read_project_config(app.cwd)["skills"] == {
        "enabled": ["set/sub/two"], "disabled": [],
    }


@pytest.mark.asyncio
async def test_tree_normalizes_existing_bare_alias_without_duplicate_rows(workspace, run_cli_with_homes):
    """A configured bare alias is represented once under its discovered source group."""
    app = make_app(workspace, run_cli_with_homes, references=["set/one"])
    run_cli_with_homes(["skill", "enable", "--no-sync", "one"], app.cwd, app.codex_home, app.codexmgr_home)
    async with app.run_test() as pilot:
        await pilot.press("r", "3")
        tree = app.query_one("#skill-tree", Tree)
        assert len(tree.root.children) == 1
        assert tree.root.children[0].data.state == "enabled"
        await pilot.press("space")
        assert app.staged.config["skills"] == {"enabled": [], "disabled": ["set/one"]}


@pytest.mark.asyncio
async def test_explicit_paths_and_missing_references_stay_selectable(workspace, run_cli_with_homes):
    """Explicit paths remain standalone rows; missing grouped leaves can be cleared."""
    app = make_app(workspace, run_cli_with_homes)
    explicit = str(app.codexmgr_home / "skills" / "set" / "one")
    app.staged.set_skill_enabled(explicit, True)
    app.staged.set_skill_enabled("missing/old", False)
    async with app.run_test() as pilot:
        await pilot.press("3")
        tree = app.query_one("#skill-tree", Tree)
        assert any(node.data.selection_value() == explicit for node in tree.root.children)
        group = next(node for node in tree.root.children if node.data.selection_value() == "missing/")
        assert group.children[0].data.missing
        tree.select_node(group)
        await pilot.press("space")
        assert "missing/old" not in app.staged.config["skills"]["disabled"]


@pytest.mark.asyncio
async def test_empty_skill_tree_can_be_opened_and_cycled(workspace, run_cli_with_homes):
    """An empty store keeps the Skills screen navigable without changing config."""
    project, codex = workspace
    manager = project.parent / "manager"
    run_cli_with_homes(["setup"], project, codex, manager)
    app = CodexMgrTui(
        cwd=project, codex_home=codex, codexmgr_home=manager,
        no_sync=True, show_diff=False,
    )
    async with app.run_test() as pilot:
        await pilot.press("3", "space", "enter", "1", "3")
        assert not app.query_one("#skill-tree", Tree).root.children
        assert not app.staged.dirty()
