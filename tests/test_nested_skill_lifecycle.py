"""Exercise nested skills through relocation, conflicts, and repeated listing."""

import shutil

from codexmgr.core.toml_io import write_toml_file
from codexmgr.tui.items import skill_items
from codexmgr.tui.state import load_staged_config

from test_nested_skills_cli import write_skill


def test_managed_nested_mirror_is_not_listed_as_another_skill(workspace, run_cli_with_homes):
    """Both lists retain the qualified enabled entry without a phantom flat copy."""
    project, codex = workspace
    manager = project.parent / "manager"
    write_skill(manager, "group/review", "review")
    run_cli_with_homes(["setup"], project, codex, manager)
    assert run_cli_with_homes(["skill", "enable", "group/review"], project, codex, manager)[0] == 0

    code, output, error = run_cli_with_homes(["skill", "list"], project, codex, manager)
    assert (code, error) == (0, "")
    assert output == "enabled group/review\n"
    staged = load_staged_config(project, codex, manager)
    assert [(item.name, item.state) for item in skill_items(staged)] == [("group/review", "enabled")]


def test_nested_copy_lock_rebinds_after_project_and_home_move(workspace, run_cli_with_homes):
    """Portable source_path follows relocated roots and cleans only the new clone."""
    project, codex = workspace
    manager = project.parent / "manager"
    write_skill(manager, "group/review", "review")
    run_cli_with_homes(["setup"], project, codex, manager)
    assert run_cli_with_homes(["skill", "enable", "group/review"], project, codex, manager)[0] == 0
    clone = project.parent / "clone"
    new_manager = project.parent / "new-manager"
    shutil.copytree(project, clone)
    shutil.copytree(manager, new_manager)
    before = (clone / ".codex" / "codexmgr.lock").read_text()

    result = run_cli_with_homes(["apply"], clone, codex, new_manager)
    assert result[0] == 0, result[2]
    assert (clone / ".codex" / "codexmgr.lock").read_text() == before
    assert run_cli_with_homes(["skill", "disable", "group/review"], clone, codex, new_manager)[0] == 0
    assert not (clone / ".agents" / "skills" / "review").exists()
    assert (project / ".agents" / "skills" / "review" / "SKILL.md").exists()


def test_nested_copy_extends_name_past_unmanaged_directory(workspace, run_cli_with_homes):
    """An unrelated project directory is preserved and reserves its flat name."""
    project, codex = workspace
    manager = project.parent / "manager"
    write_skill(manager, "group/review", "review")
    existing = project / ".agents" / "skills" / "review"
    existing.mkdir(parents=True)
    (existing / "notes.txt").write_text("local")
    run_cli_with_homes(["setup"], project, codex, manager)

    result = run_cli_with_homes(["skill", "enable", "group/review"], project, codex, manager)
    assert result[0] == 0, result[2]
    assert (existing / "notes.txt").read_text() == "local"
    assert (existing.parent / "group-review" / "SKILL.md").exists()


def test_nested_duplicate_metadata_remains_an_error(workspace, run_cli_with_homes):
    """Folder prefixes do not silently rewrite a skill's declared YAML identity."""
    project, codex = workspace
    manager = project.parent / "manager"
    first = write_skill(manager, "a/review", "shared")
    second = write_skill(manager, "b/review", "shared")
    run_cli_with_homes(["setup"], project, codex, manager)
    before = [first.read_bytes(), second.read_bytes()]
    code, _, error = run_cli_with_homes(["skill", "enable", "a/review"], project, codex, manager)
    assert code == 1
    assert "Ambiguous declared skill name: shared" in error
    assert [first.read_bytes(), second.read_bytes()] == before


def test_nested_other_stores_remain_selectable(workspace, run_cli_with_homes, read_codex_config):
    """Grouped Codex-home and project skills retain their existing selector types."""
    project, codex = workspace
    manager = project.parent / "manager"
    home_file = write_skill(codex, "set/home", "home")
    write_skill(project / ".agents", "set/local", "local")
    run_cli_with_homes(["setup"], project, codex, manager)
    write_toml_file(project / ".codex" / "codexmgr.toml", {"skills": {"enabled": ["set/home", "set/local"]}})
    result = run_cli_with_homes(["apply"], project, codex, manager)
    assert result[0] == 0, result[2]
    assert read_codex_config(project)["skills"]["config"] == [
        {"path": str(home_file), "enabled": True}, {"name": "local", "enabled": True},
    ]
