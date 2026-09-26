# Pilot delivery handover — 2026-09-26

Owner authorized the five-step pilot plan. Target: approximately 2026-10-10,
about 30 students. Owner remains Product Owner; Codex implements; existing
OpenClaw attendance-dev performs bounded read-only review. No remote push,
deployment, real-data access, backup schedule or external storage activated.

## Current checkpoint

Starting HEAD: ab61be76e10ba876afb5c0b2d033178ebbaa430f (master, five ahead of
last-known origin/master; no fetch performed). Initially no tracked edits.
Preserved output/branding/sat-factory-telegram.png, output/design-exploration/
and output/teacher-section-preview.png. Current scope: SF-17 rehearsal, SF-05
recovery, then SF-14 onboarding and SF-13 release preparation. SF-04 and SF-09
remain implemented; old roadmap proposals do not override their delivery notes.

## Verification and defect evidence

- `.\.venv\Scripts\python.exe scripts/verify.py`: baseline 142 tests passed,
  38.905s. Runner blocks the default engine BEFORE discovery and redirects the
  secret path before app.main imports. Python 3.14.7.
- `node --test tests/test_lesson_live.cjs`: five passed, Node 24.19.0. These are
  simulated-DOM polling checks, not browser/network/device tests.
- `.\.venv\Scripts\python.exe scripts/rehearse.py --report docs/rehearsal-evidence.json`:
  fictional 30-student sequential login/enrollment, then 25 simultaneous HTTP
  check-ins plus lifecycle/correction/renewal/permission scenarios. See JSON.
- P1 fixed: QueuePool starvation under concurrent arrivals. Authorization holds
  a read connection while atomic writes acquire another; 15 occupied pool slots
  could wait 30s and raise TimeoutError. SQLite file engines now use NullPool;
  in-memory behavior is unchanged. Added a deterministic test holding 30 read
  connections while a separate atomic write completes. Ten database tests pass;
  post-fix rehearsal burst 0.964s, no rejected check-ins. Local timings only.
- Rehearsal Windows console Unicode failure fixed with escaped JSON output.
- The old simulate_usage entry point now delegates to the guarded rehearsal.

## OpenClaw

Verified CLI 2026.9.6; attendance-dev points to this checkout, openai/gpt-6-sol.
Gateway loopback, token auth mode (no token read), workspaceOnly file tools,
elevated disabled, heartbeat 0m, cron false. Exec mode ask, approval defaults
allowlist / always / fallback deny. No permissions changed. Read-only review used
14 file reads, no exec, no denial. Findings accepted: add fresh post-finish denial,
audit/message assertions and concurrent arrivals. They are now in the rehearsal.
Backup review requested separately; findings/evidence still being reconciled.

## Decisions and remaining work

Owner delegated storage choice. Use local temporary fictional recovery storage
for now; proposed operational local folder is %LOCALAPPDATA%/SAT Factory/backups.
No real-data operation authorized/activated by this checkpoint. Off-laptop
protected copy, access and retention approval still needed before launch.
Daily + pre-upgrade / 14 versions remain proposed; no achieved recovery SLA.
Credential issuance/recovery choice and hosting budget/address questions pending.
Owner experience review, real phones/Wi-Fi and supervised pilot not performed.

Next: finish recovery review/failure tests, record a recovery drill, prepare the
isolated browser demo, then complete unblocked onboarding/release work. Commit
completed slices separately; keep this document current after each checkpoint.
