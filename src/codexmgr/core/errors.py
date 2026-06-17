"""Shared exceptions for command-facing codexmgr failures."""


class CommandError(Exception):
    """Raised when a command cannot complete with the provided inputs."""
