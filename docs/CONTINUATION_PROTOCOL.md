# SuperAgent — Continuation Protocol

## Starting a new chat

Use these files as the canonical project handoff:

- `docs/PROJECT_STATE.md` — current implementation status, known blockers and next priorities.
- `docs/ARCHITECTURE_MAP.md` — stable architecture and dependency rules.
- `docs/CONTINUATION_PROTOCOL.md` — how to resume work safely.

The Git history is authoritative for what was actually committed. Do not infer completion from prose alone.

## Before changing code

1. Read `docs/PROJECT_STATE.md`.
2. Inspect the current `main` commit and relevant implementation files.
3. Check existing tests before adding a new abstraction.
4. Reproduce the reported failure when possible.
5. Fix the smallest architectural root cause rather than adding a workaround.
6. Add or update a regression test.
7. Run the focused tests, then the full suite.
8. Commit only verified changes to `main`.

## Continuation checklist

```text
[ ] Read project state
[ ] Inspect current Git commit
[ ] Reproduce current failure
[ ] Trace dependency/runtime path
[ ] Reuse existing component if present
[ ] Implement root-cause fix
[ ] Add regression test
[ ] Run focused tests
[ ] Run full pytest
[ ] Check CI
[ ] Update PROJECT_STATE if architecture/status changed
[ ] Commit and push
```

## Local verification

After pulling:

```bash
git pull origin main
git status
pytest
```

For a fast focused run, use the relevant test file or module first. A full suite failure during collection is a release blocker and should be fixed before feature work continues.

## Documentation discipline

Do not create numbered implementation/specification markdown files for every incremental change. Keep durable documentation consolidated in the three files above. Update them when the architecture or continuation state materially changes.
