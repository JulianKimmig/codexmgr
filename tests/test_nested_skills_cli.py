"""Behavioral coverage for grouped skill discovery and portable flat copies."""

from pathlib import Path

import pytest

from codexmgr.core.toml_io import write_toml_file
from codexmgr.tui.items import skill_items
from codexmgr.tui.state import load_staged_config, save_staged_config


def write_skill(root: Path, reference: str, name: str) -> Path:
    """Write a skill beneath root/reference and return its instruction path."""
    file = root / "skills" / reference / "SKILL.md"
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(f"---\nname: {name}\ndescription: Test.\n---\n# Instructions\n")
    return file


def test_recursive_discovery_stops_at_skill_and_handles_cycles(workspace, run_cli_with_homes):
    """Groups recurse, skill internals stay bundled, and symlink loops terminate."""
    project, codex = workspace
    manager = project.parent / "manager"
    write_skill(manager, "set1/skill1", "one")
    write_skill(manager, "set1/deeper/skill2", "two")
    write_skill(manager, "set1/skill1/examples/demo", "example")
    (manager / "skills" / "set1" / "loop").symlink_to(manager / "skills", target_is_directory=True)

    code, output, error = run_cli_with_homes(["skill", "list"], project, codex, manager)

    assert (code, error) == (0, "")
    assert output.splitlines() == ["available set1/deeper/skill2", "available set1/skill1"]


@pytest.mark.parametrize("reference", ["skill1", "set1/skill1"])
def test_nested_skill_copies_flat_and_refreshes(reference, workspace, run_cli_with_homes, read_lock):
    """Bare and qualified names copy entire skills and retain their source path."""
    project, codex = workspace
    manager = project.parent / "manager"
    source = write_skill(manager, "set1/skill1", "one")
    asset = source.parent / "scripts" / "helper.txt"
    asset.parent.mkdir()
    asset.write_text("asset")
    run_cli_with_homes(["setup"], project, codex, manager)

    result = run_cli_with_homes(["skill", "enable", reference], project, codex, manager)

    assert result[0] == 0, result[2]
    target = project / ".agents" / "skills" / "skill1"
    assert (target / "scripts" / "helper.txt").read_text() == "asset"
    assert (target / "SKILL.md").read_bytes() == source.read_bytes()
    assert not (target.parent / "set1").exists()
    assert read_lock(project)["skills"]["copies"] == [{
        "name": "skill1", "source": "codexmgr_home",
        "source_path": "set1/skill1", "target": ".agents/skills/skill1",
    }]
    assert run_cli_with_homes(["apply", "--check"], project, codex, manager)[0] == 0
    assert run_cli_with_homes(["apply"], project, codex, manager)[0] == 0
    assert run_cli_with_homes(["skill", "disable", reference], project, codex, manager)[0] == 0
    assert not target.exists()
    assert source.exists()


@pytest.mark.parametrize(
    ("references", "targets"),
    [
        (["set1/review", "set2/review"], ["set1-review", "set2-review"]),
        (["a/common/review", "b/common/review"], ["a-common-review", "b-common-review"]),
        (["review", "set1/review"], ["review", "set1-review"]),
        (["set1-review", "set1/review", "set2/review"], ["set1-review", None, "set2-review"]),
    ],
)
def test_colliding_copy_names_use_group_prefixes(references, targets, workspace, run_cli_with_homes):
    """Destination names expand through groups and fail only when exhausted."""
    project, codex = workspace
    manager = project.parent / "manager"
    for index, reference in enumerate(references):
        write_skill(manager, reference, f"skill-{index}")
    run_cli_with_homes(["setup"], project, codex, manager)
    write_toml_file(project / ".codex" / "codexmgr.toml", {"skills": {"enabled": references}})

    code, _, error = run_cli_with_homes(["apply"], project, codex, manager)

    if None in targets:
        assert code == 1
        assert "skill copy name" in error.lower()
        assert not (project / ".agents" / "skills").exists()
    else:
        assert (code, error) == (0, "")
        for reference, target in zip(references, targets):
            assert (project / ".agents" / "skills" / target / "SKILL.md").read_bytes() == (
                manager / "skills" / reference / "SKILL.md"
            ).read_bytes()
        assert run_cli_with_homes(["apply", "--check"], project, codex, manager)[0] == 0


