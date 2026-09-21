# Student Attendance Tracker — Teacher workspace

The teacher page supports creating groups, creating student accounts, enrolling
students with a 12-lesson package, and viewing group rosters and package balances.
Lesson creation, check-in and package renewal remain future stages.

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
forwarded headers. Existing accounts are preserved. This update requires you to
log in again because the session format changed. No default accounts are added.

## Teacher workflow

1. Create a group, such as SAT Advanced.
2. Create a student account; passwords require 12–128 characters. Share the account
   details privately yourself. The form can only create student accounts.
3. Select the student and group, then enroll with 12 lessons.
4. The roster displays `0 / 12 lessons used` and `12 remaining`.
5. Try the same enrollment again: an error appears and no extra package is added.

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
| `app/main.py` | App setup, login/logout, student page and error handling |
| `app/teacher.py` | Teacher-only routes, enrollment transaction and balance queries |
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

## Verify and learn

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

All 40 tests use isolated databases, not real student data. Read the
[security review](docs/security-review.md) for reproduced issues and remaining
limits, and [dependency results](docs/dependency-audit.json) for the advisory check.

Exercise: find `flush()` and `commit()` in `enroll_student()`. Explain why saving
membership before creating its package could leave incomplete data.

Earlier explanations are archived in [Stage 1](docs/stage-1.md),
[Stage 2](docs/stage-2.md) and [Stage 3](docs/stage-3.md). Those describe earlier
milestones; this README describes the current app.
