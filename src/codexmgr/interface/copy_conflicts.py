"""Interactive CLI presentation for managed-copy conflict decisions."""

from collections.abc import Callable
from typing import TextIO

from ..project.copy_conflicts import CopyConflict, CopyResolution


def build_cli_conflict_resolver(
    stdin: TextIO,
    stdout: TextIO,
) -> Callable[[CopyConflict], CopyResolution] | None:
    """Build a prompt callback when the input stream is interactive.

    Args:
        stdin: Stream used to read conflict choices.
        stdout: Stream used to present provenance and choices.

    Returns:
        Interactive conflict callback, or ``None`` for non-terminal input.
    """
    if not stdin.isatty():
        return None

    def resolve(conflict: CopyConflict) -> CopyResolution:
        """Prompt until one supported action is selected.

        Args:
            conflict: Source-backed target requiring a decision.

        Returns:
            Selected copy resolution, including abort.
        """
        stdout.write(
            "Managed copy conflict\n"
            f"  Target: {conflict.target}\n"
            f"  Source: {conflict.source}\n"
            "Choose [k]eep local, [o]verwrite local, "
            "[u]pdate shared source, or [a]bort: ",
        )
        stdout.flush()
        choices = {
            "k": CopyResolution.KEEP_LOCAL,
            "keep-local": CopyResolution.KEEP_LOCAL,
            "o": CopyResolution.OVERWRITE_LOCAL,
            "overwrite-local": CopyResolution.OVERWRITE_LOCAL,
            "u": CopyResolution.UPDATE_SOURCE,
            "update-source": CopyResolution.UPDATE_SOURCE,
            "a": CopyResolution.ABORT,
            "abort": CopyResolution.ABORT,
        }
        while True:
            answer = stdin.readline()
            if answer == "":
                return CopyResolution.ABORT
            selected = choices.get(answer.strip().lower())
            if selected is not None:
                return selected
            stdout.write(
                "Choose k, o, u, or a: ",
            )
            stdout.flush()

    return resolve


def write_source_update_warning(conflict: CopyConflict, stdout: TextIO) -> None:
    """Warn immediately before a reusable source is updated.

    Args:
        conflict: Validated local-to-source update.
        stdout: Stream receiving the warning.
    """
    stdout.write(
        "Warning: updating shared source "
        f"{conflict.source} from local file {conflict.target}\n",
    )
