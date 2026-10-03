# Assignment security and workflow review — 2026-09-29

Baseline: 01139a9. Tracked tree clean at start. Review covers assignment creation,
category selection, independent attempts, student progress and teacher reports;
shared authentication, CSRF, request limits and attendance controls were inspected
and the wider isolated suite run. This is a bounded code/regression review, not a
claim that every possible vulnerability has been excluded. No live data or secrets
read, no external service access, no migrations or deployment.

## Confirmed issues fixed

- Alternate numeric spellings such as 1:2 and 01:02 bypassed string duplicate
  detection and reached a database uniqueness error. Reject duplicate revision IDs
  after parsing, before inserts. Transaction remains atomic.
- A year-0001 local deadline could underflow during UTC conversion. Treat overflow
  as invalid input with a clear 400 response.
- Transaction conflicts/busy storage raised an unhandled error on assignment writes.
  Map the transaction helper's rolled-back failures to a generic 503 with Retry-After;
  the existing submission key remains reusable. Do not expose storage internals.
- Student assignment list performed two queries per task. Batch items and personal
  attempts in two queries total; regression test asserts query count and isolation.

Oversized answer IDs were already protected; a new regression confirms rejection.
No auth bypass was demonstrated in this review. Existing tests cover teacher report
ownership, recipient access, enrollment revocation, CSRF, independent practice,
immutable history, concurrent retries, sealed snapshots and restore reconciliation.

## Remaining work / limits

- No fresh package advisory scan or external penetration test in this pass.
- No real-phone or sustained classroom load test; no owner acceptance inferred.
- Reports load all attempts for their saved recipients; long-lived data may need SQL
  aggregation/pagination. Lists expose the latest 100 tasks. Creation loads published
  questions in one page. These are scaling/workflow limits, not proven data leaks.
- Practice and assignment submissions have no dedicated persisted rate limiter;
  authenticated rapid submissions can grow history. Define and test a shared limiter
  preserving legitimate retries before broader deployment.
- A rejected creation form still uses a general error page and browser Back to retain
  entries. An inline re-render preserving selections is a future usability improvement.

No schema or dependency changes. Changes are pending the next authorized local
server restart; this audit does not start or connect to the working database.

## Verification evidence

- `.venv\Scripts\python.exe scripts/verify.py`: 235 passed, 148.850s.
  This run started before the final assignment transaction-error wrapper was added.
- Final `.venv\Scripts\python.exe scripts/verify.py --pattern test_assignments.py`:
  12 passed, 19.536s, including the wrapper and successful retry after a simulated failure.
- `node --test tests/test_lesson_live.cjs tests/test_practice_highlights.cjs tests/test_question_math.cjs`:
  11 passed; `node --test tests/test_practice_preview.cjs`: 3 passed.
- `.venv\Scripts\python.exe -m pip check`: no broken requirements. This checks
  compatibility, not vulnerability advisories.
- `git diff --check`: passed.

## Follow-up status — 2026-10-03

The creation-form recovery item was completed in 55bd3be. The next bounded change
adds a shared persisted budget for new assignment/practice answers (30 per student
per rolling minute), preserving identical retries. See the latest product backlog
and pilot handover entries for verification and limits. The earlier remaining-work
list describes the review baseline, not current completion status. Real classroom
Wi-Fi/device testing and sustained production load testing remain outstanding.
