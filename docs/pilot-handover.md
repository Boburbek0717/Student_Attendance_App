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

## Public design slice 1 delivered — 2026-09-26

Starting HEAD 555d739; no pre-existing tracked edits. Shared public header, scoped
foundation tokens, homepage hierarchy and compact portal entry implemented.
Existing public scores/comments/teacher biography preserved. No new dependencies.
Keyboard review repaired off-screen card focus. See design-refinement.md for
responsive/contrast checks and isolated auth test command (24 passed, 7.030s).
Static preview script in output/design-preview.py imports only Jinja/public data;
unrelated output artifacts preserved. No live DB, remote push or deployment.
Ready for owner visual review; next: Results/Login refinement, then SF-10.

## Results/Login design checkpoint — 2026-09-27

Finished the interrupted Results/Login refinement; see design-refinement.md for
scope and evidence (24 auth + 2 onboarding tests, responsive/keyboard/text checks).
No backend changes. Prior completed commits through 8d4f0e0 pushed to origin/master
at owner's explicit request. Local scratch previews and unrelated output preserved.
Next implementation: bounded SF-10 teacher-dashboard hierarchy. Do not treat SF-10,
SF-17 or owner design acceptance as completed by the public-page changes.

## SF-10 dashboard hierarchy slice — 2026-09-27

Classes and recent lesson actions now precede setup forms. Rosters collapse per
group; setup opens on empty state or rejected input with an error navigation link.
Eight isolated teacher tests passed (2.841s); fictional 30-student responsive and
keyboard checks recorded in design-refinement.md. No backend changes. SF-10 remains
In progress: group search/pagination/scale checks are not delivered by this slice.
Next bounded action: group discovery, then lesson-roster design. Unrelated output
files remain local; no live database or real accounts used.

## Question Bank foundation checkpoint — 2026-09-27

Scope switched by owner from SF-10 to the Question Bank brief. Starting HEAD
c741fb5 on master; tracked tree initially clean, unrelated output artifacts retained.
Owner chose access for any active course enrollment and supplied a split-pane
question layout reference. See [question-bank-plan.md](question-bank-plan.md) for
the audit, entities, route plan, accepted layout, phases and operational cautions.

QB-01 delivered: normalized schema, seeded SAT taxonomy, sealed question revisions,
immutable attempts, retry-key uniqueness, additive transactional version-1 migration,
empty-only rollback, legacy/new backup compatibility and recovery verification.
The startup migration has only been exercised on fictional temporary databases.
No live server restart, secret read, working DB connection, remote push or deployment.

Exact verification:
- `.\.venv\Scripts\python.exe scripts/verify.py --pattern test_question_bank_schema.py`:
  10 passed, 5.266s.
- `.\.venv\Scripts\python.exe scripts/verify.py`: final 169 passed, 52.136s.
  Initial full run exposed two stale expectations: teacher-dashboard copy from
  before c741fb5 and pre-feature table inventory. Updated to teacher navigation/
  HTTP success and explicit current tables; database fixtures now run initialization.
- `node --test tests/test_lesson_live.cjs`: 5 passed (simulated attendance polling).
- `git diff --check`: passed. Only related source/tests/docs staged for this checkpoint;
  existing output files remain untracked and unchanged. Identify the resulting
  commit by subject `Add versioned Question Bank foundation and recovery checks`.

No authoring/student routes or Question Bank UI exist yet. No browser, real-device,
owner acceptance or new OpenClaw review claimed. No new dependencies. Remaining
work is explicit in QB-02 onward, not a production-ready Question Bank claim.
Next bounded action: QB-02 teacher create/edit/preview and publish lifecycle with
safe revision creation, validation, audit and authorization tests. Then implement
QB-03 answering using the owner's reference layout and active-enrollment policy.

## Draft authoring checkpoint — 2026-09-27

Starting HEAD 16e49f0. Delivered QB-02 first slice: teacher draft creation/editing,
20-row library, preview with source/answer key and historical revisions. Publication
and student practice remain unfinished. No schema/dependency change. Full isolated
command `.\.venv\Scripts\python.exe scripts/verify.py`: 179 passed, 58.240s.
Temporary fictional static preview checked desktop split and mobile stacking,
labels and keyboard focus, then stopped. See question-bank-plan.md for limits.
Unrelated output preserved. Commit subject: `Add teacher question draft authoring and preview`.
Owner steered ongoing work to testing the supplied PDF; next is a bounded extraction
and isolated draft-import rehearsal, retaining PSAT 8/9 provenance and punctuation.

