# Iteration: Phase 0 bootstrap

- Date: 2026-04-08
- Branch: `main`
- Commit(s): `ed5d726`
- Owner: `codex`
- Status: `completed`

## Input

- Task/requirements: initialize empty repository `kuzakovvd-lgtm/WorkAI` with Phase 0 skeleton.
- Constraints: no business logic, strict package/module layout, entrypoints in `scripts/`, keep v1 system untouched.
- Non-goals: runtime features, domain schema implementation.

## Plan

1. Clone empty repo and create required tree/files.
2. Configure tooling (`pyproject`, lint/type/test, CI workflow).
3. Validate locally and on server; push first commit to `main`.

## Changes

### Files added

- Package skeleton: `WorkAI/*` module `__init__.py` files.
- Tooling/docs: `.editorconfig`, `.gitignore`, `pyproject.toml`, `README.md`, `ARCHITECTURE.md`, `.github/workflows/ci.yml`.
- Infra placeholders: `scripts/.gitkeep`, `sql/.gitkeep`, `migrations/.gitkeep`, `deploy/systemd/.gitkeep`, `deploy/secrets.example/.gitkeep`, `docs/.gitkeep`.
- Tests skeleton with bootstrap test.

### Files updated

- None (root commit).

### Files removed

- Removed accidental `.DS_Store` before commit.

## Validation

### Automatic checks

- Local environment note: `python3.12` unavailable on workstation (`Python 3.14.3` present), so local verification executed on 3.14.
- `ruff check .`: passed.
- `mypy WorkAI`: passed.
- `pytest`: passed after adding one minimal bootstrap test (`tests/unit/test_bootstrap.py`).

### Manual checks

- Server SSH connectivity: confirmed to `root@72.56.83.16`.
- Repo push to GitHub: successful (`main` branch created).
- Server setup at `/opt/WorkAI`: clone + `.venv` with `python3.12.3`.
- Server checks (`ruff/mypy/pytest`): passed on Python 3.12.

## Decisions and rationale

- Added `N999` to Ruff ignore due to required package name `WorkAI` (capitalized by project contract).
- Added one bootstrap unit test to avoid `pytest` exit code 5 (no tests collected) in CI.

## Risks / caveats

- Name-style lint exception (`N999`) intentionally retained due to package naming contract.

## Next step

- Phase 1: implement core infrastructure (`config`, `common`, `db`, Alembic baseline).
