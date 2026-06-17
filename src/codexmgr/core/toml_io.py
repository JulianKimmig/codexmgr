"""Small TOML IO helpers for codexmgr-managed configuration files."""

import json
import re
from collections.abc import Mapping, MutableMapping, Sequence
from pathlib import Path
from typing import Any

import tomlkit
from tomlkit.exceptions import TOMLKitError

from .errors import CommandError

BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


def load_toml_file(path: Path) -> MutableMapping[str, Any]:
    """Load a TOML file and convert parse failures into CommandError.

    Args:
        path: TOML file path to read.

    Returns:
        Parsed TOML document.
    """
    try:
        return tomlkit.parse(path.read_text(encoding="utf-8"))
    except TOMLKitError as exc:
        raise CommandError(f"Invalid TOML in {path}: {exc}") from exc


def load_optional_toml_file(path: Path) -> MutableMapping[str, Any]:
    """Load a TOML file or return an empty document when it is missing.

    Args:
        path: Optional TOML file path to read.

    Returns:
        Parsed TOML document, or an empty TOML document.
    """
    if not path.exists():
        return tomlkit.document()
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


def new_toml_table() -> MutableMapping[str, Any]:
    """Create an empty TOML table suitable for insertion into a document.

    Returns:
        A mutable TOML table.
    """
    return tomlkit.table()


def ensure_toml_table(
    container: MutableMapping[str, Any],
    key: str,
    error_message: str,
) -> MutableMapping[str, Any]:
    """Return an existing child table or create a new one.

    Args:
        container: Parent TOML mapping.
        key: Child table key.
        error_message: Error to raise when the key exists but is not a table.

    Returns:
        Mutable child TOML table.
    """
    existing = container.get(key)
    if existing is None:
        table = new_toml_table()
        container[key] = table
        return table
    if not isinstance(existing, MutableMapping):
        raise CommandError(error_message)
    return existing


def plain_toml_value(value: Any) -> Any:
    """Convert TOMLKit scalar/container wrappers into plain Python values.

    Args:
        value: TOMLKit value or plain Python value.

    Returns:
        Plain Python value with mappings and lists recursively converted.
    """
    unwrap = getattr(value, "unwrap", None)
    if callable(unwrap):
        return unwrap()
    if isinstance(value, Mapping):
        return {key: plain_toml_value(item) for key, item in value.items()}
    if _is_sequence(value):
        return [plain_toml_value(item) for item in value]
    return value


def format_toml_value(value: Any) -> str:
    """Format a Python value as a TOML literal.

    Args:
        value: Supported TOML scalar, list, or mapping value.

    Returns:
        TOML literal string.
    """
    return _format_value(plain_toml_value(value))


def dump_toml(data: Mapping[str, Any]) -> str:
    """Serialize supported TOML data into a TOML document.

    Args:
        data: Parsed TOML-style mapping to serialize.

    Returns:
        TOML document text ending with a newline when non-empty.
    """
    _reject_nested_tables_in_array_items(data)
    text = tomlkit.dumps(data)
    return text if not text or text.endswith("\n") else f"{text}\n"


def _reject_nested_tables_in_array_items(
    data: Mapping[str, Any],
    prefix: tuple[str, ...] = (),
) -> None:
    """Fail before TOML serialization would emit unsupported nested arrays.

    Args:
        data: Mapping for the current TOML table.
        prefix: TOML path for the current table.
    """
    for key, value in data.items():
        path = (*prefix, key)
        if _is_array_of_tables(value):
            _reject_nested_array_tables(value, path)
        elif isinstance(value, Mapping):
            _reject_nested_tables_in_array_items(value, path)


def _reject_nested_array_tables(items: Sequence[Any], prefix: tuple[str, ...]) -> None:
    """Reject nested mappings inside array-of-table items.

    Args:
        items: Array items that are all mappings.
        prefix: TOML path for the array-of-table.
    """
    for item in items:
        for key, value in item.items():
            if isinstance(value, Mapping):
                path = ".".join((*prefix, key))
                raise CommandError(
                    f"Unsupported nested table in TOML array item: {path}"
                )


def _is_array_of_tables(value: Any) -> bool:
    """Return whether a value should be emitted as TOML array-of-tables.

    Args:
        value: Candidate value from a TOML mapping.

    Returns:
        True when the value is a non-empty list containing only mappings.
    """
    return (
        _is_sequence(value)
        and bool(value)
        and all(isinstance(item, Mapping) for item in value)
    )


def _is_sequence(value: Any) -> bool:
    """Return whether a value is a non-string sequence.

    Args:
        value: Candidate sequence.

    Returns:
        True when the value behaves like a list or tuple.
    """
    return isinstance(value, Sequence) and not isinstance(value, str | bytes)


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
