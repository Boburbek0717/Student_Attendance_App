# Student Attendance Tracker — Stage 3

This increment adds local account creation, login, logout, and separate protected
teacher/student welcome pages. It uses the six existing tables without changing
or deleting their data. Group management and attendance check-in come later.

Earlier lessons: [Stage 1: requests and templates](docs/stage-1.md) and
[Stage 2: tables and constraints](docs/stage-2.md).

## Run and try it

In PowerShell, open this `attendance-tracker` folder. On this computer the packages
are installed already. To install the updated dependencies on another checkout:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Create your teacher account:

```powershell
.\.venv\Scripts\python.exe -m app.create_user teacher --name "Teacher" --role teacher
```

Choose and repeat a password at the hidden prompt. Use 12–128 characters. Passwords
are never passed as command arguments, saved in source files, or printed back.
Run this command in an interactive terminal so the password can remain hidden.
There is no default password and no pre-created account.

Create a student account to try both roles:

```powershell
.\.venv\Scripts\python.exe -m app.create_user madina --name "Madina"
```

The default role is student. Usernames use 3–100 ASCII letters, digits, dots,
underscores or hyphens. They are trimmed and lowercased: `MADINA` and `madina` refer
to the same account. Display names retain their case. Passwords are not trimmed
or lowercased. An existing username is rejected, never overwritten.

Start the app:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/login. Stop an older server first if it occupies that
port, or add `--port 8001` and open the new port. Press Ctrl+C to stop.

1. Log in as teacher and see the teacher welcome page.
2. Log out, then log in as Madina and see the student welcome page.
3. While logged in as Madina, open `/teacher`: it returns a permission error.
4. Log out and try `/student`: it sends you back to login.
5. Try a wrong password: the form shows an error and keeps the password field empty.

We use a local account command in this stage so the teacher can create the first
account without a public registration route. Anyone who can run this command with
access to your local database can create a teacher. Student creation in the teacher
interface will be a later increment; students cannot choose or change their role.

## What happens when you log in

```text
Browser -- GET /login --> server renders form + hidden CSRF token
   |
   +-- POST /login (username, password, token; session cookie)
                  |
                  v
           Check form token
           Look up username in SQLite
           Verify password against Argon2 hash
                  |
          +-------+---------+
          |                 |
        failure           success
          |                 |
     Show same error    Replace session contents
     for unknown user   Store user ID + new form token
     or bad password    Sign session cookie
                            |
                        303 redirect
                            |
Browser -- GET /student or /teacher --> look up user + check current role
                            |
                       Render welcome page
```

`GET` requests read pages. `POST` submits an action, which is why login and logout
use forms. A **303 redirect** tells the browser to follow a successful POST with a
GET, so refreshing the welcome page doesn't submit the login again.

## Three concepts to learn now

**Password hashing:** we need to check a password without storing the password
itself. Argon2 produces a salted, deliberately expensive hash. `pwdlib` handles
hashing and verification; two users with the same password get different hashes.
The database stores only the hash. This reduces the damage of a database leak;
it does not make weak passwords impossible to guess. We use the established
library rather than inventing a password algorithm.

**Sessions:** after login, the browser needs a way to identify the same user on
later requests. A cookie carries a small signed session containing only a user ID
and form token. The signature detects edits. Signed does not mean encrypted, so
we never put passwords or hashes in it. The local `.session-secret` key is generated
once, reused across restarts, and ignored by Git. Keep it private. This simple
server-rendered app uses Starlette's cookie sessions; JWT access/refresh tokens or
a database-backed session system would add concepts we do not need for this stage.

**Authentication versus authorization:** authentication asks “who are you?”;
authorization asks “may you open this page?” A successful login proves identity.
Every protected request separately reads the role from SQLite. Hiding a teacher
link would not protect the teacher URL, so the server performs the check.

The hidden **CSRF token** ties a submitted form to the browser session that loaded
it. It helps prevent another website from tricking your browser into sending an
action. Both login and logout require it, and login rotates it. A form from an old
session may need to be reloaded. `HttpOnly` blocks JavaScript from reading the
session cookie; `SameSite=Lax` limits when browsers send it across sites. These
complement the form token.

