# Milestones

## Milestone Overview

| Milestone | Objective | Tasks | Exit Gate |
| --- | --- | --- | --- |
| M01 | Safe foundation for user config edits | TASK-001, TASK-002 | Temporary `CODEX_HOME/config.toml` can be parsed and round-trip edited in tests. |
| M02 | Read-only MCP visibility | TASK-003 | Existing MCP servers can be listed and shown without writes. |
| M03 | Persistent MCP toggling and parameters | TASK-004, TASK-005 | Existing servers can be enabled/disabled and safe fields can be updated. |
| M04 | Diagnostics, documentation, release readiness | TASK-006, TASK-007, TASK-008 | Docs and full regression checks are complete. |

## M01: Safe User Config Foundation

Entry criteria:

- Repository tests are available.
- Existing fixtures can inject `codex_home`.

Deliverables:

- Test fixtures for user Codex config.
- Round-trip TOML editing infrastructure.
- Path helper for `CODEX_HOME/config.toml`.
- No real user home config reads or writes in tests.

Validation gates:

- Tests cover preserving unrelated config and comments.
- Tests cover missing config and invalid TOML.
- Full test command still passes after dependency changes.

Related tasks:

- `TASK-001`
- `TASK-002`

## M02: Read-Only MCP Visibility

Entry criteria:

- M01 complete.
- MCP config can be loaded through the new infrastructure.

Deliverables:

- MCP server read model.
- Existing-server validation.
- `codexmgr mcp list`.
- `codexmgr mcp show <server-id>`.

Validation gates:

- List/show work without a project `.codex/`.
- List/show do not print raw secret values.
- Invalid MCP table shapes fail clearly.

Related tasks:

- `TASK-003`

## M03: Persistent MCP Toggling And Parameters

Entry criteria:

- M02 complete.
- Server ids can be resolved and validated.

Deliverables:

- `codexmgr mcp enable <server-id>`.
- `codexmgr mcp disable <server-id>`.
- Safe parameter mutation commands for existing servers.
- Tests proving no add/remove behavior.

Validation gates:

- Enable/disable preserve all unrelated config.
- Commands fail for missing server ids.
- Parameter commands only mutate allowlisted fields.
- Secret-handling rules are tested.

Related tasks:

- `TASK-004`
- `TASK-005`

## M04: Diagnostics, Documentation, Release Readiness

Entry criteria:

- M03 complete.
- CLI behavior and command names are stable.

Deliverables:

- MCP validation command or diagnostics.
- README updates.
- Final regression and line-count checks.
- Completion evidence for handoff.

Validation gates:

- Full test suite passes.
- Source files remain below 300 lines.
- README matches implemented behavior.
- No plan-only assumptions remain unaddressed.

Related tasks:

- `TASK-006`
- `TASK-007`
- `TASK-008`
