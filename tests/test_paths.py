from pathlib import Path

import pytest

from codexmgr.paths import global_codex_dir


def test_defaults_to_home_codex_directory(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("CODEX_HOME", raising=False)

    assert global_codex_dir() == Path.home() / ".codex"


def test_uses_codex_home_environment_variable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CODEX_HOME", "/tmp/custom-codex-home")

    assert global_codex_dir() == Path("/tmp/custom-codex-home")