## Read the important files

| File | What changed and why |
| --- | --- |
| `app/create_user.py` | Local command, hidden password confirmation, input validation and account insertion. `create_user()` is also testable without a terminal. |
| `app/security.py` | Username normalization, Argon2 verification, local signing key, current-user lookup and form-token checks. An unknown user still performs a dummy password check to reduce timing differences. |
| `app/main.py` | Login/logout and protected routes. `create_app()` allows tests to provide a separate database and key. `get_db()` opens and closes a SQLAlchemy Session per request. |
| `app/database.py` | Initialization can receive a test engine; the SQLite configuration remains the same. |
| `app/models.py` | Unchanged. The existing User fields are sufficient for this increment. |
| `app/templates/base.html` | Shared page structure and logout form; other templates extend it instead of repeating the same HTML. |
| `app/templates/index.html` | Public welcome page with a login link. |
| `app/templates/login.html` | Labeled form, browser password-manager support, hidden token and error message. |
| `app/templates/teacher.html`, `student.html` | Separate welcome pages with the logged-in user's escaped display name. |
| `app/templates/error.html` | Readable permission, expired-form and missing-page errors. |
| `app/static/style.css` | Simple form styling and visible keyboard focus. |
| `tests/test_auth.py` | Account creation, login, sessions, permissions, logout and invalid-input tests. |
| `tests/test_database.py` | Existing Stage 2 integrity tests, still run unchanged. |
| `requirements.txt` | Adds password hashing, cookie signing, form parsing and the HTTP test client, with pinned dependencies. |
| `.gitignore` | Also excludes the local signing key. |

A **SQLAlchemy Session** is a unit of database work. It is unrelated to the
**browser session** that remembers login. `Depends(get_db)` supplies a database
session to each route and closes it afterward. `commit()` saves an account;
`rollback()` clears a failed write, such as a duplicate username.

`base.html` introduces template inheritance: each child fills its `content` block.
Jinja2 escapes names and error values when displaying them as HTML. Protected
pages use `Cache-Control: no-store` so normal browser caching does not retain them.

## Test this stage

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

The suite has 25 tests: 9 database tests and 16 authentication tests. Authentication
tests use temporary SQLite files and test-only passwords, never your real database.
The HTTP client exercises actual routes, forms, cookies and templates in-process.

The checks include hashing and salting, normalization, validation, duplicate
accounts, both roles, generic login errors, missing/wrong/cross-browser form tokens,
POST-only logout, expired/tampered cookies, current database permissions, deleted
users, HTML escaping, unusable placeholder hashes, and the account command.

New libraries: `pwdlib` with Argon2 hashes passwords, `itsdangerous` signs cookies,
`python-multipart` parses forms, and `httpx2` supports the installed Starlette test
client. Python's built-in `unittest` remains the test runner.

## Exact limits of this increment

The cookie expires eight hours after issue. Logging out clears this browser's
cookie; a previously copied cookie is not individually revoked by this cookie-only
approach. Changing the signing key invalidates all existing cookies. There is no
password-reset or session-management screen yet.

This remains a local HTTP app. Secure-only cookies are disabled so localhost HTTP
works. Login throttling and the HTTPS/deployment configuration are not included in
this increment and must be addressed before opening it to real students online.
No schema migration is needed here; the six Stage 2 tables are unchanged.

## Your turn before the next stage

1. Predict what happens if Madina types `/teacher` directly into the address bar.
   Find the comparison in `role_page()` that explains the result.
2. Change the student welcome sentence in `student.html`, refresh the page, then
   use `git diff` to inspect your change. Explain why the teacher page is unaffected.

The Git milestone is `add account creation and session authentication`. The next
small increment can add teacher group creation and student enrollment with a
12-lesson package.

References: [FastAPI password hashing](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#password-hashing)
and [Starlette session middleware](https://www.starlette.io/middleware/#sessionmiddleware).
We use the password-hashing guidance from the first reference, not its JWT flow.
