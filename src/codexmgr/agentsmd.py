from pathlib import Path
from typing import Any

from .agents_file import write_managed_agents_md
from .errors import CommandError
from .paths import agents_md_path, config_path, resolve_template
from .project_config import (
    agents_md_sources,
    load_required_project_config,
    require_codex_dir,
    set_agents_md_sources,
)
from .renderer import render_agents_markdown
from .toml_io import load_optional_toml_file, load_toml_file, write_toml_file


def add_agentsmd(reference: str, cwd: Path, codex_home: Path) -> str:
    require_codex_dir(cwd)
    resolve_template(reference, cwd, codex_home)

    config = load_optional_toml_file(config_path(cwd))
    sources = agents_md_sources(config)
    if reference not in sources:
        sources.append(reference)
    set_agents_md_sources(config, sources)
    write_toml_file(config_path(cwd), config)
    return reference


def remove_agentsmd(source_id: str, cwd: Path) -> str:
    config = load_required_project_config(cwd)
    sources = agents_md_sources(config)
    if source_id not in sources:
        raise CommandError(f"Source not found in codexmgr.toml: {source_id}")

    set_agents_md_sources(config, [source for source in sources if source != source_id])
    write_toml_file(config_path(cwd), config)
    return source_id


def resolve_locked_agents_md(
    config: dict[str, Any],
    cwd: Path,
    codex_home: Path,
) -> dict[str, Any]:
    """Resolve configured AGENTS.md sources into lock data.

    Args:
        config: Parsed .codex/codexmgr.toml content.
        cwd: Project directory used to resolve path sources.
        codex_home: Global Codex home used to resolve named sources.

    Returns:
        Resolved source data keyed by source identifier.
    """
    locked_sources: dict[str, Any] = {}
    for reference in agents_md_sources(config):
        source_id, template_path = resolve_template(reference, cwd, codex_home)
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