## PDF rehearsal checkpoint — 2026-09-27

Draft-authoring commit ee955df completed. Owner-selected supplied PDF test now
extracts 30 candidates and imports/reconciles all 30 through the teacher routes in
a disposable database, including backup/recovery. See pdf-import-rehearsal.md for
exact evidence/commands and limitations. Four PDF tests and ten authoring tests
passed after the import slice. No app dependency added; bundled pypdf used.
Original PDF, working data and unrelated output preserved. Review artifacts under
output/pdf-import-test remain local and excluded from the commit. A loopback-only
static review server is available on port 8768 for owner inspection; it serves only
output/pdf-import-test/review-1, not the repo or a database. Stop it when no longer
needed. No public deployment, actual database import, push or owner acceptance.
Commit subject: `Test bounded PDF question extraction and isolated draft import`.
Next: inspect owner feedback, then implement staged import review and the audited
publication lifecycle in bounded slices before student answering. Do not present
this one-profile development rehearsal as the completed PDF import system.

## Publication preparation — 2026-09-27

Owner requested interactivity (local preview committed d7d504c), then explicitly
authorized official publication after checks, naming Teacher as the actor. Built
server-side student practice and audited publication, with v2 migration and
legacy/v1/v2 backup support. See question-publication-release.md for scope, exact
verification and limitations. Full 191 tests passed; later focused seven practice
tests and eight Node tests passed. Disposable operator rehearsal published 30,
repeat added zero, restored records matched. No production operation claimed yet.
Next concrete action: checkpoint code, then run the explicitly authorized importer
with a pre-upgrade backup under LOCALAPPDATA/SAT Factory/backups/question-bank-release,
restart the matching local server and verify anonymous access remains protected.

## Official batch published — 2026-09-27

Owner-authorized publication completed under Teacher: 30 PSAT 8/9 Boundaries
questions, schema v2, immutable publication events. Backup and smoke evidence in
question-publication-release.md. Server on port 8000 restarted; anonymous routes
redirect to login; owner browser verified 20+10 published rows and one exact preview.
Post-publication small UI fixes: distinguish library entries by passage; revisiting
a student question restores their latest result; new attempts remain explicit.
Focused authoring 10 and practice 7 tests passed after these fixes. No real student
practice submissions were made. No remote push. Unrelated outputs remain untouched.
Next: owner tries the official teacher/student experience; address observed defects,
then add saved-question/history directories and staged PDF import UI in bounded steps.


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


## Homepage visual refresh — 2026-10-03

Owner requested more energy. Homepage-only home.css adds deep-green hero, lime
headline/action, decorative geometric steps, numbered score tickets and restrained
hover feedback. Existing public results and teacher content preserved; no libraries,
data or backend changes. Reference: Linear interface hierarchy design article.
Browser reviewed at 1440px and 390px; mobile document has no horizontal overflow.
Reduced-motion CSS disables card movement. Public homepage served updated assets
without server restart. Screenshot: output/home-refresh.png. Owner review pending.


## Text Structure and Purpose PDF import — 2026-10-03

Owner requested this supplied PDF be added to the question bank. Published 35
questions under Teacher in PSAT/NMSQT & PSAT 10 / Reading and Writing /
Craft and Structure / Text Structure and Purpose. 37 PDF pages: pages 11 and 28
continue preceding answers. All A–D options, difficulty, answers and complete
rationales retained. Twelve underlined references visually checked against rendered
PDF pages; prompts say quoted instead and include the exact referenced text to
preserve meaning in the plain-text question renderer. No unsafe HTML added.
Source SHA256: 96206f8c97dfcf0620ad0009e71764f8da16a552b965075e30a2b1ff9b4e09d3.
Candidates and rendered evidence: output/text-structure/ (local, untracked).
One rationale has 2808 characters; bounded explanation validation raised from
2000 to 4000 (existing Text storage; no schema change). Generic upload parser
remains restricted to its existing profiles; this was an operator-reviewed batch.

