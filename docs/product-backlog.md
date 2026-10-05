# SAT Factory — Product Backlog

Created: 2026-09-23. Baseline: commit 92089e0. Sprint 1 started 2026-09-23. SF-01 and SF-02 are implemented and verified;
see [Sprint 1 evidence](sprint-01-review.md). Remaining items await selection.

Roadmap: [next stages](next-stages.md), revised 2026-09-24. Stages are proposals;
existing story statuses remain unchanged. SF-04 and SF-09 are implemented; see Stage 1 verification.

Product Goal: make SAT Factory dependable for everyday classes and a credible,
privacy-conscious showcase of student results.

Existing capabilities are not new backlog work: accounts, groups, enrollment,
code check-in, snapshot absences, early/late renewal, debt counters, manual balance
corrections, lesson reopening and persistent check-in limits already exist.

Priority: P1 = essential next work; P2 = important next increments; P3 = later or
conditional. Order within a priority is intentional. Estimates are provisional
relative story points (2/3/5/8), not hours or promised delivery dates. Split an
8-point item further if it cannot fit the selected sprint. SF-01 and SF-02: Done. SF-03, SF-04 and SF-09: Done. All other statuses: Backlog.
Evidence IDs refer to [the usage simulation](usage-simulation.md).

| Order / ID | Priority | Backlog item | Points | Evidence | Dependencies |
| --- | --- | --- | --- | --- | --- |
| 1 / SF-01 | P1 | Classroom-safe login protection | 5 | U01 | None |
| 2 / SF-02 | P1 | Audited teacher attendance correction | 8 | U03 | None |
| 3 / SF-03 | P1 | School-local dates and times | 3 | U05 | None |
| 4 / SF-04 | P1 | Clear lesson lifecycle and attendance status | 5 | U02, U04 | Product decision D1 |
| 5 / SF-05 | P1 | Backup and tested recovery | 5 | U09 | Storage decision D3 |
| 6 / SF-06 | P1 | Anonymous results drafts | 5 | U07 | Real content from owner |
| 7 / SF-07 | P1 | Publish/unpublish approved results | 5 | U07 | SF-06, permission policy D2 |
| 8 / SF-08 | P1 | Prospective-student contact route | 2 | U07 | Owner's contact destination |
| 9 / SF-09 | P2 | Live attendance feedback and retry clarity | 5 | U02, U10 | SF-04 |
| 10 / SF-10 | P2 | Teacher dashboard organized around today's classes | 5 | U06 | SF-03; schedule scope D4 |
| 11 / SF-11 | P2 | Explainable student balance statement | 5 | U03, U08 | None |
| 12 / SF-12 | P2 | Renewal receipt and correction trail | 5 | U08 | Renewal mistake policy |
| 13 / SF-13 | P2 | Safe deployment and operational checks | 8 | U09 | SF-05, hosting decision |
| 14 / SF-14 | P2 | First-login and account recovery guidance | 5 | U11 | SF-01 |
| 15 / SF-15 | P2 | Group archive, rename and membership transfer | 5 | U12 | Transfer-credit policy |
| 16 / SF-16 | P2 | Attendance and balance exports | 3 | U08 | SF-02, SF-03 |
| 17 / SF-17 | P2 | Accessibility and realistic scale validation | 5 | U06, U10 | None; apply basics in every story |
| 18 / SF-18 | P3 | Assigned-teacher permissions | 8 | U13 | Only if multiple independent teachers are needed |

## Acceptance criteria and user stories

### SF-01 — Classroom-safe login protection
As a student, I can sign in with classmates on the same Wi-Fi without another
student consuming my whole allowance.
- Thirty distinct valid accounts can sign in from one connection address within
  one minute in an isolated test; normal student logins do not lock out the teacher.
- Repeated bad credentials still trigger a documented account-based limit and a
  separate broader connection-abuse limit; guessed accounts get generic errors.
- Limits survive restarts and parallel workers. Time-based recovery is tested;
  account identifiers cannot be used to create unbounded stored limiter rows.
- Define exact thresholds during refinement; do not remove protection to pass the test.

### SF-02 — Audited teacher attendance correction
As a teacher, I can record a present student whose phone failed and correct a
mistaken attendance without editing their balance as a substitute.
- Teacher selects an enrolled student on a specific lesson, sees current status
  and proposed balance effect, and supplies a reason before confirmation.
- Mark-present charges exactly once, including owed lessons when credit is exhausted.
  Reversal restores exactly the corresponding credit; repeated requests do neither twice.
- Original code/manual origin, actor, reason, timestamps and correction chain
  remain reviewable. Do not delete the historical evidence.
- Present/absent lists, student history and totals agree after a correction.
  Renewal and later corrections remain consistent; student/CSRF/stale-form attacks fail.
- Historical or inactive enrollments require explicit eligibility rules at refinement;
  a student from another group cannot be selected accidentally.

### SF-03 — School-local dates and times
As a teacher or student, I see understandable lesson dates in Asia/Tashkent.
- Display school timezone and UTC offset on lesson, attendance, renewal and
  correction views; store timestamps in UTC.
- A lesson near UTC midnight appears under the correct local date, consistently
  for both roles. Code expiry still uses server time, not the browser clock.

### SF-04 — Clear lesson lifecycle and attendance status
As a teacher, I can distinguish a new class, a closed code window and a finished class.
- After a code expires, the recent lesson is easy to reopen from its group card;
  starting another lesson clearly identifies that it creates a separate class.
- Keep the requested Absent label; while check-in is open, explicitly qualify it
  as provisional. On closure/finalization, show the relevant status and time.
- D1 resolved by owner: finishing is permanent, with attendance corrections allowed afterward.
- Reopening preserves lesson identity and roster; does not double-charge attendance.
  Accidental empty lessons can be visibly cancelled, preserving their audit record.

### SF-05 — Backup and tested recovery
As the course owner, I can recover records after a laptop failure or failed update.
- Document a backup process with destination, frequency, retention and failure
  indication; include SQLite-consistent backups and restricted access to personal data.
- Restore a backup into a separate environment and verify accounts, attendance,
  corrections, renewals and foreign keys. Revoke sessions during recovery.
- Agree recovery objectives before implementation; proposed targets: at most one
  day of lost records, recovery within one working hour. These are not achieved SLAs.
- Database changes have versioned migration and recovery instructions. Never test
  destructive restoration against the working database.

