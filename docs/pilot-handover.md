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

## Smaller-chunk instruction and checkpoint

Owner requested smaller chunks on 2026-09-26. Stop after this recovery tooling
checkpoint. Do not automatically start onboarding or release work in this turn.
Unfinished onboarding/template and production configuration edits were removed;
existing behavior remains intact. Completed rehearsal/fix commit: abc0212.

Recovery: scripts/backup.py, scripts/recovery_drill.py, tests/test_backup.py and
backup-recovery.md. Full post-pool-fix suite: 151 tests passed in 44.223s. After
OpenClaw backup review, 11 focused backup tests passed in 5.992s, including three
new regressions. Review findings repaired: validate timestamps before publication,
retain per source identity, reject destination symlinks, hash balances in manifest.
See recovery-evidence.json for the final drill measurement. No live data touched.

Decisions received: keep teacher-issued passwords and teacher resets. Hosting
budget preference: as low as practical; no provider/address chosen or purchase
approved. Backups remain fictional-only with operational destination, access,
off-laptop protection and final retention/schedule awaiting a concrete review.

Next chunks, one at a time:
1. Finish SF-17 browser/mobile/keyboard rehearsal and owner walkthrough; prepare
   the launch-blocker checklist and pilot script. Automated rehearsal is complete,
   but real-user review and device/network evidence are still missing.
2. SF-14 focused first-login/recovery guidance under the chosen existing password
   process, with mobile/error-message checks.
3. SF-13 deployment configuration and upgrade/rollback rehearsal; present a
   concrete low-cost host proposal. No public deployment until explicitly approved.
4. Supervised small pilot only after deployment and participants are ready.

Open launch gates: real phones/classroom Wi-Fi, owner review, operational backup
activation/off-laptop protection, tested host configuration and approved deployment.
No claim that any whole five-step milestone is complete.

## Mobile/keyboard chunk — 2026-09-26

Started from b6fca9e. Added scripts/demo_class.py: disposable fictional 30-student
browser environment, separate session cookie and hidden password prompt. Fixed
320px header word splitting and associated login/check-in errors with their inputs.
Browser scenarios and owner walkthrough are in mobile-classroom-review.md.
24 focused auth tests passed (7.976s), 2 demo tests passed (0.457s), diff check passed.
Review server stopped normally; no real data or normal server restart. Existing
untracked assets preserved; added fictional screenshot/review-prompt artifacts.
Owner walkthrough, 200% text zoom, assistive-technology and real-device/Wi-Fi
validation remain pending. SF-17 is not marked Done. Next implementation chunk is
SF-14 first-login/recovery guidance with existing teacher-issued passwords/resets.
Do not automatically begin that next chunk in this turn.

## SF-14 guidance chunk — 2026-09-26

Starting HEAD 45af814; no pre-existing tracked edits. Added first-login/recovery,
missing/inactive enrollment and check-in troubleshooting copy, preserving the
owner's teacher-issued password/reset process. No authentication/accounting writes
changed. See onboarding-review.md: 2 new tests and 9 student-management tests passed;
320/390px static browser checks and Enter expansion passed. Unrelated outputs
preserved; output/onboarding-help.png added as a fictional preview artifact.
SF-14 implementation is ready for review, not Done until real novice review occurs.
Next selected chunk: SF-13 release configuration and deployment procedure, without
publishing. No real data, real backup activation, remote push or deployment in this
chunk. Owner walkthrough, real-device/Wi-Fi and operational launch gates remain open.

## Design priority update — 2026-09-26

Owner deferred deployment and selected research-led visual/UI/UX refinement for
the next few sessions, in small chunks. This supersedes the SF-13 next action
above. Baseline 0c2ad75; tracked tree initially clean, unrelated output artifacts
preserved. See design-refinement.md for code/saved-preview findings, researched
references, page directions, dependency decisions and review criteria. No app
code, live data, dependencies or tests changed in this research checkpoint.
Next bounded implementation proposal: public header/homepage hierarchy and the
minimum shared design tokens, with isolated responsive and cross-page review.
SF-10 and focused SF-17 follow; no new implementation story is marked complete.