Rehearsal: temporary fictional DB publication of 35, exact fields/options/answer
keys reconciled, repeat import created zero and recognized 35 existing questions.
Authoring suite: 19 passed, 10.745s. Authorized local publication: 35 created,
0 previously present. Read-only verification of these 35 published records and
category passed; no private student/account information exposed.
Pre-publication consistent backup bundle:
sat-backup-20261003T121141-326caa4f00e34967bcf302bcbe0fb0d4
under LOCALAPPDATA/SAT Factory/backups/question-bank-release.
Questions are available on refresh; updated explanation edit limit needs server
restart. No remote push. Owner practice review remains pending.

## Answer submission protection — 2026-10-03

Scope: the persisted submission throttling and classroom simulation left pending
by Assignment Stages 1/2 and creation recovery. Baseline b649fff, tracked tree clean;
all pre-existing untracked output artifacts preserved. Deployment remains deferred.

Implemented one shared 30-new-answers/60-second/student budget for assignments and
practice. Existing immutable attempts provide persisted state; checks run under
the same immediate write transaction after authorization, validation and duplicate
recognition. Identical saved retries succeed at capacity. Excess new answers return
429 with Retry-After and an actionable message; history remains unchanged. No schema
or dependency change; live records/secrets not accessed, no server restart or push.

Acceptance: reject excess new history across both routes, preserve retries, survive
new engine/process state, serialize the last available slot, and keep different
students independent. TestClient simulation covers 30 fictional student sessions
and 60 concurrent answer/retry POSTs. This does not establish real-device or Wi-Fi
behavior, sustained production capacity, or owner acceptance. No OpenClaw review
was performed for this slice; automated evidence is identified separately.

Limits: the limiter bounds successful answer history, not every incoming request.
Assignment queries use existing student-leading indexes; measure long-term history
before adding an additional time index. No classroom bandwidth simulation or
proxy-level abuse protection was attempted.

Next concrete action: review assignment/practice recovery UX on mobile and keyboard,
including the temporary 429 wait and slow/lost-response experience, using fictional
data. Arrange owner/real-phone review separately; do not infer acceptance.

Verification for this increment:
- `.venv\Scripts\python.exe scripts/verify.py`: 240 passed, 144.492s.
- Final classroom scenario: 30 students / 60 answer-and-retry POSTs in 1.497s;
  exactly 30 assignment attempts persisted. Timing excludes account/login setup.
- Initial focused run: `.venv\Scripts\python.exe scripts/verify.py --pattern test_submission_limits.py`
  passed 16 checks in 24.883s (13 assignment checks were also discovered through a
  class import). The import was corrected before the full run to avoid duplicate
  discovery; the final full run includes the three new checks once each.
- `git diff --check`: passed. No JavaScript changed; Node checks not rerun.
- Changes are saved in the accompanying local commit. Runtime activation requires
  the next authorized local server restart; no deployment or remote push performed.

## Assignment recovery checkpoint — 2026-10-04

Baseline 2e704c3; tracked tree clean, unrelated untracked artifacts preserved.
Scope: Assignments Stage 3 answer recovery, following the latest handover next step.
400/429/503 recoverable answer failures now keep the question, valid selected option
and retry key on screen. Access rechecked after rollback; CSRF and conflicting keys
remain fail-closed. Focus goes to the error; no new answer disclosure or schema.
Exact commands, outcomes and preview limits: docs/question-bank-plan.md final entry.
14 assignment + 3 limiter tests passed; 8 Node checks passed. Thirty students each
submitted and retried: 30 records, 60 requests, 1.418s excluding login setup.
Browser static 390/1440px checks passed for layout/focus/radio keyboard behavior.
No full-suite repeat, OpenClaw review, live-data access, server restart, push or owner
acceptance claimed. Local commit records this slice; new preview artifacts untracked.
Next: isolated browser interrupted-response flow, then owner teacher-report review;
actual Wi-Fi/device testing remains outstanding. No general assignment edit/delete
or changes to immutable recipients/deadlines were introduced.


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

## Student dashboard + personal goal — 2026-10-05

