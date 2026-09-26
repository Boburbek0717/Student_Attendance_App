# SF-17 mobile and keyboard classroom review — 2026-09-26

Starting checkpoint b6fca9e. This chunk covers a disposable browser rehearsal,
small accessibility fixes, and a repeatable owner walkthrough. It does not add
onboarding policy, production configuration or hosting. Homepage content is unchanged.

## Reproduce the isolated demo

```powershell
.\.venv\Scripts\python.exe scripts/demo_class.py
```

Choose a disposable password at the hidden prompt. It is not printed, stored in
source, placed in a URL or passed as a process argument. Open
http://127.0.0.1:8766/login and use demo-teacher or demo-00 through demo-29 with
that password. All names, groups and packages are fictional. Thirty students
start with twelve lessons each. The demo is loopback-only, uses temporary SQLite
and a temporary signing secret, blocks the normal engine, and has a distinct
sat_factory_demo_session cookie. The normal app need not be restarted.

Ctrl+C stops the server and removes the temporary database on normal shutdown.
A forced process kill or power failure may leave a temporary fictional directory;
never interpret it as an operational backup. Each new run starts fresh. The
review server was stopped after this session; no background job was installed.

## Recorded browser evidence

Codex in-app Chromium browser; viewport simulations, not physical phones. Widths
320 and 390 include a 15px scrollbar (measured content widths 305 and 375).
Long fictional names and a 30-student roster were used.

| Scenario | Observed outcome |
| --- | --- |
| Login at 320px | Tab reached username; typing, Tab and Enter signed in as teacher. No page horizontal overflow. |
| Teacher dashboard | Long names wrapped and all setup/class controls remained available. Thirty-student roster is lengthy. |
| Start lesson | Enter on Start a new lesson created lesson 1; 0 present / 30 absent. |
| Invalid check-in | Current-code guidance appeared. Found missing field/error association; added aria-describedby and aria-invalid. Rechecked association in the browser. |
| Student check-in | Keyboard submitted current code; status identified group/lesson; balance 12 to 11; history recorded attendance. |
| Teacher correction at 390px | Preview showed 11 to 12; reason entry, Tab, visible solid focus outline and Enter reversed the fictional attendance; 0 present / 30 absent. |
| Renewal at 390px | Preview showed 12 to 24, Enter saved renewal; success status appeared. |
| Finish at 390px | Warning explained permanence, Enter confirmed; Finished permanently appeared, no reopen action, correction links retained. |
| Reflow | No page-level overflow on measured dashboard, check-in, correction and finished lesson views. Header Results initially split at 320px; added wrapping/non-shrinking links. Final screenshot verified at 390px. |

Saved local screenshots: output/mobile-checkin-review.png (full student page),
output/mobile-lesson-review.png (finished lesson viewport). These are fictional
review artifacts, not student publication records. No screenshot contains a password.

## Verification

- `python scripts/verify.py --pattern test_auth.py` with project interpreter:
  24 passed in 7.976s, including HTTP error associations and fresh-page reset.
- `python scripts/verify.py --pattern test_demo_class.py`: 2 passed in 0.457s,
  checking loopback/no access logs, 31 fictional accounts/30 enrollments,
  separate cookie, temporary file cleanup and invalid-password refusal.
- `git diff --check`: passed. No backend attendance/accounting writes changed;
  no full-suite rerun or new Node run was necessary for this template/CSS chunk.
- No 200% text-only zoom, screen-reader, touch keyboard or real-network result is
  claimed. Keyboard activation used native Tab/Enter plus targeted focus for
  distant links; this was not an exhaustive Tab traversal of every roster link.

## Owner walkthrough (feedback pending)

1. Start a fresh demo and log in as teacher. Find the fictional class and start it.
2. Note the displayed code. Log out, sign in as demo-00, enter a wrong code, then
   the current one. Confirm the success message, history and eleven remaining.
3. Return as teacher. Confirm one present and 29 absent. Review a correction,
   enter a reason and verify its balance effect. Renew a package and review totals.
4. Finish the same lesson. Confirm it cannot reopen and corrections remain offered.
5. Record any confusing label, difficult tap target, excessive scrolling or missing
   feedback. Owner acceptance remains blank until feedback is actually received.

Use a separate private browser session if observing both roles simultaneously;
ordinary tabs in the same profile share the demo login. Do not enter real records.

## Launch checklist and triage

- [x] Automated 30-student rehearsal and concurrent-arrival defect repair (prior chunk).
- [x] Fictional recovery with restored-session revocation (prior chunk).
- [x] This bounded browser/keyboard rehearsal and demonstrated accessibility fixes.
- [ ] Owner walkthrough and feedback.
- [ ] 200% text zoom, screen-reader and real-phone/touch-keyboard validation.
- [ ] Teacher-issued credential/recovery guidance (next SF-14 chunk).
- [ ] Approved persistent host, HTTPS, production configuration and restart checks.
- [ ] Authorized real backups, restricted access and protected off-laptop copy.
- [ ] Consenting supervised pilot on classroom Wi-Fi, including interrupted connections.

No new critical app defect remained in the exercised scenarios. Optional issue:
SF-10 dashboard setup forms and long roster require substantial phone scrolling;
prioritize after essentials unless owner finds this blocks teaching. Launch gates
above remain unmet; local testing alone is not readiness approval.

For the eventual pilot: record time to first login/check-in, successful versus
rejected submissions, retries, teacher correction reasons, reconciled totals and
backup availability. Keep observations anonymous in shared development notes;
owner supervises consenting participants. Do not start the real pilot yet.

OpenClaw attendance-dev performed a bounded read-only source review of the demo,
forms, media query and regression test: no concrete defects found. It did not
execute tests or validate real devices. Its cookie/cleanup limitations are covered
only to the extent of the two local demo tests above; forced termination remains
unverified. Primary developer reviewed the diff and browser evidence independently.

## Header wrapping follow-up — 2026-09-26

Owner screenshot exposed word splitting at intermediate widths above the old
480px fix. Header items now wrap at every width; navigation labels and portal
arrow use nowrap, and the mobile badge width cap is removed. Static Jinja preview
(no database/app import) checked at 588px and 320px: content/scroll widths match
573/573 and 305/305 respectively. Labels remained intact. CSS cache version updated.
No backend change or additional full-suite run. Screenshot: output/header-wrap-fixed.png.
