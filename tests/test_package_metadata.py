"""Tests for importable package metadata."""

import importlib.resources
import tomllib

import codexmgr


def test_runtime_version_matches_project_metadata():
    """The importable package version stays aligned with pyproject.toml."""
    with open("pyproject.toml", "rb") as pyproject_file:
        project = tomllib.load(pyproject_file)["project"]

    assert codexmgr.__version__ == project["version"]


def test_package_includes_pep_561_typed_marker():
    """The package exposes a py.typed marker for typed consumers."""
    typed_marker = importlib.resources.files("codexmgr").joinpath("py.typed")

    assert typed_marker.is_file()


def test_project_metadata_includes_repository_url():
    """The package metadata points users to the source repository."""
    with open("pyproject.toml", "rb") as pyproject_file:
        project = tomllib.load(pyproject_file)["project"]

    assert project["urls"]["Repository"] == "https://github.com/JulianKimmig/codexmgr/"
