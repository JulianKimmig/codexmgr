"""Exercise package composition, shared selections, and validation via CLI and TUI."""

import os

import pytest

from codexmgr.commands.codex_jit import CodexJitRequest, build_jit_project_state
from codexmgr.core.toml_io import write_toml_file
from codexmgr.tui.items import package_items
from codexmgr.tui.saving import save_staged_config
from codexmgr.tui.state import load_staged_config
from test_nested_skills_cli import write_skill
from test_package_skill_groups import write_package


@pytest.fixture
def packages(workspace, run_cli_with_homes):
    """Return isolated projects, a manager home, and their normal CLI entry point."""
    project, codex = workspace
    manager = project.parent / "manager"

    def cli(*args):
        """Invoke codexmgr in the isolated workspace and return its result."""
        return run_cli_with_homes(list(args), project, codex, manager)

    assert cli("setup")[0] == 0
    return project, codex, manager, cli


def test_include_graph_order_and_profile_isolation(packages, read_project_config):
    """Composition follows declaration order and includes root entries only."""
    project, _, manager, cli = packages
    write_package(manager, 'skills = ["shared"]\n[profiles.strict]\nskills = ["ignored"]\n', "shared")
    write_package(manager, 'skills = ["left"]\npackages = ["shared"]\n', "left")
    write_package(manager, 'skills = ["right"]\npackages = ["shared", "shared"]\n', "right")
    write_package(manager, 'packages = ["right"]\n', "wrapper")
    write_package(
        manager,
        'skills = ["base"]\npackages = ["left", "wrapper"]\n'
        '[profiles.strict]\nskills = ["strict"]\npackages = ["extra"]\n',
        "programming",
    )
    write_package(manager, 'skills = ["extra"]\n', "extra")
    assert cli("package", "enable", "--no-sync", "programming", "--profile", "strict")[0] == 0
    assert read_project_config(project)["skills"]["enabled"] == [
        "base", "left", "shared", "right", "strict", "extra",
    ]


@pytest.mark.parametrize(
    ("manifest", "error"),
    [
        ('packages = ["absent"]\n', "broken -> absent"),
        ('packages = ["broken"]\n', "broken -> broken"),
        ('packages = ["loop"]\n', "broken -> loop -> broken"),
        ('packages = ["../sibling"]\n', "bare name"),
        ('packages = ["C:other"]\n', "bare name"),
        ('packages = [123]\n', "list of strings"),
    ],
)
@pytest.mark.parametrize("operation", ["enable", "disable"])
def test_invalid_include_keeps_entire_batch_unmodified(packages, manifest, error, operation):
    """Bad include graphs produce actionable errors before the batch writes config."""
    project, _, manager, cli = packages
    write_package(manager, 'skills = ["good"]\n', "good")
    write_package(manager, 'packages = ["broken"]\n', "loop")
    write_package(manager, manifest, "broken")
    config = project / ".codex" / "codexmgr.toml"
    before = config.read_bytes()
    code, _, stderr = cli("package", operation, "--no-sync", "good", "broken")
    assert code == 1
    assert error in stderr
    assert config.read_bytes() == before


def test_two_explicit_selections_keep_include_until_last_disable(packages, read_project_config):
    """An explicitly enabled include survives the parent and can later be disabled."""
    project, _, manager, cli = packages
    write_package(manager, 'skills = ["maintain-changelog"]\n', "changelog")
    write_package(manager, 'packages = ["changelog"]\nskills = ["review"]\n', "programming")
    assert cli("package", "enable", "--no-sync", "programming", "changelog")[0] == 0
    assert cli("package", "disable", "--no-sync", "programming")[0] == 0
    assert read_project_config(project)["skills"] == {
        "enabled": ["maintain-changelog"], "disabled": ["review"],
    }
    assert cli("package", "disable", "--no-sync", "changelog")[0] == 0
    config = read_project_config(project)
    assert config["skills"] == {"enabled": [], "disabled": ["review", "maintain-changelog"]}
    assert "package_selections" not in config


@pytest.mark.skipif(os.name != "nt", reason="Windows package paths are case insensitive")
def test_package_name_case_alias_is_the_same_selection(packages, read_project_config):
    """A Windows path spelling does not create a second owner for the same package."""
    project, _, manager, cli = packages
    write_package(manager, 'skills = ["review"]\n', "parent")
    assert cli("package", "enable", "--no-sync", "PARENT")[0] == 0
    assert cli("package", "disable", "--no-sync", "parent")[0] == 0
    config = read_project_config(project)
    assert config["skills"]["enabled"] == []
    assert "package_selections" not in config


def test_profile_keeps_shared_group_leaf_after_cli_root_disable(packages, read_project_config):
    """A selected profile protects a nested skill referenced by a different alias."""
    project, _, manager, cli = packages
    write_skill(manager, "team/audio", "audio")
    write_skill(manager, "team/physics", "physics")
    write_package(manager, 'skills = ["team/"]\n[profiles.audio]\nskills = ["audio"]\n', "game")
    assert cli("package", "enable", "--no-sync", "game", "--profile", "audio")[0] == 0
    assert cli("package", "disable", "--no-sync", "game")[0] == 0
    assert read_project_config(project)["skills"] == {
        "enabled": ["team/audio"], "disabled": ["team/physics"],
    }
    assert cli("package", "disable", "--no-sync", "game", "--profile", "audio")[0] == 0
    assert read_project_config(project)["skills"]["enabled"] == []


