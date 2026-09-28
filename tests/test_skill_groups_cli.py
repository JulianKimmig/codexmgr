"""Behavioral checks for batch selection of discovered skill groups."""

import pytest

from test_nested_skills_cli import write_skill


@pytest.mark.parametrize("command", ["enable", "disable"])
def test_skill_group_expands_current_descendants(
    command, workspace, run_cli_with_homes, read_project_config,
):
    """Group commands save individual descendants and respect folder boundaries."""
    project, codex = workspace
    manager = project.parent / "manager"
    for reference in ["set/one", "set/sub/two", "set-other/three"]:
        write_skill(manager, reference, reference.replace("/", "-"))
    run_cli_with_homes(["setup"], project, codex, manager)

    result = run_cli_with_homes(
        ["skill", command, "--no-sync", "set/"], project, codex, manager,
    )

    assert result[0] == 0, result[2]
    assert read_project_config(project)["skills"][f"{command}d"] == ["set/one", "set/sub/two"]
    assert "set/" not in read_project_config(project)["skills"][f"{command}d"]
    write_skill(manager, "set/later", "later")
    assert "set/later" not in read_project_config(project)["skills"][f"{command}d"]


def test_unknown_group_rejects_entire_batch(workspace, run_cli_with_homes):
    """Invalid groups fail before any requested config mutation is written."""
    project, codex = workspace
    manager = project.parent / "manager"
    write_skill(manager, "set/one", "one")
    run_cli_with_homes(["setup"], project, codex, manager)
    config = project / ".codex" / "codexmgr.toml"
    before = config.read_bytes()

    code, _, error = run_cli_with_homes(
        ["skill", "enable", "--no-sync", "set/", "missing/"], project, codex, manager,
    )

    assert code == 1
    assert "Skill group not found: missing/" in error
    assert config.read_bytes() == before


def test_group_disable_replaces_enabled_bare_alias(
    workspace, run_cli_with_homes, read_project_config,
):
    """Batch changes cannot leave an older bare alias enabled for the same skill."""
    project, codex = workspace
    manager = project.parent / "manager"
    write_skill(manager, "set/one", "one")
    run_cli_with_homes(["setup"], project, codex, manager)
    run_cli_with_homes(["skill", "enable", "one"], project, codex, manager)

    result = run_cli_with_homes(["skill", "disable", "set/"], project, codex, manager)

    assert result[0] == 0, result[2]
    assert read_project_config(project)["skills"] == {"enabled": [], "disabled": ["set/one"]}
    assert not (project / ".agents" / "skills" / "one").exists()


def test_skill_directory_with_trailing_slash_is_not_a_group(
    workspace, run_cli_with_homes, read_project_config,
):
    """An explicit path to one skill retains existing directory-path semantics."""
    project, codex = workspace
    manager = project.parent / "manager"
    source = write_skill(manager, "set/one", "one")
    run_cli_with_homes(["setup"], project, codex, manager)
    reference = f"{source.parent}/"
    result = run_cli_with_homes(["skill", "enable", reference], project, codex, manager)
    assert result[0] == 0, result[2]
    assert read_project_config(project)["skills"]["enabled"] == [reference]


def test_explicit_path_still_disambiguates_duplicate_stores(workspace, run_cli_with_homes):
    """Group support must not prevent explicit paths from bypassing store collisions."""
    project, codex = workspace
    manager = project.parent / "manager"
    source = write_skill(manager, "one", "one")
    write_skill(codex, "one", "one")
    run_cli_with_homes(["setup"], project, codex, manager)
    result = run_cli_with_homes(["skill", "enable", str(source)], project, codex, manager)
    assert result[0] == 0, result[2]


def test_reenabling_group_member_does_not_reorder_configuration(workspace, run_cli_with_homes):
    """An already enabled individual keeps its stable position after group selection."""
    project, codex = workspace
    manager = project.parent / "manager"
    write_skill(manager, "set/one", "one")
    write_skill(manager, "set/two", "two")
    run_cli_with_homes(["setup"], project, codex, manager)
    run_cli_with_homes(["skill", "enable", "--no-sync", "set/"], project, codex, manager)
    config = project / ".codex" / "codexmgr.toml"
    before = config.read_bytes()
    result = run_cli_with_homes(["skill", "enable", "--no-sync", "set/one"], project, codex, manager)
    assert result[0] == 0, result[2]
    assert config.read_bytes() == before


def test_overlapping_group_and_bare_alias_select_each_skill_once(
    workspace, run_cli_with_homes, read_project_config,
):
    """A combined batch cannot create two selectors for the same nested skill."""
    project, codex = workspace
    manager = project.parent / "manager"
    write_skill(manager, "set/one", "one")
    write_skill(manager, "set/sub/two", "two")
    run_cli_with_homes(["setup"], project, codex, manager)
    result = run_cli_with_homes(
        ["skill", "enable", "--no-sync", "set/", "one", "set/sub/"], project, codex, manager,
    )
    assert result[0] == 0, result[2]
    assert read_project_config(project)["skills"]["enabled"] == ["set/one", "set/sub/two"]
