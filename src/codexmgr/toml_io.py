import json
import re
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .errors import CommandError

BARE_KEY = re.compile(r"^[A-Za-z0-9_-]+$")


def load_toml_file(path: Path) -> dict[str, Any]:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise CommandError(f"Invalid TOML in {path}: {exc}") from exc


def load_optional_toml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return load_toml_file(path)


def write_toml_file(path: Path, data: Mapping[str, Any]) -> None:
    path.write_text(dump_toml(data), encoding="utf-8")


def format_toml_value(value: Any) -> str:
    return _format_value(value)


def dump_toml(data: Mapping[str, Any]) -> str:
    tables = list(_iter_tables(data))
    chunks = [_format_table(path, values, is_array) for is_array, path, values in tables]
    return "\n\n".join(chunks) + ("\n" if chunks else "")


def _iter_tables(
    data: Mapping[str, Any],
    prefix: tuple[str, ...] = (),
) -> list[tuple[bool, tuple[str, ...], dict[str, Any]]]:
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
    tables: list[tuple[bool, tuple[str, ...], dict[str, Any]]] = []
    for item in items:
        scalars = {key: value for key, value in item.items() if not isinstance(value, Mapping)}
        tables.append((True, prefix, scalars))
    return tables


def _format_table(path: tuple[str, ...], values: Mapping[str, Any], is_array: bool) -> str:
    formatted_path = ".".join(_format_key(part) for part in path)
    lines = []
    if path:
        heading = f"[[{formatted_path}]]" if is_array else f"[{formatted_path}]"
        lines.append(heading)
    lines.extend(f"{_format_key(key)} = {_format_value(value)}" for key, value in values.items())
    return "\n".join(lines)


def _is_array_of_tables(value: Any) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, Mapping) for item in value)


def _format_key(key: str) -> str:
    if BARE_KEY.match(key):
        return key
    return json.dumps(key)


def _format_value(value: Any) -> str:
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
