# Question Bank delivery plan — 2026-09-27

Owner selected this feature after the SF-10 dashboard hierarchy slice (c741fb5).
Deliver in small reviewable phases, retaining FastAPI, SQLAlchemy, SQLite, Jinja
and the existing session/CSRF protections. No public deployment is included.

## Decisions and audit

- Access: any student with an active course enrollment. Check the existing
  Enrollment.active field at request/write time; do not create parallel grants.
  Teacher authoring is teacher-only. These route checks are still to implement.
- Existing signed cookies refer to revocable database login sessions. Reuse this
  mechanism and the role checks, with a separate Question Bank access helper.
- Existing static files are public. Question media must use private storage and
  authorized delivery, never the static directory. Uploads are not implemented.
- Existing forms have a 16 KB body limit. Introduce a narrowly scoped upload limit
  when media/imports arrive; do not relax every endpoint.
- Database startup previously only created missing tables. This feature introduces
  an additive version ledger and transactional migration for its own tables.
- No new Python or JavaScript dependency in the foundation. Evaluate locally
  served KaTeX for math at rendering time, with trust disabled and bounded input:
  [KaTeX security](https://katex.org/docs/security). PDF extraction dependencies
  and import workers will be evaluated with the import phase, not installed now.
- Taxonomy seeds two sections, eight domains and thirty skills from
  [College Board content domains](https://satsuite.collegeboard.org/practice/content-domains).
  Internal skill codes are local identifiers, not official College Board codes.
  Seeding happens once; restarting must not overwrite future taxonomy edits.

## Structure and relationships

`app/question_bank/models.py` owns the normalized feature tables on the existing
shared Base. A bank contains sections, domains and skills. A question owns numbered
revisions; each revision references a skill, difficulty, passage, stem, explanation,
optional source and private media record. Flexible choices and a separate answer
key belong to a revision. A question points to its current and published revision.

Draft revisions can be assembled before sealing. Sealing requires complete content
and answers; sealed content and answers cannot be updated or deleted. Corrections
will create a new revision. Publishing requires a sealed revision belonging to the
question. Student attempts reference that exact revision and choice, preserve their
recorded correctness and are append-only. Unique submission keys support future
retry-safe submission; service logic must still implement retries and concurrency.
Bookmarks belong to a student and question. Numeric answers have schema support,
but numeric validation/grading is not yet delivered.

Services must calculate correctness server-side, authorize every request, avoid
answer/explanation leakage before submission, and prevent edits to media used by
historical revisions (immutable storage objects). A schema alone is not a complete
authorization, upload, audit or grading implementation.

## Selected question-screen direction

Use the owner's supplied screenshot as a structural reference, not a visual copy:

- Desktop: restrained top toolbar; passage/diagram on the left, question and
  answer choices on the right. Comfortable reading width and a clear divider.
- No passage: a centered question column instead of an empty left panel.
- Mobile: passage above the question; no forced horizontal split or tiny text.
- Bottom navigation: question position, previous/next and clear submission action.
  Keep controls reachable without obscuring answers or keyboard focus.
- Retain SAT Factory typography, colors and restrained components. Selected,
  focused, submitted and error states must be distinct beyond color alone.
- Explanations appear after an accepted submission. Bookmark/review controls only
  appear when functional. Timer, highlighting and answer elimination are separate
  later increments; do not copy unsupported controls from the reference.

This layout is recorded, not yet implemented or visually tested.

Update: QB-02 first slice now uses the split layout in teacher preview, with a
single column without a passage and stacked mobile layout. Student answering and
its bottom navigation remain QB-03 work.

## Bounded delivery sequence

| ID | Increment | Acceptance / status |
| --- | --- | --- |
| QB-01 | Schema, taxonomy, migration and recovery compatibility | Implemented; isolated evidence below. No user-facing feature yet. |
| QB-02 | Teacher authoring | Implemented: drafts, preview, publication/unpublication/archive and immutable publication audit. Unpublish before editing. |
| QB-03 | Student browsing and answering | Core implemented: active-enrollment gate, pagination, responsive split, server grading, atomic attempts/retries and own-result review. Broader practice-session UX remains QB-08. |
| QB-04 | History, saved questions and mistakes | Student-owned records, revision-aware review and dependable empty/error states. |
| QB-05 | Filters and progress | Taxonomy/difficulty filters, indexed queries, explainable attempt-based summaries; scale tests. |
| QB-06 | Structured imports | JSON/CSV draft staging, validation, duplicate warnings, provenance and human approval. No auto-publication. |
| QB-07 | PDF-assisted import | Bounded extraction jobs, private storage and review pipeline; source permissions required. |
| QB-08 | Practice sessions and final hardening | Persisted session navigation, mobile/keyboard/scale/security checks and documented limitations. |

Attempt recording ships with answering rather than as a later unsafe addition.
Likewise pagination ships with browsing. Add import jobs and practice-session
entities when implementing those workflows. Assignments, mock exams and adaptive
testing remain future extensions.

Expected route families: `/teacher/questions` for management/editor/preview;
`/student/questions` for browse/practice/history/saved/mistakes/progress. Private
media and import review routes follow later. No such routes exist in QB-01.

## Migration and recovery operation

`app/question_bank/migrations.py` owns schema version 1 and integrity triggers.
Normal application startup calls `initialize_database`, which applies or validates
the migration. **The next normal operator restart will add these tables.** This
development session has not restarted or migrated the working database.

Before an operational upgrade, use the existing explicit backup procedure in
[backup-recovery.md](backup-recovery.md) with the old matching release and an
authorized destination. Rehearse upgrade on a restored separate copy first.
Backups now recognize both pre-feature and complete version-1 databases and refuse
partial/unknown schemas or missing integrity triggers. They preserve Question Bank
records alongside existing balances, and restore continues to revoke sessions.
Validation checks names/columns/version and required trigger names, not a cryptographic
attestation of arbitrary database DDL.

For isolated maintenance, call `upgrade(engine)` or `downgrade_empty(engine)` with
an explicitly constructed engine pointing to the disposable destination. Never
use the module's default working engine in verification. Empty rollback removes
only the unused feature schema, including seed taxonomy; it refuses question,
source, media, attempt or bookmark records. Once content exists, restore a verified
backup into a new destination and use the matching code release. Do not run old
code against a newer schema. Subsequent schema changes need a new migration version.

## QB-01 evidence and limits

- `.\.venv\Scripts\python.exe scripts/verify.py --pattern test_question_bank_schema.py`:
  10 tests passed. Existing and fresh databases; repeatable upgrade; transactional
  failure; empty rollback and populated refusal; cross-revision integrity;
  sealed/attempt immutability; duplicate submission keys; incomplete-publication
  denial; unknown version/missing-trigger refusal; backup/restore reconciliation.
- All fixtures are fictional temporary SQLite files. Existing-table fingerprints
  and enrollment balances are compared across migration and recovery.
- `node --test tests/test_lesson_live.cjs`: 5 passed. Existing attendance polling
  regression checks with simulated DOM; not Question Bank browser coverage.
- Full isolated suite outcome is recorded in the handover after completion.
- No Question Bank UI, real-device validation, owner acceptance, OpenClaw review,
  live migration, uploaded content or production readiness is claimed.

## QB-02 draft-authoring slice — 2026-09-27

Delivered private `/teacher/questions` library (20 per page), create/edit drafts,
preview and latest-20 revision history. Saves append revisions, preserve source
notes, reject stale/concurrent edits, recheck the session within the write lock and
roll back failed writes. Incomplete drafts are allowed; complete revisions seal.
No publication endpoints, uploads, math rendering or student access yet. QB-02 is
still in progress; audited publish/unpublish/archive is the next lifecycle slice.
Plain-text editor supports up to six choices and retains the existing 16 KB request
limit. A retried new-question creation can create another draft; matching current
content is flagged in preview, not silently merged.

Form design reuses existing tokens and semantic fieldsets, informed by
[W3C grouping controls](https://www.w3.org/WAI/tutorials/forms/grouping/) and
[GOV.UK error summaries](https://design-system.service.gov.uk/components/error-summary/).
Isolated static browser review: 1365px desktop split, 390px mobile stacked preview;
narrow editor had no horizontal overflow, labelled controls and visible keyboard
focus. This is simulated browser verification, not real-device/user acceptance.
Full isolated verification: 179 tests passed in 58.240s, including ten authoring
tests for permissions/CSRF, revocation race, revision preservation, stale/concurrent
writes, validation, rollback, escaping, duplicates and pagination. No live data used.

Owner subsequently selected a bounded PDF-import test with a supplied PSAT 8/9
Boundaries document. This is an isolated rehearsal ahead of full QB-06/QB-07, not
authorization to auto-publish or a claim that a general PDF importer exists.

Later owner instruction explicitly authorized official publication under `Teacher`.
That batch has now been published after protected practice and audited publication
were implemented; see question-publication-release.md and the latest handover.
Historical statements above about unavailable routes apply to their dated slices.


## Owner change: simpler authoring — 2026-09-28

Supersedes the earlier six-choice and mandatory explanation/source requirements.
Editor now has A–D only. Explanation, source name, permission note and reference
are independently optional. Publication requires four nonempty choices and a valid
correct answer; incomplete drafts remain saveable. Category, question text and
difficulty remain required. Schema v3 removes the explanation sealing condition
without modifying existing revisions or attempt history. Legacy records with more
than four choices cannot be silently truncated by the four-choice editor.
Backup tooling accepts v1/v2/v3. Before upgrading, create a consistent backup;
rollback to older code requires restoring the pre-upgrade backup into a separate
destination and switching to that destination while the server is stopped, rather
than running old code against v3. Post-upgrade records would not be in that backup.