### SF-06 — Anonymous results drafts
As the owner, I can prepare accurate score cards without publishing faces or names.
- Teacher-only editor stores anonymous label, test date, official/practice type,
  total and section scores, optional baseline and story, and evidence reference.
- Validate score ranges/increments against official SAT guidance during implementation;
  reject inconsistent section totals and misleading mixed test types.
- Drafts and private evidence never appear in anonymous public responses or public files.
  No automatic publication from a student's attendance/account profile.

### SF-07 — Publish/unpublish approved results
As a visitor, I can see authentic results while students retain privacy.
- Owner previews a card and records permission status before explicit publication.
  Real examples must be supplied; no fabricated metrics or testimonials.
- Only published entries are public. Unpublishing removes cards and dependent
  aggregate statistics; cache behavior is checked.
- No faces, full names, account links, raw score-report identifiers or private
  evidence appear publicly. Empty states remain honest when no results are approved.
- Keep aggregate statistics out of the first release unless sample/period rules
  and duplicate-student counting are explicitly defined.

### SF-08 — Prospective-student contact route
As a visitor, I can ask about joining without needing an existing student account.
- Add one clear enquiry CTA linked to an owner-provided email, phone or messaging
  destination; label it separately from course login.
- Verify destination and mobile behavior; never invent contact information or
  transmit a visitor's details automatically. No enquiry database needed initially.

### SF-09 — Live attendance feedback and retry clarity
As a teacher/student, I know whether attendance is saved without repeated guessing.
- Teacher counts/status refresh with an accessible last-updated indicator and
  a connection-failure message; no code or roster leaks to students.
- Student success identifies the lesson and group; retry after a lost response
  confirms existing attendance instead of suggesting another charge.
- Rate-limit response communicates when to retry; background polling stops or
  backs off when hidden/offline and cannot spend the check-in attempt allowance.

### SF-10 — Teacher dashboard focused on daily work
As a teacher, I find my group and current class before account-creation forms.
- Put current lessons and group search first; move setup forms behind clear links.
- Search/filter groups and students; paginate directory/rosters and histories.
- Demonstrate 10 groups and 300 fictional students with recorded response timings
  on stated hardware; agree a target before calling it performance-ready.
- Avoid promising a 'today' timetable until D4 defines scheduling requirements.

### SF-11 — Explainable student balance statement
As a student, I can understand why my credit changed.
- Show chronological purchases, attendance debits and manual corrections with a
  running balance. Teacher-private notes stay private; students receive an appropriate label.
- Totals match the existing balance for early renewal, negative credit, corrections
  and transfers if supported. Show 'correction' instead of implying a purchase.

### SF-12 — Renewal receipt and correction trail
As a teacher, I can trace a recorded renewal and safely fix a mistaken one.
- Record actor, timestamp, package and optional private reference for new renewals.
  Historical rows without actor metadata remain explicitly unknown.
- Show an identifiable confirmation. A correction retains the original record,
  explains its balance impact and rejects stale/repeated submissions.
- Clarify consumed-credit handling before implementing reversal. No online payment flow.

### SF-13 — Safe deployment and operational checks
As the owner, I can give students a reachable URL without exposing a development server.
- Choose hosting explicitly; configure HTTPS, secure cookies, secret handling,
  trusted host/proxy boundaries and production startup without reload mode.
- Health checks, error logs without codes/passwords, dependency review and restart
  recovery are tested. SF-05 restore drill completed before public use.
- Localhost on the teacher's laptop is not presented as a URL students can use
  on their own devices. Deployment is a separate release decision, not done by planning.

### SF-14 — Account onboarding and recovery
As a new student, I understand where to log in and how to regain access.
- Clear help for forgotten usernames/passwords and no group enrollment; generic
  responses avoid account enumeration.
- Define teacher-issued temporary-password versus student-change flow; if temporary,
  require a change and invalidate prior sessions. Never send passwords in URLs/logs.
- Test novice mobile login with a real consenting user before claiming usability success.

### SF-15 — Group lifecycle
As a teacher, I can tidy old groups and move students without losing their records.
- Rename/archive groups, retain historical references, and block accidental new
  lessons for archived groups while allowing history review.
- Transfer membership with an explicit choice about credit; no implicit duplicate
  12-lesson purchase. Old rosters and attendance remain tied to original lessons.

### SF-16 — Reports and exports
As the owner, I can reconcile a period's attendance and balances outside the app.
- Teacher-only date/group filters and UTF-8 CSV; local-date boundaries match the UI.
- Totals match records; neutralize spreadsheet-formula injection in user text.
  No password hashes, sessions or attendance codes in exports.

### SF-17 — Accessibility and scale validation
As a mobile or keyboard user, I can finish everyday tasks confidently.
- Keyboard-only login, code entry, renewal and correction have visible focus,
  meaningful error associations and accessible status announcements.
- Test 320px width, 200% text zoom, long names and empty/large rosters; no hidden
  essential actions or page-level horizontal overflow.
- Record real-user observations and measured timings separately from assumptions.

### SF-18 — Assigned-teacher access (conditional)
As an owner with independent teachers, I can restrict access to assigned groups.
- Define owner/teacher responsibilities first. Current all-teachers-share-one-business
  behavior is intentional, not a demonstrated cross-tenant exploit.
- Test direct URL and POST access across assignments for rosters, balances, password
  resets and results administration; log privileged changes without secrets.

## Decisions for refinement

- D1 resolved 2026-09-24: Finish permanently; corrections only afterward.
  Absent label retained, with provisional explanation while check-in is open.
- D2: Who grants and records publication permission, what evidence is retained,
  and what is the withdrawal process? No faces by default.
- D3: Where should recoverable backups live, and who may access them?
- D4: Is a recurring timetable needed, or are searchable groups sufficient?

Keep manual renewals and late check-in with owed lessons. Do not add online
payments, facial recognition, GPS attendance, a parent portal or a messaging
service merely because they are common in other school apps.

## Owner-requested design preview — 2026-09-23

A local visual exploration related to SF-06/SF-07 now compares three designs on
/#results: score ticket, student story, and bold scorecard. The owner explicitly
supplied Asilbek Shukurov's full name, 610 EBRW, 690 Math and testimonial for this
preview. This request supersedes anonymous labels for this local example only;
public publishing policy, draft editor and permissions remain unimplemented.
Starting from zero is expressed as starting from scratch; no invented baseline,
score improvement, date or test certification is shown. Comment is lightly edited.
Desktop and mobile browser checks cover responsive cards and anchor navigation.
No database changes or external publishing. SF-06/SF-07 remain Backlog.