def test_skill_alias_snapshot_follows_the_applied_reference(packages, read_project_config):
    """A later enable can change the spelling of a shared skill before its source disappears."""
    project, _, manager, cli = packages
    source = write_skill(manager, "team/audio", "audio")
    write_package(manager, 'skills = ["audio"]\n', "alias")
    write_package(manager, 'skills = ["team/audio"]\n', "qualified")
    assert cli("package", "enable", "--no-sync", "alias")[0] == 0
    assert cli("package", "enable", "--no-sync", "qualified")[0] == 0
    assert cli("package", "disable", "--no-sync", "qualified")[0] == 0
    source.unlink()
    assert cli("package", "disable", "--no-sync", "alias")[0] == 0
    assert read_project_config(project)["skills"]["enabled"] == []


@pytest.mark.parametrize(
    ("family", "project_folder"), [("rules", ".rules"), ("guides", ".guides")],
)
@pytest.mark.parametrize("release_folder", [True, False])
def test_overlapping_folder_disable_keeps_retained_paths(packages, family, project_folder, release_folder):
    """Disabling either side of a folder overlap leaves the retained files generated."""
    project, _, manager, cli = packages
    root = manager / family / "team"
    root.mkdir(parents=True)
    (root / "shared.md").write_text("# Shared\n", encoding="utf-8")
    (root / "other.md").write_text("# Other\n", encoding="utf-8")
    write_package(manager, f'{family} = ["team/"]\n', "folder")
    write_package(manager, f'{family} = ["team/shared.md"]\n', "file")
    assert cli("package", "enable", "folder", "file")[0] == 0
    assert cli("package", "disable", "folder" if release_folder else "file")[0] == 0
    assert (project / project_folder / "team" / "shared.md").is_file()
    assert (project / project_folder / "team" / "other.md").is_file() is (not release_folder)


def test_reenable_and_disable_use_recorded_contributions(packages, read_project_config):
    """Selection history survives manifest edits and is additive on re-enable."""
    project, _, manager, cli = packages
    write_package(manager, 'packages = ["child"]\n', "parent")
    write_package(manager, 'skills = ["original"]\n', "child")
    assert cli("package", "enable", "--no-sync", "parent")[0] == 0
    write_package(manager, 'skills = ["new"]\n', "child")
    assert cli("package", "enable", "--no-sync", "parent")[0] == 0
    write_package(manager, 'packages = ["missing"]\n', "parent")
    assert cli("package", "disable", "--no-sync", "parent")[0] == 0
    assert read_project_config(project)["skills"] == {
        "enabled": [], "disabled": ["original", "new"],
    }


def test_tui_include_can_be_selected_independently_and_saved(packages, read_project_config):
    """An included TUI row can acquire its own selection, which survives clear and save."""
    project, codex, manager, cli = packages
    write_package(manager, 'skills = ["shared"]\n', "child")
    write_package(manager, '[profiles.full]\npackages = ["child"]\n', "parent")
    staged = load_staged_config(project, codex, manager)
    staged.set_package_profile_enabled("parent", "full", True)
    assert staged.package_profile_state("parent", "full") == "enabled"
    assert staged.package_state("child") == "available"
    staged.set_package_enabled("child", True)
    staged.set_package_profile_available("parent", "full")
    save_staged_config(staged, no_sync=True)
    assert read_project_config(project)["skills"]["enabled"] == ["shared"]
    assert cli("package", "disable", "--no-sync", "child")[0] == 0
    assert read_project_config(project)["skills"]["enabled"] == []


def test_tui_reports_invalid_profile_graph_on_its_own_row(packages):
    """A broken profile has one error row and leaves its valid root selectable."""
    project, codex, manager, _ = packages
    write_package(manager, 'skills = ["base"]\n[profiles.broken]\npackages = ["absent"]\n', "parent")
    rows = package_items(load_staged_config(project, codex, manager))
    assert [(item.name, item.state) for item in rows] == [
        ("parent", "available"), ("parent / broken", "error"),
    ]
    assert "parent.broken -> absent" in rows[1].detail


def test_jit_include_is_temporary(packages):
    """A temporary overlay includes nested resources without recording package selections."""
    project, codex, manager, _ = packages
    write_skill(manager, "team/review", "review")
    write_package(manager, 'skills = ["team/review"]\n', "child")
    write_package(manager, 'packages = ["child"]\n', "parent")
    base = {"skills": {"enabled": [], "disabled": []}}
    config_path = project / ".codex" / "codexmgr.toml"
    write_toml_file(config_path, base)
    before = config_path.read_bytes()
    request = CodexJitRequest(True, ["parent"], [], [])
    state = build_jit_project_state(base, request, project, codex, manager)
    assert {copy.source_path for copy in state.skill_copies} == {"team/review"}
    assert base == {"skills": {"enabled": [], "disabled": []}}
    assert config_path.read_bytes() == before
