# SAT Factory — Course attendance app

Future development follows the [Scrum working agreement](docs/scrum-working-agreement.md).
See the [ordered backlog](docs/product-backlog.md), [usage simulation](docs/usage-simulation.md)
and [active Sprint 1](docs/sprint-01-proposal.md) and [implementation evidence](docs/sprint-01-review.md).

The portal uses SAT Factory branding, a workshop-inspired graphite, paper and lime theme, responsive
layouts, and keyboard-visible focus styles. All styling and the SF mark are local;
no external fonts or image services are required.

The teacher page supports creating groups, creating student accounts, enrolling
students with a 12-lesson package, starting group lessons, and viewing balances
and attendance history. Students can check in with a temporary code. Teachers can
manually renew packages, including early and late renewals; no payments are taken
in the app. Available, advance and owed lesson counters are calculated from records.
Teachers can also search students, edit profiles, reset passwords and deactivate
or reactivate group enrollments from **Manage students**.
Each group now has **Manage lessons** for lesson history, attendance lists, and
closing or reopening check-in for the same class.

## Run

Use Python 3.14. From this project folder, install packages on a new checkout:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

If you need a teacher account, create one with a hidden password prompt:

```powershell
.\.venv\Scripts\python.exe -m app.create_user teacher --name "Teacher" --role teacher
```

