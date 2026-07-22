"""Reusable rendering for marker-delimited codexmgr-managed text blocks."""

from ..core.errors import CommandError


def render_managed_block(
    current: str,
    generated: str,
    *,
    begin_marker: str,
    end_marker: str,
    artifact_name: str,
) -> str:
    """Replace or append one marker-delimited generated text block.

    Args:
        current: Existing artifact content, or an empty string when missing.
        generated: Generated content to place between the markers.
        begin_marker: Exact line marking the beginning of managed content.
        end_marker: Exact line marking the end of managed content.
        artifact_name: Human-readable artifact name for validation errors.

    Returns:
        Full artifact content with one current codexmgr-managed block.

    Raises:
        CommandError: If existing managed-block markers are malformed.
    """
    begin_count = current.count(begin_marker)
    end_count = current.count(end_marker)
    if begin_count != end_count:
        raise CommandError(
            f"Incomplete CODEXMGR generated block in {artifact_name}"
        )
    if begin_count > 1:
        raise CommandError(f"Multiple CODEXMGR generated blocks in {artifact_name}")

    block = _format_block(generated, begin_marker, end_marker)
    if begin_count == 0:
        return _append_block(current, block)

    begin_index = current.index(begin_marker)
    end_index = current.index(end_marker, begin_index)
    after_index = end_index + len(end_marker)
    return f"{current[:begin_index]}{block}{current[after_index:]}"


def _append_block(current: str, block: str) -> str:
    """Append a formatted managed block to existing content.

    Args:
        current: Existing artifact content.
        block: Fully formatted block including both markers.

    Returns:
        Content ending in the appended managed block and a newline.
    """
    if not current:
        return f"{block}\n"
    trimmed = current.rstrip("\n")
    return f"{trimmed}\n\n{block}\n"


def _format_block(generated: str, begin_marker: str, end_marker: str) -> str:
    """Wrap generated content in its managed-block markers.

    Args:
        generated: Generated text to normalize and wrap.
        begin_marker: Beginning marker line.
        end_marker: Ending marker line.

    Returns:
        Marker-delimited content without a trailing newline.
    """
    body = generated.rstrip("\n")
    if not body:
        return f"{begin_marker}\n{end_marker}"
    return f"{begin_marker}\n{body}\n{end_marker}"
