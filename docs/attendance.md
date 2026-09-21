# Attendance: one working increment

The teacher starts a group lesson and shares a temporary code. An authenticated,
enrolled student can submit it once, consuming one lesson from the oldest package
with capacity. Both sides can inspect balances; teachers can open an individual
student's history. Existing history is never reset or deleted.

## Flow

```text
Teacher POST /teacher/groups/{id}/lessons
    -> check teacher permission and CSRF token
    -> reserve SQLite write transaction
    -> reuse an open lesson, or create a new lesson with a unique active code
    -> commit -> redirect to teacher page

Student POST /student/check-in
    -> identify student from session (never from a submitted user ID)
    -> check student role, CSRF token and attempt limit
    -> reserve SQLite write transaction
    -> validate code + expiry + active group enrollment
    -> reject duplicate attendance
    -> find oldest package with remaining lessons
    -> insert attendance -> commit -> redirect to updated dashboard
```

## Why the transaction begins before reading the balance

Two browser requests can arrive together. If each reads “one lesson remaining”
before either writes, both could spend it. SQLite's `BEGIN IMMEDIATE` reserves the
single writer slot before the checks. The next request waits, then reads the
updated attendance count. A unique attendance constraint separately stops the same
enrollment from checking into the same lesson twice.

This is **concurrency control**: coordinating simultaneous operations so they
preserve the rules. A fresh SQLAlchemy Session owns this short write transaction;
the route's read-only session is not reused for it. A busy database returns a retry
message rather than silently losing an attendance. This approach is appropriate
for our small SQLite app; PostgreSQL would require a different locking strategy.

## Code behavior

- Codes are random, six ASCII digits, including possible leading zeroes. The form
  is text with a numeric keyboard hint, so a code like `000123` retains its zeroes.
- Active codes cannot collide through the lesson-creation service: collision
  checks and insertion happen while the database writer is reserved.
- A code is invalid at or after its expiry. Expiry is checked on the server after
  obtaining the transaction; refreshing a page cannot extend it.
- Default lifetime is 15 minutes. Set a value from 1 to 60 before starting:

```powershell
$env:ATTENDANCE_CODE_MINUTES = "10"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --no-proxy-headers
```

- Configuration changes affect newly created lessons, not existing expiry times.
- A second start while the group has an open lesson returns that same lesson,
  even if requests arrive together. After expiry, **Start a new lesson** creates a
  separate class. Reopening an old class or extending its code is not implemented;
  do not use a new lesson to extend the previous class's attendance window.
- Students get ten submission attempts per minute per account, shared across
  sessions in this server process. A code identifies a lesson, not the student.
- Codes are shown only on teacher pages, not student dashboards/history or URLs.
  There is no automatic refresh or live countdown; refresh the teacher page to
  update its code status and balances.

## Balances and history

`check_in()` checks the student's active membership in the lesson's group, rejects
duplicate attendance, then chooses the oldest non-exhausted package in that
membership. It counts attendance instead of maintaining a separate counter.
An exhausted package does not block a newer available package. Renewal creation
in the UI is a later increment; tests construct renewals to verify consumption.

`student_records()` filters every query by the authenticated student's ID. A query
parameter or form field cannot select somebody else's records. The teacher history
route uses the same reader after a teacher-role check. All teachers remain admins
of one business, as in the previous stage.

Dates are shown in UTC, matching the database convention. The records page lists
each package separately and preserves its attendance when another package exists.

## Files and verification

- `app/attendance.py`: business rules, writer transaction and record queries.
- `app/student.py`: authenticated student routes and form feedback.
- `app/teacher.py`: starts lessons and opens student history.
- `app/main.py`: registers the new student router and configures duration.
- `app/security.py`: the existing limiter is now named `AttemptLimiter` and is
  reused with a separate account-keyed instance for code attempts.
- `student.html` and `teacher.html`: check-in and lesson controls.
- `package_summary.html` and `attendance_history.html`: shared display fragments.
- `student_history.html`: teacher's view of one student's records.
- `tests/test_attendance.py`: 17 new tests, including actual parallel database
  connections competing for the last lesson and duplicate lesson starts.

Run all 57 tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The interruption check also verified the real database using read-only integrity
and foreign-key checks: integrity was OK and there were zero foreign-key violations.
All automated write tests use temporary databases.

Exercises: explain why `expires_at > now` rejects the exact expiry boundary.
Then explain why the final-lesson concurrency test uses two different lesson IDs.

This is still a local development app. Deployment settings and distributed abuse
protection remain future work; this stage does not claim to prevent code sharing.
Reference: [SQLite transaction behavior](https://www.sqlite.org/lang_transaction.html).
