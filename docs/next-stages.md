# SAT Factory — Next stages

Prepared 2026-09-24. Proposed roadmap, not authorization to implement every item.
This updates the earlier sprint forecast using the current product. No fixed
release dates or velocity promises. Keep two-week sprint planning horizons;
select a feasible slice of each stage rather than equating a stage with one sprint.

## Current position

SF-01 classroom login protection, SF-02 audited attendance correction and SF-03
Tashkent time display are implemented. The last full suite recorded 122 passing
tests; later homepage changes received focused checks, not a new full-suite run.
The course already supports students, groups, code attendance, manual package
renewals, owed lessons, balance corrections and saved lesson rosters.

The homepage now has the selected SF logo, teacher profile, three static student
Score Tickets and restrained motion. Teacher photo is still a placeholder.
Results are edited in a template; draft/publish tools do not exist. Named examples
were explicitly supplied for local display; do not infer a general publication
permission policy from those examples. Sprint 1 implementation is complete;
stakeholder review and retrospective are still pending in the records.

## Stage 1 — Make a class easy to run

Goal: the teacher can identify the right lesson and trust its attendance status.
Next proposed sprint focus: SF-04, split if needed. SF-09 follows the lifecycle work.

- Show the recent lesson prominently, including when its code has expired, with a
  clear way to reopen the same lesson. Identify starting a new class explicitly.
- Preserve Absent as requested. Recommended wording while a class remains open:
  "Absent — not checked in yet". Code expiry alone should not finish the lesson.
- Proposed lifecycle: in progress, finished, cancelled; code open/closed is a
  separate property. Finish closes check-in. Reopen requires an explicit teacher
  action and preserves the same roster, attendance and balance history.
- Cancel only empty accidental lessons, retaining evidence. Recommended initial
  rule: any original attendance, even reversed, prevents cancellation.
- Then add attendance refresh with a visible last-updated time, offline feedback,
  and retry messages that identify an already-recorded check-in.

Decide before implementing new states: whether to adopt Finish lesson, whether
finished lessons can be reopened, and the provisional absence wording. These are
proposals, not decisions already made by the owner. Audited corrections should
remain possible on finished lessons.

Review scenario: code expires midway through a class; teacher reopens that class,
student retries a submission, teacher corrects one record and finishes the lesson.
Exactly one debit per effective attendance; correct present/absent lists; no new
lesson created by reopening; no duplicate credit from concurrent requests.

## Stage 2 — Protect records and prepare for failure

Goal: recover the business data after laptop loss or a failed update. SF-05.

- Provide a documented SQLite-consistent backup process and clear success/failure
  feedback, with destination, frequency and retention explicitly configured.
- Proposed starting policy: daily backups, an additional backup before upgrades,
  14 daily versions, and a protected copy on another device or service. Owner must
  choose destination and access. Same-laptop copies alone do not cover laptop loss.
- Restore into a separate environment, verify students, packages, attendance,
  corrections and balances, and revoke restored sessions.
- Record actual recovery time and recoverable data age; proposed objectives are
  one working hour to recover and at most one day of lost records, not current SLAs.

Review scenario: restore a realistic backup with owed lessons and corrections;
reconcile totals and confirm old sessions cannot be reused. Never overwrite the
working database to rehearse recovery.

## Stage 3 — Manage the public course page without editing code

Goal: maintain trustworthy student stories and give prospects a way to enquire.
SF-06, SF-07 and SF-08 as separate small increments.

- Keep the selected Score Ticket layout. Add teacher-only result drafts with
  validated section scores, calculated total and optional baseline and comment.
- Represent "started from scratch" separately from a numeric previous score.
  Record test date/type without inventing missing information.
- Add preview, publish and unpublish. Keep private evidence and permission notes
  out of public pages; attendance profiles never become public automatically.
- Decide name policy: anonymous labels by default or individually approved names.
  Confirm who records permission and how a removal request is handled.
- Add an enquiry button using the owner's chosen Telegram, email or other address.
  Add the real teacher portrait when supplied. Keep biography updates simple;
  no general website builder is needed for this increment.

Inputs: portrait, contact destination, agreed publication policy and missing result
metadata. Existing static stories remain available locally; they do not count as
completion of draft/publish acceptance criteria.

Review scenario: draft stays private, preview shows correct total, publishing shows
only approved fields, unpublishing removes the story, and the enquiry link opens
the supplied destination on mobile without sending anything automatically.

## Stage 4 — Reduce daily administration

Goal: teachers find their class quickly and students understand their balance.
Prioritize SF-10, then SF-11; refine SF-12 and SF-16 separately.

- Put current/recent classes and group search before setup forms. Add pagination
  where needed; do not invent a timetable until scheduling is requested.
- Show a balance statement of package additions, attendance and corrections.
  Explain carried debt and early renewals without exposing teacher-private notes.
- Add renewal receipts and an audited correction flow once consumed-credit rules
  are agreed. Payments remain outside the app.
- Add teacher-only date/group CSV exports using local dates, protecting private
  fields and spreadsheet users from formula-like text.

Review scenario: student starts with two owed lessons, renews 12, attends once and
receives a correction. Teacher, student statement and exported totals agree.

## Stage 5 — Prepare a controlled public launch

Goal: students can use a secure reachable service, with recovery already rehearsed.
SF-13, SF-14 and focused SF-17 work; operational preparation may overlap earlier
stages, but deployment is a separate explicit decision.

- Choose hosting, domain and database/storage plan. Configure HTTPS, secure cookies,
  trusted proxy/host settings, secrets, process restart and useful sanitized logs.
- Repeat security checks against the deployed configuration; check permissions,
  expiry, request limits and concurrent balance updates. Test upgrade and rollback.
- Provide clear login and recovery guidance, then run a small consenting class pilot
  on real phones and classroom Wi-Fi. Fix observed problems before broader rollout.
- Measure with a stated realistic dataset; check mobile widths, keyboard access,
  reduced motion, long names, and slow/interrupted connections.

Release evidence: tested external URL, successful recovery drill, no unresolved
critical defects, reconciled attendance/balances, and owner acceptance of pilot
outcomes. A localhost preview is not a student-accessible deployment.

## Scrum working rhythm

Before selecting new scope, demonstrate the completed attendance/time changes and
record owner feedback plus one retrospective improvement. Do not invent a completed
ceremony. At planning choose one outcome, order its stories, and keep an achievable
forecast. During active work record progress and obstacles; there are no background
runs or scheduled ceremonies unless requested. At review demonstrate the scenarios,
record defects and feedback, then reorder this roadmap and the Product Backlog.

Keep existing Definition of Done: relevant tests, permissions and transaction
checks where applicable, mobile/keyboard review, recovery for data changes,
accurate docs and a committed runnable increment. Track completed work and carryover
before inferring velocity.

## Recommended next action

Refine the three lesson-lifecycle decisions above, then select the first SF-04
slice. Start with recent-lesson visibility and clear reopen/new-class actions;
add finish/cancel states after their behavior is agreed. Keep backups next in order.
Do not add online payments, facial recognition, GPS attendance or unrelated portals.
