"""Guide package/profile activation and temporary launch restoration."""

from copy import deepcopy

import pytest

from codexmgr.commands.codex_jit import CodexJitRequest, build_jit_project_state, run_with_jit_overlay
from codexmgr.core.errors import CommandError
from codexmgr.tui.state import load_staged_config
from test_guides_cli import guides, write_guide
from test_package_skill_groups import write_package


def test_package_profiles_use_persistent_guide_selectors(guides, read_project_config):
    """Package roots and profiles merge guide references without flattening them."""
    project, _, manager, cli = guides
    write_package(manager, 'guides = ["games/general/monetization"]\n[profiles.full]\nguides = ["games", "games/"]\n')
    result = cli("package", "enable", "phaser", "--profile", "full")
    assert result[0] == 0, result[2]
    assert read_project_config(project)["guides"]["enabled"] == ["games/general/monetization/", "games/"]
    write_guide(manager, "games/new.md")
    assert cli("apply")[0] == 0
    assert (project / ".guides/games/new.md").exists()
    assert cli("package", "disable", "phaser", "--profile", "full")[0] == 0
    assert not (project / ".guides").exists()


def test_staged_package_profile_enable_disable_clear(guides):
    """Package status uses canonical guide refs and staged clear preserves siblings."""
    project, codex, manager, _ = guides
    write_package(manager, 'guides = ["other/readme.txt"]\n[profiles.full]\nguides = ["games"]\n')
    staged = load_staged_config(project, codex, manager)
    assert staged.package_state("phaser") == "available"
    staged.set_package_enabled("phaser", True)
    assert staged.package_state("phaser") == "enabled"
    staged.set_package_profile_enabled("phaser", "full", True)
    assert staged.package_profile_state("phaser", "full") == "enabled"
    staged.set_package_profile_enabled("phaser", "full", False)
    assert staged.package_profile_state("phaser", "full") == "disabled"
    staged.set_package_profile_available("phaser", "full")
    assert staged.package_profile_state("phaser", "full") == "available"
    assert staged.config["guides"] == {"enabled": ["other/readme.txt"], "disabled": []}
    staged.set_package_available("phaser")
    assert staged.config["guides"] == {"enabled": [], "disabled": []}


def test_invalid_package_guide_is_atomic(guides):
    """An invalid guide does not partially mutate package peers in memory or on disk."""
    project, codex, manager, cli = guides
    write_package(manager, 'skills = ["base"]\nguides = ["missing/"]\n')
    config = project / ".codex/codexmgr.toml"
    before = config.read_bytes()
    assert cli("package", "enable", "--no-sync", "phaser")[0] == 1
    assert config.read_bytes() == before
    staged = load_staged_config(project, codex, manager)
    original = deepcopy(staged.config)
    with pytest.raises(CommandError):
        staged.set_package_enabled("phaser", True)
    assert staged.config == original


@pytest.mark.parametrize("failure", [False, True])
@pytest.mark.parametrize("existing_root", [False, True])
def test_jit_restores_guides_after_child_exit(guides, failure, existing_root):
    """Temporary guide trees restore exactly after an external child's success/failure."""
    project, codex, manager, _ = guides
    write_guide(manager, "games/.guides/deep.md")
    write_package(manager, 'guides = ["games/"]\n')
    local = project / ".guides/local.txt"
    if existing_root:
        local.parent.mkdir()
        local.write_bytes(b"mine")
    request = CodexJitRequest(True, ["phaser"], [], [])
    base = {"guides": {"enabled": [], "disabled": []}}
    original = deepcopy(base)
    state = build_jit_project_state(base, request, project, codex, manager)
    assert base == original
    assert len(state.guide_copies) == 4
    config = (project / ".codex/codexmgr.toml").read_bytes()

    def external_child(cwd, args):
        """Simulate only the external Codex process; inspect real overlay outputs."""
        assert (cwd / ".guides/games/.guides/deep.md").exists()
        if failure:
            raise RuntimeError("child failed")
        return 7

    if failure:
        with pytest.raises(RuntimeError, match="child failed"):
            run_with_jit_overlay(request, project, codex, manager, external_child)
    else:
        assert run_with_jit_overlay(request, project, codex, manager, external_child) == 7
    assert (project / ".codex/codexmgr.toml").read_bytes() == config
    if existing_root:
        assert list(local.parent.iterdir()) == [local]
        assert local.read_bytes() == b"mine"
    else:
        assert not (project / ".guides").exists()


def test_jit_rejects_unrelated_symlinks_before_snapshot(guides):
    """Snapshot preflight must not dereference or replace unrelated guide symlinks."""
    project, codex, manager, _ = guides
    write_package(manager, 'guides = ["games/"]\n')
    root = project / ".guides"
    root.mkdir()
    outside = project.parent / "private.txt"
    outside.write_bytes(b"private")
    link = root / "local-link"
    link.symlink_to(outside)

    def external_child(cwd, args):
        """The external Codex process must not start after unsafe snapshot discovery."""
        pytest.fail("unsafe guide snapshot reached child process")

    with pytest.raises(CommandError, match="symlink"):
        run_with_jit_overlay(CodexJitRequest(True, ["phaser"], [], []), project, codex, manager, external_child)
    assert link.is_symlink()
    assert outside.read_bytes() == b"private"
    assert not (root / "games").exists()
