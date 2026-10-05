# Portfolio demo: local preparation

Scope: SF-13 demo preparation, separate from the postponed course launch.

Run from the repository using Python 3.14 and the installed project dependencies:

```powershell
.venv\Scripts\python.exe scripts/portfolio_demo.py
```

Open http://127.0.0.1:8767/login. The page displays intentionally public demo
credentials. Use demo-teacher or demo-student with Explore-SAT-Factory!.
These credentials must never be reused for real accounts.

The demo contains six fictional students, one group, twelve-lesson purchases,
a finished lesson (four present, two absent), three original sample questions
in separate categories, and a three-question assignment. No imported PDF content
or real student accounts are copied. Existing public homepage/results content is
unchanged. The banner identifies the shared sandbox on every application page.

Suggested walkthrough:
1. Log in as the student, inspect the 11 remaining lessons and assignment.
2. Try a question, its feedback and the assignment flow; set a target score.
3. Log out, enter as the teacher, inspect the completed lesson and start a new one.
4. Share its code with another browser signed in as the demo student.
5. Inspect attendance and try a renewal or correction.
6. Try a password reset or enrollment deactivation: demo access is protected.

All writes go to a generated temporary directory. There is no configurable
existing database path. The import guard blocks the normal database engine and
redirects the session-secret path for the full lifetime. A separate cookie avoids
replacing a course login on the same hostname. Restarting generates a fresh database
and secret; previous sessions no longer work. Ctrl+C performs normal cleanup.
A forced process termination may leave a temporary directory; it is never reused.

Account profile/password and enrollment-status writes are blocked by a demo-only
middleware. Ordinary application authentication, CSRF and role checks still apply.
Other sandbox edits are shared: this is not a private workspace per visitor.
Do not enter personal data. Restart locally to recover any altered demonstration.

## Not yet a public-hosting entry point

This launcher binds only to loopback and uses local HTTP. Do not expose it through
a tunnel or change its bind address as a shortcut to deployment. The next chunk
must prepare HTTPS/proxy/host configuration, health checks, bounded public writes
and upload behavior, shared-login rate limits, resource caps and reset strategy.
Review free-host constraints and decide how simultaneous visitors share activity
before publication. No Render resources, billing, external storage or schedule
have been created. No public uptime or real-phone acceptance is claimed.

Verification uses `scripts/verify.py --pattern test_portfolio_demo.py`.
Tests cover seeding/foreign keys, student and teacher access, role denial,
protected mutations, CSRF, target writes, refusing reseeding existing data, and
fresh storage/session invalidation on restart.