Baseline 2fe9bf0, tracked working tree clean; existing unrelated output preserved.
Scope: owner screenshot adaptation plus persistent target score, exam date and
Tashkent calendar-day countdown. Goal editing is student-only, CSRF protected,
re-authorized inside serialized writes, and versioned against concurrent/stale tabs.
Includes empty/today/past states and optional field clearing. No predictive analytics.
Additive student_goals table; old/new backup schemas supported and goal fingerprints
reconcile on restore. Existing homepage, attendance and assignment semantics retained.
Read docs/product-backlog.md latest entry and docs/backup-recovery.md upgrade note.
Static fictional previews at 390/1440px passed overflow and keyboard checks;
output/student-goal-preview/dashboard.png. Live database/secrets not read; no live
migration, restart, deployment or remote push. Owner/real-device review pending.
Next: authorized backed-up local activation, then owner reviews student goal flow.

Final verification: `.venv\Scripts\python.exe scripts/verify.py` — 246 passed in
97.871s, including five new goal scenarios and existing attendance, assignment,
authentication, migration and backup tests. First full run exposed two expected
fixture updates (welcome copy/table list); fixed and final full suite passed.
Goal tests cover save/edit/clear, validation/CSRF/roles, privacy, simultaneous/stale
updates, Tashkent midnight/today/past, legacy table creation and backup/restore.
`git diff --check` passed. No new JavaScript; no extra Node rerun. Test evidence:
output/student-goal-preview/verification.txt. Activation and owner review pending.

## Switchable homepage spotlight — 2026-10-05

Owner requested equal spotlight treatment for 1470, 1420 and 1380 while preserving
the existing single-ticket design. Added manual score selector buttons for
Allonazarov Javohir (680+790), Go'zal Anvarova (660+760) and Nurmuhammadov
Bekmuhammad (650+730). All content remains server-rendered and links to the matching
full result. Existing featured row remains unchanged. No auto-rotation/dependency.
Buttons support native keyboard activation, pressed state and a polite screen-reader
announcement. Nonselected cards are hidden from navigation. Without JS, first card
and full results link remain available. Checked isolated homepage render, JS syntax,
browser click/Enter switching, visible card count and score breakdowns, and 390px
layout without overflow. Corrected an initially visible screen-reader announcement
during review. Static screenshot: output/spotlight-switch-preview/desktop.png.
No DB/secret access or server restart. New render context requires application
reload/restart; owner acceptance pending. No full-suite rerun for this UI-only change.

### Spotlight control simplification — 2026-10-05

Owner requested a single arrow instead of three score choices. Replaced selectors
with a 48px circular Next student result button. Cycles 1470 → 1420 → 1380 → 1470;
retains native keyboard activation and polite announcement, without auto-rotation.
JS syntax, Node VM cycle/wrap/one-visible-card check and git diff --check passed.
No backend/database change or fresh browser review for this small adjustment.

## Compact target score — 2026-10-05

Owner removed the exam date/countdown feature. Dashboard now shows a compact
22rem-max target card with score and native Edit/Set target disclosure, collapsed
by default even when unset; errors expand it. Date inputs, countdown display and
calculation removed, and goal POST no longer accepts date changes. Existing nullable
exam_date column/values retained solely for backward schema/backup compatibility;
no destructive migration. Personal target validation, CSRF, privacy, atomic writes
and stale-tab guard retained. README reflects current behavior.
Verification: isolated `scripts/verify.py --pattern test_student_goals.py`: five
passed (2.224s), including ignored date submissions and hidden legacy dates.
Desktop/390px fictional previews and native keyboard disclosure checked; no overflow.
Screenshot: output/compact-target-preview/desktop.png. `git diff --check` passed.
No live DB access, restart, remote push or full-suite repeat. Runtime reload needed.

## Portfolio documentation and pre-push workflow — 2026-10-06

Owner authorized README/workflow optimization and pushing all completed project
work to the connected GitHub repository. Baseline c78962b; tracked tree clean with
40 commits ahead after fetching origin (no divergence). Rewrote the README around
current features, architecture decisions, fictional demo setup, verification,
operations and honest pilot/scale limitations. Includes a reviewed screenshot of
fictional test data, copied intentionally to docs/images/student-dashboard.png.
CONTRIBUTING.md defines bounded changes and explicit staging/review.

