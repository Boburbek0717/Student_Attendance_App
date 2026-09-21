# Student Attendance Tracker — Attendance check-in

The teacher page supports creating groups, creating student accounts, enrolling
students with a 12-lesson package, starting group lessons, and viewing balances
and attendance history. Students can check in with a temporary code. Package
renewal remains a future stage.

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

Open http://127.0.0.1:8000/login. Stop an older server if the port is occupied.
The proxy flag makes local login limiting use the connection address rather than
forwarded headers. Existing accounts are preserved. No default accounts are added.
This attendance stage needs no database-schema changes or new dependencies.

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
   of the old one.
7. Log in as the student in a separate browser/private window, or log out of the
   teacher account first. Enter the code on the student page and click **Check in**.
8. The student sees `1 / 12 lessons used`, `11 remaining`, and a history entry.
   Refresh the teacher page to see the updated balance. Its **Attendance history**
   link opens the individual student's history.

Repeat the check-in: it must show an error without using another lesson. Codes are
sent through POST forms, never URLs. All displayed lesson times are labeled UTC.
See [the attendance lesson](docs/attendance.md) for the flow, configuration and
concurrency explanation.

Group names may repeat; IDs distinguish them. Usernames are unique and lowercased.
Inactive enrollments are shown but cannot be re-created. Reactivation and renewal
will have explicit actions later. All teachers administer the same business.

## Concepts introduced

A **transaction** saves related records together. Enrollment creates a membership
and package in one transaction. `flush()` obtains the membership ID without
committing it; `commit()` saves both records. If package creation fails, `rollback()`
undoes the pending membership. A test deliberately forces that failure.

A **query** derives balances from history. The page counts attendance for each
package, then calculates `remaining = lesson_limit - count`. An outer join keeps
packages with zero attendance visible. Each package is listed separately so old
and new purchases are not merged into a misleading balance.

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

Login permits ten attempts per connection address per minute. This local,
per-process limit resets on restart. Incoming bodies are capped at 16 KiB before
parsing, including streamed bodies. HTML responses restrict embedding and form
submissions and are not cached. HTTPS deployment remains outside this local stage.

## Important files

| File | Purpose |
| --- | --- |
| `app/main.py` | App setup, login/logout, code-duration configuration and route registration |
| `app/teacher.py` | Teacher-only routes, enrollment, starting lessons and student history |
| `app/student.py` | Student-only dashboard and check-in form handling |
| `app/attendance.py` | Serialized lesson creation/check-in and student record queries |
| `app/web.py` | Shared template rendering and database connections per request |
| `app/models.py` | Six business tables plus revocable login sessions |
| `app/database.py` | SQLite setup, foreign keys and table creation |
| `app/security.py` | Password checks, sessions, CSRF tokens and login limiter |
| `app/middleware.py` | Request body limit before parsing |
| `app/create_user.py` | Reusable account creation and local teacher-account command |
| `app/templates/teacher.html` | Forms, errors and group rosters |
| `app/templates/base.html` | Shared layout and logout form |
| `app/static/style.css` | Responsive forms and roster styling |
| `tests/test_teacher.py` | Teacher flow, access control, rollback and balance tests |
| `tests/test_auth.py` | Login, sessions, revocation and request-limit tests |
| `tests/test_database.py` | Database-integrity tests |
| `tests/test_attendance.py` | Attendance rules, privacy, expiry, collisions and simultaneous requests |

## Verify and learn

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

All 60 tests use isolated databases, not real student data. Read the
[security review](docs/security-review.md) for reproduced issues and remaining
limits, and [dependency results](docs/dependency-audit.json) for the advisory check.

Exercise: predict the result of two check-ins arriving while only one lesson
remains. Find the test that proves this and explain why a duplicate-attendance
constraint alone would not protect two different lessons.

Earlier explanations are archived in [Stage 1](docs/stage-1.md),
[Stage 2](docs/stage-2.md) and [Stage 3](docs/stage-3.md). Those describe earlier
milestones; this README describes the current app.
