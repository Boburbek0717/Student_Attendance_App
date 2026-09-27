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

## Operational outcome

Code checkpoint: 288f6b1. Owner-authorized command completed: published 30, already
published 0, actor `Teacher`. Consistent pre-upgrade backup saved under
`%LOCALAPPDATA%/SAT Factory/backups/question-bank-release/`
`sat-backup-20260927T182808-943814f564e3440b8ab441c6e2b6cf15`.
No backup contents or unrelated student records exposed. Matching local server
restarted using `scripts/open_sat_factory.py --no-browser`.
Anonymous `/teacher/questions` and `/student/questions` both redirect to login.
Authenticated owner browser showed 20 published questions on page 1 and 10 on page 2;
question 30 preview confirmed PSAT 8/9 / Boundaries and its original choices/key.

Final usability corrections: passage snippets distinguish the repeated grammar
prompt in the teacher library; obsolete unavailable-practice copy removed. Latest
saved student answer persists when revisiting a question, with explicit new-attempt
link. Ten authoring tests passed (3.931s); seven focused practice tests passed again
(3.451s). These are the final scoped checks after the earlier full 191-test run.
No real student attempts were created during operational verification; grading
and permission scenarios used fictional data. No remote push/public hosting.


## Transitions collection published — 2026-09-27

Owner requested the same import/publication workflow for SQB PSAT 10 Transitions
(excluded) ANSWERS.pdf. Added a bounded extraction profile and an explicitly
allowlisted publication batch. Preserved source assessment PSAT/NMSQT & PSAT 10,
Reading and Writing / Expression of Ideas / Transitions, separate from PSAT 8/9.
Source SHA-256: 5be306b0b9b3dfb3dec9f8492b8d7fcb9574a8a30a8ead8c90fc1517fe6e4fd6.

Evidence:
- 33 pages extracted, zero quarantined; 8 easy, 9 medium, 16 hard.
- Independent pdfplumber comparison matched all 33 passages/explanations/keys and
  all 132 choices against pypdf extraction; rendered pages 1, 17, 33 inspected.
- `.venv/Scripts/python.exe scripts/verify.py --pattern test_sqb_pdf_extract.py`:
  five tests passed, including profile isolation and original Boundaries regression.
- `.venv/Scripts/python.exe output/transitions-import/rehearse.py`: temporary-only
  publication of 33, repeat added zero, every stored field/key reconciled, all 33
  protected student pages rendered, theme count/pagination checked. Backup restore
  fingerprints matched; recovery 0.038 seconds. Local review artifacts remain untracked.
- Authorized operational command: `.venv/Scripts/python.exe
  scripts/publish_reviewed_questions.py --database attendance.db --candidates
  output/transitions-import/candidates.json --teacher Teacher --backup-directory
  "$env:LOCALAPPDATA/SAT Factory/backups/question-bank-release" --apply`.
  Result: 33 published, zero duplicates. Backup bundle:
  sat-backup-20260927T185003-0d80c77da8ab4c4e9efc9e56ae1b6eee.
- Scoped read-only post-publication count confirmed Transitions = 33 published.
  No accounts, credentials, attendance or unrelated records were inspected/edited.

QB-03 collection automatically appears using existing theme browsing; no app schema
or UI changes and no server restart required. No remote push/public deployment.
General PDF upload remains outside this bounded operator import. Next action:
owner can open Question practice > Transitions and try the collection.