Added scripts/check.py: the current interpreter runs the guarded Python suite,
then explicitly discovered Node test files, pip compatibility and both whitespace
checks; fail-fast and missing tools fail visibly. No installations, app startup,
data access, commit or push are performed by this helper. Added output/ and logs
to .gitignore while preserving tracked branding references and all local files.
Generated PDFs/import previews and unrelated local artifacts are not published.

README local file links resolved. Filename-only all-ref history audit found no
.env/session-secret/database/log paths; this is not an exhaustive secret scan.
No live databases, credentials or backup contents read. No deployment or restart.

Verification: `.venv\Scripts\python.exe scripts/check.py` passed: 246 isolated
Python tests in 149.054s; 18 Node checks; pip dependency compatibility; staged and
unstaged whitespace checks. Local log: output/check-2026-10-06.txt (ignored).
These are automated checks, not owner acceptance, real-device testing or deployment.
Next action: commit this documentation/workflow checkpoint and push master normally,
then confirm the remote branch matches the local commit. External pilot/release
choices remain separate from this repository publication.

## SF-13 portfolio demo preparation — 2026-10-06

Owner postponed the real course and selected a free portfolio demonstration.
Baseline 0a0a718, clean tree. Added scripts/portfolio_demo.py: loopback-only disposable
sandbox with guarded imports, separate cookie/secret/database, six fictional
students, completed lesson/history, three original questions published through the
publication service, and a recipient-snapshotted assignment. Demo-only access guards
block profile/password/enrollment-status changes. Normal startup is unaffected.
Banner and public fictional login guidance added; README links portfolio-demo.md.

Verification: `.venv\Scripts\python.exe scripts/verify.py --pattern test_portfolio_demo.py`
3 passed (1.578s); `--pattern test_auth.py` 24 passed (12.309s); git diff --check passed.
Browser keyboard login and 396px layout inspected; content width 381px, no horizontal
overflow. Preview output/portfolio-demo/student.png is ignored. No real-device test.
Local review server started at 127.0.0.1:8767 (process 6172); it remains available
for owner review. Its initial history timestamps predate the final fixture alignment;
restart the launcher to load the final seed. Normal port 8000 and live data untouched.
No public deployment, external resources, schedules or remote push in this chunk.

Next bounded task: free-host entry point and configuration with HTTPS, host/proxy
validation, health checks and resource/abuse controls. Shared visitor state, login
throttling, uploads and content edits require public-demo review before exposure.
Local demo preparation is implemented; SF-13 public release remains incomplete.

## SF-13 free-host preparation — 2026-10-06

Baseline 46f3629, clean tree. Added an opt-in Render-only demo launcher and free
Blueprint with automatic deploys disabled. Public-mode cookies/HTTPS/host checks,
DB health probe, no-index robots, bounded global traffic/write counters and mutation
allowlist added. Shared lesson/practice/renewal remain interactive; uploads and
content/account creation are denied before body buffering. One worker and concurrency
limit 20. No production records accessed, no resources provisioned, no remote push.
Normal/local demo defaults unchanged; existing local preview was not restarted.

Commands and evidence:
- `.venv\Scripts\python.exe scripts/verify.py --pattern test_demo_host.py`: 3 passed,
  0.545s (config denial, secure cookies, health/host, roles, upload/content blocks,
  minute-window/lifetime limits and recovery).
- Same runner `--pattern test_portfolio_demo.py`: 3 passed, 1.537s.
- Same runner `--pattern test_production_security.py`: 3 passed, 1.065s.
- `git diff --check`: passed.
Provider docs checked for free-plan lifecycle, Python pinning, Blueprint and proxy
defaults. Full suite not repeated for this isolated demo slice. No new browser or
real-device review; login copy adds public-demo limits. No owner acceptance claimed.

Next: owner-authorized publication, push reviewed commits and run Render build/HTTPS
smoke checks including restart/session reset. Linux wheel availability and actual
health-proxy behavior are unverified. Shared-state/rate-limit interference is an
explicit demo limitation, not suitable for real course operation.


## Public guest Question Library — 2026-10-06

