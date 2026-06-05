"""Shared pytest fixtures for codexmgr tests."""

import io
import tomllib
from pathlib import Path
from typing import Callable

import pytest

from codexmgr.cli import main

BEGIN = "<!-- BEGIN CODEXMGR GENERATED -->"
END = "<!-- END CODEXMGR GENERATED -->"


@pytest.fixture
def workspace(tmp_path: Path) -> tuple[Path, Path]:
    """Create isolated project and global Codex home directories."""
    project = tmp_path / "project"
    codex_home = tmp_path / "codex-home"
    project.mkdir()
    codex_home.mkdir()
    return project, codex_home


@pytest.fixture
def write_home_template() -> Callable[[Path, str, str], Path]:
    """Return a helper that writes a named global AGENTS.md template."""
    return _write_home_template


@pytest.fixture
def run_cli():
    """Return a helper that runs the CLI with captured output streams."""
    return _run_cli


@pytest.fixture
def run_cli_with_environment():
    """Return a helper that runs the CLI without an injected Codex home."""
    return _run_cli_with_environment


@pytest.fixture
def read_project_config():
    """Return a helper that loads the project codexmgr.toml file."""
    return _read_project_config


@pytest.fixture
def read_lock():
    """Return a helper that loads the project codexmgr.lock file."""
    return _read_lock


@pytest.fixture
def read_codex_config():
    """Return a helper that loads the project .codex/config.toml file."""
    return _read_codex_config


@pytest.fixture
def assert_agents_md():
    """Return a helper that asserts the generated managed AGENTS.md block."""
    return _assert_agents_md


def _write_home_template(codex_home: Path, name: str, content: str) -> Path:
    template_dir = codex_home / "agentsmd"
    template_dir.mkdir(parents=True, exist_ok=True)
    path = template_dir / f"{name}.toml"
    path.write_text(content, encoding="utf-8")
    return path


def _run_cli(argv: list[str], project: Path, codex_home: Path):
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = main(
        argv,
        cwd=project,
        codex_home=codex_home,
        stdout=stdout,
        stderr=stderr,
    )
    return exit_code, stdout.getvalue(), stderr.getvalue()


def _run_cli_with_environment(argv: list[str], project: Path):
    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = main(argv, cwd=project, stdout=stdout, stderr=stderr)
    return exit_code, stdout.getvalue(), stderr.getvalue()


def _read_project_config(project: Path):
    return tomllib.loads((project / ".codex" / "codexmgr.toml").read_text())


def _read_lock(project: Path):
    return tomllib.loads((project / ".codex" / "codexmgr.lock").read_text())


def _read_codex_config(project: Path):
    return tomllib.loads((project / ".codex" / "config.toml").read_text())


def _assert_agents_md(project: Path, generated: str):
    assert (project / "AGENTS.md").read_text(encoding="utf-8") == (
        f"{BEGIN}\n{generated}{END}\n"
    )
