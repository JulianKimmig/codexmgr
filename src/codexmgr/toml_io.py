"""Small TOML IO helpers for codexmgr-managed configuration files."""

import json
import re
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .errors import CommandError

BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


def load_toml_file(path: Path) -> dict[str, Any]:
    """Load a TOML file and convert parse failures into CommandError.

    Args:
        path: TOML file path to read.

    Returns:
        Parsed TOML document.
    """
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise CommandError(f"Invalid TOML in {path}: {exc}") from exc


def load_optional_toml_file(path: Path) -> dict[str, Any]:
    """Load a TOML file or return an empty document when it is missing.

    Args:
        path: Optional TOML file path to read.

    Returns:
        Parsed TOML document, or an empty dictionary.
    """
    if not path.exists():
        return {}
    return load_toml_file(path)


def write_toml_file(path: Path, data: Mapping[str, Any]) -> None:
    """Write TOML data with UTF-8 encoding.

    Args:
        path: TOML file path to write.
        data: Mapping to serialize.

    Returns:
        None. The file is replaced atomically by pathlib's write_text behavior.
    """
    path.write_text(dump_toml(data), encoding="utf-8")


def format_toml_value(value: Any) -> str:
    """Format a Python value as a TOML literal.

    Args:
        value: Supported TOML scalar, list, or mapping value.

    Returns:
        TOML literal string.
    """
    return _format_value(value)


def dump_toml(data: Mapping[str, Any]) -> str:
    """Serialize supported TOML data into a deterministic TOML document.

    Args:
        data: Parsed TOML-style mapping to serialize.

    Returns:
        TOML document text ending with a newline when non-empty.
    """
    tables = list(_iter_tables(data))
    chunks = [_format_table(path, values, is_array) for is_array, path, values in tables]
    return "\n\n".join(chunks) + ("\n" if chunks else "")


def _iter_tables(
    data: Mapping[str, Any],
    prefix: tuple[str, ...] = (),
) -> list[tuple[bool, tuple[str, ...], dict[str, Any]]]:
    """Flatten nested TOML tables into renderable table chunks.

    Args:
        data: Mapping for the current TOML table.
        prefix: TOML path for the current table.

    Returns:
        Table chunks as ``(is_array, path, values)`` tuples.
    """
    scalars: dict[str, Any] = {}
    children: list[tuple[str, Mapping[str, Any]]] = []
    arrays: list[tuple[str, list[Mapping[str, Any]]]] = []

    for key, value in data.items():
        if _is_array_of_tables(value):
            arrays.append((key, value))
        elif isinstance(value, Mapping):
            children.append((key, value))
        else:
            scalars[key] = value

    tables: list[tuple[bool, tuple[str, ...], dict[str, Any]]] = []
    if scalars:
        tables.append((False, prefix, scalars))

    for key, child in children:
        tables.extend(_iter_tables(child, (*prefix, key)))

    for key, items in arrays:
        tables.extend(_iter_array_tables(items, (*prefix, key)))

    return tables


def _iter_array_tables(
    items: list[Mapping[str, Any]],
    prefix: tuple[str, ...],
) -> list[tuple[bool, tuple[str, ...], dict[str, Any]]]:
    """Flatten TOML array-of-table items into renderable chunks.

    Args:
        items: Array items that are all mappings.
        prefix: TOML path for the array-of-table.

    Returns:
        Array table chunks as ``(True, path, values)`` tuples.
    """
    tables: list[tuple[bool, tuple[str, ...], dict[str, Any]]] = []
    for item in items:
        for key, value in item.items():
            if isinstance(value, Mapping):
                path = ".".join((*prefix, key))
                raise CommandError(
                    f"Unsupported nested table in TOML array item: {path}"
                )
        scalars = dict(item)
        tables.append((True, prefix, scalars))
    return tables


def _format_table(path: tuple[str, ...], values: Mapping[str, Any], is_array: bool) -> str:
    """Format one TOML table chunk.

    Args:
        path: TOML table path.
        values: Scalar values to write in the table.
        is_array: Whether the table is an array-of-tables item.

    Returns:
        TOML text for the table chunk.
    """
    formatted_path = ".".join(_format_key(part) for part in path)
    lines = []
    if path:
        heading = f"[[{formatted_path}]]" if is_array else f"[{formatted_path}]"
        lines.append(heading)
    lines.extend(f"{_format_key(key)} = {_format_value(value)}" for key, value in values.items())
    return "\n".join(lines)


def _is_array_of_tables(value: Any) -> bool:
    """Return whether a value should be emitted as TOML array-of-tables.

    Args:
        value: Candidate value from a TOML mapping.

    Returns:
        True when the value is a non-empty list containing only mappings.
    """
    return isinstance(value, list) and bool(value) and all(isinstance(item, Mapping) for item in value)


def _format_key(key: str) -> str:
    """Format a TOML key, quoting keys that are not bare-key compatible.

    Args:
        key: Raw key name.

    Returns:
        TOML key text.
    """
    if BARE_KEY.match(key):
        return key
    return json.dumps(key)


def _format_value(value: Any) -> str:
    """Format a supported Python value as TOML.

    Args:
        value: Value to serialize.

    Returns:
        TOML literal or inline table text.
    """
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return f"[{', '.join(_format_value(item) for item in value)}]"
    if isinstance(value, Mapping):
        items = (f"{_format_key(key)}={_format_value(item)}" for key, item in value.items())
        return f"{{{', '.join(items)}}}"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    raise CommandError(f"Unsupported TOML value type: {type(value).__name__}")
