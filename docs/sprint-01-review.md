# Sprint 1 implementation and review evidence

2026-09-23: SF-01 and SF-02 implemented and verified. Sprint remains active;
stakeholder review and retrospective are pending. No later stories selected.

## Delivered

SF-01: persistent SQLite login limits, 10 attempts per normalized username and
120 per connection address in a rolling 60 seconds. All attempts count, including
unknown accounts. Keys are fingerprinted; expired rows are pruned; storage is
bounded to 8,192 rows and fails closed when full. Retry-After explains recovery.
Run local Uvicorn with --no-proxy-headers. Production/distributed abuse remains SF-13.

SF-02: teacher preview, required reason and confirmation for manual presence,
reversal and restoration. Each effective attendance uses one lesson, including
debt; reversal restores one. Original rows are retained with application-level
append-only events recording actor, timestamp, origin and reason. Students see
status and origin, never teacher reasons. This is not tamper-proof against direct
database access. Serialized writes and version checks prevent duplicate charges
and stale changes, including reversal/restoration with an unchanged net balance.

Eligibility requires the matching group and existing attendance or saved roster
membership; inactive historical members remain eligible. Legacy lessons without
snapshots use active membership with a warning. Future lessons are rejected.
Code entry cannot undo a teacher reversal; a teacher can restore it with a reason.

## Evidence

119 tests passed in 84.675 seconds on isolated databases. New coverage includes:
30 student accounts plus teacher on one address; account/connection throttling;
independent engines, restart, time recovery, parallel requests and storage cap;
manual/code duplicates; debt, reversal, restoration, later renewal and balance
correction; stale forms, role and CSRF denial, escaped reasons and student privacy;
simultaneous manual/code entry; rollback on audit failure; additive schema upgrade
and backup restoration. No real student data was used.

Browser rehearsal on isolated port 8001 verified login, lesson links, preview,
manual entry and reversal. At 390 by 844 pixels the form fit, Tab showed visible
focus and Enter submitted. Present changed from 0 to 1 and absent from 1 to 0;
reversal preview showed balance 11 to 12 and returned the student to absent.
Teacher, reason, timestamp and manual origin remained visible. This focused
mobile/keyboard check is not a full accessibility assessment.

## Upgrade and recovery

No new dependencies. Startup adds login_attempt_windows and attendance_corrections
without changing existing columns. Tests initialize twice over the prior schema,
preserve balances, and restore an isolated SQLite backup with integrity_check=ok,
no foreign-key errors, and retained correction history. The real runtime database
was not used for tests or deliberately migrated in this task.

Before restarting the real app, stop its server and preserve its SQLite database
and .session-secret privately outside the serving tree. Both are Git-ignored.
Start using README instructions; startup adds the tables. For recovery, stop the
app, retain the affected database for diagnosis, restore matching backup and code,
and verify balances and history. Never run pre-sprint code against correction data:
old queries would charge reversed entries. Restoring old backups loses later writes.
A backup product and scheduled backups remain SF-05.

## Review pending

Demonstrate phone-failure attendance, correction after renewal and shared-Wi-Fi
login to the owner. Gather feedback on labels and historical eligibility before
reordering Sprint 2. No external release performed.
Suggested retrospective topics: keep isolated realistic fixtures; address Windows
file-handle cleanup in recovery tests; maintain a compact scenario checklist.
Codex maintains test evidence; actual owner feedback and retrospective outcomes
remain pending.