## Selected results design

Owner selected Score Ticket and supplied Axadjon Axmadqulov (1350: 640 + 710)
and Shoxjaxon Akramov (1210: 610 + 600). Three distinct students now use the
same design; comparison options removed. Comments lightly polished. No baseline
invented for Shoxjaxon; scratch labels apply only to Asilbek and Axadjon.
This remains static owner-supplied content; SF-06/SF-07 management tools remain Backlog.

## Owner-requested branding exploration

Three generated SAT Factory logo concepts saved under output/branding; no final
logo selected. Homepage teacher introduction added before results with a labeled
portrait placeholder and editable name, biography, approach and background text.
No qualifications or personal history asserted. No changes to sprint story scope.

Branding verification: homepage returned HTTP 200; teacher section visually checked
at 1280 x 900 and 390 x 844. Existing student results remain below the section.

Owner selected logo 1 (industrial SF monogram), now used in the shared header.
Teacher profile uses owner-supplied name Noraliev Boburbek, SAT 1430, IELTS 8.5,
teaching since 2024 and university description. Teaching copy polished around
practical understanding. Portrait remains a labeled placeholder awaiting a photo.

## Owner-requested brand motion — 2026-09-24

Homepage sections receive short one-time viewport entrances, result tickets lift
on fine-pointer hover, and action arrows respond to hover/keyboard focus. Native
anchor navigation is smooth only without a reduced-motion preference. No looping
animations or score counters. Content remains visible without JavaScript; preference
changes cancel running animations. No attendance workflow or sprint scope changes.

Verification: homepage, local script and login return HTTP 200; login does not
load the entrance script. Browser confirmed script loading, visible content and
smooth anchor styling with no console errors; mobile layout checked at 390 x 844.
Reduced-motion branches reviewed in CSS/JS; OS preference switching was not exercised.

Homepage copy cleanup requested by owner: removed the work/story footnote,
Practice/Persistence/Progress strip, edited-comments caption, repeated ticket
slogans, portrait index and footer slogan. Teacher biography and student
testimonials preserved.

## Pilot priority update — 2026-09-26

The owner selected classroom validation (SF-17), backup/recovery (SF-05),
onboarding (SF-14), and release preparation (SF-13), in that order. These are
In progress / Selected respectively; no owner acceptance or public release is
claimed. SF-04/SF-09 stay Done. Results tools and additional branding are deferred.
Implementation of fictional recovery mechanisms is authorized before final
storage/retention decisions. See pilot-handover.md for current evidence and limits.

## Bounded recovery tooling checkpoint — 2026-09-26

SF-05 local mechanisms implemented and fictional recovery verified; operational
storage/access/retention and off-laptop copy remain pending. It is not Done.
See backup-recovery.md and recovery-evidence.json. SF-17 automated rehearsal found
and fixed classroom connection starvation (abc0212); mobile/keyboard and owner
walkthrough remain pending. SF-14 and SF-13 remain Selected, not delivered.
Owner chose existing teacher-issued passwords and teacher resets, and requested
one small chunk at a time. Stop at the recovery checkpoint before new feature work.

## SF-17 browser review slice — 2026-09-26

Mobile/keyboard rehearsal completed on fictional data at 320/390 viewport widths.
Header wrapping and error-field associations repaired; disposable owner demo and
launch checklist delivered in mobile-classroom-review.md. SF-17 remains In progress:
owner, real-device/network, 200% text zoom and assistive-technology checks pending.
No new deployment or onboarding scope included in this slice.

## SF-14 implementation review — 2026-09-26

Owner selected teacher-issued passwords and teacher resets. Guidance implemented;
SF-14 moves to Review. Evidence: onboarding-review.md. Real first-time user/mobile
validation remains outstanding; no self-service reset or forced-change flow added.
SF-13 remains Selected for the next bounded chunk, with deployment authorization
and provider-specific decisions separate.

## Visual refinement slice 1 — 2026-09-26

Owner deferred SF-13 and selected research-led design refinement. Homepage and
public header slice implemented, in Review; see design-refinement.md for exact
evidence and scope. Focused SF-17 responsive/keyboard checks included a mobile
off-screen focus fix. SF-17 as a whole remains In progress. No SF-08 contact route
or SF-10 teacher dashboard completion is implied. Next bounded design slice:
Results and Login, before broader portal changes.

## Visual refinement slice 2 — 2026-09-27

Results/Login refinement implemented and in Review; evidence in design-refinement.md.
Existing content and authentication behavior retained. SF-10 dashboard is the next
bounded implementation. SF-17 overall and real-device/owner review remain open.

## SF-10 first design slice — 2026-09-27

SF-10 In progress: daily-class controls first, group roster disclosures and secondary
setup implemented. Validation errors remain visible and setup opens automatically
on rejection/empty state. Evidence: design-refinement.md. Search/pagination and
larger-scale acceptance remain outstanding. This does not complete SF-17.

## Question Bank selected — 2026-09-27

Owner selected the Question Bank brief as the current priority, superseding the
next SF-10 slice. SF-10 remains incomplete; deployment remains deferred.
Use [Question Bank plan](question-bank-plan.md) for QB-01 through QB-08 acceptance
criteria and sequencing. QB-01 foundation is implemented and verified (169 Python
tests and five Node checks passed); QB-02 teacher authoring is next. Student access is any active course
enrollment. The owner's two-column question-screen reference is recorded for QB-03.
The schema is not a usable Question Bank increment by itself; do not mark the
whole feature done or claim authoring/practice has shipped.

QB-02 first slice implemented: private draft library/editor/preview/history; ten
new tests, 179 total passed. Publishing lifecycle remains open. Owner next selected
an isolated PDF import rehearsal using supplied PSAT 8/9 Boundaries questions.
See question-bank-plan.md; QB-06/QB-07 are not marked complete by the rehearsal.

PDF rehearsal evidence: [pdf-import-rehearsal.md](pdf-import-rehearsal.md). Thirty
PSAT 8/9 Boundaries drafts imported and recovery-reconciled in isolation. No live
import or publication; owner review and the production import workflow remain open.

Owner subsequently authorized official publication under `Teacher`. QB-02 audited
publication lifecycle and QB-03 core server-graded practice are implemented and
verified; see question-publication-release.md. Operational publication outcome
is recorded in the release note: 30 published under Teacher after pre-upgrade backup.
General import UI, saved/history directories and
analytics remain open; the one-profile operator importer does not complete QB-07.


## QB-03 theme browsing — 2026-09-27

