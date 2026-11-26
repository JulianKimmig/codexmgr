"""Verify MCP source references through package CLI, TUI, and temporary launches."""

from pathlib import Path

import pytest

from codexmgr.commands.codex_jit import CodexJitRequest, run_with_jit_overlay
from codexmgr.core.errors import CommandError
from codexmgr.core.toml_io import dump_toml
from codexmgr.tui.saving import save_staged_config
from codexmgr.tui.state import load_staged_config
from test_package_includes import packages
from test_package_skill_groups import write_package


def write_mcp_source(manager: Path, name: str, server: str | None = None) -> Path:
    """Write a reusable MCP source and return its manifest path.

    Args:
        manager: Test manager home.
        name: Source filename stem and its test server command.
        server: Optional server ID, defaulting to the source name.
    """
    source = manager / "mcp" / f"{name}.toml"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(f'[mcp_servers.{server or name}]\ncommand = "{name}"\n', encoding="utf-8")
    return source


def test_mcp_packages_compose_root_profiles_and_nested_sources(
    packages, read_project_config, read_codex_config, read_lock,
):
    """Package source names resolve in first-seen order and apply through normal MCP generation."""
    project, _, manager, cli = packages
    for name in ("root", "nested", "profile"):
        write_mcp_source(manager, name)
    write_package(manager, 'mcp = ["nested"]\n[profiles.full]\nmcp = ["ignored"]\n', "leaf")
    write_package(manager, 'packages = ["leaf"]\n', "middle")
    write_package(
        manager,
        'mcp = ["root"]\npackages = ["middle"]\n[profiles.full]\nmcp = ["profile", "nested"]\n',
        "bundle",
    )
    generated = project / ".codex" / "config.toml"
    original = generated.read_bytes()
    result = cli("package", "enable", "--no-sync", "bundle", "--profile", "full")
    assert result[0] == 0, result[2]
    config = read_project_config(project)
    assert config["mcp"]["enabled"] == ["root", "nested", "profile"]
    assert config["package_selections"]["bundle"] == {
        "root": {"mcp": ["root", "nested"]},
        "profiles": {"full": {"mcp": ["profile", "nested"]}},
    }
    assert generated.read_bytes() == original
    assert cli("apply")[0] == 0
    assert list(read_codex_config(project)["mcp_servers"]) == ["root", "nested", "profile"]
    assert read_lock(project)["mcp"]["enabled"] == ["root", "nested", "profile"]


def test_disable_removes_only_unshared_sources_and_preserves_overrides(
    packages, read_project_config, read_codex_config, read_lock,
):
    """A retained profile protects its sources until release, with project overrides preserved."""
    project, _, manager, cli = packages
    for name in ("shared", "unique"):
        write_mcp_source(manager, name)
    write_package(manager, 'mcp = ["shared", "unique"]\n[profiles.full]\nmcp = ["shared"]\n', "bundle")
    config = project / ".codex" / "codexmgr.toml"
    config.write_text('[mcp.servers.shared]\nenabled = false\n', encoding="utf-8")
    assert cli("package", "enable", "bundle", "--profile", "full")[0] == 0
    assert cli("package", "disable", "bundle")[0] == 0
    assert read_codex_config(project)["mcp_servers"] == {
        "shared": {"command": "shared", "enabled": False},
    }
    assert read_project_config(project)["mcp"]["enabled"] == ["shared"]

    # A saved selection also supports cleanup when its profile or source is missing.
    (manager / "mcp" / "shared.toml").unlink()
    write_package(manager, 'mcp = []\n', "bundle")
    assert cli("package", "disable", "bundle", "--profile", "full")[0] == 0
    assert read_project_config(project)["mcp"] == {
        "enabled": [], "servers": {"shared": {"enabled": False}},
    }
    assert read_codex_config(project)["mcp_servers"] == {"shared": {"enabled": False}}
    assert read_lock(project)["mcp"]["enabled"] == []


