"""Argument parser helpers for custom-agent commands."""

import argparse


def add_agents_parser(
    subparsers: argparse._SubParsersAction,
    add_no_sync,
) -> None:
    """Add custom-agent management parsers.

    Args:
        subparsers: Top-level subparser action.
        add_no_sync: Callback that adds the shared --no-sync argument.
    """
    agents = subparsers.add_parser("agents", help="Manage project custom agents")
    agents_subparsers = agents.add_subparsers(dest="agents_command", required=True)

    enable = agents_subparsers.add_parser("enable", help="Enable a custom agent")
    add_no_sync(enable)
    enable.add_argument("agents", nargs="+", help="Custom-agent names")

    disable = agents_subparsers.add_parser("disable", help="Disable a custom agent")
    add_no_sync(disable)
    disable.add_argument("agents", nargs="+", help="Custom-agent names")

    agents_subparsers.add_parser("list", help="List available and configured agents")
