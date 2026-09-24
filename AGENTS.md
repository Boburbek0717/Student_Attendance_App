# SAT Factory workflow

Honor parent workspace instructions; synced sources remain read-only.

For future development, consult docs/product-backlog.md and
docs/scrum-working-agreement.md. Identify the story being implemented and its
acceptance criteria; update status and evidence when work is actually complete.

docs/sprint-01-proposal.md records Sprint 1, authorized on 2026-09-23.
That authorization covers SF-01 and SF-02, not the entire backlog. User instructions take precedence. Do not
introduce repetitive approval gates for already-authorized work.

## OpenClaw attendance-dev operating rules

This is a launch-bound SAT Factory product. Prioritize working behavior,
reliability and small reviewable changes. Follow docs/openclaw-development.md.
The existing FastAPI, SQLAlchemy, SQLite and Jinja architecture is authoritative.
Use the project Python 3.14 virtual environment and unittest, not assumed pytest
commands. Audit the repository and test setup before changing application code.

Preserve existing commits and other work in progress. Never reset, clean, stash,
rewrite history or commit unrelated edits. No force pushes, remote writes or
deployment without the owner's explicit authorization.

Do not read or expose .env files, .session-secret, credential stores, live
attendance.db, database backups or private student records. Do not start the app,
run migrations, create users or connect to live data as part of an audit/test run.
Tests must use temporary/in-memory databases and a disposable session secret.

Keep OpenClaw execution approval-based, elevated access disabled and filesystem
tools scoped to this repository. Never weaken execution policy to get past a
denial. If approval is unavailable, stop the command and report the blocker.
Do not install additional skills/plugins, schedule work or connect messaging
channels as part of ordinary development.

Protect teacher/student authorization, duplicate check-in prevention, immutable
attendance/correction history and atomic balance updates. Twelve-lesson purchases,
early renewal credit and late attendance debt remain separate per enrollment.
Store times in UTC and display Asia/Tashkent. Verify rollback, stale requests and
concurrency when changing attendance or balance writes.