@pytest.mark.parametrize(
    ("manifest", "error"),
    [
        ('mcp = "existing"\n', "mcp must be a list of strings"),
        ('mcp = ["missing"]\n', "MCP source not found"),
        ('mcp = ["../existing"]\n', "MCP source name must be a bare name"),
        ('mcp = ["C:existing"]\n', "MCP source name must be a bare name"),
        ('mcp = ["existing.toml"]\n', "MCP source name must be a bare name"),
        ('mcp = ["invalid"]\n', "must contain an [mcp_servers] table"),
        ('mcp = ["conflict"]\n', "Duplicate MCP server id existing"),
    ],
)
def test_package_mcp_rejects_invalid_source_set_before_writing(packages, manifest, error):
    """Any invalid source fails the whole CLI batch even when sync is suppressed."""
    project, _, manager, cli = packages
    write_mcp_source(manager, "existing")
    write_mcp_source(manager, "conflict", server="existing")
    write_mcp_source(manager, "invalid").write_text('command = "invalid"\n', encoding="utf-8")
    assert cli("mcp", "enable", "existing")[0] == 0
    write_package(manager, 'skills = ["success"]\n', "first")
    write_package(manager, manifest, "broken")
    config = project / ".codex" / "codexmgr.toml"
    before = config.read_bytes()
    code, _, stderr = cli("package", "enable", "--no-sync", "first", "broken")
    assert code == 1
    assert error in stderr
    assert config.read_bytes() == before


def test_staged_mcp_only_package_tracks_availability_and_shared_usage(
    packages, read_project_config, read_codex_config,
):
    """MCP-only package rows can be staged, shared, cleared, and saved through their normal handlers."""
    project, codex, manager, _ = packages
    write_mcp_source(manager, "shared")
    write_mcp_source(manager, "unique")
    write_mcp_source(manager, "conflict", server="shared")
    write_package(manager, 'mcp = ["shared"]\n', "child")
    write_package(manager, 'mcp = ["unique"]\npackages = ["child"]\n', "parent")
    write_package(manager, 'mcp = ["conflict"]\nskills = ["other"]\n', "broken")
    staged = load_staged_config(project, codex, manager)
    staged.set_package_enabled("parent", True)
    assert staged.package_state("parent") == "enabled"
    assert staged.package_state("child") == "available"
    before = dump_toml(staged.config)
    with pytest.raises(CommandError, match="Duplicate MCP server id shared"):
        staged.set_package_enabled("broken", True)
    assert dump_toml(staged.config) == before

    staged.set_package_enabled("child", True)
    staged.set_package_available("parent")
    assert staged.package_state("parent") == "available"
    assert staged.package_state("child") == "enabled"
    save_staged_config(staged, no_sync=False)
    assert read_project_config(project)["mcp"]["enabled"] == ["shared"]
    assert read_codex_config(project)["mcp_servers"] == {"shared": {"command": "shared"}}


@pytest.mark.parametrize("failure", [False, True])
def test_jit_mcp_restores_generated_config_and_lock(
    packages, read_codex_config, read_lock, failure,
):
    """The temporary launch includes bundled sources and restores saved project files on exit."""
    project, codex, manager, cli = packages
    write_mcp_source(manager, "base")
    write_mcp_source(manager, "temporary")
    write_package(manager, 'mcp = ["temporary"]\n', "child")
    write_package(manager, 'packages = ["child"]\n', "parent")
    assert cli("mcp", "enable", "base")[0] == 0
    paths = [project / ".codex" / name for name in ("codexmgr.toml", "config.toml", "codexmgr.lock")]
    before = [path.read_bytes() for path in paths]
    request = CodexJitRequest(True, ["parent"], [], ["exec"])

    def run_codex(cwd: Path, args: list[str]) -> int:
        """Read the real overlay in place of launching the external Codex process."""
        assert cwd == project
        assert args == ["exec"]
        assert read_codex_config(cwd)["mcp_servers"]["temporary"] == {"command": "temporary"}
        assert read_lock(cwd)["mcp"]["enabled"] == ["base", "temporary"]
        if failure:
            raise RuntimeError("external process failed")
        return 7

    if failure:
        with pytest.raises(RuntimeError, match="external process failed"):
            run_with_jit_overlay(request, project, codex, manager, run_codex)
    else:
        assert run_with_jit_overlay(request, project, codex, manager, run_codex) == 7
    assert [path.read_bytes() for path in paths] == before
