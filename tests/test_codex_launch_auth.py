"""Verify managed Codex launch when the global auth symlink cannot be created."""

import errno
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def configured_launch(workspace, monkeypatch):
    """Return the temporary project and Codex home with global auth configured.

    Args:
        workspace: Isolated project and Codex home paths.
        monkeypatch: Fixture for setting the global auth source.
    Returns:
        The project and Codex home paths used by the CLI.
    """
    project, codex_home = workspace
    (project / ".codex" / ".runtime").mkdir(parents=True)
    (project / ".codex" / "codexmgr.toml").touch()
    global_auth = codex_home / "auth.json"
    global_auth.write_text("global auth", encoding="utf-8")
    monkeypatch.setenv("CODEX_GLOBAL_AUTH", str(global_auth))
    return project, codex_home


@pytest.mark.parametrize(
    ("error_number", "winerror", "reason"),
    [
        pytest.param(errno.EACCES, 5, "Access is denied", id="windows-denied"),
        pytest.param(errno.ENOTSUP, 50, "The request is not supported", id="windows-unsupported"),
        pytest.param(errno.ENOSPC, None, "No space left on device", id="no-space"),
    ],
)
@pytest.mark.parametrize("project_auth_exists", [False, True], ids=["first-launch", "signed-in"])
def test_os_error_creating_auth_link_continues(
    configured_launch, monkeypatch, run_cli, project_auth_exists, error_number, winerror, reason
):
    """Keep project auth and launch Codex when the optional link operation fails."""
    project, codex_home = configured_launch
    project_auth = project / ".codex" / ".runtime" / "auth.json"
    if project_auth_exists:
        project_auth.write_text("project auth", encoding="utf-8")

    def fail_symlink(link, target):
        """Raise the selected OS error at the filesystem boundary."""
        assert link.name == project_auth.name
        assert target == codex_home / "auth.json"
        error = OSError(error_number, reason)
        if winerror is not None:
            error.winerror = winerror
        raise error

    def run_codex(command, cwd, env):
        """Verify the child process starts with the project runtime home."""
        assert command == ["codex", "--version"]
        assert cwd == project
        assert env["CODEX_HOME"] == str(project_auth.parent)
        return SimpleNamespace(returncode=42)

    monkeypatch.setattr(Path, "symlink_to", fail_symlink)
    monkeypatch.setattr("codexmgr.commands.codex.subprocess.run", run_codex)

    exit_code, _, stderr = run_cli(["codex", "--version"], project, codex_home)

    assert exit_code == 42
    if project_auth_exists:
        assert project_auth.read_text(encoding="utf-8") == "project auth"
        assert "Sign in to Codex" not in stderr
    else:
        assert not project_auth.exists()
        assert "Sign in to Codex for this project if prompted" in stderr
    assert "Developer Mode" not in stderr
    if winerror != 5:
        assert reason in stderr
    elif project_auth_exists:
        assert stderr == ""
    else:
        assert "Windows denied access while creating the global auth link" in stderr
    assert (codex_home / "auth.json").read_text(encoding="utf-8") == "global auth"
    assert list(project_auth.parent.glob(".auth-*")) == []


def test_windows_access_denied_creating_staging_directory_raises(
    configured_launch, monkeypatch, run_cli
):
    """A denial writing the runtime directory remains an error."""
    project, codex_home = configured_launch
    runtime_home = project / ".codex" / ".runtime"
    mkdtemp = tempfile.mkdtemp

    def deny_staging_directory(suffix=None, prefix=None, dir=None):
        """Report access denied when creating an auth staging directory.

        Args:
            suffix: Optional suffix for the temporary directory name.
            prefix: Optional prefix for the temporary directory name.
            dir: Optional parent directory for the temporary directory.
        Returns:
            The created path for temporary directories outside auth staging.
        """
        if dir == runtime_home and prefix == ".auth-":
            denied = PermissionError(errno.EACCES, "Cannot create staging directory")
            denied.winerror = 5
            raise denied
        return mkdtemp(suffix, prefix, dir)

    # Older Windows Python versions retry PermissionError from mkdir in mkdtemp.
    monkeypatch.setattr(tempfile, "mkdtemp", deny_staging_directory)

    with pytest.raises(PermissionError, match="Cannot create staging directory"):
        run_cli(["codex", "--version"], project, codex_home)
