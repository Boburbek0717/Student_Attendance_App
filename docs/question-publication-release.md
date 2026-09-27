# Question publication and practice — 2026-09-27

Owner explicitly authorized publishing the reviewed PDF batch after checks and
selected username `Teacher` for ownership/publication attribution. This authorizes
the specific operational import, pre-upgrade backup and local server restart; it
does not authorize a remote push, public hosting or unrelated data inspection.

## Release scope

- Teacher publication/unpublication/archive with immutable actor/revision history,
  stale-state checks, source-note requirement, CSRF and session recheck under lock.
- Active-enrollment-only student library and question practice. Pagination is 20.
  Answers are graded server-side, attempts append-only, and retries/concurrent
  duplicate submissions return the existing attempt. Explanation and key enter
  HTML only for a submitted attempt owned by the requesting student.
- Bookmark add/remove and previous/next navigation. Assessment labels preserved.
  No timer, highlighting, dedicated bookmark/history directory, analytics or
  resumable practice-session interface yet. These remain bounded next increments.
- Schema v2 adds publication history. Upgrade from v1 preserves questions/attempts;
  backup validation recognizes legacy, v1 and v2. Pre-release backup required.
  Old code should not run on v2. Restore a matching backup into a separate destination
  for rollback; never delete real records with the empty-foundation downgrade helper.
- Local static interactive preview remains a separate owner artifact with client-side
  keys. It is never used as the authenticated grading page.

## Verification before operational publication

- `.\.venv\Scripts\python.exe scripts/verify.py`: 191 passed, 90.972s.
- Subsequent `.\.venv\Scripts\python.exe scripts/verify.py --pattern test_question_practice.py`:
  7 passed, 3.364s, including added cross-student attempt denial and taxonomy display.
- `node --test tests/test_lesson_live.cjs tests/test_practice_preview.cjs`: 8 passed.
- Schema tests include v1-to-v2 content fingerprint preservation and backup support.
- Disposable 30-question operator rehearsal: published 30, second run added zero
  and recognized 30 existing entries; 30 publication events. Backup/restore
  fingerprints matched; local recovery 0.038s.
- Fictional HTTP-rendered browser fixture: mobile 390px stacked passage and choices,
  no horizontal overflow, labelled radios. No real student/device acceptance claim.
- `git diff --check` passed. No new dependency.

## Specific batch operation

`scripts/publish_reviewed_questions.py` requires explicit database, candidate path,
teacher and backup destination, plus `--apply`. It only accepts the reviewed PDF's
source SHA and 30 unique IDs. It creates a SQLite-consistent backup before migration,
then imports all questions and publishes in one transaction. Repeated imports skip
identical already-published entries; conflicting, withdrawn or ambiguous entries
stop the batch instead of overwriting them. It never creates users or reads secrets.
The source hash is provenance, not authentication of arbitrary edited JSON; use
only the locally generated, reviewed candidate file.

Official operation outcome is appended to the handover after it actually succeeds.
The reviewed source and generated question artifacts are kept outside Git.
