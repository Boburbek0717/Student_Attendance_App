# Student Attendance Tracker — Stage 2

Stage 2 adds the six database models planned from the uploaded specification,
creates their tables at startup, and tests database constraints. The page stays
simple. Account creation, authentication, enrollment screens, lesson creation,
and attendance check-in are future increments.

The original architecture and user flows are preserved in [Stage 1](docs/stage-1.md).
That document describes the earlier milestone; this README describes the current app.

## Run

From this folder in PowerShell (Python 3.14):

```powershell
# Only needed on a new checkout:
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# Start the app:
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/ and stop with Ctrl+C. If the old Stage 1 server is
still running, stop it first, or add `--port 8001` and open that port.
Startup creates missing tables in `attendance.db`; it does not add sample users.
The Python environment and database stay out of Git.

## The new concept: models

We need a consistent shape for each kind of stored information. A **model** is a
Python class mapped to a database table by SQLAlchemy's ORM. One object represents
one row. Without this shared definition, every query would have to repeat our
assumptions about columns and their types.

```text
User --< Enrollment >-- Group --< Lesson
             |
             +--< LessonPackage --< Attendance >-- Lesson
             +--------------------< Attendance
```

`--<` means one-to-many. Each enrollment belongs to one student and one group.
Each package belongs to an enrollment, keeping course balances separate. Each
attendance points to a lesson, enrollment, and the specific package consumed.

| Table | What one row means |
| --- | --- |
| users | An account with username, display name, password hash and role |
| groups | A teaching group |
| enrollments | A student's membership in a group, with an active flag |
| lesson_packages | One purchase, normally 12 lessons, with its purchase time |
| lessons | One group lesson; optional temporary-code fields reserved for later |
| attendance | One enrollment attending one lesson using one package |

The password column is for a hash, never a plaintext password. No password
creation or verification is implemented. Tests use obvious placeholders only in
throwaway databases. The models cannot determine whether a supplied string is
actually a secure hash; the future account-creation code must ensure that.

## Read the code in this order

1. `app/database.py`: `Base` collects table definitions. `make_engine()` creates
   a connection manager and enables SQLite foreign keys on **every connection**.
   SQLite needs this explicitly; otherwise declared links would not be enforced.
   `initialize_database()` imports the models then creates missing tables.
2. `app/models.py`: six model classes. `Mapped[int]` describes a Python attribute;
   `mapped_column(primary_key=True)` makes its unique row ID. `ForeignKey` links
   to another table. Non-optional mapped fields are required (`NOT NULL`).
   Defaults such as 12 are supplied by SQLAlchemy when inserting a row.
3. `app/main.py`: startup now calls `initialize_database()` instead of `SELECT 1`.
   The home route and Jinja2 rendering still work as in Stage 1.
4. `tests/test_database.py`: writes valid and invalid records into an in-memory
   SQLite database and checks the outcomes. It never writes to `attendance.db`.

Foreign keys express the relationships at this stage. We haven't added Python
`relationship()` navigation attributes because no screen needs them yet.

## Constraints: rules the database enforces

- Usernames must be unique; roles must be teacher or student.
- A student can have only one enrollment per group. Reactivate that membership
  instead of creating another if the student returns.
- Each enrollment can have only one attendance per lesson, even if someone tries
  to use a different package for the second record.
- A package's lesson allowance must be positive.
- The attendance's package must belong to its enrollment. This uses a **composite
  foreign key**: SQLite checks the pair `(package_id, enrollment_id)` together.
  The matching unique pair in `lesson_packages` is required for that reference.
- Referenced parents cannot be deleted; no cascade deletion removes history.
- A lesson's code and expiry must either both be absent or both be present, with
  expiry after lesson start. Code generation and collision handling come later.

A foreign key prevents a reference to a missing row. A unique constraint prevents
repeated combinations. A check constraint validates values in a row. These rules
continue to work if a future route accidentally skips its own validation.

Not every rule is in these tables: student-only enrollment, active membership,
matching lesson/enrollment groups, unexpired codes, and remaining package capacity
must be checked by future application code. Concurrent spending of the final
lesson will also need transaction handling and tests. This schema alone is not a
complete or usable check-in system. SQLite does not enforce `String(100)` as a
length limit; future forms must validate length and normalize usernames.

All stored timestamps represent UTC. SQLite returns naive datetimes, so
`utc_now()` deliberately stores UTC without a timezone marker. Future expiry
comparisons must follow the same convention.

## History and balances

A renewal creates a **new** LessonPackage row. Existing attendance continues to
reference the old package. No used or remaining counters are stored:

```text
used = count of attendance rows for this package
remaining = lesson_limit - used
```

The tests demonstrate 1 attendance out of 12 leaving 11, while a new package has
zero attendance. This is a query demonstration, not a balance endpoint. The later
check-in transaction must prevent consumption beyond the allowance.

`create_all()` creates missing tables; it does **not** update existing table
columns or constraints. It is sufficient to move from Stage 1's empty file to this
first schema. Later schema changes will need migrations; do not delete real data
to make a changed model take effect.

## Verify

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Nine tests cover foreign keys, duplicate membership, duplicate attendance across
packages, incorrect package ownership, invalid package sizes, renewal history,
protected deletion, role/username constraints, and incomplete code windows.
`Session` is SQLAlchemy's unit of database work; `commit()` saves it and
`rollback()` clears a failed transaction so work can continue. Tests intentionally
attempt invalid writes and expect `IntegrityError`, the database rejection.

For a read-only look at the local tables after startup:

```powershell
.\.venv\Scripts\python.exe -c "from sqlalchemy import inspect; from app.database import engine; print(inspect(engine).get_table_names())"
```

Refresh the home page to check HTML and CSS still load. No student data appears yet.

## Files

| File | Purpose |
| --- | --- |
| `app/__init__.py` | Marks the app as a Python package |
| `app/database.py` | Base, SQLite engine, foreign-key setup and schema creation |
| `app/models.py` | Six tables and their constraints |
| `app/main.py` | Application startup, home route and static-file serving |
| `app/templates/index.html` | Jinja2-rendered welcome page |
| `app/static/style.css` | Basic responsive styling |
| `tests/test_database.py` | Isolated database tests using Python's built-in unittest |
| `requirements.txt` | Pinned packages; no new dependencies in Stage 2 |
| `.gitignore` | Excludes local databases, secrets, environments and caches |
| `docs/stage-1.md` | Earlier design and beginner HTTP/template explanations |
| `README.md` | Current stage, setup, concepts and verification |

## Your turn

1. Before running it, predict what happens if the same enrollment attends the same
   lesson using a newly purchased package. Find the test that proves your answer.
2. In the renewal test, add an assertion that the new package has 12 remaining
   lessons. Calculate it from its allowance and attendance count.

Use `git diff` to review your exercise change before committing it. This milestone
is saved as `add database models and integrity tests`. A sensible next increment
is safe account creation and authentication, after these relationships make sense.

Reference: [SQLAlchemy SQLite foreign keys](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#foreign-key-support).
