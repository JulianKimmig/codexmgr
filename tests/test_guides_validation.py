"""Guide validation at config, lock, filesystem, and staged-interface boundaries."""

import os

import pytest

from codexmgr.core.toml_io import write_toml_file
from codexmgr.tui.sections import items_for_section, set_section_selected
from codexmgr.tui.state import load_staged_config
from test_guides_cli import guides


@pytest.mark.parametrize("value", ["invalid", {"enabled": "games/"}, {"disabled": [1]}])
def test_malformed_config_fails_before_copying(guides, value):
    """Configuration type errors surface as command errors without guide writes."""
    project, _, _, cli = guides
    write_toml_file(project / ".codex/codexmgr.toml", {"guides": value})
    assert cli("apply")[0] == 1
    assert not (project / ".guides").exists()


@pytest.mark.parametrize("value", ["invalid", {"copies": "invalid"}, {"copies": [1]}, {"copies": [{}]}])
def test_malformed_lock_fails_before_copying(guides, value):
    """All portable-copy lock fields are validated before applying ownership."""
    project, _, _, cli = guides
    assert cli("guides", "enable", "--no-sync", "games")[0] == 0
    write_toml_file(project / ".codex/codexmgr.lock", {"guides": value})
    assert cli("apply")[0] == 1
    assert not (project / ".guides").exists()


@pytest.mark.parametrize("kind", ["root-file", "ancestor-file", "target-directory"])
def test_wrong_target_types_fail_during_preflight(guides, kind):
    """File/directory obstructions fail before unrelated selected files are copied."""
    project, _, _, cli = guides
    root = project / ".guides"
    if kind == "root-file":
        root.write_bytes(b"mine")
    elif kind == "ancestor-file":
        (root / "games/general").mkdir(parents=True)
        (root / "games/general/monetization").write_bytes(b"mine")
    else:
        (root / "games/general/monetization/intro.md").mkdir(parents=True)
    result = cli("guides", "enable", "games")
    assert result[0] == 1
    assert not (root / "games/general/frameworks/intro.md").exists()


def test_repeated_enable_is_byte_stable(guides):
    """Repeated canonical selections keep config and lock contents unchanged."""
    project, _, _, cli = guides
    assert cli("guides", "enable", "games", "games/")[0] == 0
    paths = [project / ".codex" / name for name in ("codexmgr.toml", "codexmgr.lock")]
    before = [path.read_bytes() for path in paths]
    assert cli("guides", "enable", "games/")[0] == 0
    assert [path.read_bytes() for path in paths] == before


def test_missing_owned_target_can_be_disabled(guides):
    """An already-removed project copy does not block managed cleanup."""
    project, _, _, cli = guides
    assert cli("guides", "enable", "games")[0] == 0
    (project / ".guides/games/general/monetization/intro.md").unlink()
    assert cli("guides", "disable", "games")[0] == 0
    assert not (project / ".guides").exists()


def test_special_source_files_are_rejected_without_reading(guides):
    """FIFO descendants produce errors instead of blocking on a file read."""
    _, _, manager, cli = guides
    os.mkfifo(manager / "guides/games/pipe")
    assert cli("guides", "enable", "games")[0] == 1


def test_empty_listing_and_staged_checkbox_semantics(workspace, run_cli_with_homes):
    """Empty stores list cleanly, and checkbox clear uses original selector state."""
    project, codex = workspace
    manager = project.parent / "manager"
    assert run_cli_with_homes(["setup"], project, codex, manager)[0] == 0
    assert run_cli_with_homes(["guides", "list"], project, codex, manager) == (0, "", "")
    staged = load_staged_config(project, codex, manager)
    set_section_selected(staged, "guides", "unknown/", False)
    assert "guides" not in staged.config


def test_staged_file_selection_clears_new_and_disables_original(guides):
    """Checkbox entrypoints share canonical selectors with CLI and tree dispatch."""
    project, codex, manager, cli = guides
    staged = load_staged_config(project, codex, manager)
    set_section_selected(staged, "guides", "games", True)
    items, warning = items_for_section(staged, "guides")
    assert not warning
    assert next(item for item in items if item.name == "games/").state == "enabled"
    set_section_selected(staged, "guides", "games/", False)
    assert staged.config["guides"] == {"enabled": [], "disabled": []}
    assert cli("guides", "enable", "--no-sync", "games")[0] == 0
    staged = load_staged_config(project, codex, manager)
    set_section_selected(staged, "guides", "games/", False)
    assert staged.config["guides"] == {"enabled": [], "disabled": ["games/"]}


def test_removing_last_resource_clears_lock_ownership(guides, read_lock):
    """Removing the final resource table clears lock state as well as its copies."""
    project, _, _, cli = guides
    assert cli("guides", "enable", "games")[0] == 0
    write_toml_file(project / ".codex/codexmgr.toml", {})
    assert cli("apply")[0] == 0
    assert read_lock(project) == {}
    assert cli("apply", "--check")[0] == 0
