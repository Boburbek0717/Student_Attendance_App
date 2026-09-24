# OpenClaw attendance development

Agent: `attendance-dev`. Workspace, working directory and repo root point to this
existing repository. OpenClaw state and credentials belong outside Git.

## Start with a read-only audit

Read AGENTS.md, README.md, the selected story and its acceptance criteria. Record
`git status --short --branch`, `git rev-parse HEAD`, recent history and the current
diff before implementation. Treat existing edits as work owned by their author.
Do not inspect secret files, live SQLite data or database backups. A Git upstream
ahead/behind count reflects the last fetch, not necessarily the current server.

## Verified test workflow

The project's interpreter is `.venv\Scripts\python.exe` (Python 3.14). The
documented suite is `python -m unittest discover -s tests -v`; no pytest dependency
is required. Before executing it, review fixture setup and import side effects.
Most tests inject temporary SQLite engines; database integrity tests use memory.
Importing app.main also creates the default app and calls load_session_secret.

For setup verification, use a wrapper that imports app.database/app.security,
registers a SQLAlchemy `do_connect` handler on app.database.engine that raises if
the live engine is used, redirects app.security.SECRET_PATH to a TemporaryDirectory,
and then discovers/runs tests. Do not substitute or copy the real session secret.
The wrapper and its test log are retained with this setup task's local records.

After a failure, reproduce it with the smallest relevant test, inspect the cause,
make a bounded fix within the authorized task, and rerun focused tests plus the
suite when shared behavior changes. Do not invent a code change when tests pass.
Review the final diff, report evidence and preserve unrelated files. Commit only
the task's reviewed files when authorized by the working agreement/current task.

## Permissions and boundaries

Host commands require human approval; missing approval fails closed. OpenClaw
file tools are workspace-scoped. Native Codex starts with read-only filesystem
permissions and a user reviewer; explicit tool restrictions prevent inherited
native tool/MCP surfaces from bypassing the OpenClaw tool policy. File edits through
enabled OpenClaw tools are restricted to this repo but are not all individually
approval-prompted. These controls are not a separate OS-user isolation boundary.
Never approve commands that read credentials or access the live database.

Use the local authenticated dashboard to review command requests. Prefer allow
once after checking executable, arguments and working directory. Do not grant
broad interpreter or Git allow rules. Do not select full/YOLO permissions.
No messaging channels, scheduled work, remote exposure or deployment are needed.

## Product invariants

Keep per-enrollment credit/debt correct, reject duplicate attendance atomically,
preserve original records and audited corrections, enforce roles and session/CSRF
checks, and respect permanent lesson completion. Display school time using
Asia/Tashkent while retaining UTC storage. Do not expand the selected product
story or change the architecture merely to demonstrate agent capability.