def test_ambiguous_bare_name_requires_group_reference(workspace, run_cli_with_homes):
    """A short input cannot arbitrarily choose between different grouped skills."""
    project, codex = workspace
    manager = project.parent / "manager"
    first = write_skill(manager, "a/review", "a-review")
    second = write_skill(manager, "b/review", "b-review")
    run_cli_with_homes(["setup"], project, codex, manager)
    code, _, error = run_cli_with_homes(["skill", "enable", "review"], project, codex, manager)
    assert code == 1
    assert "Ambiguous skill reference" in error
    assert str(first) in error
    assert str(second) in error


def test_explicit_relative_path_bypasses_group_lookup(workspace, run_cli_with_homes, read_codex_config):
    """An explicit ./ path selects project files even when a store has that group."""
    project, codex = workspace
    manager = project.parent / "manager"
    write_skill(manager, "set/review", "manager")
    local = write_skill(project, "set/review", "local")
    run_cli_with_homes(["setup"], project, codex, manager)
    result = run_cli_with_homes(["skill", "enable", "./skills/set/review"], project, codex, manager)
    assert result[0] == 0, result[2]
    assert read_codex_config(project)["skills"]["config"] == [{"path": str(local), "enabled": True}]


def test_tui_lists_selects_and_saves_nested_skill(workspace, run_cli_with_homes):
    """The TUI uses qualified discovery entries and the same flat-copy pipeline."""
    project, codex = workspace
    manager = project.parent / "manager"
    write_skill(manager, "set/review", "review")
    run_cli_with_homes(["setup"], project, codex, manager)
    staged = load_staged_config(project, codex, manager)
    assert [item.name for item in skill_items(staged)] == ["set/review"]
    staged.set_skill_enabled("set/review", True)
    save_staged_config(staged, no_sync=False)
    assert (project / ".agents" / "skills" / "review" / "SKILL.md").is_file()


def test_existing_copy_keeps_target_when_new_group_appears(workspace, run_cli_with_homes):
    """New groups cannot rename a managed copy or remove its local extras."""
    project, codex = workspace
    manager = project.parent / "manager"
    write_skill(manager, "a/review", "a-review")
    run_cli_with_homes(["setup"], project, codex, manager)
    assert run_cli_with_homes(["skill", "enable", "a/review"], project, codex, manager)[0] == 0
    extra = project / ".agents" / "skills" / "review" / "local.txt"
    extra.write_text("preserved")
    write_skill(manager, "b/review", "b-review")
    result = run_cli_with_homes(["skill", "enable", "b/review"], project, codex, manager)
    assert result[0] == 0, result[2]
    assert extra.read_text() == "preserved"
    assert (extra.parent.parent / "b-review" / "SKILL.md").exists()


@pytest.mark.parametrize("source_path", ["../outside", "/outside", "a/../../outside", "a\\outside", "."])
def test_nested_lock_rejects_unsafe_source_paths(source_path, workspace, run_cli_with_homes):
    """Portable nested source identities cannot escape the configured skill root."""
    project, codex = workspace
    manager = project.parent / "manager"
    run_cli_with_homes(["setup"], project, codex, manager)
    write_toml_file(project / ".codex" / "codexmgr.toml", {"skills": {"enabled": []}})
    write_toml_file(project / ".codex" / "codexmgr.lock", {"skills": {"copies": [{
        "name": "review", "source": "codexmgr_home", "source_path": source_path,
        "target": ".agents/skills/review",
    }]}})
    code, _, error = run_cli_with_homes(["apply"], project, codex, manager)
    assert code == 1
    assert "safe skill source path" in error
