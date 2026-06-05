# Implementation Roadmap

## Roadmap Summary

Build a thin, safe path first:

1. Create isolated tests and fixtures for temporary user Codex configs.
2. Add round-trip config infrastructure for `CODEX_HOME/config.toml`.
3. Add read-only MCP list/show behavior.
4. Add persistent enable/disable behavior for existing servers.
5. Add safe parameter mutation commands.
6. Add diagnostics and documentation.
7. Run final verification and record completion evidence.

## Full Ordered Sequence

1. `TASK-001`: Establish MCP user config test fixtures and scope guards.
2. `TASK-002`: Add round-trip user Codex config infrastructure.
3. `TASK-003`: Implement MCP read model, validation, list, and show.
4. `TASK-004`: Implement enable and disable for existing MCP servers.
5. `TASK-005`: Implement safe parameter mutation for existing MCP servers.
6. `TASK-006`: Add MCP validation diagnostics and command help polish.
7. `TASK-007`: Update README and user-facing documentation.
8. `TASK-008`: Run final regression, line-count, and handoff checks.

## Sequencing Rationale

The first task prevents accidental real-home mutations and codifies the scope
before implementation. The second task addresses the highest technical risk:
editing `~/.codex/config.toml` without destroying formatting and comments. The
read-only path comes before mutation so server discovery and validation are
settled before writes. Enable/disable is the first user-value mutation because
it is the main requested workflow. Parameter mutation is later because it needs
the same validation and write infrastructure plus stricter secret-handling rules.

## Thin End-To-End Path

The minimum usable increment is:

- Temporary `CODEX_HOME/config.toml` fixture with an existing MCP server.
- `codexmgr mcp list` can display it.
- `codexmgr mcp disable <id>` can persist `enabled = false`.
- `codexmgr mcp enable <id>` can persist `enabled = true`.
- Tests prove no new MCP server can be created through these commands.

This is completed by `TASK-004`.

## Parallelization Opportunities

- After `TASK-002`, documentation drafting can happen in parallel with read-only
  CLI work if the command names are stable.
- After `TASK-004`, `TASK-005` and `TASK-006` can partially overlap, but they
  should coordinate on validation message text.
- `TASK-008` must remain last.

## Replanning Checkpoints

Replan if:

- Adding `tomlkit` is rejected or impractical.
- The existing CLI structure cannot add `mcp` commands without exceeding the
  300-line source-file limit.
- Tests reveal Codex uses a config shape materially different from
  `[mcp_servers.<id>]`.
- The user decides raw token storage is required in v1.
