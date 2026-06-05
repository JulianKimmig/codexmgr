# MCP User Config Management Plan

## Plan Identity

- Plan name: MCP user config management for codexmgr
- Plan folder: `.plan/mcp-user-config-management/`
- Status: ready for implementation
- Scope owner: codexmgr CLI

## Source Request Summary

The requested implementation is narrower than the earlier MCP design proposal:

- Main goal: let `codexmgr` turn existing MCP servers on or off in
  `~/.codex/config.toml`.
- Optional goal: let `codexmgr` change or add specific parameters on existing
  MCP server entries, especially token-related settings.
- Explicit non-goal: do not add or remove MCP server definitions. Server
  creation and removal should continue through the traditional Codex CLI or
  direct config editing workflow.
- Required planning context: use all files in `.thoughts/mcp-server-management/`.

## How To Use This Plan

Start with `00-current-state.md`, then follow tasks in numeric order unless a
dependency table says otherwise. Implementation agents should use the task files
as executable work packages and update status/evidence after each completed task.

This plan assumes TDD: write behavior tests before source changes for every
implementation task.

## File Map

- `00-current-state.md`: current repo state, scope, assumptions, unknowns.
- `01-implementation-roadmap.md`: ordered implementation sequence.
- `02-milestones.md`: milestone objectives, deliverables, gates.
- `03-dependencies.md`: task and milestone dependency map.
- `04-validation-and-risk.md`: validation strategy and risk register.
- `05-agent-handoff.md`: instructions for future coding agents.
- `decision-log.md`: scope and architecture decisions.
- `appendix-thoughts-synthesis.md`: how the prior MCP thought artifacts were
  used and adapted.
- `tasks/`: one executable task file per implementation task.

## First Recommended Task

Start with `TASK-001: Establish MCP User Config Test Fixtures And Scope Guards`.
It creates the test safety rails for mutating temporary `CODEX_HOME/config.toml`
fixtures instead of the real user config.

## Current Status

No implementation has started. All task files are ready.
