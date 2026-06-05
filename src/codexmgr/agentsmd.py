"""Manage configured AGENTS.md template sources and rendered output."""

from pathlib import Path
from typing import Any

from .agents_file import write_managed_agents_md
from .errors import CommandError
from .options import list_toml_options
from .paths import agents_md_path, config_path, resolve_template
from .project_config import (
    agents_md_sources,
    load_required_project_config,
    require_codex_dir,
    set_agents_md_sources,
)
from .renderer import render_agents_markdown
from .toml_io import load_optional_toml_file, load_toml_file, write_toml_file


def add_agentsmd(reference: str, cwd: Path, codexmgr_home: Path) -> str:
    """Add an AGENTS.md template reference to project configuration.

    Args:
        reference: Named template or TOML path to add.
        cwd: Project directory whose codexmgr.toml should be updated.
        codexmgr_home: codexmgr home used to validate named template references.

    Returns:
        The reference that was added or already present.
    """
    require_codex_dir(cwd)
    resolve_template(reference, cwd, codexmgr_home)

    config = load_optional_toml_file(config_path(cwd))
    sources = agents_md_sources(config)
    if reference not in sources:
        sources.append(reference)
    set_agents_md_sources(config, sources)
    write_toml_file(config_path(cwd), config)
    return reference


def remove_agentsmd(source_id: str, cwd: Path) -> str:
    """Remove an AGENTS.md template reference from project configuration.

    Args:
        source_id: Source identifier or reference to remove.
        cwd: Project directory whose codexmgr.toml should be updated.

    Returns:
        The removed source identifier.
    """
    config = load_required_project_config(cwd)
    sources = agents_md_sources(config)
    if source_id not in sources:
        raise CommandError(f"Source not found in codexmgr.toml: {source_id}")

    set_agents_md_sources(config, [source for source in sources if source != source_id])
    write_toml_file(config_path(cwd), config)
    return source_id


def list_agentsmd_options(codexmgr_home: Path) -> list[str]:
    """List named AGENTS.md template options available to add.

    Args:
        codexmgr_home: codexmgr home directory containing the ``agentsmd``
            template store.

    Returns:
        Sorted template names that can be passed to ``codexmgr agentsmd add``.
    """
    return list_toml_options(codexmgr_home / "agentsmd")


def show_agentsmd(reference: str, cwd: Path, codexmgr_home: Path) -> str:
    """Render one AGENTS.md template reference as markdown.

    Args:
        reference: Named template or TOML path to render.
        cwd: Project directory used to resolve path references.
        codexmgr_home: codexmgr home used to resolve named references.

    Returns:
        Rendered markdown for the template.
    """
    source_id, template_data = _load_template(reference, cwd, codexmgr_home)
    return render_agents_markdown({source_id: template_data})


def validate_agentsmd(reference: str, cwd: Path, codexmgr_home: Path) -> str:
    """Validate that one AGENTS.md template can be loaded and rendered.

    Args:
        reference: Named template or TOML path to validate.
        cwd: Project directory used to resolve path references.
        codexmgr_home: codexmgr home used to resolve named references.

    Returns:
        Source identifier for the valid template.
    """
    source_id, template_data = _load_template(reference, cwd, codexmgr_home)
    render_agents_markdown({source_id: template_data})
    return source_id


def init_agentsmd_template(name: str, codexmgr_home: Path) -> Path:
    """Create a starter named AGENTS.md template.

    Args:
        name: Bare template name to create.
        codexmgr_home: codexmgr home where the template should be created.

    Returns:
        Path to the created template file.
    """
    _validate_template_name(name)
    template_dir = codexmgr_home / "agentsmd"
    template_dir.mkdir(parents=True, exist_ok=True)
    path = template_dir / f"{name}.toml"
    if path.exists():
        raise CommandError(f"Template already exists: {path}")
    path.write_text(_starter_template(), encoding="utf-8")
    return path


def resolve_locked_agents_md(
    config: dict[str, Any],
    cwd: Path,
    codexmgr_home: Path,
) -> dict[str, Any]:
    """Resolve configured AGENTS.md sources into lock data.

    Args:
        config: Parsed .codex/codexmgr.toml content.
        cwd: Project directory used to resolve path sources.
        codexmgr_home: codexmgr home used to resolve named sources.

    Returns:
        Resolved source data keyed by source identifier.
    """
    locked_sources: dict[str, Any] = {}
    for reference in agents_md_sources(config):
        source_id, template_path = resolve_template(reference, cwd, codexmgr_home)
        if source_id in locked_sources:
            raise CommandError(f"Duplicate AGENTS.md source identifier: {source_id}")
        template_data = load_toml_file(template_path)
        if not template_data:
            raise CommandError(f"Template is empty: {template_path}")
        locked_sources[source_id] = template_data
    return locked_sources


def write_agents_md(cwd: Path, locked_sources: dict[str, Any]) -> None:
    """Write resolved AGENTS.md lock data to the managed block.

    Args:
        cwd: Project directory whose root AGENTS.md should be updated.
        locked_sources: Resolved source data keyed by source identifier.
    """
    write_managed_agents_md(agents_md_path(cwd), render_agents_markdown(locked_sources))


def _load_template(
    reference: str,
    cwd: Path,
    codexmgr_home: Path,
) -> tuple[str, dict[str, Any]]:
    """Load a named or path-backed AGENTS.md template.

    Args:
        reference: Named template or TOML path to load.
        cwd: Project directory used to resolve path references.
        codexmgr_home: codexmgr home used to resolve named references.

    Returns:
        Source identifier and parsed TOML data.
    """
    source_id, template_path = resolve_template(reference, cwd, codexmgr_home)
    template_data = load_toml_file(template_path)
    if not template_data:
        raise CommandError(f"Template is empty: {template_path}")
    return source_id, template_data


def _validate_template_name(name: str) -> None:
    """Validate a starter template name.

    Args:
        name: Candidate bare template name.

    Returns:
        None. ``CommandError`` is raised for invalid names.
    """
    if not name or "/" in name or "\\" in name or name.endswith(".toml"):
        raise CommandError(f"Template name must be a bare name: {name}")


def _starter_template() -> str:
    """Return starter TOML content for a new AGENTS.md template.

    Returns:
        A minimal renderable template document.
    """
    return (
        "[instructions]\n"
        'text = """\n'
        "- Replace this with reusable project guidance.\n"
        '"""\n'
    )
