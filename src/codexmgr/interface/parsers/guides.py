"""CLI parser registration for reusable guide documents."""

import argparse


def add_guides_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register guide listing and multi-reference selection commands.

    Args:
        subparsers: Root command parser collection to extend.
    """
    parser = subparsers.add_parser("guides", help="Manage reusable guide documents")
    commands = parser.add_subparsers(dest="guides_command", required=True)
    commands.add_parser("list", help="List guide files and folders as a tree")
    for name in ("enable", "disable"):
        command = commands.add_parser(name, help=f"{name.title()} guide files or folders")
        command.add_argument("--no-sync", action="store_true", help="Save selection without applying copies")
        command.add_argument("guides", nargs="+", help="Guide file or folder references")
