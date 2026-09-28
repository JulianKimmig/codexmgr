"""New local document import decisions shared by Rules and Guides."""

import io
import shutil

import pytest

from codexmgr.interface.cli import main


class TerminalInput(io.StringIO):
    """In-memory terminal input used to exercise real interactive CLI prompts."""

    def isatty(self) -> bool:
        """Return True to emulate an external terminal stream."""
        return True


@pytest.fixture(params=["guides", "rules"])
def local_document(request, workspace, run_cli_with_homes):
    """Return isolated roots, resource kind, and CLI helper with an enabled empty folder."""
    project, codex = workspace
    manager = project.parent / "manager"
    family = request.param
    (manager / family / "games").mkdir(parents=True)

    def cli(*args):
        """Run the actual CLI against the isolated document stores."""
        return run_cli_with_homes(list(args), project, codex, manager)

    assert cli("setup")[0] == 0
    assert cli(family, "enable", "games/")[0] == 0
    target = project / f".{family}/games/new/deep.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"# Local document\n")
    return project, codex, manager, family, target, cli


def test_noninteractive_apply_reports_new_file_without_writing(local_document):
    """An empty enabled source folder still discovers nested project additions."""
    project, _, manager, family, target, cli = local_document
    lock = project / ".codex/codexmgr.lock"
    before = lock.read_bytes()
    result = cli("apply")
    assert result[0] == 1
    assert "New local file" in result[2]
    assert target.relative_to(project).as_posix() in result[2]
    assert "update-source" in result[2] and "keep-local" in result[2]
    assert lock.read_bytes() == before
    assert not (manager / family / "games/new/deep.md").exists()


def test_import_creates_source_and_manages_copy_in_same_apply(local_document, read_lock):
    """Explicit publishing copies bytes and records portable ownership immediately."""
    project, _, manager, family, target, cli = local_document
    target.write_bytes(b"\xff\x00asset")
    result = cli("apply", "--resolve", str(target), "update-source")
    assert result[0] == 0, result[2]
    assert "shared source" in result[1]
    assert (manager / family / "games/new/deep.md").read_bytes() == target.read_bytes()
    assert read_lock(project)[family]["copies"] == [{
        "relative_path": "games/new/deep.md", "source": "codexmgr_home",
        "target": f".{family}/games/new/deep.md",
    }]
    assert cli("apply", "--check")[0] == 0
    target.write_bytes(b"edited")
    assert "Managed copy conflict" in cli("apply")[2]
    assert cli(family, "disable", "games/")[0] == 0
    assert not target.exists()


def test_keep_project_only_is_remembered_and_unmanaged(local_document, read_lock):
    """Remembered local files are not repeatedly prompted, published, or cleaned up."""
    project, _, manager, family, target, cli = local_document
    assert cli("apply", "--resolve", str(target), "keep-local")[0] == 0
    assert read_lock(project)[family]["project_only"] == ["games/new/deep.md"]
    assert not read_lock(project)[family].get("copies")
    target.write_bytes(b"later edit")
    assert cli("apply")[0] == 0
    assert cli("apply", "--check")[0] == 0
    assert not (manager / family / "games/new/deep.md").exists()
    assert cli(family, "disable", "games/")[0] == 0
    assert target.read_bytes() == b"later edit"
    assert cli(family, "enable", "games/")[0] == 0


@pytest.mark.parametrize("action,code", [("u", 0), ("k", 0), ("a", 1)])
def test_interactive_import_choices(local_document, action, code):
    """CLI prompts offer publishing, persistent project-only choice, and abort."""
    project, codex, manager, family, target, _ = local_document
    before = (project / ".codex/codexmgr.lock").read_bytes()
    out, err = io.StringIO(), io.StringIO()
    result = main(["apply"], cwd=project, codex_home=codex, codexmgr_home=manager,
                  stdin=TerminalInput(action + "\n"), stdout=out, stderr=err)
    assert result == code, err.getvalue()
    assert "New local file" in out.getvalue()
    assert "project-only" in out.getvalue()
    assert (manager / family / "games/new/deep.md").exists() == (action == "u")
    if action == "a":
        assert (project / ".codex/codexmgr.lock").read_bytes() == before
    assert target.read_bytes() == b"# Local document\n"


def test_readonly_modes_report_pending_imports(local_document):
    """Checks and diffs show pending imports without prompting or modifying state."""
    project, _, manager, family, _, cli = local_document
    before = (project / ".codex/codexmgr.lock").read_bytes()
    for flag in ("--check", "--diff"):
        result = cli("apply", flag)
        assert result[0] == 1
        assert "Pending import:" in result[1]
        assert result[2] == ""
    assert not (manager / family / "games/new/deep.md").exists()
    assert (project / ".codex/codexmgr.lock").read_bytes() == before


def test_import_scan_respects_exclusions_and_does_not_scan_siblings(local_document):
    """Disabled files/subtrees and unselected folders remain project-only without prompts."""
    project, _, _, family, target, cli = local_document
    assert cli(family, "disable", "games/new/")[0] == 0
    sibling = project / f".{family}/outside/local.md"
    sibling.parent.mkdir(parents=True)
    sibling.write_bytes(b"outside")
    assert cli("apply")[0] == 0
    assert target.exists() and sibling.exists()
    assert cli(family, "enable", "--no-sync", "games/new/")[0] == 1  # no source folder yet
    assert cli(family, "disable", "games/new/deep.md")[0] == 0


def test_source_deletion_does_not_reimport_previously_owned_file(local_document):
    """Owned stale targets follow existing cleanup semantics instead of resurrection."""
    _, _, manager, family, target, cli = local_document
    assert cli("apply", "--resolve", str(target), "update-source")[0] == 0
    (manager / family / "games/new/deep.md").unlink()
    assert cli("apply")[0] == 0
    assert not target.exists()


def test_no_sync_defers_import_decisions(local_document):
    """Selection-only operations never publish local files or ask for decisions."""
    _, _, manager, family, target, cli = local_document
    assert cli(family, "enable", "--no-sync", "games/")[0] == 0
    assert not (manager / family / "games/new/deep.md").exists()
    assert target.exists()


def test_project_only_lock_is_portable(local_document, run_cli_with_homes):
    """Remembered local-only paths survive moving both project and shared store."""
    project, codex, manager, family, target, cli = local_document
    assert cli("apply", "--resolve", str(target), "keep-local")[0] == 0
    clone, store = project.parent / "clone", project.parent / "store"
    shutil.copytree(project, clone)
    shutil.copytree(manager, store)
    assert run_cli_with_homes(["apply", "--check"], clone, codex, store)[0] == 0
    assert (clone / f".{family}/games/new/deep.md").exists()


def test_disabled_ancestor_overrides_explicit_child_folder_enable(local_document):
    """An enabled child beneath a disabled ancestor does not prompt for local files."""
    _, _, manager, family, _, cli = local_document
    (manager / family / "games/new").mkdir()
    assert cli(family, "enable", "--no-sync", "games/new/")[0] == 0
    assert cli(family, "disable", "games/")[0] == 0
    assert cli("apply", "--check")[0] == 0


def test_individual_file_selection_does_not_import_siblings(local_document):
    """Only enabled folder selectors grant scope to discover project additions."""
    _, _, manager, family, target, cli = local_document
    source = manager / family / "games/existing.md"
    source.write_bytes(b"shared document")
    assert cli(family, "disable", "games/")[0] == 0
    assert cli(family, "enable", "games/existing.md")[0] == 0
    assert target.exists()
    assert cli("apply", "--check")[0] == 0