Owner authorized opening published practice to everyone. Baseline 32b5d2e; clean
working tree at start. Added separate /questions routes, shared page rendering,
homepage Free practice link, guest browser progress/bookmarks and explicit teacher
public-publication label. No course data writes or migrations. Enrolled student
visits redirect to existing saved practice; protected assignment/attendance paths
retain original access checks. Guest checking uses CSRF, revision/choice validation,
bounded signed-cookie recent checks and per-process/IP request limits. First wrong
answer does not disclose key/explanation; repeated identical submission does not
advance disclosure. Demo allowlist admits only public answer POST additionally.

Verification (guarded fictional engines/secrets):
- scripts/verify.py --pattern test_public_practice.py: 5 passed, 6.802s.
- scripts/verify.py --pattern test_question_practice.py: 15 passed, 26.667s.
- scripts/verify.py --pattern test_assignments.py: 14 passed, 33.841s.
- scripts/verify.py --pattern test_demo_host.py: 3 passed, final 1.581s.
All commands use .venv/Scripts/python.exe.
- node --test tests/test_guest_practice.cjs: 4 passed; node --check guest script passed.
- Browser fictional demo on isolated port 8772: homepage link, category/question,
  bookmark retained across answer navigation, first wrong hidden key, correct retry,
  collapsed explanation, persistent yellow grid badge. 390px homepage/library had
  no overflow. No real account data accessed. git diff --check passed.

Limits: guest progress is self-study/browser-local, no account merge; last-six
cookie check state can reset/evict and concurrent tabs are not durable records.
Per-process throttles need host proxy/scaling review before course deployment.
Redistribution permissions for actual imported PDFs were not verified. No live
server restart, remote push or public deployment. Normal server needs restart to
load routes. Fictional review server stopped after checks. Owner acceptance pending.
Next: owner review of guest experience; public content rights review before launch.


## Zero-token PDF workflow clarification — 2026-10-07

Owner requested repeatable PDF extraction/publication with minimal token use.
Inspection confirmed the teacher uploader already performs local deterministic
extraction, review, duplicate checks and transactional publication. Avoided building
a second importer. Offline extraction CLI now defaults to the same per-page auto
profile detection; explicit profiles remain supported. Teacher upload/review copy
clarifies zero AI use, source-provided difficulty/answers and public publication.
Added docs/pdf-question-workflow.md with everyday steps, offline command, limits
and future format-extension path. No PDF supplied or published in this turn.
Verification: guarded test_sqb_pdf_extract.py 5 passed (2.897s),
test_question_import.py 9 passed (14.089s), CLI --help and git diff --check passed.
No live database/credentials accessed, deployment or remote push. Scope remains
Boundaries/Transitions SQB layouts; OCR/general PDF or diagram parsing is not added.
Next for broader support: inspect one representative new layout and add a tested
profile; do not infer missing difficulty or automatically publish uncertain pages.


## Automatic PDF format recognition expansion — 2026-10-07

Baseline d9e188d. Owner requested automatic new-format recognition without manual
profiles. Added scripts/flexible_pdf.py fallback after the existing exact profiles:
SQB metadata across new skills/assessments, numbered worksheets with variant A-D
labels, multiple questions per page, inline answers or separate numbered key pages,
explicit page/question taxonomy/difficulty, optional explanations and labelled
passage/prompt. Two-pass extraction matches keys and rejects unmatched/duplicate
numbers, conflicting answers, missing labels, extra choices and unknown images.
Categories are validated and automatically created or reused by exact hierarchy
names. Duplicate comparison now includes section. No AI calls or dependencies.

Evidence: guarded test_flexible_pdf.py 8 passed (1.391s), including an actual generated
two-page PDF through the subprocess parser; test_sqb_pdf_extract.py 5 passed
(2.085s); test_question_import.py 10 passed after category reuse change (14.210s),
including new Math category publication and repeat import skipping. Commands:
.venv/Scripts/python.exe scripts/verify.py --pattern <filename>. git diff --check passed.
All data fictional; no provided PDFs, live database, real publications, remote push
or deployment. Updated upload/review guidance and docs/pdf-question-workflow.md.

Limits: this does not identify every arbitrary format. Scans/OCR, complex diagrams,
ambiguous reading order and cross-page question continuations remain unsupported.
Unlabelled metadata/difficulty is not guessed. Review remains mandatory before
publication; a flagged page blocks the batch. Next: evaluate representative owner
PDFs against the new recognizer before claiming broad real-document coverage.
