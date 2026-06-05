# Agent Handoff

## Read-First Order

1. `README.md`
2. `00-current-state.md`
3. `decision-log.md`
4. `01-implementation-roadmap.md`
5. The next task file in `tasks/`
6. `04-validation-and-risk.md`

Before coding, also read:

- `AGENTS.md`
- `README.md`
- `src/codexmgr/cli.py`
- `src/codexmgr/cli_parser.py`
- `src/codexmgr/paths.py`
- `src/codexmgr/toml_io.py`
- Relevant tests in `tests/`

## How To Choose The Next Task

Pick the lowest-numbered task with status `ready` or `not-started` whose
dependencies are complete. Do not skip ahead to parameter mutation before
enable/disable works end to end.

## How To Update Statuses

After completing a task:

- Change its status to `done`.
- Add completion evidence to the task file.
- Update `05-agent-handoff.md` current next task.
- Update milestone status in `02-milestones.md` if a milestone is complete.
- Record any replanning decisions in `decision-log.md`.

## What Evidence To Record

Record:

- Tests added.
- Source files changed.
- Commands run.
- Test output summary.
- Line-count output when source files are added or expanded.
- Any behavior intentionally deferred.

## When To Stop And Ask The User

Stop and ask if:

- The user rejects adding `tomlkit`.
- Literal token storage is required in v1.
- Existing `~/.codex/config.toml` behavior needs to be inspected directly.
- A command would need to start MCP servers or make network calls.
- The requested behavior would require adding or removing MCP server definitions.

## Replanning Protocol

When replanning:

1. Record the reason in `decision-log.md`.
2. Mark affected tasks as `needs-replan`.
3. Add replacement task files with new stable IDs.
4. Do not renumber existing task IDs.

## Current Next Task

`TASK-001: Establish MCP User Config Test Fixtures And Scope Guards`
