# Contributing and local workflow

Keep changes small enough to review and demonstrate. Read AGENTS.md and the latest
entry in docs/pilot-handover.md before starting. Older plan entries may be superseded
by newer delivery notes; inspect code rather than reimplementing completed work.

## Before editing

- Inspect `git status --short --branch` and the current diff.
- Pick one backlog item or concrete defect and state its acceptance criteria.
- Keep live databases, secrets, accounts and real backups out of development checks.
- Preserve uncommitted work and unrelated artifacts. Never reset or clean to simplify a task.

## Before a shared checkpoint

```powershell
.\.venv\Scripts\python.exe scripts/check.py
```

The command uses the current interpreter, guarded Python tests, explicit discovery
of Node test files, `pip check`, and Git whitespace checks. It does not install
packages, start the working server, modify data, commit or push. Missing Node/Git
is an error, not a silently skipped check. Advisory scanning remains a separate task.

For UI work, check narrow/wide layouts, keyboard focus and error/empty states using
fictional data. For critical writes, check authorization, stale requests, retry,
rollback and concurrency. New schema needs isolated upgrade and backup/restore
coverage plus an operator rollback note. Do not rerun unrelated checks repeatedly
without a new failure/change that warrants them.

## Commit and hand over

Review explicit staged paths with `git diff --cached --stat` and
`git diff --cached --check`. Stage source, tests and documentation intentionally;
do not use generated output as a blanket staging target. Make a focused commit.
Push only to the intended remote/branch when authorized; never force-push shared
history. A push does not authorize deployment or restarting an active class.

Update the backlog/handover with scope, verification evidence, limitations and the
next concrete action. Record owner acceptance only after receiving it. Local demos,
static browser previews and concurrent TestClient requests are distinct evidence.
