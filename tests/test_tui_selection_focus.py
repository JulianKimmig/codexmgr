"""Regression tests for preserving TUI focus across state cycles."""

from pathlib import Path

import pytest
from textual.widgets import SelectionList, Tree

from codexmgr.tui.app import CodexMgrTui
from codexmgr.tui.models import ManagedItem


@pytest.mark.asyncio
async def test_tui_cycle_keeps_selection_list_highlighted_item(
    workspace,
    run_cli_with_homes,
):
    """Cycling a list row keeps focus on the same resource after refresh."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_skill(codexmgr_home, "alpha")
    _write_skill(codexmgr_home, "beta")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    app = CodexMgrTui(
        cwd=project,
        codex_home=codex_home,
        codexmgr_home=codexmgr_home,
        no_sync=True,
        show_diff=False,
    )

    async with app.run_test() as pilot:
        await pilot.press("3")
        await pilot.press("down")
        await pilot.press("space")
        await pilot.pause()
        items = app.query_one("#items", SelectionList)

    assert items.highlighted_option is not None
    assert items.highlighted_option.value == "beta"


@pytest.mark.asyncio
async def test_tui_cycle_keeps_rule_tree_highlighted_item(
    workspace,
    run_cli_with_homes,
):
    """Cycling a rule tree node keeps focus on the same rule after refresh."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_rule(codexmgr_home, "alpha.md")
    _write_rule(codexmgr_home, "beta.md")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    app = CodexMgrTui(
        cwd=project,
        codex_home=codex_home,
        codexmgr_home=codexmgr_home,
        no_sync=True,
        show_diff=False,
    )

    async with app.run_test() as pilot:
        await pilot.press("6")
        await pilot.pause()
        tree = app.query_one("#rule-tree", Tree)
        tree.select_node(tree.root.children[1])
        await pilot.press("space")
        await pilot.pause()
        item = tree.cursor_node.data

    assert isinstance(item, ManagedItem)
    assert item.selection_value() == "beta.md"


@pytest.mark.asyncio
async def test_tui_cycle_keeps_nested_rule_tree_highlighted_item(
    workspace,
    run_cli_with_homes,
):
    """Cycling a nested rule tree node keeps focus on the same rule."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_rule(codexmgr_home, "react/components.md")
    _write_rule(codexmgr_home, "react/materials/colors.md")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    app = CodexMgrTui(
        cwd=project,
        codex_home=codex_home,
        codexmgr_home=codexmgr_home,
        no_sync=True,
        show_diff=False,
    )

    async with app.run_test() as pilot:
        await pilot.press("6")
        await pilot.pause()
        tree = app.query_one("#rule-tree", Tree)
        react_node = tree.root.children[0]
        materials_node = react_node.children[1]
        colors_node = materials_node.children[0]
        react_node.expand()
        materials_node.expand()
        await pilot.pause()
        tree.move_cursor_to_line(colors_node.line)
        await pilot.press("space")
        await pilot.pause()
        item = tree.cursor_node.data

    assert isinstance(item, ManagedItem)
    assert item.selection_value() == "react/materials/colors.md"


def _write_skill(home: Path, name: str) -> Path:
    """Create a reusable skill in a codexmgr home directory.

    Args:
        home: Codexmgr home directory.
        name: Skill directory name.

    Returns:
        Path to the created skill file.
    """
    skill_dir = home / "skills" / name
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(
        f"---\nname: {name}\ndescription: Test skill.\n---\n\n# Skill\n",
        encoding="utf-8",
    )
    return skill_file


def _write_rule(home: Path, relative_path: str) -> Path:
    """Create a reusable rule file in a codexmgr home directory.

    Args:
        home: Codexmgr home directory.
        relative_path: POSIX path below the reusable rules root.

    Returns:
        Path to the created rule file.
    """
    path = home / "rules" / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Rule\n", encoding="utf-8")
    return path