Start the local server:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --no-proxy-headers
```

Open http://127.0.0.1:8000/ for the welcome page, or /login for the course portal.
The welcome page uses the selected Score Ticket design for three owner-supplied
student stories: Asilbek Shukurov (1300), Axadjon Axmadqulov (1350), and
Shoxjaxon Akramov (1210), with section scores and lightly edited comments.
Starting from scratch is descriptive, not a numeric baseline score. No faces
are displayed. Content is static; results-management tools remain future work. The brand header
and login page link back to it. Signed-in users can open their dashboard from home. Stop an older server if the port is occupied.
The proxy flag makes local login limiting use the connection address rather than
forwarded headers. Existing accounts are preserved. No default accounts are added.
Sprint 1 adds two tables on startup without changing existing columns or dependencies.
See the sprint review for upgrade and recovery notes.

## Teacher workflow

1. Create a group, such as SAT Advanced.
2. Create a student account; passwords require 12–128 characters. Share the account
   details privately yourself. The form can only create student accounts.
3. Select the student and group, then enroll with 12 lessons.
4. The roster displays `0 / 12 lessons used` and `12 remaining`.
5. Try the same enrollment again: an error appears and no extra package is added.
6. Click **Start a new lesson** on the group's card. Share its six-digit code with
   the group. It lasts 15 minutes by default; starting again while it is open reuses
   the same lesson. After expiry, the button starts a new class, not an extension
   of the old one. To give students more time for the same class, open that lesson
   from **Manage lessons** and use **Reopen check-in for this lesson** instead.
7. Log in as the student in a separate browser/private window, or log out of the
   teacher account first. Enter the code on the student page and click **Check in**.
8. The student sees `1 / 12 lessons used`, `11 remaining`, and a history entry.
   Refresh the teacher page to see the updated balance. Its **Attendance history**
   link opens the individual student's history.
9. Click **Renew package** beside a student in the group roster or on their history
   page. Review the current balance and the preview, then confirm **add 12 lessons**.
   This records the teacher's manual renewal; there is no checkout or payment form.

An early renewal preserves unused credit: 4 remaining + 12 = 16 available, with 12
saved in the later package. Late students can still check in after credit runs out.
Their extra attendance increases **Lessons owed**: 2 owed + a 12-lesson renewal =
10 available and 0 owed. Counters are separate for each group and visible to both
teacher and student. See [renewals and counters](docs/packages.md) for the examples.

Repeat the check-in: it must show an error without using another lesson. Codes are
sent through POST forms, never URLs. Displayed dates use Asia/Tashkent (UTC+05:00); stored timestamps remain UTC.
See [the attendance lesson](docs/attendance.md) for the flow, configuration and
concurrency explanation.

Group names may repeat; IDs distinguish them. Usernames are unique and lowercased.
Inactive enrollments cannot be re-created or renewed. Use **Manage students** to
reactivate the existing enrollment without adding a package. All teachers
administer the same business.

## Student management

Choose **Manage students** on the teacher page, search by name or username, and
open a student's management page. This also lists students without a group.

- **Save details** updates name and username; it keeps the same account ID and history.
- **Reset password** requires two matching entries of 12–128 characters and signs
  out that student's existing sessions. Share the new password privately yourself.
- **Deactivate enrollment** blocks check-in and renewal for that group, while
  keeping available/owed lessons and history. The student can still log in.
- **Reactivate enrollment** restores the same membership and balance; it creates
  no new package. Other groups are unaffected.

There is no account deletion or student self-service editing in this increment.
See [the student-management lesson](docs/student-management.md) for the code and tests.

## Lesson management

Choose **Manage lessons** on a group card, then open a lesson to see recorded
attendees and check-in times. History is newest first, with 25 lessons per page.
**Close check-in** stops new submissions without changing attendance or balances.
**Reopen check-in for this lesson** creates a new code window for the same class;
it preserves the original date and prevents duplicate attendance charges.
Close any other open lesson in that group before reopening an earlier one.

New lessons save their starting roster. Students without recorded attendance show
as **Absent**, and become **Present** on check-in. Absence does not deduct lessons.
Older lessons use the current roster with an explicit historical-data warning. All times use Asia/Tashkent (UTC+05:00). Refresh to see new check-ins.
See [the lesson-management guide](docs/lesson-management.md) for the flow,
relationships, transactions and code explanation.

## Attendance corrections

Open **Manage lessons**, choose a lesson, then **Mark present / review history**
or **Review / correct attendance** beside the student. Review the balance preview,
enter a reason and confirm. Marking present uses one lesson; reversing restores one;
restoring a reversed entry uses one again. This also works when the balance is owed.
Original records and every teacher correction remain in history. Reasons are teacher-only.
A reversed entry can only be restored by a teacher, not by resubmitting a code.
Saved lesson-roster members remain eligible after deactivation. Existing attendees
remain correctable; older lessons without snapshots use active membership as a
fallback and display a warning. Future lessons and other-group memberships are rejected.

`app/attendance_corrections.py` handles previews and atomic audited writes;
`app/attendance_state.py` provides the shared effective-attendance rule used by
balances, dashboards and history. `tests/test_attendance_corrections.py` and
`tests/test_classroom_login.py` cover the Sprint 1 behavior.

## Balance corrections

Use **Change balance** beside a student, then expand **Change remaining lesson
count** in the relevant group. Enter the desired balance and a reason. Positive
means available, negative means owed, and zero clears both. Corrections preserve
attendance and purchases, appear in both dashboards, and work with later renewals.
The management page keeps a correction history. Stale forms are rejected if the
balance changed while the page was open.

See [teacher conveniences](docs/teacher-convenience.md) for examples, absence
rules and the three new tables created automatically on startup.

## Concepts introduced

A **transaction** saves related records together. Enrollment creates a membership
and package in one transaction. `flush()` obtains the membership ID without
committing it; `commit()` saves both records. If package creation fails, `rollback()`
undoes the pending membership. A test deliberately forces that failure.

A **query** derives balances from history: `net balance = total package lessons + corrections -
effective (non-reversed) attendance`, within one enrollment. Positive credit is available; negative
credit is shown as lessons owed. Earlier excess attendance uses credit from later
renewals without moving historical attendance records. No separate mutable counter
can fall out of sync with the history.

## Attendance security

Check-in allows ten attempts per student in a rolling minute, shared across
server processes and preserved through restarts and new logins. Failed attempts
count. Invalid and unauthorized codes return the same message, and sessions are
rechecked inside the attendance write transaction. Startup adds a small attempt
window table. See [attendance security review](docs/attendance-security.md).

## Security corrections

Signed cookies detect editing, but a copied cookie previously remained usable
after logout. The browser now carries a random session token. A new SQLite
`login_sessions` table stores its fingerprint, user, eight-hour expiry and a
fingerprint of the password hash. Logout revokes the row. User deletion removes
login sessions, so an old cookie cannot follow a reused user ID. Changing the
password hash invalidates prior sessions. Attendance history keeps its existing
no-cascade protections.

Passwords still use salted Argon2. SHA-256 fingerprints are used only for already
random session tokens and comparison against password hashes, not for passwords.
Startup adds the session table without altering the six existing business tables.

Login permits ten attempts per normalized username and 120 per connection address
in a rolling minute. These SQLite limits survive restarts and are shared by workers.
All attempts count; unknown usernames follow the same rules. Expired entries are
pruned and storage is capped at 8,192 rows, failing closed when full. Incoming bodies are capped at 16 KiB before
parsing, including streamed bodies. HTML responses restrict embedding and form
submissions and are not cached. HTTPS deployment remains outside this local stage.

## Important files

| File | Purpose |
| --- | --- |
| `app/main.py` | App setup, login/logout, code-duration configuration and route registration |
| `app/teacher.py` | Teacher-only routes, renewal preview/confirmation, enrollment and lessons |
| `app/student.py` | Student-only dashboard and check-in form handling |
| `app/student_management.py` | Teacher student search, profile updates, password resets and enrollment status |
| `app/lesson_management.py` | Group lesson history, attendance details and close/reopen check-in |
| `app/attendance.py` | Serialized lesson creation/check-in and student record queries |
| `app/packages.py` | Package accounting, carried debt, renewal transaction and stale-form checks |
| `app/web.py` | Shared template rendering and database connections per request |
| `app/models.py` | Business tables, balance corrections, saved lesson rosters and login sessions |
| `app/database.py` | SQLite setup, foreign keys, table creation and shared write transaction |
| `app/security.py` | Password checks, sessions, CSRF tokens and login limiter |
| `app/middleware.py` | Request body limit before parsing |
| `app/create_user.py` | Reusable account creation and local teacher-account command |
| `app/templates/teacher.html` | Forms, errors and group rosters |
| `app/templates/renew_package.html` | Teacher renewal preview and confirmation |
| `app/templates/lesson_balance.html` | Shared available, advance and owed counters |
| `app/templates/students.html`, `manage_student.html` | Student directory and management forms |
| `app/templates/lessons.html`, `lesson.html` | Lesson history and detail forms |
| `app/templates/base.html` | Shared layout and logout form |
| `app/static/style.css` | Responsive forms and roster styling |
| `tests/test_teacher.py` | Teacher flow, access control, rollback and balance tests |
| `tests/test_auth.py` | Login, sessions, revocation and request-limit tests |
| `tests/test_database.py` | Database-integrity tests |
| `tests/test_attendance.py` | Attendance rules, privacy, expiry, collisions and simultaneous requests |
| `tests/test_packages.py` | Early/late renewal, debt settlement, history and concurrent requests |
| `tests/test_student_management.py` | Management permissions, validation, password revocation and preserved records |
| `tests/test_teacher_convenience.py` | Balance corrections, absence snapshots and regression checks |
| `tests/test_lesson_management.py` | Lesson access, close/reopen, pagination and simultaneous requests |

## Verify and learn

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

All 122 tests use isolated databases, not real student data. Read the
[security review](docs/security-review.md) for reproduced issues and remaining
limits, and [dependency results](docs/dependency-audit.json) for the advisory check.

Exercise: predict the balance after 14 attended lessons, one 12-lesson package,
and then a renewal. Explain why changing a stored remaining counter would be less
reliable than calculating from the package and attendance records.

Earlier explanations are archived in [Stage 1](docs/stage-1.md),
[Stage 2](docs/stage-2.md) and [Stage 3](docs/stage-3.md). Those describe earlier
milestones; this README describes the current app.

## School-local times (SF-03)

Lesson, attendance and correction timestamps use the shared `school_time` Jinja
filter from `app/school_time.py`. Renewal previews include recorded package dates.
Naive SQLite timestamps are explicitly interpreted as UTC, then converted using
Asia/Tashkent IANA rules. Every formatted time includes the timezone and offset.
Code expiry, ordering and saved form versions remain UTC-based. No schema or data
migration is needed. Install requirements before restarting: tzdata provides the
IANA database on Windows. Midnight rollover and exact expiry are regression-tested.

## Brand motion

Homepage sections animate once as they enter view (480 ms). Score tickets and
links have restrained hover feedback; anchor navigation uses native smooth scrolling.
app/static/motion.js is a small local progressive enhancement loaded only on the
homepage. Content stays readable without JavaScript. Reduced-motion preferences
disable effects, including cancellation when the preference changes. No libraries,
looping effects, timers or changes to attendance forms.

Future work: [next-stage roadmap](docs/next-stages.md), with proposed sprint goals,
review scenarios, dependencies and decisions required before selection.
