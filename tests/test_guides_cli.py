"""Guide discovery, persistent selection, and CLI lifecycle behavior."""

from pathlib import Path

import pytest


def write_guide(manager: Path, ref: str, content: bytes = b"# Guide\n") -> Path:
    """Write bytes at a store-relative guide ref and return the source path."""
    path = manager / "guides" / ref
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


@pytest.fixture
def guides(workspace, run_cli_with_homes):
    """Return isolated project/store roots and a CLI callable with sample guides."""
    project, codex = workspace
    manager = project.parent / "manager"
    write_guide(manager, "games/general/monetization/intro.md")
    write_guide(manager, "games/general/frameworks/intro.md", b"# Frameworks\n")
    write_guide(manager, "games/general/frameworks/diagram.png", b"\x89PNG\xff\x00")
    write_guide(manager, "other/readme.txt")

    def cli(*args):
        """Run CLI arguments against the isolated roots; return captured results."""
        return run_cli_with_homes(list(args), project, codex, manager)

    assert cli("setup")[0] == 0
    return project, codex, manager, cli


@pytest.mark.parametrize("ref,count", [
    ("games", 3), ("games/general", 3),
    ("games/general/monetization/", 1),
    ("games/general/frameworks/intro.md", 1),
])
def test_enable_preserves_full_paths_and_portable_lock(guides, ref, count, read_lock, read_project_config):
    """Every selectable level retains its complete store-relative destination."""
    project, _, manager, cli = guides
    result = cli("guides", "enable", ref)
    assert result[0] == 0, result[2]
    copies = read_lock(project)["guides"]["copies"]
    assert len(copies) == count
    for copy in copies:
        assert copy["source"] == "codexmgr_home"
        assert copy["target"] == f'.guides/{copy["relative_path"]}'
        assert (project / copy["target"]).read_bytes() == (manager / "guides" / copy["relative_path"]).read_bytes()
    canonical = ref if ref.endswith(("/", ".md")) else ref + "/"
    assert read_project_config(project)["guides"] == {"enabled": [canonical], "disabled": []}
    assert cli("apply", "--check")[0] == 0


def test_folder_selection_tracks_added_and_removed_files(guides, read_lock):
    """Reapply discovers new descendants and deletes only stale managed files."""
    project, _, manager, cli = guides
    assert cli("guides", "enable", "games")[0] == 0
    write_guide(manager, "games/new/deep.txt", b"new")
    (manager / "guides/games/general/monetization/intro.md").unlink()
    local = project / ".guides/games/local.txt"
    local.write_bytes(b"local")
    assert cli("apply", "--check")[0] == 1
    assert cli("apply", "--resolve", str(local), "keep-local")[0] == 0
    assert (project / ".guides/games/new/deep.txt").read_bytes() == b"new"
    assert not (project / ".guides/games/general/monetization").exists()
    assert local.read_bytes() == b"local"
    assert len(read_lock(project)["guides"]["copies"]) == 3


def test_exclusions_win_over_overlapping_enables(guides, read_lock):
    """Parent and leaf enables deduplicate; file and folder exclusions win."""
    project, _, _, cli = guides
    assert cli("guides", "enable", "games", "games/general/frameworks/intro.md")[0] == 0
    assert len(read_lock(project)["guides"]["copies"]) == 3
    assert cli("guides", "disable", "games/general/frameworks", "games/general/monetization/intro.md")[0] == 0
    assert not (project / ".guides").exists()
    assert cli("guides", "enable", "games")[0] == 0
    assert not (project / ".guides").exists()


def test_batch_no_sync_and_exact_filename_resolution(guides, read_project_config):
    """Folders beat same-stem documents, and no-sync persists selectors only."""
    project, _, manager, cli = guides
    write_guide(manager, "games.md")
    result = cli("guides", "enable", "--no-sync", "games", "other/readme.txt")
    assert result[0] == 0, result[2]
    assert read_project_config(project)["guides"]["enabled"] == ["games/", "other/readme.txt"]
    assert not (project / ".guides").exists()
    assert cli("apply")[0] == 0
    assert not (project / ".guides/games.md").exists()


def test_listing_and_health_include_configured_missing_refs(guides):
    """Listings retain hierarchy; doctor diagnoses missing enables, not exclusions."""
    project, _, manager, cli = guides
    assert cli("guides", "enable", "--no-sync", "games/general/frameworks/intro.md")[0] == 0
    assert cli("guides", "disable", "missing/folder/")[0] == 0
    assert cli("doctor")[0] == 0
    (manager / "guides/games/general/frameworks/intro.md").unlink()
    code, output, error = cli("guides", "list")
    assert code == 0, error
    assert "games/" in output and "frameworks/" in output
    assert "intro.md" in output and "missing" in output
    assert "Enabled guides:" in cli("status")[1]
    result = cli("doctor")
    assert result[0] == 1
    assert "games/general/frameworks/intro.md" in result[1] + result[2]
    assert cli("apply")[0] == 1


def test_disable_preserves_unmanaged_content_and_source(guides):
    """Cleanup only removes lock-owned targets, never unrelated project files."""
    project, _, manager, cli = guides
    assert cli("guides", "enable", "games")[0] == 0
    local = project / ".guides/games/general/monetization/local.md"
    local.write_bytes(b"mine")
    assert cli("guides", "disable", "games")[0] == 0
    assert local.read_bytes() == b"mine"
    assert (manager / "guides/games/general/monetization/intro.md").is_file()
    assert not (project / ".guides/games/general/frameworks").exists()


def test_empty_store_and_empty_folder(guides):
    """Empty selections can be enabled without materializing target directories."""
    project, _, manager, cli = guides
    (manager / "guides/empty").mkdir()
    assert cli("guides", "enable", "empty")[0] == 0
    assert not (project / ".guides").exists()
    assert "empty/" in cli("guides", "list")[1]
