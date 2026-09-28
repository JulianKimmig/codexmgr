"""Real TUI save prompts for newly authored rules and guides."""

import pytest
from textual.widgets import Button, Static

from codexmgr.tui.app import CodexMgrTui
from test_local_imports import local_document


@pytest.mark.asyncio
@pytest.mark.parametrize("choice", ["u", "k", "a"])
async def test_tui_save_offers_new_file_decisions(local_document, choice, read_lock):
    """TUI save requires explicit publishing and remembers project-only choices."""
    project, codex, manager, family, target, _ = local_document
    before = (project / ".codex/codexmgr.toml").read_bytes()
    app = CodexMgrTui(cwd=project, codex_home=codex, codexmgr_home=manager, no_sync=False, show_diff=True)
    async with app.run_test() as pilot:
        await pilot.press("s")
        assert app.screen.__class__.__name__ == "CopyConflictScreen"
        assert "shared" in str(app.screen.query_one("#copy-conflict-detail", Static).render())
        assert app.screen.query_one("#overwrite-local", Button).disabled
        await pilot.press("o")
        assert app.screen.__class__.__name__ == "CopyConflictScreen"
        await pilot.press(choice)
        assert app.screen.__class__.__name__ != "CopyConflictScreen"
        if choice == "k":
            await pilot.press("s")
            assert app.screen.__class__.__name__ != "CopyConflictScreen"
    assert target.exists()
    assert (manager / family / "games/new/deep.md").exists() == (choice == "u")
    if choice == "a":
        assert (project / ".codex/codexmgr.toml").read_bytes() == before
    if choice == "k":
        assert read_lock(project)[family]["project_only"] == ["games/new/deep.md"]


@pytest.mark.asyncio
async def test_no_sync_tui_save_does_not_prompt(local_document):
    """Saving selections without applying never publishes local documents."""
    project, codex, manager, family, _, _ = local_document
    app = CodexMgrTui(cwd=project, codex_home=codex, codexmgr_home=manager, no_sync=True, show_diff=False)
    async with app.run_test() as pilot:
        await pilot.press("s")
        assert app.screen.__class__.__name__ != "CopyConflictScreen"
    assert not (manager / family / "games/new/deep.md").exists()