Owner requested collections instead of a flat student question list. Implemented
published-question collections by existing skill, with assessment/section labels,
counts, paginated collection contents, and previous/next restricted to that skill.
The imported PSAT 8/9 questions appear together under Boundaries. Teacher authoring
continues to list individual records. No schema or content migration is needed.
Acceptance evidence: `scripts/verify.py --pattern test_question_practice.py`:
8 tests passed, including collection counts, unpublished exclusion, cross-theme
navigation and enrollment enforcement. Shared responsive library styles and native
links are reused; no new real-device visual check or owner acceptance claimed.


Owner-authorized Transitions batch published: 33 PSAT/NMSQT & PSAT 10 questions
under Teacher, with extraction, isolated retry/recovery checks and a pre-publication
backup. See question-publication-release.md. General PDF import UI remains open.


## QB-03 teacher category parity — 2026-09-27

Fixed the teacher library's flat list: its entry page now groups current revisions
by skill with assessment/section labels and total/published counts. Category pages
retain preview/edit/publication access and category-scoped pagination. Drafts and
archived records stay manageable; student published-only access is unchanged.
Preview links return to the relevant category. No database changes.
Verification: `scripts/verify.py --pattern test_question_authoring.py` (11 passed)
and `scripts/verify.py --pattern test_question_practice.py` (8 passed), isolated
from working records. Covers categories, scoped pagination, escaping, authorization
and existing practice/publication behavior. Shared responsive styles reused; no
new real-device visual review claimed. Next: owner review of teacher categories.


## QB-02 category creation — 2026-09-28

Question editor explicitly requires Category. Teachers can select an existing
category or choose Create a new category and supply its name and assessment/subject
area. Category and draft save atomically under the existing write lock with session
reauthorization and CSRF protection. Normalized matching names within one domain
reuse the existing category. Missing/invalid fields retain the question text and
return actionable errors. Existing schema, published content and student access
are unchanged; categories become student-visible only with published questions.
Verification: `scripts/verify.py --pattern test_question_authoring.py`: 14 passed;
` scripts/verify.py --pattern test_question_practice.py`: 8 passed. New checks cover
mandatory selection, creation/reuse, invalid input preservation and category rollback
when draft saving fails. `git diff --check` passed. No real-device review claimed.
Next: owner can try Create question > Category > Create a new category.


## QB-02 optional fields and A–D editor — 2026-09-28

Owner requested optional explanation/source details and only four options. Delivered
four-slot editor, independent optional source fields, optional explanations through
publication/grading, and a publication check requiring all A–D texts and correct key.
Existing drafts remain saveable unfinished. Schema v3 removes only the explanation
sealing requirement; existing content/history is not rewritten. Updated backup
compatibility and rollback guidance in question-bank-plan.md.
Evidence: isolated `scripts/verify.py --pattern test_question*.py` 36 passed;
full `scripts/verify.py` 201 passed. Includes v2 upgrade content preservation,
backup/recovery, source-free publication and grading, A–D validation, permissions,
concurrency and existing attendance behavior. `git diff --check` passed.
Operational pre-upgrade backup: sat-backup-20260928T092453-0d6ffdbab533486594fdfeec6f6ee319
in LOCALAPPDATA/SAT Factory/backups/question-bank-release. Guarded launcher restart
succeeded; scoped schema-ledger check confirmed [1,2,3]. No student data printed,
remote push or public deployment. No new real-device visual review claimed.
Next: owner can use the simplified Create question form; no owner acceptance assumed.


## QB-07 local PDF upload — 2026-09-28

Delivered teacher Upload > Review > Import as drafts/Publish for the two verified
SQB formats. Auto-category, exact duplicate skipping, conflict/unsupported-page
blocking, atomic audited confirmation and bounded private parser/review storage.
Full evidence and limits: [pdf-upload.md](pdf-upload.md). 210 isolated tests passed;
actual 30+33 PDFs rehearsed in a disposable DB, all duplicates detected on re-upload.
Desktop/390px/keyboard review completed on isolated rendered pages. No real student
records touched, public deployment, remote push or owner acceptance claimed.
Next: owner tries Import PDF; arbitrary/scanned PDF support remains out of scope.


## QB-08 reliability/security slice — 2026-09-28

Owner deferred further PDF work and selected optimization/bug fixing/security.
Scope: manual question forms, publication retries, response header coverage.
Reproduced before fixing: a valid 3,500-character Cyrillic passage returned HTTP413;
FastAPI validation responses lacked no-store/nosniff/CSP headers used by rendered pages.

Delivered:
- Only new/edit question POST forms get 192 KB envelopes for percent-encoded Unicode;
  existing per-field limits remain enforced. Other forms keep 16 KB, PDF envelope
  unchanged. Boundary tests prove the exception does not widen unrelated endpoints.
- Shared security headers now cover normal responses, redirects, validation and
  body-limit errors. Non-static responses use no-store; static caching remains intact.
  Built-in API documentation retains its existing asset policy to avoid breaking
  its inline/CDN assets. Existing authentication/session/CSRF checks are unchanged.
- Re-publishing the current published revision exits before loading revision,
  options and key (at most two SELECTs in regression test), still checks teacher
  identity/current revision and retains one audit event. Archived/missing snapshots
  are rejected before sealing work. No schema/data migration.

Evidence: two new regression cases failed before changes and pass after them.
`scripts/verify.py --pattern test_question*.py`: 49 passed at initial checkpoint.
`scripts/verify.py`: 214 passed in 68.555 seconds. Final compatibility adjustment
for built-in docs then passed all 19 authoring tests, including a new docs regression.
`git diff --check` passed. Refreshed dependency-audit.json: PyPI version metadata
checked all 30 pinned packages, no listed advisories, no unavailable packages.
This is an advisory metadata check, not a penetration test/security certification.
Working records/secrets were not read during verification. Existing untracked
artifacts preserved. No PDF feature expansion, public deployment or remote push.
Next bounded opportunity: manual new-question retry protection and larger-library
query profiling; neither is claimed complete by this slice.


## QB-03 student text highlighting — 2026-09-28

Added selection-based highlighting to passage/question text, selected highlight
removal and Clear highlights. Uses native text selection and safe text/mark nodes;
no HTML insertion, grading requests or answer-key exposure. Browser-local offset
storage is keyed by student and exact revision, so it persists on that browser
when revisiting; no cross-device sync is claimed. No text, answers or credentials
are stored. Malformed/out-of-bounds storage is ignored; unavailable storage gives
a visible temporary-only notice. Bounded ranges; controls hidden without JS.
Verification: `node --test tests/test_practice_highlights.cjs`: 3 passed (overlap,
malformed/bounded data, removal/splitting). `scripts/verify.py --pattern
 test_question_practice.py`: 10 passed. Isolated browser fixture: drag selection,
