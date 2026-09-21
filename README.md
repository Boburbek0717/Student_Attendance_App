# Student Attendance Tracker — Stage 1

Based on the uploaded `Pasted text.txt` specification. This stage delivers one
server-rendered page, a working SQLite connection through SQLAlchemy, and Git.
There are no accounts, database tables, attendance rules, or check-in forms yet.

## 1. Minimal architecture

```text
Browser -- GET / --> Uvicorn --> FastAPI home route
                                  |
                                  v
                             Jinja2 + index.html
                                  |
Browser <-- HTML response --------+
   |
   +-- GET /static/style.css --> FastAPI static files

At server startup: FastAPI --> SQLAlchemy engine --> attendance.db (SQLite)
```

The browser asks for a page using an HTTP request. A **route** connects a URL and
HTTP method to a Python function. Without a route for `/`, that address would
return “not found.” `GET` reads a resource; later, `POST` will submit changes.

Uvicorn is the server that listens for requests; FastAPI decides how to respond.
Jinja2 fills placeholders such as `{{ title }}` before sending HTML. The browser
receives ordinary HTML, not Python or template instructions. CSS controls its
appearance. This avoids adding a separate JavaScript application for a simple UI.

SQLite stores data in a local file without a separate database server. SQLAlchemy
manages connections now; its ORM (mapping Python objects to database rows) will
help us work with models later. Raw SQL is another option, but SQLAlchemy gives
us one consistent place to define those models as this app grows.

## 2. User flows — planned, not implemented

```text
Teacher: create group -> create student -> enroll student + 12-lesson package
         -> start group lesson -> share temporary code
         -> inspect student balances and attendance history

Student: log in -> enter code -> submit Check In
         -> see confirmation and used / remaining lessons
         -> or see a clear validation error
```

When a student eventually presses **Check In**, the browser will send a `POST`
with the code and the student's session cookie. The backend will identify the
student, check the code and expiry, group membership, duplicate attendance, and
an available package. A database transaction (a group of changes that succeeds
or fails together) will record one attendance against that package. The server
will then render or redirect to the updated balance. Invalid requests will make
no attendance change. The code identifies a lesson; it does not prove identity.
Teacher and student permissions and pages will be separate in later stages.

## 3. Database relationships — design only

```text
User (student) 1 ---- many Enrollment many ---- 1 Group
                              |                    |
                              1                    1
                              |                    |
                             many                 many
                         LessonPackage           Lesson
                              |                    |
                              1                    1
                              |                    |
                             many                 many
                              +---- Attendance ----+
```

| Entity | Planned key fields and purpose |
| --- | --- |
| User | id, login identifier, password hash, role (teacher/student); an account |
| Group | id, name; the teaching group |
| Enrollment | id, student_id, group_id, active; a student's membership |
| LessonPackage | id, enrollment_id, lesson_limit (default 12), purchased_at; a purchased allowance |
| Lesson | id, group_id, started_at, temporary code, code_expires_at; one group session |
| Attendance | id, lesson_id, enrollment_id, package_id, checked_in_at; one consumed lesson |

A primary key is a row's unique ID. A foreign key points to a row in another
table: for example, `Lesson.group_id` identifies its group. These links let us
connect records without repeating names and prevent references to missing rows.
Enrollment joins students and groups because each side can have many of the other.

**Package choice:** a package attached directly to a student would allow a shared
balance across groups, but could accidentally spend a course's lessons elsewhere.
An enrollment-owned package keeps each course's balance separate. We choose the
latter for the multiple-course possibility in the specification. The tradeoff is
that transfers between groups would need an explicit policy later.

Planned integrity rules for the model stage:

- Unique `(student_id, group_id)` enrollment; reuse its identity if reactivated.
- Unique `(enrollment_id, lesson_id)` attendance. Together with unique enrollment,
  this prevents the same student checking into the same lesson twice, even when
  two requests arrive together.
- Attendance's package must belong to its enrollment (use a composite foreign key
  when implementing models). Its lesson must belong to the enrollment's group;
  validate this during check-in. Enable SQLite foreign-key enforcement then.
- Positive package size; use a transaction to prevent simultaneous requests from
  spending the final available lesson twice.
- Keep old packages and attendance. Do not cascade-delete historical records;
  deactivate memberships instead of removing their history.
- For V1, consume the oldest non-exhausted package in the enrollment. Each
  attendance points to exactly the package it consumed. Renewals create a new row.

