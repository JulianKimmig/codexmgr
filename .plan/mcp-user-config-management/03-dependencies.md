# Dependencies

## Task Dependency Table

| Task | Depends On | Blocks | Notes |
| --- | --- | --- | --- |
| TASK-001 | none | TASK-002, TASK-003, TASK-004, TASK-005 | Establishes safety fixtures and scope tests. |
| TASK-002 | TASK-001 | TASK-003, TASK-004, TASK-005 | Adds round-trip config infrastructure. |
| TASK-003 | TASK-002 | TASK-004, TASK-005, TASK-006 | Defines read model and list/show behavior. |
| TASK-004 | TASK-003 | TASK-005, TASK-006 | Implements main requested toggle workflow. |
| TASK-005 | TASK-004 | TASK-006, TASK-007 | Adds optional parameter mutation. |
| TASK-006 | TASK-005 | TASK-007, TASK-008 | Stabilizes diagnostics and help text. |
| TASK-007 | TASK-006 | TASK-008 | Documents implemented command surface. |
| TASK-008 | TASK-007 | none | Final regression and handoff. |

## Milestone Dependency Table

| Milestone | Depends On | Blocks |
| --- | --- | --- |
| M01 | none | M02 |
| M02 | M01 | M03 |
| M03 | M02 | M04 |
| M04 | M03 | none |

## Critical Path

The critical path is:

`TASK-001 -> TASK-002 -> TASK-003 -> TASK-004 -> TASK-005 -> TASK-006 -> TASK-007 -> TASK-008`

`TASK-004` is the core value point. If scope needs to be reduced, finish through
`TASK-004` before considering parameter mutation.

## External Dependencies

- `tomlkit`, assumed for round-trip TOML editing.
- Codex config schema for MCP servers under `[mcp_servers.<id>]`.
- Existing `uv` development workflow.

## Decision Gates

- DEC-001: MCP commands edit `CODEX_HOME/config.toml`, not project
  `.codex/config.toml`.
- DEC-002: Use a round-trip TOML library for user config writes.
- DEC-003: Do not add or remove MCP server definitions.
- DEC-004: Parameter mutation is allowlisted and secret-safe by default.

## Blocking Questions

There are no blocking questions for planning.

Non-blocking questions are recorded in `00-current-state.md`.
