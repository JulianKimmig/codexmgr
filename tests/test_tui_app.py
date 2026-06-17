"""Headless interaction tests for the Textual codexmgr TUI."""

import pytest

from codexmgr.tui.app import CodexMgrTui


@pytest.mark.asyncio
async def test_tui_app_toggles_skill_and_saves_without_sync(
    workspace,
    run_cli_with_homes,
    read_project_config,
):
    """The Skills screen lets users select a skill and save staged changes."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_skill(codexmgr_home, "review")
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
        await pilot.press("space")
        await pilot.press("s")
        await pilot.pause()

    assert read_project_config(project)["skills"] == {
        "enabled": ["review"],
        "disabled": [],
    }
    assert not (project / ".agents" / "skills" / "review").exists()


@pytest.mark.asyncio
async def test_tui_app_does_not_rebuild_skill_list_on_toggle(
    workspace,
    run_cli_with_homes,
    monkeypatch,
):
    """Toggling a skill updates staged state without rescanning the list."""
    project, codex_home = workspace
    codexmgr_home = codex_home.parent / "codexmgr-home"
    _write_skill(codexmgr_home, "review")
    run_cli_with_homes(["setup"], project, codex_home, codexmgr_home)
    calls = {"count": 0}

    from codexmgr.tui import app as tui_app

    original_skill_items = tui_app.skill_items

    def counted_skill_items(staged):
        calls["count"] += 1
        return original_skill_items(staged)

    monkeypatch.setattr(tui_app, "skill_items", counted_skill_items)
    app = CodexMgrTui(
        cwd=project,
        codex_home=codex_home,
        codexmgr_home=codexmgr_home,
        no_sync=True,
        show_diff=False,
    )

    async with app.run_test() as pilot:
        await pilot.press("3")
        await pilot.pause()
        assert calls["count"] == 1
        await pilot.press("space")
        await pilot.pause()
        assert calls["count"] == 1


def _write_skill(home, name):
    """Create a codexmgr-home skill for tests.

    Args:
        home: Codexmgr home directory.
        name: Skill directory name.

    Returns:
        Path to the created SKILL.md file.
    """
    skill_dir = home / "skills" / name
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text("# Skill\n", encoding="utf-8")
    return skill_file