`used = COUNT(attendance records for this package)`

`remaining = lesson_limit - used`

Do not store a separate remaining balance or used counter. For Madina, 8 records
against a package of 12 means 4 remain. A new package does not reset those records.
There is intentionally no models file or empty ORM scaffolding in Stage 1.

## 4. Files and important code

```text
attendance-tracker/
  .gitignore
  README.md
  requirements.txt
  app/
    __init__.py
    main.py
    database.py
    templates/index.html
    static/style.css
```

| File | What it does and why it exists |
| --- | --- |
| `app/__init__.py` | Marks `app` as a Python package so imports are straightforward; intentionally empty. |
| `app/main.py` | Creates FastAPI, runs the startup database check, mounts CSS, and defines `GET /`. `context` passes the title to Jinja2. |
| `app/database.py` | Locates the database relative to this file, creates a SQLAlchemy engine, and checks connectivity with `SELECT 1`. An engine is the connection manager, not the database itself. |
| `app/templates/index.html` | The page structure. Jinja2 inserts the title and generates the CSS URL. |
| `app/static/style.css` | Small responsive stylesheet; served as a separate browser request. |
| `requirements.txt` | Exact installed dependency versions, including dependencies of our four chosen packages, so setup can be repeated. |
| `.gitignore` | Keeps environments, Python caches, local databases, and secret environment files out of new Git commits. |
| `README.md` | This design, run guide, and learning notes. |

`lifespan` runs setup before serving requests. Code before `yield` checks SQLite;
code after it releases engine resources on shutdown. If the database cannot open,
startup fails instead of pretending everything worked. `with engine.connect()`
returns the connection when the check finishes. `SELECT 1` checks connectivity;
it does not create tables or demonstrate storing student data.

`check_same_thread=False` allows SQLite connections to be used by FastAPI's worker
threads; it does not remove the need for transactions or concurrency checks later.
The home page does not query the database. File paths use `__file__`, so templates,
CSS, and the database are located consistently.

Generated local items are `.venv/` (isolated Python and packages), `attendance.db`
(created on startup; contains no application tables yet), and `.git/` (Git history).
The database file may be empty at this stage: opening it and running `SELECT 1`
does not create a schema. All synced source material remains outside this project.

## 5. Run on Windows (PowerShell)

Open a terminal in this `attendance-tracker` folder. The environment is already
installed on this computer; to reproduce setup on another machine with Python 3.14:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Start the app:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open <http://127.0.0.1:8000/>. Keep the terminal open; press **Ctrl+C** to stop.
`app.main:app` means “load the `app` object from `app/main.py`.” `--reload` restarts
the development server when Python files change. This is a local development setup.
Calling the environment's Python directly avoids PowerShell activation issues and
the other Python installation on this computer that has no pip.

If port 8000 is occupied, add `--port 8001` and open that port instead.

## 6. Check this increment

With the server running, check:

1. `/` displays “Student Attendance Tracker” in a styled panel.
2. `/static/style.css` returns the stylesheet.
3. `/missing` returns 404, because no route handles it.
4. `attendance.db` exists in the project root after successful startup.

No business-rule tests are needed yet. In the model and attendance stages we will
introduce tests for duplicates, expired codes, wrong groups, exhausted packages,
and calculated balances as those rules are implemented.

## 7. A small Git workflow

Git saves named snapshots of source files so changes can be reviewed and recovered.
The initial milestone is committed as `initial FastAPI project setup`.

After a small change, inspect it, select files, and save a meaningful snapshot:

```powershell
git status
git diff
git add app/templates/index.html
git commit -m "update welcome message"
git log --oneline
```

`git add` selects content for the next snapshot; `git commit` saves it locally.
Git is not hosting or a database backup. `.gitignore` prevents accidental tracking
of listed files but does not untrack files already committed.

## 8. Two small exercises before Stage 2

1. Predict where the page changes if you edit `context["title"]` in `main.py`.
   Then change the title, refresh, and inspect both the heading and browser tab.
2. Change the background color in `style.css`, refresh, and explain why the browser
   requests that file separately from the HTML.

Stop here. The next increment can introduce models and database constraints after
you can explain how a request reaches the template.

Implementation references: [FastAPI templates](https://fastapi.tiangolo.com/advanced/templates/)
and [SQLAlchemy SQLite](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html).
