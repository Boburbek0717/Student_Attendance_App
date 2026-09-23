# SAT Factory — Usage simulation

Date: 2026-09-23. Baseline: 92089e0.

Executed scripts/simulate_usage.py against temporary SQLite with FastAPI TestClient,
one fictional teacher, one group and 24 fictional students. Login, lesson creation
and check-in used HTTP forms; service calls and fixture edits represented a balance
workaround and elapsed code time. Twelve logins shared one simulated IP within a
minute. No real accounts or working database records were changed.

This is an engineering simulation, not real-user research, a phone/Wi-Fi test or a
load test. Observed means executed; inspection means source review; hypotheses
need validation.

| ID | Scenario | Evidence | User problem / backlog |
| --- | --- | --- | --- |
| U01 | Class signs in on shared Wi-Fi | Observed: 12 valid accounts yielded ten HTTP 303 successes, then two HTTP 429 blocks. | Legitimate classmates share the login limit. SF-01 |
| U02 | Teacher starts a class | Observed: check-in open and all 24 already labelled Absent. | Provisional status may look final; manual refresh required. Preserve requested Absent behavior while refining clarity. SF-04, SF-09 |
| U03 | Student attends with a dead phone | Observed: balance changed from 12 to 11, but no presence record added; 23 remain absent after a different student checks in. Inspection confirms no manual attendance form/service. | Balance correction cannot fix attendance. SF-02, SF-11 |
| U04 | Late student needs an expired code | Observed: expired code returns 400; Start a new lesson creates lesson number two. Reopen already exists on detail page. | Teacher can accidentally split one class into two. SF-04 |
| U05 | Teacher reads lesson times | Observed: UTC labels; school context is Asia/Tashkent, UTC+05:00. | Mental conversion and date-boundary confusion; no wrong stored time demonstrated. SF-03 |
| U06 | Teacher views a full class | Observed: all 24 roster cards below setup forms. Inspection: student directory has no pagination. | Likely scrolling burden with more groups; scale latency not measured. SF-10, SF-17 |
| U07 | Prospective student explores home | Observed: honest result preview, no contact/enquiry link. Inspection: no publishing workflow. | Cannot assess real outcomes or ask to join. SF-06, SF-07, SF-08 |
| U08 | Owner reconciles records | Inspection: corrections audited, renewal packages lack actor/receipt metadata, exports and running statement absent. | Disputes harder to explain. Existing early/late balance tests already cover arithmetic. SF-11, SF-12, SF-16 |
| U09 | Laptop/server stops or needs recovery | Inspection: loopback development server and manual backups, no routine restore workflow. | Other devices cannot use the teacher's localhost address; recovery readiness unknown. No actual data loss simulated. SF-05, SF-13 |
| U10 | Student retries after losing response | Observed: first check-in 303, retry 400, exactly one row and balance 11. | Safe accounting but ambiguous error experience. Actual offline and screen-reader testing pending. SF-09, SF-17 |
| U11 | Forgotten credentials | Inspection: teacher password reset exists; recovery/change-password onboarding limited. | Teacher becomes classroom help desk. SF-14 |
| U12 | Move to another group | Inspection: deactivation/reactivation exists; another enrollment creates a new 12-lesson package; no transfer/archive workflow. | Credit transfer policy unclear. SF-15 |
| U13 | Add independent teachers | Inspection: all teachers administer one business by design. | Assignment-based access only needed if business model changes. SF-18 |

Normal check-in, duplicate prevention and expired-code rejection worked. The last
security pass reported 105 passing tests; this planning task did not rerun that
suite or perform a new security audit.

Reproduce from the project directory:

```powershell
.\.venv\Scripts\python.exe scripts/simulate_usage.py
```

The script prints results and removes its temporary database. Its route-name check
is supporting evidence only; source review confirmed the missing manual workflow.

Next validation: observe one teacher and three consenting students rehearsing
login, code entry, expiry, unavailable phone and balance lookup. Record completion,
help needed and confusing wording without collecting passwords or filming faces.
Ask a prospective student to find results and an enquiry route. These sessions
have not happened yet.
