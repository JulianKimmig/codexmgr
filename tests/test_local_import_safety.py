"""Pre-write safety and per-file authorization for local document imports."""

import io
import os

import pytest

from codexmgr.core.errors import CommandError
from codexmgr.core.toml_io import write_toml_file
from codexmgr.interface.cli import main
from codexmgr.project.apply import build_project_state, prepare_project_state_apply, execute_prepared_project_apply
from codexmgr.project.copy_conflicts import CopyResolution
from test_local_imports import TerminalInput, local_document


def test_all_decisions_precede_any_source_write(local_document):
    """Accepting one candidate then aborting another does not publish either one."""
    project, codex, manager, family, target, _ = local_document
    other = target.with_name("second.md")
    other.write_bytes(b"second")
    before = (project / ".codex/codexmgr.lock").read_bytes()
    out, err = io.StringIO(), io.StringIO()
    result = main(["apply"], cwd=project, codex_home=codex, codexmgr_home=manager,
                  stdin=TerminalInput("u\na\n"), stdout=out, stderr=err)
    assert result == 1
    assert not (manager / family / "games/new").exists()
    assert (project / ".codex/codexmgr.lock").read_bytes() == before


def test_import_overwrite_local_is_invalid(local_document):
    """A missing source cannot be selected as an overwrite-local operation."""
    _, _, _, _, target, cli = local_document
    assert cli("apply", "--resolve", str(target), "overwrite-local")[0] == 1
    assert target.read_bytes() == b"# Local document\n"


@pytest.mark.parametrize("change", ["target", "source", "source-parent-link", "target-link"])
def test_changed_paths_invalidate_import_decisions(local_document, change):
    """Stale approval cannot publish changed bytes or overwrite a newly appeared source."""
    project, codex, manager, family, target, _ = local_document
    state = build_project_state(project, codex, manager)
    prepared = prepare_project_state_apply(state, cwd=project,
        copy_resolutions={target.absolute(): CopyResolution.UPDATE_SOURCE})
    source = manager / family / "games/new/deep.md"
    outside = project.parent / "outside"
    outside.mkdir()
    if change == "target":
        target.write_bytes(b"changed")
    elif change == "source":
        source.parent.mkdir()
        source.write_bytes(b"new source")
    elif change == "source-parent-link":
        source.parent.symlink_to(outside, target_is_directory=True)
    else:
        target.unlink()
        (outside / "private.md").write_bytes(b"# Local document\n")
        target.symlink_to(outside / "private.md")
    with pytest.raises(CommandError):
        execute_prepared_project_apply(prepared)
    if change == "source":
        assert source.read_bytes() == b"new source"
    else:
        assert not source.exists()


@pytest.mark.parametrize("where", ["source", "target"])
def test_discovery_rejects_symlink_paths(local_document, where):
    """Neither publishing destinations nor local discovery may traverse symlinks."""
    project, _, manager, family, target, cli = local_document
    outside = project.parent / "outside"
    outside.mkdir()
    if where == "source":
        (manager / family / "games/new").symlink_to(outside, target_is_directory=True)
    else:
        target.with_name("link").symlink_to(outside, target_is_directory=True)
    assert cli("apply")[0] == 1
    assert not list(outside.iterdir())


def test_existing_unmanaged_source_collision_remains_an_error(local_document):
    """A source that already exists cannot be adopted by the new-file workflow."""
    _, _, manager, family, target, cli = local_document
    source = manager / family / "games/new/deep.md"
    source.parent.mkdir()
    source.write_bytes(b"shared")
    result = cli("apply", "--resolve", str(target), "update-source")
    assert result[0] == 1 and "unmanaged" in result[2]
    assert source.read_bytes() == b"shared"


@pytest.mark.parametrize("value", ["bad", ["../outside"], [42]])
def test_invalid_project_only_lock_refs_fail_safely(local_document, read_lock, value):
    """Remembered choices require validated relative file references."""
    project, _, _, family, _, cli = local_document
    data = read_lock(project)
    data[family]["project_only"] = value
    write_toml_file(project / ".codex/codexmgr.lock", data)
    result = cli("apply")
    assert result[0] == 1
    assert "project_only" in result[2]


def test_existing_conflicts_and_imports_are_one_decision_batch(local_document):
    """An unresolved managed edit prevents publishing another newly authored file."""
    _, _, manager, family, target, cli = local_document
    assert cli("apply", "--resolve", str(target), "update-source")[0] == 0
    target.write_bytes(b"changed managed copy")
    other = target.with_name("second.md")
    other.write_bytes(b"new document")
    result = cli("apply", "--resolve", str(other), "update-source")
    assert result[0] == 1 and "Managed copy conflict" in result[2]
    source = manager / family / "games/new/second.md"
    assert not source.exists()
    assert cli("apply", "--resolve", str(other), "update-source",
               "--resolve", str(target), "keep-local")[0] == 0
    assert source.read_bytes() == b"new document"
    assert target.read_bytes() == b"changed managed copy"


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="Requires os.mkfifo to create a FIFO")
def test_special_local_files_fail_without_blocking_or_publishing(local_document):
    """Local FIFOs cannot be read as document imports, even beside valid files."""
    _, _, manager, family, target, cli = local_document
    os.mkfifo(target.with_name("pipe"))
    result = cli("apply")
    assert result[0] == 1 and "regular file" in result[2]
    assert not (manager / family / "games/new").exists()
