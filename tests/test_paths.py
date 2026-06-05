from pathlib import Path

import pytest

from codexmgr.paths import global_codex_dir, global_codexmgr_dir


def test_defaults_to_home_codex_directory(monkeypatch: pytest.MonkeyPatch):
    """CODEX_HOME defaults to ~/.codex when the environment variable is absent."""
    monkeypatch.delenv("CODEX_HOME", raising=False)

    assert global_codex_dir() == Path.home() / ".codex"


def test_uses_codex_home_environment_variable(monkeypatch: pytest.MonkeyPatch):
    """CODEX_HOME overrides the default Codex home directory."""
    monkeypatch.setenv("CODEX_HOME", "/tmp/custom-codex-home")

    assert global_codex_dir() == Path("/tmp/custom-codex-home")


def test_codexmgr_home_defaults_to_home_codexmgr_directory(
    monkeypatch: pytest.MonkeyPatch,
):
    """CODEXMGR_HOME defaults to ~/.codexmgr when the environment variable is absent."""
    monkeypatch.delenv("CODEXMGR_HOME", raising=False)

    assert global_codexmgr_dir() == Path.home() / ".codexmgr"


def test_codexmgr_home_uses_environment_variable(monkeypatch: pytest.MonkeyPatch):
    """CODEXMGR_HOME overrides the default codexmgr home directory."""
    monkeypatch.setenv("CODEXMGR_HOME", "/tmp/custom-codexmgr-home")

    assert global_codexmgr_dir() == Path("/tmp/custom-codexmgr-home")
