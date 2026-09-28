"""Guide copy safety, validation, conflict handling, and portable ownership."""

import shutil

import pytest

from codexmgr.core.toml_io import write_toml_file
from test_guides_cli import guides, write_guide


@pytest.mark.parametrize("ref", ["", ".", "../escape", "/absolute", "games/../other", "games\\bad", "games//bad", "./games"])
@pytest.mark.parametrize("operation", ["enable", "disable"])
def test_invalid_reference_leaves_config_unchanged(guides, ref, operation):
    """Unsafe references fail before a valid earlier batch item is persisted."""
    project, _, _, cli = guides
    config = project / ".codex/codexmgr.toml"
    before = config.read_bytes()
    assert cli("guides", operation, "--no-sync", "games", ref)[0] == 1
    assert config.read_bytes() == before


def test_missing_enable_is_atomic(guides):
    """Missing sources reject the entire batch without persisting valid siblings."""
    project, _, _, cli = guides
    config = project / ".codex/codexmgr.toml"
    before = config.read_bytes()
    assert cli("guides", "enable", "games", "missing/")[0] == 1
    assert config.read_bytes() == before


def test_unmanaged_target_is_not_overwritten(guides):
    """An existing project document cannot silently become a managed copy."""
    project, _, _, cli = guides
    target = project / ".guides/games/general/frameworks/intro.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"mine")
    result = cli("guides", "enable", "games")
    assert result[0] == 1
    assert "unmanaged" in result[2]
    assert target.read_bytes() == b"mine"


@pytest.mark.parametrize("kind", ["source", "target", "target-root"])
def test_symlink_escape_is_rejected(guides, kind):
    """Source and destination links must not read or write outside their roots."""
    project, _, manager, cli = guides
    outside = project.parent / "outside"
    outside.mkdir()
    (outside / "secret.md").write_bytes(b"secret")
    if kind == "source":
        (manager / "guides/games/escape").symlink_to(outside, target_is_directory=True)
    elif kind == "target":
        (project / ".guides").mkdir()
        (project / ".guides/games").symlink_to(outside, target_is_directory=True)
    else:
        (project / ".guides").symlink_to(outside, target_is_directory=True)
    assert cli("guides", "enable", "games")[0] == 1
    assert list(outside.iterdir()) == [outside / "secret.md"]


@pytest.mark.parametrize("action", ["keep-local", "overwrite-local", "update-source"])
def test_managed_conflicts_use_existing_resolution_flow(guides, action):
    """Guide drift is visible and cannot be overwritten without a chosen action."""
    project, _, manager, cli = guides
    assert cli("guides", "enable", "games")[0] == 0
    ref = "games/general/frameworks/intro.md"
    target = project / ".guides" / ref
    source = manager / "guides" / ref
    original = source.read_bytes()
    target.write_bytes(b"local")
    assert cli("apply")[0] == 1
    assert target.read_bytes() == b"local"
    result = cli("apply", "--diff")
    assert result[0] == 1 and f".guides/{ref}" in result[1]
    result = cli("apply", "--resolve", f".guides/{ref}", action)
    assert result[0] == 0, result[2]
    assert target.read_bytes() == (original if action == "overwrite-local" else b"local")
    assert source.read_bytes() == (b"local" if action == "update-source" else original)


def test_binary_diff_and_obsolete_binary_copy(guides):
    """Binary assets support drift reports and removal previews without decoding."""
    project, _, manager, cli = guides
    assert cli("guides", "enable", "games")[0] == 0
    ref = "games/general/frameworks/diagram.png"
    (project / ".guides" / ref).write_bytes(b"\xfflocal")
    assert "Binary files differ" in cli("apply", "--diff")[1]
    (manager / "guides" / ref).unlink()
    result = cli("apply", "--diff")
    assert result[0] == 1 and ref in result[1]
    assert cli("apply")[0] == 0


def test_lock_rebinds_to_current_roots(guides, run_cli_with_homes, read_lock):
    """A relocated project cleans only its own copies, not those of the old clone."""
    project, codex, manager, cli = guides
    assert cli("guides", "enable", "games")[0] == 0
    clone = project.parent / "clone"
    store = project.parent / "other-manager"
    shutil.copytree(project, clone)
    shutil.copytree(manager, store)
    result = run_cli_with_homes(["apply", "--check"], clone, codex, store)
    assert result[0] == 0, result[2]
    assert run_cli_with_homes(["guides", "disable", "games"], clone, codex, store)[0] == 0
    assert not (clone / ".guides").exists()
    assert (project / ".guides/games/general/frameworks/intro.md").exists()


def test_malformed_lock_cannot_delete_outside_project(guides, read_lock):
    """Untrusted copy identities fail validation before cleanup or writes."""
    project, _, _, cli = guides
    assert cli("guides", "enable", "games")[0] == 0
    lock = read_lock(project)
    lock["guides"]["copies"][0]["relative_path"] = "../../outside"
    write_toml_file(project / ".codex/codexmgr.lock", lock)
    assert cli("guides", "disable", "games")[0] == 1


def test_removed_guides_table_cleans_owned_copies(guides, read_project_config):
    """Removing configuration stops selection while preserving unowned documents."""
    project, _, _, cli = guides
    assert cli("guides", "enable", "games")[0] == 0
    config = read_project_config(project)
    del config["guides"]
    write_toml_file(project / ".codex/codexmgr.toml", config)
    assert cli("apply")[0] == 0
    assert not (project / ".guides").exists()
