# AI Contribution Guide

## Core rules

- Start from [DOCS_INDEX.md](./DOCS_INDEX.md).
- Follow dependency direction from `ARCHITECTURE.md`.
- Never add secrets to repository.
- Never initialize DB/network side effects on module import.
- Keep changes minimal and safe.

## Required workflow per iteration

1. Read relevant docs and current iteration logs.
2. State a short plan.
3. Implement smallest coherent change.
4. Run checks:
   - `ruff check .`
   - `mypy WorkAI`
   - `pytest`
5. Update/create iteration log in `docs/iteration-logs/`.
6. Update `docs/iteration-logs/README.md` index with the new entry.
7. Update `TASK_BOARD.md` (status date + task state transitions).
8. Record important architecture changes in `DECISIONS.md`.

This workflow is mandatory for every non-trivial change.

## Quality gates

- Strict typing for `WorkAI` package.
- CI must stay green.
- DB-related behavior must be explicit and testable.

## Commit expectations

- One phase/iteration = one coherent commit when possible.
- Commit message should map to phase and scope.
