from pathlib import Path

from .errors import CommandError

BEGIN_MARKER = "<!-- BEGIN CODEXMGR GENERATED -->"
END_MARKER = "<!-- END CODEXMGR GENERATED -->"


def write_managed_agents_md(path: Path, generated_markdown: str) -> None:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    updated = _replace_block(current, generated_markdown)
    path.write_text(updated, encoding="utf-8")


def _replace_block(current: str, generated_markdown: str) -> str:
    begin_count = current.count(BEGIN_MARKER)
    end_count = current.count(END_MARKER)
    if begin_count != end_count:
        raise CommandError("Incomplete CODEXMGR generated block in AGENTS.md")
    if begin_count > 1:
        raise CommandError("Multiple CODEXMGR generated blocks in AGENTS.md")

    block = _format_block(generated_markdown)
    if begin_count == 0:
        return _append_block(current, block)

    begin_index = current.index(BEGIN_MARKER)
    end_index = current.index(END_MARKER, begin_index)
    after_index = end_index + len(END_MARKER)
    return f"{current[:begin_index]}{block}{current[after_index:]}"


def _append_block(current: str, block: str) -> str:
    if not current:
        return f"{block}\n"
    return f"{current.rstrip('\n')}\n\n{block}\n"


def _format_block(generated_markdown: str) -> str:
    body = generated_markdown.rstrip("\n")
    if not body:
        return f"{BEGIN_MARKER}\n{END_MARKER}"
    return f"{BEGIN_MARKER}\n{body}\n{END_MARKER}"