Highlight, reload persistence, Clear, reload with zero marks all verified. Real
student records untouched. Desktop browser check only; real mobile touch selection
remains unverified. Screenshot in output/highlights-check (untracked).
Next: owner tries highlighting in student practice. No owner acceptance assumed.


## Security checklist implementation — 2026-09-28

Owner requested review of a 20-item security checklist and implementation of useful
gaps. Full assessment: security-checklist-review.md. Implemented explicit production
mode requiring external session secret and exact hosts, Secure cookies, HTTPS redirect,
HSTS on HTTPS, disabled production docs/OpenAPI; local HTTP preserved. Added generic
validation responses without reflected input. No secrets or real records inspected.
Protected filename/index/history checks and limited tracked-source key patterns found
no candidates; no Git history rewrite, secret rotation or exhaustive history claim.
Verification: three new production-security tests passed; full guarded
`scripts/verify.py`: 218 passed in 70.073 seconds. `git diff --check` passed.
Production protections prepared, not activated/deployed. Disk/backup encryption,
TLS/proxy/storage choices and real pilot remain outstanding. No scope expansion into
CAPTCHA, external bot services or a different database. Next: owner can review the
20-row assessment; actual production activation waits for hosting decisions.

## Student practice visual refinement — 2026-09-28

Owner-requested Question Bank UX slice, related to student practice delivery.
Refined student-only navigation, theme cards, question rows and split reading/answer
layout. Correct and incorrect submissions now get distinct icon/text/color panels
and labeled answer choices. Brief entry/result animations respect reduced motion;
fresh feedback receives focus once, while saved results remain quiet. Submission
shows a busy state. Native radio keyboard behavior and server-side grading remain.
No new dependencies, migrations or live-record reads.

