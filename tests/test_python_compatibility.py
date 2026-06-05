"""Tests for compatibility with the declared Python version floor."""

import re
from pathlib import Path

FSTRING_WITH_BACKSLASH_EXPRESSION = re.compile(
    r"""(?i)(?:^|[^A-Za-z0-9_])f(?P<quote>["'])(?:(?!(?P=quote)).)*"""
    r"""\{[^}\n]*\\[^}\n]*\}"""
)


def test_source_avoids_python_312_only_f_string_expression_backslashes():
    """Source files do not use f-string expressions rejected by Python 3.11."""
    offenders = []
    for path in Path("src").rglob("*.py"):
        lines = path.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            if FSTRING_WITH_BACKSLASH_EXPRESSION.search(line):
                offenders.append(f"{path}:{line_number}: {line.strip()}")

    assert offenders == []
