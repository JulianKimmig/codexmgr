"""CLI bridge for launching the interactive codexmgr TUI."""

import argparse
from pathlib import Path

from .app import CodexMgrTui


def run_tui_command(
    args: argparse.Namespace,
    cwd: Path,
    codex_home: Path,
    codexmgr_home: Path,
) -> int:
    """Run the interactive TUI command.

    Args:
        args: Parsed argparse namespace with TUI options.
        cwd: Project directory.
        codex_home: Resolved Codex home directory.
        codexmgr_home: Resolved codexmgr home directory.

    Returns:
        Process-style exit code.
    """
    app = CodexMgrTui(
        cwd=cwd,
        codex_home=codex_home,
        codexmgr_home=codexmgr_home,
        no_sync=args.no_sync,
        show_diff=args.show_diff,
    )
    result = app.run()
    return int(result or 0)