References: Carbon motion (https://carbondesignsystem.com/elements/motion/overview/)
and GOV.UK notification banners (https://design-system.service.gov.uk/components/notification-banner/).
Applied purposeful short motion and outcome text/icons rather than color alone.

Evidence: `.venv\Scripts\python.exe scripts/verify.py --pattern test_question_practice.py`
passed 12 tests (5.860s); `node --test tests/test_practice_highlights.cjs` passed 3.
Fictional isolated rendered fixtures checked in browser at desktop and 390px mobile
width; no horizontal overflow; native Space/arrow answer selection verified.
Correct/incorrect server results and one-time animation flag covered by tests.
Real phones and owner acceptance are not claimed. Full suite not repeated for this slice.
Baseline 4d66e33; feature files committed separately from pre-existing untracked output.
Next: owner reviews practice flow; preserve existing highlights and question content.

## Practice retry disclosure — 2026-09-28

Owner-requested follow-up to student Question Bank refinement. Shared templates
already apply the design to future published categories/questions; a regression
test now creates a new category and published question to verify this.
First incorrect submission withholds the answer key, correct-choice styling and
explanation server-side, while marking the student's wrong choice and offering
Try again. Correct submissions or the second saved submission for that revision
reveal the answer/explanation. Refreshes and duplicate request retries do not
advance the count. Old first-attempt URLs retain their original disclosure state.
No schema or live-data changes. Verification: `.venv\Scripts\python.exe scripts/verify.py
--pattern test_question_practice.py`: 13 passed (6.452s), including new-category
styling, first-error secrecy, repeat submissions and second-attempt disclosure.
Next: owner reviews the two-try flow. No owner acceptance assumed.

## Optional explanation expansion — 2026-09-28
Student practice explanations now start collapsed. Students choose whether to open
"Why this answer works" using the native keyboard-accessible disclosure. Existing
first-mistake disclosure rules remain unchanged; shared template applies to future
questions. Guarded practice suite: 13 passed (6.472s). No data/schema changes.

## Math preparation, first slice — 2026-09-28

Prepared existing multiple-choice authoring/practice for formatted math. Existing
Math taxonomy reused; no production questions or records created. Teacher editor
now documents inline \(...\) and display \[...\] notation and examples. Teacher
preview and student passage/stem/choices/explanation render locally using pinned
KaTeX 0.18.9 (official npm tarball integrity verified; license and provenance included).
No external browser service/CDN. Trust disabled, strict errors, bounded expansion
and size; no question content logged. Plain prices are not math delimiters.
Design includes Math category symbol. Existing answer disclosure and collapsed
explanation behavior retained. Text highlighting excludes math-containing regions
so its text-offset renderer cannot destroy generated equations; plain-text regions
remain highlightable. Numerical-input grading, diagrams and math PDF import are
not delivered in this slice.
References: https://katex.org/docs/autorender and https://katex.org/docs/security.
Evidence: guarded practice suite 13 passed (6.419s); guarded authoring suite 19
passed (6.946s). `node --test tests/test_question_math.cjs tests/test_practice_highlights.cjs`
passed 6. Isolated fictional student page rendered six formulas without errors;
desktop and 390px browser viewport inspected, no horizontal page overflow.
Real-device/screen-reader validation and owner acceptance remain pending.
Next: teacher tries creating a Math draft with the notation guide; typed numeric
responses and private diagrams can be separate bounded follow-ups.

## Question difficulty/result grid — 2026-09-29

Owner-requested student Question Bank organization delivered for review. Category
pages show numbered question tiles; question pages have a collapsed navigator for
the current 20-question block with a link to the full paginated theme. Existing
question previews remain in a disclosure. Difficulty: green easy, amber medium,
purple hard. Separate badges: green tick = first saved submission correct; amber
circle = correct after an earlier mistake; red cross = attempted, no correct
submission yet; no badge = unattempted. A later wrong retry does not erase an
earlier success. Results use only the signed-in student's displayed revision,
aggregated in one query per grid; no answer-key disclosure or schema changes.
Shared templates include future questions/categories, accessible link labels,
legends and current-question outline. Empty pages omit inverted range labels.
Evidence: guarded practice suite 15 passed (7.314s), covering first-try success,
wrong-to-correct transitions and personal results alongside prior auth/retry checks.
Fictional browser fixtures reviewed desktop and 390px mobile, all badge states,
no horizontal overflow. No real-device or owner acceptance claimed.
Next: owner reviews the grid in student practice. Deployment remains deferred.

## Assignments Stage 1 — 2026-09-29

Scope: owner-approved group assignment creation and student start/resume/complete.
Teacher dashboard links to Assignments; create title/instructions, group, optional
Asia/Tashkent deadline and 1–50 manually selected published multiple-choice questions.
Search by category/text and difficulty filter preserve hidden selections. Publication
revision checked under write lock to reject stale selection. Teacher listing shows
own assignments, target group and recipient count. Assignments and recipients are
snapshots; later enrollments do not automatically receive old work. No edit/delete
UI in this stage. Access requires recipient membership plus active course enrollment.

Student dashboard lists latest three assignments; dedicated page groups latest 100
into To do/In progress/Completed. Overview resumes first unanswered item, shows
saved results/difficulty, accepts late work. All questions answered = complete,
regardless of correctness. Dedicated attempt records keep Question Bank practice
separate. First wrong answer withholds answer/explanation; correct or second attempt
reveals them with explanation collapsed. Existing math rendering/highlighting used.
Assigned sealed revisions remain available even after question unpublication.
Stage 2 teacher per-student reporting and Stage 3 convenience remain future work.

QB schema v4 adds four tables with FK constraints, duplicate-request protection,
and immutable update/delete triggers. Versions 1–3 migrate additively; old rows
remain unchanged. Backup inspector now accepts v4 and recognizes older versions.
Rollback after real use: restore a verified v3 backup into a SEPARATE destination
with matching previous code; do not run old code against v4 or delete new history.

Evidence: `.venv\Scripts\python.exe scripts/verify.py` passed 231 tests (86.097s).
An initial run found outdated schema fixtures; corrected and final run passed.
After teacher listing refinement, `scripts/verify.py --pattern test_assignments.py`
passed 7 (4.963s). Includes separate grading, resume, completed-but-wrong, late
status, CSRF/access, saved recipients, unpublication, concurrent retry, immutability,
and backup/restore reconciliation. Migration tests cover repeatable v3 upgrade.
Isolated fictional browser previews: desktop and 390px student layout, keyboard
radio/checkbox controls, filter retains selections; no horizontal overflow.
No real-device or owner acceptance claimed. No live records read or migrated.

Activation PENDING: because the owner prohibits live database access, do not restart
the working app until backup/upgrade operation is authorized. Next concrete step:
run established SQLite-consistent backup into LOCALAPPDATA/SAT Factory/backups/
question-bank-release (no pruning), then guarded launcher restart to apply v4.
Previous baseline 4c9f93a; only assignment-related files staged, unrelated output
preserved. Screenshots and fictional fixtures are untracked under output/assignments-preview.


### Assignments Stage 1 activation — 2026-09-29

The owner authorized the pending local activation. This supersedes the activation
PENDING note above. Implementation checkpoint: e4eb9fa. Tracked working tree was
clean before activation; unrelated untracked output remains preserved.

SQLite-consistent backup completed successfully using scripts.backup.backup with
source attendance.db and destination LOCALAPPDATA/SAT Factory/backups/question-bank-release,
without pruning. Backup bundle:
`C:/Users/noral/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Local/SAT Factory/backups/question-bank-release/sat-backup-20260929T101633-cef8cb5de81d42c5b23e6009f77d72a6`.

`.venv\Scripts\python.exe scripts/open_sat_factory.py --no-browser` exited 0 and
restarted the local app, applying the additive migration. Read-only verification:
`SELECT version FROM qb_schema_versions ORDER BY version` returned 1,2,3,4;
all four assignment tables exist; `PRAGMA integrity_check` returned ok and
`PRAGMA foreign_key_check` returned no violations. Loopback GET / and /login
returned 200. Unauthenticated GET /teacher/assignments and /student/assignments
both returned 303 to /login. No account login or real assignment creation was
performed during verification. Security controls remain enabled.

No application code changed during activation, so the previously recorded 231-test
suite and 7-test focused follow-up were not repeated. Local activation is complete;
owner experience review and real-device validation remain pending. No remote push
or deployment performed. Next: owner creates a group assignment and reviews the
student start/resume experience; per-student teacher reporting remains Stage 2.


### Assignment category selection — 2026-09-29

Stage 1 follow-up: teacher can select/deselect a whole category, then adjust
individual questions. Category controls show partial selection and include filtered
questions explicitly; selection counts remain visible. All selected question IDs
use the existing snapshot/authorization route. The 50-question limit remains;
client validation explains excess selections without silently truncating categories.
Without JavaScript, individual question selection remains available. No schema change.
Verification: isolated `scripts/verify.py --pattern test_assignments.py`: 7 passed
(5.112s). Node VM interaction checks passed for category selection/deselection,
partial state, category isolation, hidden selections and validation focus recovery.
`git diff --check` passed. Owner/browser experience review pending. Refresh the
assignment creation page to load the updated template and versioned script.


## Assignments Stage 2 — teacher progress reporting, 2026-09-29

Implemented the planned bounded reporting stage. Assignment titles now link to an
owner-only teacher report: saved recipients, answered/total, To do/In progress/
Completed, first-try correct, correct after a mistake, not-yet-correct counts,
expandable per-question results, completion time, last activity and late status.
Completion remains answering every question, not achieving every correct answer.
Later retries do not change initial completion time or erase earlier success.
Regular Question Bank attempts remain excluded. Recipients stay visible after
enrollment changes. Shared summary logic keeps student/teacher semantics aligned;
queries fetch recipients and attempts in batches instead of querying per student.
No schema changes or new dependencies. No real records used in verification.

Verification: `.venv\Scripts\python.exe scripts/verify.py --pattern test_assignments.py`
passed 9 tests (6.536s), including reporting progression, inactive recipient history,
student/other-teacher/anonymous boundaries, invalid IDs, completion timing and retries.
`git diff --check` passed. Browser/real-device and owner acceptance remain pending.
Next: owner reviews the report; Stage 3 convenience features remain future scope.


## Assignment review and hardening — 2026-09-29

Follow-up to Stages 1/2, baseline 01139a9. Fixed canonical duplicate selections,
UTC date underflow, and retryable storage failures. Batched student list progress
into two queries instead of two per assignment. No schema changes. Review scope,
reproductions, verification and remaining work: docs/assignment-review.md.
Full isolated suite 235 passed; final focused assignment suite 12 passed; 14 Node
checks passed; pip compatibility check passed. Final transaction-error wrapper
was verified by the focused suite after the full run started. Live data untouched;
server not restarted during audit. No remote push. Owner/real-device review pending.
Next: submission rate limiting and realistic classroom load checks, then creation
form error recovery. Existing untracked artifacts preserved.


## Assignment creation recovery — 2026-10-03

Bounded Stage 3 workflow improvement from docs/assignment-review.md: creation
validation errors now re-render the form with title, instructions, group, deadline,
valid selections and submission key retained. Unavailable or changed revision
selections are removed with an explicit review warning, never silently replaced.
CSRF and teacher authorization remain enforced; persisted creation still rechecks
publication in the write transaction. Existing retry headers are preserved.
No schema/dependency changes. Isolated assignment suite: 13 passed. Regression
covers escaped input, saved values/selections, stale publication warning and no
partial write. Browser/owner review pending. Live records not used for tests.
Next: persisted submission throttling and classroom load testing remain pending;
this session deliberately completes only the form-recovery slice.

## Answer submission protection — 2026-10-03

Bounded follow-up to Assignment Stages 1/2 and the assignment security review.
New saved answers share a rolling budget of 30 per student per 60 seconds across
independent practice and assignments. Authentication, enrollment, CSRF, choice
validation and duplicate-key checks remain in place. Identical saved retries bypass
the budget; altered reuse of a key is still rejected. HTTP 429 explains that the
new answer was not saved, gives a waiting period, and includes Retry-After.

The budget is derived from existing immutable attempt timestamps within the same
SQLite BEGIN IMMEDIATE transaction as the write. It survives process restarts and
cannot be raced by simultaneous fresh keys. Failed/rolled-back writes do not consume
capacity. No schema change, dependency, IP restriction or cleanup job was added.
The existing student-leading indexes scope the queries, each returning at most 30
rows. Long-lived assignment history may warrant a dedicated student/time index
following measurement. This bounds saved history growth; it is not an edge-level
DoS defense and does not throttle invalid requests or identical saved retries.

Automated scenarios cover combined practice/assignment capacity, unchanged retry,
429 reporting, expiry, a fresh engine reading the persisted budget, a race for the
last slot, and 30 separately authenticated fictional students each submitting and
retrying through HTTP concurrently. The classroom check uses a local TestClient
and temporary SQLite, not real Wi-Fi, phones, a multi-worker server or production
capacity certification. Real-device and owner feedback remain pending.

Verification: isolated `scripts/verify.py` passed all 240 tests in 144.492s. The
30-student simulation completed 60 POSTs (including retries) in 1.497s, excluding
login setup, and persisted exactly 30 answers. `git diff --check` passed. Pending
runtime restart and owner/mobile review; no live-data test or remote deployment.

## Assignment answer recovery — 2026-10-04

Implemented the next Stage 3 reliability slice: invalid answers, temporary storage
failures and submission throttling re-render the assignment question with selected
answer and retry key preserved. Error receives keyboard focus; response status and
Retry-After remain correct. Authorization is rechecked; errors reveal no answers.
Stages 1/2 and prior hardening are reconciled in docs/question-bank-plan.md.
Evidence: 14 assignment tests, 3 limiter/classroom tests and 8 Node checks passed;
fictional static preview checked at 390px/1440px with keyboard radio navigation.
No schema changes, live-data access or deployment. Real-device/owner review pending.


## Homepage experience refinement — 2026-10-04

Owner requested a modern, vibrant, animated public homepage. Replaced the abstract
bar graphic with a linked student spotlight using existing featured result data,
layered lavender card backing and decorative orbit lines. Dark ink/lime hero,
colored result breakdown panels, compact teacher card and lavender portal panel
now share an intentional visual system. No portraits, invented results or added
libraries. Homepage-only stylesheet/body class prevents portal style changes.
New native animation script reveals each section once, cancels on keyboard focus
and reduced-motion changes; content remains available without JS. CSS hover states
respect reduced motion. Existing teacher biography/results unchanged.
Verification: browser inspection at 1440px and 390px, no mobile document overflow,
teacher anchor works, no browser errors observed. `node --test tests/test_home_motion.cjs`
2 passed; `node --check app/static/home-motion.js` and `git diff --check` passed.
Screenshot: output/home-experience-desktop.png. Live public assets updated without
server restart; no private records read or migrations performed. Owner review pending.


## Public experience continuation — 2026-10-04

Owner approved the new homepage direction and requested extension plus teacher
emphasis. Completed this slice: results library and login share ink/lime/lavender
styling and one-shot motion. Teacher section now uses a dark spotlight, larger name
and colored SAT/IELTS credential cards, without portrait or biography changes.
Login retains all form fields, CSRF, autocomplete, error associations and recovery
help. Styles scoped to public-experience/home-page; course dashboards unchanged.
Verification: isolated `scripts/verify.py --pattern test_auth.py`: 24 passed (12.414s);
`node --test tests/test_home_motion.cjs`: 2 passed. Browser desktop/mobile review,
390px login/results no horizontal document overflow, result story disclosure works.
Teacher screenshot: output/teacher-spotlight.png. Public assets updated without
restart; no private records used. Next visual slice: student/teacher dashboard and
assignment views using fictional previews. Owner acceptance of this slice pending.


## Dashboards and Question Library refresh — 2026-10-05

Completed the previously unfinished visual slice (baseline 5091f39). Shared scoped
portal-experience.css covers student/teacher dashboards and both role libraries.
Dark welcome panels, lime actions, lavender/mint accents, clearer category cards,
student practice/assignment shortcuts and direct check-in anchor. Existing forms,
CSRF fields, statuses, difficulty semantics and question-practice screens preserved.
Singular library question count corrected. No new dependencies or database changes.
Verification: guarded attendance suite 20 passed (4.496s), teacher suite 8 passed
(3.570s), final question-practice suite 15 passed. Fictional rendered previews:
desktop teacher/library and 390px teacher/student/library; student and teacher
pages and student library had no horizontal document overflow. Check-in anchor
confirmed at heading. No real-account or real-device acceptance claimed.
Screenshot: output/portal-style-preview/library-finished.png. Preview artifacts
remain untracked; unrelated output preserved. Runtime templates/styles require
page refresh, not a migration. Next scope: assignment visual refinement.


## Question reading surface refresh — 2026-10-05

Owner identified question pages as missing from the dashboard/library refresh.
Completed shared question-experience.css, scoped to regular and assignment
question templates: compact ink heading, lavender highlighting tools and selected
choices, lime submission/navigation, white passage/answer reading panels and a
brief reduced-motion-aware heading entrance. Existing difficulty/result semantics,
CSRF/forms, first-wrong answer concealment and collapsed explanations preserved.
No new dependency or data changes. Applies to future questions through templates.
Verification: `.venv\Scripts\python.exe scripts/verify.py --pattern test_question_practice.py`
15 passed (10.941s); same runner with `--pattern test_assignments.py` 14 passed
(15.046s). Fictional static previews inspected; 390px regular/assignment layouts
had no document overflow. Keyboard radio selection and visible focus confirmed.
Preview screenshot: output/question-style-preview/finished.png (fictional data).
Baseline 11f9924; only this slice committed, unrelated output preserved. No live
records accessed, no push/deploy. Owner/real-device acceptance pending.
Next: assignment list, creation and report visual refinement.


## Step 2 — Assignment visual refinement — 2026-10-05

Delivered the owner-selected visual continuation from aafb307: student task list
and overview, teacher list, creation and progress report. Shared scoped stylesheet
uses ink headers, lime actions, lavender selection/status accents and white panels.
Native labelled progress bars represent answered questions, not accuracy. Reports
show first-try/retried/incorrect separately; student deadlines distinguish Overdue
from Completed late. Creation groups details and question selection, retaining all
form names, CSRF, saved values, category selection and filter behavior. Empty lists
provide next-step guidance. No dependencies, database or backend changes.
Reference: https://design-system.service.gov.uk/components/task-list/ (explicit task
statuses and grouping); applied within the existing SAT Factory visual language.
Verification: `.venv\Scripts\python.exe scripts/verify.py --pattern test_assignments.py`
14 passed (17.919s), `git diff --check` passed. Initial report assertions were coupled
to uninterrupted HTML text; updated them to check rendered words across number
markup, and updated the late-label expectation. Fictional browser previews covered
all five screens; 390px teacher list/create/report and student overview had no
horizontal overflow. Category keyboard selection survives a filter hiding every
question; report disclosure expands. Textarea width corrected during visual review.
Preview: output/assignment-style-preview/report.png. Static previews do not prove
real-device or owner acceptance. No live records read, no push/deployment.
Only this visual slice committed; unrelated untracked outputs preserved.
Next proposed step: student progress visibility using existing records, keeping
assignment results separate from independent practice. Owner review remains pending.

## Student dashboard goals — 2026-10-05

Owner requested a dashboard structured like the supplied reference, with editable
Target score, Exam date and Exam countdown. Implemented a calm two-column welcome
and goal area, white goal panel, lime study action, existing colored shortcuts and
separate assignment/check-in panels. Mobile stacks these panels. No invented
analytics, score forecasts, study-plan engine or additional dependencies.

Each student can set/edit/clear either field. Target score is 400–1600 in steps of
10 (College Board score scale); date is a calendar date chosen by the student, not
an official test-date picker/registration. Countdown recalculates on dashboard
requests using Asia/Tashkent calendar dates. Empty, future, today and past states
have explicit messages. No ticking timer or recurring job. Other students and
teachers cannot change the goal via this route. CSRF, server validation, session
reauthorization within the transaction and a version field prevent unauthorized
writes and stale-tab overwrites. Values survive validation errors.

Schema: additive student_goals table (student PK/FK, nullable target_score/date,
version). Existing initializer creates it idempotently. Backup inspector supports
both pre-goal and current schemas and validates/reconciles new goals. Upgrade and
rollback guidance is in docs/backup-recovery.md. No working DB migration/restart
performed during development; all simulation data is fictional and isolated.

Design/requirements references: owner screenshot; existing portal-experience
palette and native disclosure/forms; College Board score definition:
https://satsuite.collegeboard.org/scores/what-scores-mean
https://research.collegeboard.org/media/pdf/sat-suite-assessments-technical-manual.pdf
Browser static previews at 390px and 1440px: no horizontal overflow; keyboard
opens editor; labelled target/date fields and empty state verified. Preview:
output/student-goal-preview/dashboard.png. HTTP tests verify actual saves; static
browser preview does not constitute real-phone acceptance.

Verification: final isolated full suite 246 passed (97.871s), including five goal
scenarios. Two old expectations (welcome copy and schema table list) were updated
before the passing run. `git diff --check` passed. Local commit only; backed-up
server activation and owner review remain pending.

## Homepage spotlight selection — 2026-10-05

Delivered owner-requested manual switching among 1470/1420/1380 score tickets,
preserving the existing hero design and full-result links. Native buttons with
pressed state, keyboard activation and screen-reader feedback; no auto-rotation.
Isolated homepage rendering, `node --check app/static/spotlight.js`, browser switching
and 390px overflow checks passed. Handover records limits and preview. No deployment,
remote push or DB changes; application restart needed for new context.

### Target score simplification — 2026-10-05

Owner supersedes earlier exam-date/countdown scope: only a compact target score
card remains, with a collapsed score editor. Date UI/calculation and date writes
removed; existing storage preserved for compatibility. Five focused goal tests
passed, including privacy/stale changes/backup and ignored legacy date input.
Desktop/mobile keyboard review passed. See latest handover for evidence.

## Workflow and portfolio README — 2026-10-06

Owner requested a portfolio-ready repository and an authorized GitHub push.
Current README now presents course operations, Question Bank, assignments, personal
target, architecture tradeoffs, reproducible fictional demo and delivery limits.
Added CONTRIBUTING.md and one fail-fast scripts/check.py command combining guarded
Python, Node, dependency compatibility and whitespace checks. Generated local
output/logs ignored; reviewed fictional dashboard screenshot deliberately included.
No application behavior or deployment changes. Evidence in latest pilot handover.

## SF-13 portfolio sandbox slice — 2026-10-06

Owner postponed the course launch and approved local preparation for a free demo.
Implemented a separate resettable fictional sandbox with visible credentials,
questions, assignment and attendance history, protecting shared account access.
Acceptance evidence: 3 demo and 24 auth tests passed; narrow-screen browser and
keyboard login checked. See portfolio-demo.md and latest handover. Public hosting,
abuse/resource limits and simultaneous-visitor experience are the next slice;
no public deployment or real-course readiness is claimed.

### SF-13 free-host preparation — 2026-10-06

Prepared free Render Blueprint and opt-in hosting launcher with production security,
health check, explicit public-demo write allowlist and shared resource limits.
Nine focused tests passed; see portfolio-demo.md for setup, costs/limits and the
publication checklist. No public deployment, Linux build or owner acceptance yet.
Public course launch remains postponed; this slice is fictional portfolio use only.
