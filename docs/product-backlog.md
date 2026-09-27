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
